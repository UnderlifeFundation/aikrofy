"""
AnalyticsDashboard Models - Customizable dashboard system per user and company.
"""
from datetime import datetime
from enum import Enum
from extensions import db


class ChartType(str, Enum):
    CARD = 'card'
    BAR = 'bar'
    LINE = 'line'
    PIE = 'pie'
    FUNNEL = 'funnel'


class PredefinedMetric(db.Model):
    """System-defined analytical metrics and their query templates."""
    __tablename__ = 'predefined_metrics'

    id = db.Column(db.Integer, primary_key=True)
    metric_key = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(255), nullable=False)
    
    default_chart_type = db.Column(db.Enum(ChartType), default=ChartType.BAR, nullable=False)
    aggregation_query_template = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'metric_key': self.metric_key,
            'display_name': self.display_name,
            'default_chart_type': self.default_chart_type.value if hasattr(self.default_chart_type, 'value') else self.default_chart_type,
            'aggregation_query_template': self.aggregation_query_template
        }

    def __repr__(self):
        return f'<PredefinedMetric {self.metric_key}>'


class UserDashboard(db.Model):
    """User-specific dashboards within a company."""
    __tablename__ = 'user_dashboards'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    dashboard_name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('dashboards', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('dashboards', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'dashboard_name': self.dashboard_name,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<UserDashboard {self.dashboard_name} for company={self.company_id} user={self.user_id}>'


class DashboardWidget(db.Model):
    """Individual widgets placed on a UserDashboard."""
    __tablename__ = 'dashboard_widgets'

    id = db.Column(db.Integer, primary_key=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('user_dashboards.id'), nullable=False)
    predefined_metric_id = db.Column(db.Integer, db.ForeignKey('predefined_metrics.id'), nullable=False)
    
    widget_title = db.Column(db.String(150), nullable=False)
    chart_type = db.Column(db.Enum(ChartType), nullable=False)
    
    grid_layout = db.Column(db.JSON, default=dict, nullable=False)  # x, y, w, h configuration
    widget_settings = db.Column(db.JSON, default=dict, nullable=False) # filters, date ranges, options

    # Relationships
    dashboard = db.relationship('UserDashboard', backref=db.backref('widgets', lazy='dynamic', cascade='all, delete-orphan'))
    metric = db.relationship('PredefinedMetric', backref=db.backref('widgets', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'dashboard_id': self.dashboard_id,
            'predefined_metric_id': self.predefined_metric_id,
            'widget_title': self.widget_title,
            'chart_type': self.chart_type.value if hasattr(self.chart_type, 'value') else self.chart_type,
            'grid_layout': self.grid_layout,
            'widget_settings': self.widget_settings,
        }

    def __repr__(self):
        return f'<DashboardWidget {self.widget_title} on dashboard={self.dashboard_id}>'
