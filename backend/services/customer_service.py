"""
Customer Service - Business Logic for Customer Management
"""
from models.customer import Customer
from extensions import db
from sqlalchemy import or_

class CustomerService:
    @staticmethod
    def resolve_real_phone(company_id: int, phone: str) -> str:
        """
        Check if a given phone string is a WhatsApp LID (synthetic privacy ID)
        and attempt to resolve it to the user's actual phone number using Redis cache
        or the whatsapp_lid_mapping database table.
        If it cannot be resolved, returns None if it is a pure LID to prevent storing invalid numbers.
        """
        if not phone:
            return ""
        clean_p = str(phone).replace('whatsapp:', '').strip()
        digits = ''.join(c for c in clean_p if c.isdigit())
        lid_raw = clean_p.split('@')[0].strip()

        # If it is a real standard phone number (10-12 digits and not flagged as LID)
        if len(digits) < 13 and '@lid' not in clean_p:
            return clean_p

        # Check Redis
        try:
            from services.cache_service import CacheService
            cached = CacheService.get(f"wa:lid_map:{company_id}:{lid_raw}")
            if cached:
                return str(cached)
        except Exception:
            pass

        # Check DB
        try:
            res = db.session.execute(
                db.text("SELECT phone_number FROM whatsapp_lid_mapping WHERE company_id = :cid AND (lid_jid = :lid OR lid_jid LIKE :lid_like OR lid_jid = :lid_at) LIMIT 1"),
                {"cid": company_id, "lid": clean_p, "lid_like": f"%{lid_raw}%", "lid_at": f"{lid_raw}@lid"}
            ).fetchone()
            if res and res[0]:
                return str(res[0])
        except Exception:
            pass

        # If it's a LID that could not be resolved yet, return None to prevent saving garbage in CRM
        if len(digits) >= 13 or '@lid' in clean_p:
            return None
        return clean_p

    @staticmethod
    def save_lid_mapping(company_id: int, lid_jid: str, phone_number: str):
        """
        Store or update a mapping between a WhatsApp LID and the real phone number
        both in Redis cache and in the database table whatsapp_lid_mapping.
        """
        if not lid_jid or not phone_number:
            return
        
        clean_lid = str(lid_jid).replace('whatsapp:', '').strip()
        clean_phone = str(phone_number).replace('whatsapp:', '').replace('@s.whatsapp.net', '').strip()
        lid_raw = clean_lid.split('@')[0].strip()

        # 1. Update Redis cache
        try:
            from services.cache_service import CacheService
            CacheService.set(f"wa:lid_map:{company_id}:{lid_raw}", clean_phone, ttl=86400 * 90)
            CacheService.set(f"wa:lid_map:{company_id}:{clean_lid}", clean_phone, ttl=86400 * 90)
            CacheService.set(f"wa:raw_jid:{company_id}:{clean_phone}", f"{lid_raw}@lid", ttl=86400 * 90)
        except Exception:
            pass

        # 2. Update DB
        try:
            db.session.execute(
                db.text("""
                    INSERT INTO whatsapp_lid_mapping (company_id, lid_jid, phone_number)
                    VALUES (:cid, :lid, :phone)
                    ON DUPLICATE KEY UPDATE phone_number = :phone
                """),
                {"cid": company_id, "lid": f"{lid_raw}@lid", "phone": clean_phone}
            )
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

    @staticmethod
    def get_customer(company_id, email=None, phone=None):
        """
        Find a customer by email or phone within a company.
        Case-insensitive for email.
        For phone: supports exact match, E.164 normalization, suffix (last 9 digits),
        and WhatsApp LID resolution via whatsapp_lid_mapping.
        """
        query = Customer.query.filter_by(company_id=company_id)
        
        email = email.strip().lower() if email else None
        phone = str(phone).strip() if phone else None
        
        # Resolve mapped real phone if phone is a WhatsApp LID
        candidate_phones = []
        if phone:
            candidate_phones.append(phone)
            clean_p = phone.replace('whatsapp:', '').strip()
            if clean_p not in candidate_phones:
                candidate_phones.append(clean_p)

            # Check if phone is a LID or long numeric identifier
            digits_p = ''.join(c for c in clean_p if c.isdigit())
            lid_raw = clean_p.split('@')[0].strip()
            mapped_phone = None

            # Redis cache
            try:
                from services.cache_service import CacheService
                cached_p = CacheService.get(f"wa:lid_map:{company_id}:{lid_raw}")
                if cached_p:
                    mapped_phone = str(cached_p)
            except Exception:
                pass

            # DB mapping
            if not mapped_phone:
                try:
                    res = db.session.execute(
                        db.text("SELECT phone_number FROM whatsapp_lid_mapping WHERE company_id = :cid AND (lid_jid = :lid OR lid_jid LIKE :lid_like OR lid_jid = :lid_at) LIMIT 1"),
                        {"cid": company_id, "lid": clean_p, "lid_like": f"%{lid_raw}%", "lid_at": f"{lid_raw}@lid"}
                    ).fetchone()
                    if res and res[0]:
                        mapped_phone = str(res[0])
                except Exception:
                    pass

            if mapped_phone and mapped_phone not in candidate_phones:
                candidate_phones.append(mapped_phone)

        # 1. Direct query with email and phone candidates
        if email and candidate_phones:
            phone_conditions = []
            for p in candidate_phones:
                phone_conditions.append(Customer.phone == p)
                digits = ''.join(c for c in p if c.isdigit())
                if len(digits) >= 9:
                    phone_conditions.append(Customer.phone.like(f"%{digits[-9:]}"))
            return query.filter(or_(Customer.email.ilike(email), *phone_conditions)).first()
        elif email:
            return query.filter(Customer.email.ilike(email)).first()
        elif candidate_phones:
            # Try exact match first
            for p in candidate_phones:
                cust = query.filter(Customer.phone == p).first()
                if cust:
                    return cust

            # Try suffix match on last 9 digits (handles country code / leading zero differences)
            for p in candidate_phones:
                digits = ''.join(c for c in p if c.isdigit())
                if len(digits) >= 9:
                    cust = query.filter(Customer.phone.like(f"%{digits[-9:]}")).first()
                    if cust:
                        return cust
        return None

    @staticmethod
    def lookup_by_term(company_id, term):
        """
        Flexible search by term (email, phone, or name tokens)
        """
        if not term:
            return []
        raw_term = str(term).strip()
        pattern = f"%{raw_term}%"
        
        # 1. Try full exact/contains match first
        results = Customer.query.filter_by(company_id=company_id).filter(
            or_(
                Customer.email.ilike(pattern),
                Customer.phone.like(pattern),
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.ident_number.like(pattern)
            )
        ).limit(10).all()
        
        if results:
            return results

        # 2. If no direct match, fallback to tokenized search (e.g. 'Yosue Guachun' matches 'Yosue')
        tokens = [t for t in raw_term.split() if len(t) > 1]
        if tokens:
            token_conditions = []
            for token in tokens:
                t_pat = f"%{token}%"
                token_conditions.extend([
                    Customer.first_name.ilike(t_pat),
                    Customer.last_name.ilike(t_pat),
                    Customer.email.ilike(t_pat),
                    Customer.phone.like(t_pat)
                ])
            results = Customer.query.filter_by(company_id=company_id).filter(or_(*token_conditions)).limit(10).all()
            if results:
                return results

        return []

    @staticmethod
    def upsert_customer(company_id, data):
        """
        Create or Update a customer.
        Enforces uniqueness by email OR phone WITHIN the same company.
        """
        email = data.get('email').strip().lower() if data.get('email') else None
        phone = str(data.get('phone')).strip() if data.get('phone') else None
        
        # 1. Look for existing customer by email or phone for THIS company
        customer = CustomerService.get_customer(company_id, email, phone)
        
        if not customer:
            customer = Customer(company_id=company_id)
            from models.funnel_stage import FunnelStage
            first_stage = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).first()
            if not first_stage:
                default_names = ["Lead", "Contactado", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
                for idx, name in enumerate(default_names):
                    st = FunnelStage(company_id=company_id, name=name, sort_order=idx)
                    db.session.add(st)
                    if idx == 0:
                        first_stage = st
                db.session.flush()
            if first_stage:
                customer.funnel_stage_id = first_stage.id
            db.session.add(customer)
        
        # 2. Update fields
        fn_val = data.get('first_name')
        if fn_val:
            cleaned_fn = str(fn_val).strip()
            if cleaned_fn.lower() not in {'jonathan', 'jonnathan', 'yosue', 'josue'} or email:
                customer.first_name = cleaned_fn
        if 'last_name' in data: customer.last_name = data['last_name']
        if 'funnel_stage_id' in data and data['funnel_stage_id'] is not None:
            customer.funnel_stage_id = data['funnel_stage_id']
        elif not customer.funnel_stage_id:
            from models.funnel_stage import FunnelStage
            first_st = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).first()
            if first_st:
                customer.funnel_stage_id = first_st.id
        if 'lead_score' in data: customer.lead_score = data['lead_score']
        
        # Only update email/phone if provided (to avoid clearing existing data)
        if email: customer.email = email
        if 'country' in data: customer.country = data['country']
        if phone:
            from utils.phone import normalize_phone_number
            resolved_p = CustomerService.resolve_real_phone(company_id, phone)
            if resolved_p:
                customer.phone = normalize_phone_number(resolved_p, customer.country or data.get('country'))
        
        if 'ident_number' in data: customer.ident_number = data['ident_number']
        if 'city' in data: customer.city = data['city']
        if 'metadata' in data: customer.customer_metadata = data['metadata']
        
        db.session.commit()
        return customer

    @staticmethod
    def merge_or_upgrade_customer(company_id: int, data: dict, conversation=None):
        """
        Consolidates contact identity from incoming messages/tools.
        - If the conversation was linked to an ephemeral visitor ('Visitante Webchat' or unverified guest),
          and user provides email/phone matching an EXISTING customer:
            -> Reassigns the conversation to the existing customer.
            -> Copies any relevant details if missing on existing customer.
            -> Deletes the ephemeral customer record so no duplicate/orphan remains in Kanban.
            -> Returns the consolidated existing customer.
        - If no existing customer matches email/phone:
          - If conversation is linked to an ephemeral customer:
            -> Upgrades that ephemeral customer in place (sets real name, email, phone).
            -> Returns the upgraded customer.
          - Otherwise:
            -> Creates a new customer record via upsert_customer.
        """
        from models.customer import Customer
        from models.conversation import Conversation
        from utils.phone import normalize_phone_number

        email = data.get('email').strip().lower() if data.get('email') else None
        phone = str(data.get('phone')).strip() if data.get('phone') else None
        first_name = data.get('first_name', '').strip() if data.get('first_name') else None
        # Discard founder vocatives if sent as customer name without explicit email
        if first_name and first_name.lower() in {'jonathan', 'jonnathan', 'yosue', 'josue'} and not email:
            first_name = None
        last_name = data.get('last_name', '').strip() if data.get('last_name') else None
        ident_number = data.get('ident_number')
        country = data.get('country')
        city = data.get('city')
        buying_role = data.get('buying_role', 'End User')

        # 1. Search for existing registered customer matching email or phone
        existing_customer = CustomerService.get_customer(company_id, email=email, phone=phone)

        # 2. Check if current conversation has an ephemeral customer
        ephemeral_customer = None
        if conversation and conversation.customer_id:
            cand = Customer.query.get(conversation.customer_id)
            if cand and (
                cand.first_name == "Visitante Webchat" 
                or (cand.phone and str(cand.phone).startswith("guest_"))
                or (cand.phone and str(cand.phone).startswith("web_"))
                or not cand.email
            ):
                ephemeral_customer = cand

        # CASE A: Match found with an existing customer
        if existing_customer:
            # If current conversation had an ephemeral customer different from existing_customer, merge and clean up
            if ephemeral_customer and ephemeral_customer.id != existing_customer.id:
                # Re-link any other conversations pointing to ephemeral to the existing customer
                Conversation.query.filter_by(customer_id=ephemeral_customer.id).update(
                    {'customer_id': existing_customer.id},
                    synchronize_session=False
                )
                db.session.delete(ephemeral_customer)
                db.session.flush()

            # Ensure conversation points to existing customer
            if conversation:
                conversation.customer_id = existing_customer.id
                if first_name:
                    conversation.contact_name = f"{first_name} {last_name or ''}".strip()
                elif existing_customer.first_name:
                    conversation.contact_name = existing_customer.full_name
                if email:
                    conversation.contact_email = email
                db.session.flush()

            # Enrich existing customer with any missing info
            if first_name and (not existing_customer.first_name or existing_customer.first_name == "Visitante Webchat"):
                existing_customer.first_name = first_name
            if last_name and not existing_customer.last_name:
                existing_customer.last_name = last_name
            if email and not existing_customer.email:
                existing_customer.email = email
            if phone and not existing_customer.phone:
                resolved_p = CustomerService.resolve_real_phone(company_id, phone)
                if resolved_p:
                    existing_customer.phone = normalize_phone_number(resolved_p, country or existing_customer.country)
            elif phone and existing_customer.phone:
                # If existing phone is an invalid LID and new phone is real, upgrade it
                cur_digits = ''.join(c for c in existing_customer.phone if c.isdigit())
                if len(cur_digits) >= 13 or '@lid' in existing_customer.phone:
                    resolved_p = CustomerService.resolve_real_phone(company_id, phone)
                    if resolved_p:
                        existing_customer.phone = normalize_phone_number(resolved_p, country or existing_customer.country)
            if ident_number and not existing_customer.ident_number:
                existing_customer.ident_number = ident_number
            if country and not existing_customer.country:
                existing_customer.country = country
            if city and not existing_customer.city:
                existing_customer.city = city

            db.session.commit()
            try:
                from services.realtime_service import RealtimeService
                RealtimeService.publish_lead_update(company_id, existing_customer.id, {
                    "first_name": existing_customer.first_name,
                    "last_name": existing_customer.last_name,
                    "email": existing_customer.email,
                    "phone": existing_customer.phone,
                    "lead_score": existing_customer.lead_score,
                    "funnel_stage_id": existing_customer.funnel_stage_id
                })
            except Exception as e_rt:
                print(f"[REALTIME] Warning: Failed to publish lead update: {e_rt}")
            return existing_customer

        # CASE B: No existing customer found -> Upgrade ephemeral customer if present
        if ephemeral_customer:
            if first_name:
                ephemeral_customer.first_name = first_name
                # If ephemeral customer had an auto-generated guest identifier as last_name, replace or clear it
                if last_name:
                    ephemeral_customer.last_name = last_name
                elif ephemeral_customer.last_name and (
                    ephemeral_customer.last_name.startswith("guest_") 
                    or ephemeral_customer.last_name.startswith("test_")
                    or ephemeral_customer.last_name.startswith("web_")
                ):
                    ephemeral_customer.last_name = ""
            elif last_name:
                ephemeral_customer.last_name = last_name
            if email:
                ephemeral_customer.email = email
            if phone:
                resolved_p = CustomerService.resolve_real_phone(company_id, phone)
                if resolved_p:
                    ephemeral_customer.phone = normalize_phone_number(resolved_p, country or ephemeral_customer.country)
            if ident_number:
                ephemeral_customer.ident_number = ident_number
            if country:
                ephemeral_customer.country = country
            if city:
                ephemeral_customer.city = city
            if buying_role:
                ephemeral_customer.buying_role = buying_role

            if conversation:
                if first_name:
                    conversation.contact_name = f"{first_name} {last_name or ''}".strip()
                if email:
                    conversation.contact_email = email

            db.session.commit()
            try:
                from services.realtime_service import RealtimeService
                RealtimeService.publish_lead_update(company_id, ephemeral_customer.id, {
                    "first_name": ephemeral_customer.first_name,
                    "last_name": ephemeral_customer.last_name,
                    "email": ephemeral_customer.email,
                    "phone": ephemeral_customer.phone,
                    "lead_score": ephemeral_customer.lead_score,
                    "funnel_stage_id": ephemeral_customer.funnel_stage_id
                })
            except Exception as e_rt:
                print(f"[REALTIME] Warning: Failed to publish lead update: {e_rt}")
            return ephemeral_customer

        # CASE C: Fresh customer creation
        customer = CustomerService.upsert_customer(company_id, data)
        if conversation:
            conversation.customer_id = customer.id
            if first_name:
                conversation.contact_name = f"{first_name} {last_name or ''}".strip()
            if email:
                conversation.contact_email = email
            db.session.commit()
        try:
            from services.realtime_service import RealtimeService
            RealtimeService.publish_lead_update(company_id, customer.id, {
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
                "phone": customer.phone,
                "lead_score": customer.lead_score,
                "funnel_stage_id": customer.funnel_stage_id
            })
        except Exception as e_rt:
            print(f"[REALTIME] Warning: Failed to publish lead update: {e_rt}")
        return customer

    @staticmethod
    def delete_customer(customer_id, company_id):
        """
        Permanently delete a customer and ALL associated data across the system.
        """
        from models.customer import Customer
        from models.conversation import Conversation, Message
        from models.appointment import Appointment
        from models.transaction import Transaction
        from models.note import Note
        
        customer = Customer.query.filter_by(id=customer_id, company_id=company_id).first()
        if not customer:
            return False, "Customer not found"
            
        try:
            # 1. Notes
            Note.query.filter_by(customer_id=customer_id, company_id=company_id).delete()
            
            # 2. Appointments
            Appointment.query.filter_by(customer_id=customer_id, company_id=company_id).delete()
            
            # 3. Transactions
            Transaction.query.filter_by(customer_id=customer_id, company_id=company_id).delete()
            
            # 4. Conversations & Messages
            # We find all conversations first to delete their messages and audits
            convs = Conversation.query.filter_by(customer_id=customer_id, company_id=company_id).all()
            for conv in convs:
                # Delete any message_audits references to prevent foreign key constraint violations
                try:
                    db.session.execute(
                        db.text("DELETE FROM message_audits WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = :conv_id)"),
                        {"conv_id": conv.id}
                    )
                except Exception:
                    pass
                Message.query.filter_by(conversation_id=conv.id).delete()
                db.session.delete(conv)
            
            # 5. Finally delete the Customer
            db.session.delete(customer)
            db.session.commit()
            return True, "Customer and all associated data deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Deletion failed: {str(e)}"

    @staticmethod
    def get_timeline(customer_id):
        """
        Build a unified timeline for a customer.
        Returns a sorted list of events (messages, appointments, notes, payments).
        """
        from models.customer import Customer
        from models.conversation import Conversation, Message
        from models.appointment import Appointment
        from models.transaction import Transaction
        from models.note import Note
        
        customer = Customer.query.get(customer_id)
        if not customer: return []
        
        timeline = []
        
        # 1. Notes
        notes = Note.query.filter_by(customer_id=customer_id).all()
        for note in notes:
            timeline.append({
                'type': 'note',
                'id': note.id,
                'timestamp': note.created_at.isoformat(),
                'content': note.content,
                'author': note.author_name,
                'raw': note.to_dict()
            })
            
        # 2. Appointments
        apps = Appointment.query.filter_by(customer_id=customer_id).all()
        for app in apps:
            timeline.append({
                'type': 'appointment',
                'id': app.id,
                'timestamp': app.created_at.isoformat(),
                'title': app.title,
                'status': app.status,
                'meet_link': app.google_meet_link,
                'raw': app.to_dict()
            })
            
        # 3. Transactions (Payments)
        txns = Transaction.query.filter_by(customer_id=customer_id).all()
        for txn in txns:
            timeline.append({
                'type': 'payment',
                'id': txn.id,
                'timestamp': txn.created_at.isoformat(),
                'amount': txn.amount,
                'currency': txn.currency,
                'status': txn.status,
                'description': txn.description,
                'raw': txn.to_dict()
            })
            
        # 4. Conversations & Messages
        # We find all conversations linked to this customer
        # And extract the messages
        convs = Conversation.query.filter_by(customer_id=customer_id).all()
        for conv in convs:
            # Add conversation start as an event? 
            # Or just messages. Let's do messages.
            msgs = conv.messages.all()
            for msg in msgs:
                timeline.append({
                    'type': 'message',
                    'id': msg.id,
                    'timestamp': msg.created_at.isoformat(),
                    'role': msg.role.value if hasattr(msg.role, 'value') else msg.role,
                    'content': msg.content,
                    'channel': msg.channel.value if hasattr(msg.channel, 'value') else str(msg.channel or 'webchat'),
                    'is_user': (msg.role.value if hasattr(msg.role, 'value') else msg.role) == 'user'
                })
        
        # Sort by timestamp descending
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return timeline
