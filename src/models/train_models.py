import argparse
import os
import pandas as pd
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, f1_score,
    mean_absolute_error, precision_score, r2_score, recall_score,
    roc_auc_score, root_mean_squared_error
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor

from src.models.features_preparation import (
    clean_data, transform_features, scale_features, generate_training_data,
    save_job_market_artifacts, JobMarketModelArtifacts
)
from src.models.utils import find_top_skills, retrieve_jobs

DEFAULT_ML_N_CLUSTERS_KMEANS = 8


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def _fit_kmeans_model(X_scaled: pd.DataFrame) -> KMeans:
    n_clusters = min(_env_int("ML_N_CLUSTERS_KMEANS", DEFAULT_ML_N_CLUSTERS_KMEANS), len(X_scaled))
    if n_clusters < 1:
        raise ValueError("Impossible d'entrainer KMeans sur un dataset vide.")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(X_scaled)
    return kmeans


def _fit_salary_model(X_scaled: pd.DataFrame, target: pd.Series) -> KNeighborsRegressor:
    """
    Entraîne le modèle final de salaire sur toutes les données.
    """
    n_neighbors = min(10, len(X_scaled))
    model = KNeighborsRegressor(n_neighbors=n_neighbors, weights="distance")
    model.fit(X_scaled, target)
    return model


def _fit_ranking_model(X_scaled: pd.DataFrame, label: pd.Series) -> LogisticRegression:
    """
    Entraîne le modèle final de recommandation sur toutes les données.
    """
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_scaled, label)
    return model


def ml_train_pipeline(model_dir: str | Path | None = None) -> JobMarketModelArtifacts:
    """
    Entraîne les modèles à partir des offres PostgreSQL.

    Algo choisi pour les recommandations :
    - LogisticRegression, classification supervisée avec labels synthétiques ;
    - NearestNeighbors sert seulement à présélectionner les offres candidates.

    Algo choisi pour le salaire :
    - KNeighborsRegressor, régression supervisée simple avec y = salaire annuel.

    Pourquoi cet algo ?
    - le projet n'a pas de labels utilisateurs pour dire "bonne/mauvaise offre" ;
    - on peut quand même apprendre sur les offres PostgreSQL existantes ;
    - simple à expliquer dans une présentation ;
    - suffisant pour une première version sans labels utilisateurs.

    Appels ML explicites :
    - train_test_split(...) pour évaluer les modèles ;
    - .fit(...) pour entraîner les modèles ;
    - .predict_proba(...) classe les recommandations ;
    - .predict(...) est utilisé par predict_salary_from_profile().

    Après évaluation, les modèles sauvegardés sont réentraînés sur 100% des
    données pour maximiser les exemples disponibles côté API.
    """

    # clear cache pour forcer la récupération depuis PostgreSQL à chaque entraînement
    retrieve_jobs.cache_clear()
    find_top_skills.cache_clear()

    training_df = retrieve_jobs()
    clean_training_df = clean_data(training_df)

    if training_df.empty:
        raise ValueError("Impossible d'entraîner un modèle sur un dataset vide.")

    transformed_df, mlbs = transform_features(clean_training_df)

    # KMeans pour préfiltrer les recommandations par similarité.
    kmeans_scaler, X_kmeans_scaled = scale_features(transformed_df.drop(columns=["job_id", "salary"]))
    kmeans_model = _fit_kmeans_model(X_kmeans_scaled)
    clean_training_df["cluster"] = kmeans_model.labels_
    print("Training data after KMeans clustering finished - cluster distribution !")

    # LogisticRegression pour la recommandation.
    ranking_training_df = generate_training_data(clean_training_df)
    X_ranking_train, X_ranking_test, y_ranking_train, y_ranking_test = train_test_split(
        ranking_training_df.drop(columns=["label"]),
        ranking_training_df["label"],
        test_size=0.2,
        random_state=42,
        stratify=ranking_training_df["label"]
    )
    ranking_scaler, X_train_scaled = scale_features(X_ranking_train)
    ranking_model = _fit_ranking_model(X_train_scaled, y_ranking_train)
    X_ranking_test_scaled = ranking_scaler.transform(X_ranking_test)
    ranking_y_pred = ranking_model.predict(X_ranking_test_scaled)
    ranking_y_prob = ranking_model.predict_proba(X_ranking_test_scaled)[:, 1]
    ranking_model_metrics = {
        "ranking_accuracy": accuracy_score(y_ranking_test, ranking_y_pred),
        "ranking_precision": precision_score(y_ranking_test, ranking_y_pred),
        "ranking_recall": recall_score(y_ranking_test, ranking_y_pred),
        "ranking_f1": f1_score(y_ranking_test, ranking_y_pred),
        "ranking_roc_auc": roc_auc_score(y_ranking_test, ranking_y_prob),
        "ranking_classification_report": classification_report(y_ranking_test, ranking_y_pred),
    }
    print("Training data after ranking model evaluation !")

    # LogisticRegression pour la prédiction des salaires.
    salary_X = transformed_df.drop(columns=["job_id", "salary", "salary_bucket"])
    salary_y = transformed_df["salary"]
    X_salary_train, X_salary_test, y_salary_train, y_salary_test = train_test_split(
        salary_X,
        salary_y,
        test_size=0.2,
        random_state=42
    )
    salary_scaler, X_train_scaled = scale_features(X_salary_train)
    salary_model = _fit_salary_model(X_train_scaled, y_salary_train)
    X_salary_test_scaled = salary_scaler.transform(X_salary_test)
    salary_y_pred = salary_model.predict(X_salary_test_scaled)

    salary_model_metrics = {
        "salary_mae": float(mean_absolute_error(y_salary_test, salary_y_pred)),
        "salary_rmse": float(root_mean_squared_error(y_salary_test, salary_y_pred)),
        "salary_r2": float(r2_score(y_salary_test, salary_y_pred)),
    }

    # Save metrics for API inspection
    metrics = {
        "ranking": ranking_model_metrics,
        "salary": salary_model_metrics
    }

    artifacts = JobMarketModelArtifacts(
        training_df=clean_training_df[["job_id", "cluster", "salary"]],
        mlbs=mlbs,
        kmeans_scaler=kmeans_scaler,
        salary_scaler=salary_scaler,
        ranking_scaler=ranking_scaler,
        kmeans_model=kmeans_model,
        ranking_model=ranking_model,
        salary_model=salary_model,
        metrics=metrics,
        top_skills=find_top_skills()
    )

    if model_dir is not None:
        save_job_market_artifacts(artifacts, model_dir)

    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Job Market ML models from PostgreSQL.")
    parser.add_argument(
        "--model-dir",
        default=os.getenv("MODEL_DIR", "models"),
        help="Directory where the ML artifact pickle is written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ml_train_pipeline(model_dir=args.model_dir)


if __name__ == "__main__":
    main()
