"""
Machine Learning Scoring Pipeline - Trains and executes localized lead scoring classifiers per company.
"""
import os
import logging
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from extensions import db
from models.customer import Customer
from models.conversation import Conversation

logger = logging.getLogger(__name__)

class LocalPredictiveScoringEngine:
    @staticmethod
    def extract_features_dataframe(company_id: int):
        """
        Compile demographic, firmographic, and behavioral conversion metrics from the database.
        """
        query = """
            SELECT 
                c.id, c.email, c.country, c.buying_role,
                fs.name as stage_name,
                (SELECT COUNT(*) FROM messages m JOIN conversations cv ON m.conversation_id = cv.id WHERE cv.customer_id = c.id) as total_messages,
                (SELECT COALESCE(AVG(LENGTH(m.content)), 0) FROM messages m JOIN conversations cv ON m.conversation_id = cv.id WHERE cv.customer_id = c.id) as avg_message_length
            FROM customers c
            LEFT JOIN funnel_stages fs ON c.funnel_stage_id = fs.id
            WHERE c.company_id = :company_id
        """
        try:
            from sqlalchemy import text
            result = db.session.execute(text(query), {"company_id": company_id}).fetchall()
            if not result:
                return None
                
            # Convert query results to pandas DataFrame
            data = []
            for r in result:
                data.append({
                    "id": r[0],
                    "email": r[1],
                    "country": r[2],
                    "buying_role": r[3],
                    "stage_name": r[4],
                    "total_messages": r[5],
                    "avg_message_length": r[6]
                })
            
            df = pd.DataFrame(data)
            if df.empty or len(df) < 5:  # A very small threshold for testing/dev (production suggests 500+)
                return None
                
            # Target labels: 1 for Won ("Ganado" / "Propuesta" / "Negociación"), 0 for others
            df['target'] = df['stage_name'].apply(
                lambda x: 1 if x and any(w in str(x).lower() for w in ['ganado', 'propuesta', 'negociacion', 'calificado']) else 0
            )
            df['is_corporate'] = df['email'].apply(
                lambda x: 0 if not x or any(c in str(x).lower() for c in ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud']) else 1
            )
            
            df['country'] = df['country'].fillna('unknown')
            df['buying_role'] = df['buying_role'].fillna('unknown')
            
            return df[['country', 'buying_role', 'is_corporate', 'total_messages', 'avg_message_length', 'target']]
        except Exception as e:
            logger.error(f"Error compiling ML features: {e}")
            return None

    @staticmethod
    def train_company_model(company_id: int):
        """
        Trains localized Gradient Boosting Classifier on customer conversion historical data.
        Runs entirely on CPU and consumes negligible RAM (<30MB).
        """
        logger.info(f"Triggering ML training pipeline for company {company_id}...")
        df = LocalPredictiveScoringEngine.extract_features_dataframe(company_id)
        
        # We need a minimum number of converted samples to train a classifier
        if df is None or len(df) < 5: 
            logger.info(f"ML training skipped for company {company_id}: Insufficient historical data.")
            return {"status": "skipped", "reason": "Insufficient data"}
            
        X = df.drop(columns=['target'])
        y = df['target']
        
        # Check if we have at least one class represented
        if len(y.unique()) < 2:
            logger.info(f"ML training skipped for company {company_id}: Single class represented in target.")
            return {"status": "skipped", "reason": "Need both won and lost stages represented"}
            
        # Build training pipeline
        categorical_features = ['country', 'buying_role']
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ],
            remainder='passthrough'
        )
        
        model_pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', GradientBoostingClassifier(n_estimators=50, learning_rate=0.1, max_depth=3, random_state=42))
        ])
        
        try:
            model_pipeline.fit(X, y)
            
            # Save model pipeline artifact per company
            model_dir = f"uploads/ml_models/company_{company_id}"
            os.makedirs(model_dir, exist_ok=True)
            model_path = os.path.join(model_dir, "lead_scoring_model.pkl")
            joblib.dump(model_pipeline, model_path)
            
            logger.info(f"ML lead scoring model successfully trained for company {company_id}: {model_path}")
            return {"status": "trained", "model_path": model_path}
        except Exception as e:
            logger.error(f"Failed to train company model: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def predict_conversion_probability(company_id: int, customer: Customer) -> float:
        """
        Predict conversion probability using the company's local model if trained.
        Falls back to None (which triggers LLM zero-shot) if not trained.
        """
        model_path = f"uploads/ml_models/company_{company_id}/lead_scoring_model.pkl"
        if not os.path.exists(model_path):
            return None
            
        try:
            pipeline = joblib.load(model_path)
            
            # Fetch message statistics
            total_msg = 0
            avg_len = 0.0
            conv = Conversation.query.filter_by(customer_id=customer.id, company_id=company_id).first()
            if conv:
                msgs = conv.messages.all()
                total_msg = len(msgs)
                if total_msg > 0:
                    avg_len = sum(len(m.content) for m in msgs) / total_msg
            
            is_corp = 0
            if customer.email and not any(c in customer.email.lower() for c in ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud']):
                is_corp = 1
                
            input_df = pd.DataFrame([{
                'country': customer.country or 'unknown',
                'buying_role': customer.buying_role or 'unknown',
                'is_corporate': is_corp,
                'total_messages': total_msg,
                'avg_message_length': avg_len
            }])
            
            # Predict conversion probability (class 1)
            prob = pipeline.predict_proba(input_df)[0][1]
            logger.info(f"Local ML model prediction for customer {customer.id}: P_ML={prob:.4f}")
            return float(prob)
        except Exception as err:
            logger.error(f"Error executing local ML prediction: {err}")
            return None
