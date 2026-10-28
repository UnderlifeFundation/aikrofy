
"""
Script to retroactively log sent emails by analyzing conversation history for:
1. User requests ("enviame un correo", "mandame la info")
2. Assistant confirmations ("correo enviado", "te he enviado")

This is a "Smart Backfill" that infers email events even if the explicit tool output isn't present in message history.
"""
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.conversation import Conversation, Message
from models.customer import Customer
from models.email_log import EmailLog

app = create_app()

def main():
    print("Running SMART retroactive email log backfill...")
    with app.app_context():
        count = 0
        
        # Get all conversations with messages
        conversations = Conversation.query.all()
        
        for conv in conversations:
            # Skip if we already have logs (unless we want to find missed ones, but let's be safe)
            # existing_log = EmailLog.query.filter_by(conversation_id=conv.id).first()
            # if existing_log: continue 
            
            messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
            if not messages: continue

            # Analyze flow
            for i, msg in enumerate(messages):
                if msg.role != 'assistant': continue
                
                content = msg.content.lower()
                
                # Check for explicit tool success first (most reliable)
                if "email sent successfully" in content:
                    # Extract email
                    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.content)
                    to_email = match.group(0) if match else None
                    if not to_email and conv.contact_phone: 
                        # Try to find customer by phone if we can't find email in text
                        cust = Customer.query.filter_by(company_id=conv.company_id, phone=conv.contact_phone).first()
                        if cust: to_email = cust.email
                    
                    if to_email:
                        _create_log(conv, to_email, msg.created_at, "Tool Success: Email Sent")
                        count += 1
                        continue

                # Check for NLP confirmation patterns (Spanish & English)
                confirmation_patterns = [
                    "te he enviado un correo",
                    "correo enviado",
                    "email enviado",
                    "acabo de enviarte",
                    "te envié la información",
                    "sent the email",
                    "email has been sent" 
                ]
                
                if any(p in content for p in confirmation_patterns):
                    # Check if user asked for it recently (within last 3 messages)
                    user_asked = False
                    user_intent_patterns = ["correo", "email", "info", "detalles", "recibo", "invoice"]
                    
                    start_idx = max(0, i - 3)
                    for prev_msg in messages[start_idx:i]:
                        if prev_msg.role == 'user' and any(p in prev_msg.content.lower() for p in user_intent_patterns):
                            user_asked = True
                            break
                    
                    if user_asked:
                        # High confidence this was an email sent event
                        # Try to Resolve Email
                        to_email = None
                        
                        # 1. From regex in assistant text
                        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg.content)
                        if match: to_email = match.group(0)
                        
                        # 2. From Customer record associated with conversation
                        if not to_email and conv.contact_phone:
                             cust = Customer.query.filter_by(company_id=conv.company_id, phone=conv.contact_phone).first()
                             if cust and cust.email: to_email = cust.email
                        
                        # 3. From Customer record searched by name mentioned? (Too risky)
                        
                        if to_email:
                            # Check if duplicate before adding
                            exists = EmailLog.query.filter(
                                EmailLog.conversation_id == conv.id,
                                EmailLog.to_email == to_email,
                                EmailLog.subject == "Backfilled: Contextual Match"
                            ).first()
                            
                            if not exists:
                                _create_log(conv, to_email, msg.created_at, "Backfilled: Contextual Match")
                                count += 1
                                print(f"[MATCH] Conv {conv.id} | Email: {to_email} | Trigger: '{content[:30]}...'")

        db.session.commit()
        print(f"\nSuccessfully backfilled {count} email logs.")

def _create_log(conv, email, date, subject):
    log = EmailLog(
        company_id=conv.company_id,
        conversation_id=conv.id,
        customer_id=None, # Could map this if we had customer obj handy
        to_email=email,
        subject=subject,
        body_summary="Auto-detected from conversation history",
        sent_at=date
    )
    db.session.add(log)
    
    # Also resolve conversation
    try:
        if not conv.is_resolved:
            conv.is_resolved = True
            conv.resolved_at = date
    except:
        pass

if __name__ == '__main__':
    main()
