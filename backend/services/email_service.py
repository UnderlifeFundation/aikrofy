import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from models.channel import Channel, ChannelType, ChannelStatus
from models.company import Company
from models.platform_config import PlatformConfig

logger = logging.getLogger(__name__)

from email.mime.application import MIMEApplication
import base64

class EmailService:
    def __init__(self, company=None):
        self.company = company

    @classmethod
    def send_email(cls, company_id=None, to_email=None, subject=None, body=None, attachments=None, to=None, self=None):
        """
        Send an email using the company's configured email channel.
        Can be called as an instance method: email_service.send_email(...)
        or as a class method: EmailService.send_email(...)
        attachments: List of dicts {'name': str, 'content': bytes, 'type': str}
        """
        # Support invocation via instance if called as instance.send_email(...)
        instance = self if self is not None else (cls if isinstance(cls, EmailService) else None)
        inst_company = getattr(instance, 'company', None) if instance else None
        target_company_id = company_id or (inst_company.id if inst_company else None)
        target_email = to_email or to

        if not target_email:
            return {'success': False, 'message': 'Recipient email is required'}

        # Preventive rollback for stale connections
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        # Determine display name & company
        company = None
        if target_company_id:
            company = Company.query.get(target_company_id)
        elif inst_company:
            company = inst_company

        config = PlatformConfig.get_config()
        is_platform = (company and config and company.id == config.platform_company_id) or (target_company_id and config and target_company_id == config.platform_company_id)

        if is_platform or not company:
            display_name = "Aikrofy"
        else:
            display_name = company.name

        # Find connection
        channel = None
        if target_company_id:
            channel = Channel.query.filter_by(
                company_id=target_company_id,
                type=ChannelType.EMAIL,
                status=ChannelStatus.CONNECTED
            ).first()
        
        if not channel and config and config.platform_company_id:
            channel = Channel.query.filter_by(
                company_id=config.platform_company_id,
                type=ChannelType.EMAIL,
                status=ChannelStatus.CONNECTED
            ).first()

        # Fallback to system env SMTP if host is set or platform configuration
        from config import get_config
        cfg = get_config()
        if not channel and cfg.SMTP_HOST:
            smtp_credentials = {
                'smtp_host': cfg.SMTP_HOST,
                'smtp_port': cfg.SMTP_PORT,
                'smtp_encryption': cfg.SMTP_ENCRYPTION,
                'email_user': cfg.SMTP_USER,
                'email_pass': cfg.SMTP_PASSWORD,
                'from_email': cfg.DEFAULT_FROM_EMAIL
            }
            try:
                return cls._send_via_smtp(smtp_credentials, cfg.DEFAULT_FROM_EMAIL, target_email, subject, body, attachments, display_name)
            except Exception as e:
                logger.error(f"Fallback SMTP failed: {e}")
                return {'success': False, 'message': str(e)}

        if not channel:
            logger.warning(f"No connected email channel found for company {target_company_id} and no SMTP_HOST defined in env.")
            return {'success': False, 'message': 'No email channel connected'}
            
        credentials = channel.credentials or {}
        provider = credentials.get('provider')
        
        try:
            if provider == 'sendgrid':
                return cls._send_via_sendgrid(credentials, channel.email_address, target_email, subject, body, attachments, display_name)
            elif provider == 'smtp':
                return cls._send_via_smtp(credentials, channel.email_address, target_email, subject, body, attachments, display_name)
            else:
                 return {'success': False, 'message': f'Unknown email provider: {provider}'}
                 
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {'success': False, 'message': str(e)}

    @classmethod
    def _send_via_sendgrid(cls, credentials, from_email, to_email, subject, body, attachments=None, display_name="Aikrofy"):
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, From
        except ImportError:
            return {'success': False, 'message': 'SendGrid package not installed. Please install it or use SMTP.'}

        api_key = credentials.get('api_key')
        if not api_key:
             return {'success': False, 'message': 'SendGrid API Key missing'}

        raw_from = from_email or credentials.get('from_email')
        from_obj = From(raw_from, display_name) if display_name else raw_from

        message = Mail(
            from_email=from_obj,
            to_emails=to_email,
            subject=subject,
            html_content=body
        )
        
        if attachments:
            for att in attachments:
                encoded_file = base64.b64encode(att['content']).decode()
                attachedFile = Attachment(
                    FileContent(encoded_file),
                    FileName(att['name']),
                    FileType(att.get('type', 'application/pdf')),
                    Disposition('attachment')
                )
                message.add_attachment(attachedFile)
        
        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            if response.status_code in [200, 201, 202]:
                return {'success': True, 'message': f'Email sent to {to_email}'}
            else:
                return {'success': False, 'message': f'SendGrid error: {response.status_code}'}
        except Exception as e:
            raise e

    @classmethod
    def _send_via_smtp(cls, credentials, from_email, to_email, subject, body, attachments=None, display_name="Aikrofy"):
        smtp_host = credentials.get('smtp_host')
        smtp_port = int(credentials.get('smtp_port', 465))
        encryption = (credentials.get('smtp_encryption') or 'ssl').lower().strip()
        username = credentials.get('email_user')
        password = credentials.get('email_pass')
        raw_sender = from_email or credentials.get('from_email') or username

        formatted_sender = formataddr((display_name, raw_sender)) if display_name else raw_sender

        msg = MIMEMultipart()
        msg['From'] = formatted_sender
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        if attachments:
            for att in attachments:
                part = MIMEApplication(att['content'], Name=att['name'])
                part['Content-Disposition'] = f'attachment; filename="{att["name"]}"'
                msg.attach(part)

        context = ssl.create_default_context()
        timeout = 10  # Prevent indefinite worker hanging

        try:
            # Port 465 is always implicit SSL (SMTPS).
            if smtp_port == 465 or encryption == 'ssl':
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
                    server.login(username, password)
                    server.sendmail(raw_sender, to_email, msg.as_string())
            elif encryption == 'tls' or smtp_port == 587:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                    server.starttls(context=context)
                    server.login(username, password)
                    server.sendmail(raw_sender, to_email, msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                    server.login(username, password)
                    server.sendmail(raw_sender, to_email, msg.as_string())

            return {'success': True, 'message': f'Email sent to {to_email}'}

        except Exception as e:
            raise e

