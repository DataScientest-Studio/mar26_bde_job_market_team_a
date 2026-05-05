from airflow.sdk import dag, task
from datetime import datetime

import joblib

from src.database import create_engine
from src.models.train_models import train_clustering_model, retrieve_features_clustering

@dag(schedule="@weekly", start_date=datetime(2026, 5, 4))
def ml_workflow():
    @task
    def train_clustering():
        engine = create_engine()
        df = retrieve_features_clustering(engine)
        kmeans, scaler, mlb = train_clustering_model(df)
        return {
            "kmeans": kmeans,
            "scaler": scaler,
            "mlb": mlb
        }

    @task
    def save_model(model: dict):
        joblib.dump(model["kmeans"], "kmeans.pkl")
        joblib.dump(model["scaler"], "scaler.pkl")
        joblib.dump(model["mlb"], "mlb.pkl")

    model = train_clustering()
    save_model(model)
ml_workflow()