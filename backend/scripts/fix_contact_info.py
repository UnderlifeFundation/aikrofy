
"""
Script to backfill Conversation contact_email from EmailLog data.
This improves metadata on conversations where email was sent but contact_email wasn't set.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.conversation import Conversation
from models.email_log import EmailLog

app = create_app()

def main():
    print("Running Contact Info Fixer...")
    with app.app_context():
        # Get all email logs
        logs = EmailLog.query.filter(EmailLog.conversation_id != None).all()
        
        count = 0
        for log in logs:
            conv = Conversation.query.get(log.conversation_id)
            if conv and not conv.contact_email:
                conv.contact_email = log.to_email
                count += 1
                print(f"Updated Conv {conv.id} contact_email to {log.to_email}")
        
        db.session.commit()
        print(f"Updated {count} conversations.")

if __name__ == '__main__':
    main()
