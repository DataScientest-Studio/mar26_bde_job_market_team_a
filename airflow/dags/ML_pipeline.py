from airflow.sdk import dag, task
from datetime import datetime
from pathlib import Path

import joblib

from src.database import create_engine
from src.models.train_models import train_clustering_model, retrieve_features_clustering

@dag(schedule="@weekly", start_date=datetime(2026, 5, 4))
def ml_workflow():
    @task
    def train_clustering():
        engine = create_engine()
        df = retrieve_features_clustering(engine)
        kmeans, scaler, mlb, df = train_clustering_model(df)
        return {
            "kmeans": kmeans,
            "scaler": scaler,
            "mlb": mlb,
            "df": df[["job_id", "cluster"]]
        }

    @task
    def save_model(model: dict):
        directory = Path("ml_trained_models")
        directory.mkdir(exist_ok=True)
        time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        joblib.dump(model["kmeans"], f"{directory}/kmeans_{time_stamp}.pkl")
        joblib.dump(model["scaler"], f"{directory}/scaler_{time_stamp}.pkl")
        joblib.dump(model["mlb"], f"{directory}/mlb_{time_stamp}.pkl")
        joblib.dump(model["df"], f"{directory}/df_{time_stamp}.pkl")

    model = train_clustering()
    save_model(model)
ml_workflow()