"""
Beta Lead Model - Prospects requesting beta access via discovery onboarding form
"""
from datetime import datetime
from extensions import db

class BetaLeadStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class BetaLead(db.Model):
    """Beta application / Waitlist discovery submission model"""
    __tablename__ = 'beta_leads'

    id = db.Column(db.Integer, primary_key=True)
    
    # Contact Info
    contact_name = db.Column(db.String(255), nullable=False)
    role_in_company = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=False)
    
    # Discovery Info
    company_name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(255), nullable=False)
    employee_count = db.Column(db.String(100), nullable=False)
    products_services = db.Column(db.Text, nullable=True)
    ai_experience = db.Column(db.String(255), nullable=True) # Nivel de adopcion de IA
    ai_results_satisfaction = db.Column(db.String(255), nullable=True) # Experiencia previa / resultados obtenidos
    ai_expectations = db.Column(db.Text, nullable=True)
    additional_notes = db.Column(db.Text, nullable=True)
    
    # Status & Approval Tracking
    status = db.Column(db.String(50), default=BetaLeadStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Linked User / Company once created/approved
    created_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    credits_granted = db.Column(db.Integer, default=100)
    
    # Real-Time IP Telemetry & GPS Geolocation
    submission_ip = db.Column(db.String(64), nullable=True)
    ip_lat = db.Column(db.Float, nullable=True)
    ip_lng = db.Column(db.Float, nullable=True)
    ip_city = db.Column(db.String(100), nullable=True)
    ip_country = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'role_in_company': self.role_in_company,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'industry': self.industry,
            'employee_count': self.employee_count,
            'products_services': self.products_services,
            'ai_experience': self.ai_experience,
            'ai_results_satisfaction': self.ai_results_satisfaction,
            'ai_expectations': self.ai_expectations,
            'additional_notes': self.additional_notes,
            'status': self.status,
            'credits_granted': self.credits_granted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_user_id': self.created_user_id,
            'created_company_id': self.created_company_id
        }

    def __repr__(self):
        return f'<BetaLead {self.company_name} ({self.email})>'
