"""
Seed Script - Initializes predefined metrics in the database.
Idempotent and safe to run multiple times.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_crm_metrics")

# Load env variables
load_dotenv()
db_uri = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or "mysql+pymysql://root:root@localhost:3306/aikrofy"

def seed_metrics():
    logger.info("Initializing DB session...")
    from app import create_app
    from extensions import db
    from models.analytics_dashboard import PredefinedMetric, ChartType

    app = create_app()
    with app.app_context():
        # Define the metrics to seed
        metrics_data = [
            {
                "metric_key": "leads_by_score_range",
                "display_name": "Calificación de Prospectos (Leads por Nivel de Score)",
                "default_chart_type": ChartType.BAR,
                "aggregation_query_template": """
SELECT 
    CASE 
        WHEN lead_score >= 80 THEN 'Caliente (80-100)'
        WHEN lead_score >= 50 THEN 'Templado (50-79)'
        ELSE 'Frío (0-49)'
    END AS label,
    COUNT(*) AS value
FROM customers
WHERE company_id = :company_id 
  AND created_at >= NOW() - INTERVAL :days_back DAY
GROUP BY label;
                """.strip()
            },
            {
                "metric_key": "contacts_by_channel",
                "display_name": "Distribución de Contactos por Canal de Origen Conversacional",
                "default_chart_type": ChartType.PIE,
                "aggregation_query_template": """
SELECT 
    COALESCE(utm_source, 'Tráfico Directo / Orgánico') AS label,
    COUNT(*) AS value
FROM contact_attributions
WHERE company_id = :company_id 
  AND created_at >= NOW() - INTERVAL :days_back DAY
GROUP BY label;
                """.strip()
            },
            {
                "metric_key": "funnel_conversions",
                "display_name": "Conversiones del Embudo (Proporción de Leads por Etapa de Kanban)",
                "default_chart_type": ChartType.BAR,
                "aggregation_query_template": """
SELECT 
    fs.name AS label,
    COUNT(c.id) AS value
FROM funnel_stages fs
LEFT JOIN customers c ON c.funnel_stage_id = fs.id AND c.company_id = :company_id
WHERE fs.company_id = :company_id
GROUP BY fs.id, fs.name, fs.sort_order
ORDER BY fs.sort_order ASC;
                """.strip()
            }
        ]

        for m_data in metrics_data:
            # Check if metric already exists
            metric = PredefinedMetric.query.filter_by(metric_key=m_data["metric_key"]).first()
            if metric:
                logger.info(f"Metric '{m_data['metric_key']}' already exists. Updating query template...")
                metric.display_name = m_data["display_name"]
                metric.default_chart_type = m_data["default_chart_type"]
                metric.aggregation_query_template = m_data["aggregation_query_template"]
            else:
                logger.info(f"Creating metric '{m_data['metric_key']}'...")
                metric = PredefinedMetric(
                    metric_key=m_data["metric_key"],
                    display_name=m_data["display_name"],
                    default_chart_type=m_data["default_chart_type"],
                    aggregation_query_template=m_data["aggregation_query_template"]
                )
                db.session.add(metric)
        
        db.session.commit()
        logger.info("Predefined metrics seeding completed successfully.")

if __name__ == '__main__':
    seed_metrics()
