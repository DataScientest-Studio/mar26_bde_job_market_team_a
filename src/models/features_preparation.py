"""
Préparation ML pour le projet Job Market.

Ce fichier sert de support de conception pour expliquer le modèle sans aller trop
loin dans l'implémentation. Il suit les idées de la fiche ML :

- apprentissage supervisé : on prédit une variable cible connue ;
- apprentissage non supervisé : on cherche des groupes sans variable cible ;
- train/test split : on garde une partie des données pour évaluer le modèle ;
- métriques : elles dépendent du type de problème.

Dans notre projet, il y a deux pistes ML possibles.

1. Recommandation d'offres
   Type de problème :
   - classification supervisée : on prédit si une offre est pertinente pour un
     profil candidat.
   - comme le projet n'a pas de vrais clics/candidatures, on fabrique des labels
     synthétiques depuis les offres PostgreSQL.

   Variable cible possible :
   - label = 1 si l'offre est pertinente pour un profil candidat ;
   - label = 0 sinon.

   Variables explicatives possibles :
   - compétences présentes dans l'offre, encodées en multi-hot ;
   - années d'expérience demandées ;
   - salaire moyen ou tranche de salaire ;
   - type de contrat ;
   - remote / télétravail ;
   - localisation ;
   - secteur d'activité ;
   - titre du poste.

   Algo choisi pour une première version simple :
   - LogisticRegression pour prédire une probabilité de pertinence.
   - NearestNeighbors sert seulement de préfiltre pour ne pas scorer toutes les
     offres quand la base grossit.
   - Le modèle est entraîné avec .fit et utilisé avec .predict_proba.

2. Prediction de salaire
   Type de problème :
   - régression supervisée.

   Variable cible :
   - salaire annuel estimé.

   Variables explicatives possibles :
   - titre du poste ;
   - compétences ;
   - experience_years ;
   - localisation ;
   - type de contrat ;
   - remote ;
   - secteur.

   Algo simple possible :
   - DecisionTreeRegressor, comme dans la fiche ML.
   - Avantage : lisible, facile à expliquer.
   - Limite : risque de surapprentissage si l'arbre est trop profond.

Ce fichier reste volontairement léger : il documente le raisonnement ML et
prépare un modèle simple à partir des tables PostgreSQL analytics.
"""

from __future__ import annotations

import os
import joblib
import pandas as pd
from pathlib import Path
from dataclasses import dataclass

from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

from src.database import load_project_env
from src.models.utils import (
    find_top_skills,
    location_match_score,
    skill_match_score,
    experience_years_score,
    salary_match_score,
    relevance_score,
    encode_experience,
    salary_bucket
)


DEFAULT_MODEL_ARTIFACTS_FILENAME = "job_market_model_artifacts.pkl"
DEFAULT_LABEL_THRESHOLD = 0.6


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)


@dataclass
class JobMarketModelArtifacts:
    """
    Tous les objets créés pendant l'entraînement ML.

    - training_df : données nettoyées issues de PostgreSQL ;
    - mlbs : encodeur multi-hot des compétences ;
    - kmeans_scaler / salary_scaler : standardisation des variables ;
    - ranking_scaler : standardisation des variables user-job ;
    - kmeans_model : modèle de clusters pour les recommandations ;
    - ranking_model : classification supervisée de pertinence ;
    - salary_model : modèle supervisé de régression pour le salaire.
    """

    training_df: pd.DataFrame
    mlbs: dict[str, MultiLabelBinarizer]
    kmeans_scaler: StandardScaler
    salary_scaler: StandardScaler
    ranking_scaler: StandardScaler
    kmeans_model: KMeans
    ranking_model: LogisticRegression
    salary_model: KNeighborsRegressor
    metrics: dict[str, dict[str, float]]
    top_skills: list[str]


def get_model_dir(model_dir: str | Path | None = None) -> Path:
    """
    Répertoire des artefacts ML.

    Priorité :
    - argument explicite ;
    - variable d'environnement MODEL_DIR ;
    - dossier local models/.
    """
    load_project_env()
    return Path(model_dir or os.getenv("MODEL_DIR", "models"))


def get_model_artifacts_path(model_dir: str | Path | None = None) -> Path:
    return get_model_dir(model_dir) / os.getenv("MODEL_ARTIFACTS_FILENAME", DEFAULT_MODEL_ARTIFACTS_FILENAME)


def save_job_market_artifacts(artifacts: JobMarketModelArtifacts, model_dir: str | Path | None = None) -> Path:
    """
    Sauvegarde l'artefact complet utilisé par l'API.

    Les fichiers séparés restent utiles pour inspecter rapidement les objets,
    mais l'API charge principalement job_market_model_artifacts.pkl.
    """
    model_path = get_model_dir(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    # TODO Add versionining to artifacts and filename for better tracking of model versions
    artifacts_path = model_path / os.getenv("MODEL_ARTIFACTS_FILENAME", DEFAULT_MODEL_ARTIFACTS_FILENAME)
    joblib.dump(artifacts, artifacts_path)
    return artifacts_path


def load_job_market_artifacts(model_dir: str | Path | None = None) -> JobMarketModelArtifacts:
    """
    Charge les artefacts entraînés par make ml-train.
    """
    artifacts_path = get_model_artifacts_path(model_dir)
    if not artifacts_path.exists():
        raise FileNotFoundError(f"Artefact ML introuvable: {artifacts_path}")
    artifacts = joblib.load(artifacts_path)
    if not isinstance(artifacts, JobMarketModelArtifacts):
        raise TypeError(f"Artefact ML invalide: {artifacts_path}")
    return artifacts


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage des données avant entraînement.

    Étape "suppression/traitement des nulls" de la fiche ML :
    - salaire : variable cible pour la régression, donc on supprime les lignes
      sans salaire exploitable ;
    - experience_years : valeur numérique manquante remplacée par 0 an ;
    - compétences : suppression des valeurs vides, puis suppression des offres
      sans compétence.
    """
    top_skills = set(find_top_skills())
    cleaned = df.copy()
    cleaned["skills"] = cleaned["skills"].apply(lambda skills: [skill for skill in skills if skill in top_skills])
    cleaned = cleaned[cleaned["skills"].apply(len) > 0]

    cleaned["experience_years"] = pd.to_numeric(cleaned["experience_years"], errors="coerce").fillna(0)
    cleaned["salary"] = pd.to_numeric(cleaned["salary"], errors="coerce")

    cleaned = cleaned.dropna(subset=["job_id", "salary"])
    cleaned = cleaned.reset_index(drop=True)
    return cleaned


def transform_features(clean_training_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, MultiLabelBinarizer]]:
    """
    Prépare les matrices X pour les modèles.

    Variables explicatives retenues dans cette version :
    - compétences : multi-hot encoding avec MultiLabelBinarizer ;
    - type de contrat : multi-hot encoding avec MultiLabelBinarizer ;
    - experience_years : variable ordinale junior/intermédiaire/senior ;
    - salaire attendu : variable ordinale par tranche pour la recommandation.

    Encodage :
    - MultiLabelBinarizer transforme une liste de compétences en colonnes 0/1.
    """
    mlb_skills = MultiLabelBinarizer()
    skills_encoded = mlb_skills.fit_transform(clean_training_df["skills"])
    skills_df = pd.DataFrame(skills_encoded, columns=mlb_skills.classes_, index=clean_training_df.index)

    mlb_contract = MultiLabelBinarizer()
    contract_encoded = mlb_contract.fit_transform(clean_training_df["contract_type"].apply(lambda x: [x] if x else []))
    contract_df = pd.DataFrame(contract_encoded, columns=mlb_contract.classes_)

    clean_training_df["exp_level"] = clean_training_df["experience_years"].apply(encode_experience)
    clean_training_df["salary_bucket"] = clean_training_df["salary"].apply(salary_bucket)

    transformmed_df = pd.concat([skills_df, contract_df, clean_training_df[["job_id", "salary", "exp_level", "salary_bucket"]]], axis=1)
    mlbs = {
        "skills": mlb_skills,
        "contract": mlb_contract
    }
    return transformmed_df, mlbs


def scale_features(transformed_df: pd.DataFrame) -> tuple[StandardScaler, pd.DataFrame]:
    """
    Standardisation :
    - StandardScaler centre/réduit les variables avant les modèles à distance.
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(transformed_df)

    return scaler, X_scaled


def get_features_for_job(job: pd.Series, user: dict) -> dict:
    return {
        "skill_match_score": skill_match_score(
            user["skills"],
            job["skills"]
        ),

        "location_match_score": location_match_score(
            user["location"],
            job["location"]
        ),

        "salary_match_score": salary_match_score(
            job["salary"],
            user["expected_salary"]
        ),

        "contract_match": int(
            user["contract_preference"] == job["contract_type"]
        ),

        "experience_years_score": experience_years_score(
            user["experience_years"],
            job["experience_years"]
        )
    }

def generate_training_data(jobs: pd.DataFrame) -> pd.DataFrame:
    threshold = _env_float("LABEL_THRESHOLD", DEFAULT_LABEL_THRESHOLD)
    training_rows = []

    for _, job in jobs.iterrows():
        user = {
            "skills": job["skills"],
            "location": job["location"],
            "expected_salary": job["salary"],
            "contract_preference": job["contract_type"],
            "experience_years": job["experience_years"]
        }

        # Perfect match
        score = relevance_score(user, job)
        training_rows.append(get_features_for_job(job, user) | {
            "label": int(score > threshold)
        })

        # Different jobs for sampling
        random_jobs = jobs.sample(5)

        for _, rand_job in random_jobs.iterrows():
            rand_job_score = relevance_score(user, rand_job)
            training_rows.append(get_features_for_job(rand_job, user) | {
                "label": int(rand_job_score > threshold)
            })
    return pd.DataFrame(training_rows)
