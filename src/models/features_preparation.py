"""
Preparation ML pour le projet Job Market.

Ce fichier sert de support de conception pour expliquer le modele sans aller trop
loin dans l'implementation. Il suit les idees de la fiche ML :

- apprentissage supervise : on predit une variable cible connue ;
- apprentissage non supervise : on cherche des groupes sans variable cible ;
- train/test split : on garde une partie des donnees pour evaluer le modele ;
- metriques : elles dependent du type de probleme.

Dans notre projet, il y a deux pistes ML possibles.

1. Recommendation d'offres
   Type de probleme :
   - classification supervisee : on predit si une offre est pertinente pour un
     profil candidat.
   - comme le projet n'a pas de vrais clics/candidatures, on fabrique des labels
     synthetiques depuis les offres PostgreSQL.

   Variable cible possible :
   - label = 1 si l'offre est pertinente pour un profil candidat ;
   - label = 0 sinon.

   Variables explicatives possibles :
   - competences presentes dans l'offre, encodees en multi-hot ;
   - annees d'experience demandees ;
   - salaire moyen ou tranche de salaire ;
   - type de contrat ;
   - remote / teletravail ;
   - localisation ;
   - secteur d'activite ;
   - titre du poste.

   Algo choisi pour une premiere version simple :
   - LogisticRegression pour predire une probabilite de pertinence.
   - NearestNeighbors sert seulement de prefiltre pour ne pas scorer toutes les
     offres quand la base grossit.
   - Le modele est entraine avec .fit et utilise avec .predict_proba.

2. Prediction de salaire
   Type de probleme :
   - regression supervisee.

   Variable cible :
   - salaire annuel estime.

   Variables explicatives possibles :
   - titre du poste ;
   - competences ;
   - experience ;
   - localisation ;
   - type de contrat ;
   - remote ;
   - secteur.

   Algo simple possible :
   - DecisionTreeRegressor, comme dans la fiche ML.
   - Avantage : lisible, facile a expliquer.
   - Limite : risque de surapprentissage si l'arbre est trop profond.

Ce fichier reste volontairement leger : il documente le raisonnement ML et
prepare un modele simple a partir des tables PostgreSQL analytics.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import unicodedata

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import case, func, or_
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor, NearestNeighbors
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sqlmodel import Session, select

from src.api.models import Company, Contract, Education, Industry, JobOffer, JobSkill, JobType, Location, Salary, Skill
from src.database import get_engine, load_project_env


MAX_TRAINING_JOBS = 5000
SKILL_LIMIT = 30
MODEL_ARTIFACTS_FILENAME = "job_market_model_artifacts.pkl"


@dataclass
class JobMarketModelArtifacts:
    """
    Tous les objets crees pendant l'entrainement ML.

    - training_df : donnees nettoyees issues de PostgreSQL ;
    - mlb : encodeur multi-hot des competences ;
    - similarity_scaler / salary_scaler : standardisation des variables ;
    - recommendation_scaler : standardisation des variables user-job ;
    - similarity_model : modele de voisins pour les recommandations ;
    - recommendation_model : classification supervisee de pertinence ;
    - salary_model : modele supervise de regression pour le salaire.
    """

    training_df: pd.DataFrame
    mlb: MultiLabelBinarizer
    similarity_scaler: StandardScaler
    salary_scaler: StandardScaler
    recommendation_scaler: StandardScaler
    similarity_model: NearestNeighbors
    recommendation_model: LogisticRegression
    salary_model: KNeighborsRegressor
    similarity_columns: list[str]
    salary_columns: list[str]
    recommendation_columns: list[str]
    metrics: dict[str, float]


def get_model_dir(model_dir: str | Path | None = None) -> Path:
    """
    Repertoire des artefacts ML.

    Priorite :
    - argument explicite ;
    - variable d'environnement MODEL_DIR ;
    - dossier local models/.
    """
    load_project_env()
    return Path(model_dir or os.getenv("MODEL_DIR", "models"))


def get_model_artifacts_path(model_dir: str | Path | None = None) -> Path:
    return get_model_dir(model_dir) / MODEL_ARTIFACTS_FILENAME


def save_job_market_artifacts(artifacts: JobMarketModelArtifacts, model_dir: str | Path | None = None) -> Path:
    """
    Sauvegarde l'artefact complet utilise par l'API.

    Les fichiers separes restent utiles pour inspecter rapidement les objets,
    mais l'API charge principalement job_market_model_artifacts.pkl.
    """
    model_path = get_model_dir(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    artifacts_path = model_path / MODEL_ARTIFACTS_FILENAME
    joblib.dump(artifacts, artifacts_path)
    joblib.dump(artifacts.similarity_model, model_path / "similarity_model.pkl")
    joblib.dump(artifacts.recommendation_model, model_path / "recommendation_model.pkl")
    joblib.dump(artifacts.salary_model, model_path / "salary_model.pkl")
    joblib.dump(artifacts.similarity_scaler, model_path / "similarity_scaler.pkl")
    joblib.dump(artifacts.recommendation_scaler, model_path / "recommendation_scaler.pkl")
    joblib.dump(artifacts.salary_scaler, model_path / "salary_scaler.pkl")
    joblib.dump(artifacts.mlb, model_path / "skills_encoder.pkl")
    return artifacts_path


def load_job_market_artifacts(model_dir: str | Path | None = None) -> JobMarketModelArtifacts:
    """
    Charge les artefacts entraines par make ml-train.
    """
    artifacts_path = get_model_artifacts_path(model_dir)
    if not artifacts_path.exists():
        raise FileNotFoundError(f"Artefact ML introuvable: {artifacts_path}")
    artifacts = joblib.load(artifacts_path)
    if not isinstance(artifacts, JobMarketModelArtifacts):
        raise TypeError(f"Artefact ML invalide: {artifacts_path}")
    return artifacts


def find_top_skills(limit: int = 50) -> list[str]:
    """
    Liste les competences les plus utiles pour limiter la dimension du modele.

    Idee ML :
    - si on garde toutes les competences, on cree trop de colonnes ;
    - on limite donc le vocabulaire aux competences les plus frequentes ;
    - les autres competences peuvent etre regroupees dans une categorie "other".

    Les valeurs viennent de PostgreSQL :
    - analytics.bridge_job_skill ;
    - analytics.dim_skill.
    """
    load_project_env()

    skill_count = func.count(func.distinct(JobSkill.job_id)).label("skill_count")
    statement = (
        select(Skill.skill_name, skill_count)
        .join(JobSkill, Skill.skill_id == JobSkill.skill_id)
        .where(func.nullif(Skill.skill_name, "").is_not(None))
        .group_by(Skill.skill_name)
        .order_by(skill_count.desc(), Skill.skill_name)
        .limit(limit)
    )

    with Session(get_engine()) as session:
        rows = session.exec(statement).all()

    return [row.skill_name.lower() for row in rows]


def retrieve_features() -> pd.DataFrame:
    """
    Recupere les variables explicatives necessaires au modele de similarite.

    Structure attendue :
    - id : identifiant de l'offre ;
    - skills : liste de competences ;
    - experience : experience demandee en annees ;
    - salary : salaire annuel moyen.
    - title/location/contract/remote/industry/education : variables de matching.

    Cette fonction lit les tables marts :
    - analytics.fact_job_offers ;
    - analytics.dim_salary ;
    - analytics.bridge_job_skill ;
    - analytics.dim_skill.
    """
    load_project_env()

    salary_amount = (
        func.coalesce(Salary.salary_min, Salary.salary_max) + func.coalesce(Salary.salary_max, Salary.salary_min)
    ) / 2
    annual_salary = case(
        (Salary.frequency == "month", salary_amount * 12),
        (Salary.frequency == "week", salary_amount * 52),
        (Salary.frequency == "hour", salary_amount * 35 * 52),
        else_=salary_amount,
    )
    location_label = func.concat_ws(", ", func.nullif(Location.city, ""), func.nullif(Location.region, ""))

    statement = (
        select(
            JobOffer.job_id.label("id"),
            JobType.title.label("title"),
            Company.name.label("company"),
            location_label.label("location"),
            Contract.contract_type.label("contract_type"),
            Contract.remote.label("remote"),
            Industry.industry_name.label("industry"),
            Education.title.label("education_level"),
            func.coalesce(JobOffer.experience_years, 0).label("experience"),
            annual_salary.label("salary"),
            Skill.skill_name.label("skill"),
        )
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .outerjoin(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .outerjoin(Company, JobOffer.company_id == Company.company_id)
        .outerjoin(Location, JobOffer.location_id == Location.location_id)
        .outerjoin(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .outerjoin(Industry, JobOffer.industry_id == Industry.industry_id)
        .outerjoin(Education, JobOffer.education_id == Education.education_id)
        .where(or_(Salary.salary_min.is_not(None), Salary.salary_max.is_not(None)))
        .where(func.nullif(Skill.skill_name, "").is_not(None))
        .where(annual_salary.between(10_000, 200_000))
        .order_by(JobOffer.published_at.desc().nulls_last())
        .limit(MAX_TRAINING_JOBS)
    )

    with Session(get_engine()) as session:
        rows = session.exec(statement).all()

    raw_df = pd.DataFrame([row._asdict() for row in rows])
    if raw_df.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "title",
                "company",
                "location",
                "contract_type",
                "remote",
                "industry",
                "education_level",
                "skills",
                "experience",
                "salary",
            ]
        )

    grouped_df = (
        raw_df.groupby(
            [
                "id",
                "title",
                "company",
                "location",
                "contract_type",
                "remote",
                "industry",
                "education_level",
                "experience",
                "salary",
            ],
            dropna=False,
        )["skill"]
        .apply(lambda skills: sorted({str(skill).lower() for skill in skills if skill}))
        .reset_index(name="skills")
    )
    return clean_training_data(grouped_df)


def clean_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage des donnees avant entrainement.

    Etape "suppression/traitement des nulls" de la fiche ML :
    - salaire : variable cible pour la regression, donc on supprime les lignes
      sans salaire exploitable ;
    - experience : valeur numerique manquante remplacee par 0 an ;
    - competences : suppression des valeurs vides, puis suppression des offres
      sans competence.
    """
    cleaned = df.copy()
    cleaned["experience"] = pd.to_numeric(cleaned["experience"], errors="coerce").fillna(0)
    cleaned["salary"] = pd.to_numeric(cleaned["salary"], errors="coerce")
    cleaned["skills"] = cleaned["skills"].apply(
        lambda skills: sorted({str(skill).strip().lower() for skill in skills if str(skill).strip()})
    )

    cleaned = cleaned.dropna(subset=["id", "salary"])
    cleaned = cleaned[cleaned["skills"].apply(bool)]
    return cleaned.reset_index(drop=True)


def encode_experience(years: float) -> int:
    """
    Transforme une variable quantitative en variable ordinale.

    Variable explicative :
    - experience demandee.

    Encodage :
    - 0 = junior ;
    - 1 = intermediaire ;
    - 2 = senior.
    """
    if years <= 2:
        return 0
    if years <= 5:
        return 1
    return 2


def salary_bucket(salary: float) -> int:
    """
    Transforme le salaire en tranche.

    Variable explicative :
    - niveau de remuneration de l'offre.

    Encodage :
    - 0 = salaire bas ;
    - 1 = salaire moyen ;
    - 2 = salaire eleve.
    """
    if salary < 30000:
        return 0
    if salary < 60000:
        return 1
    return 2


def _normalize_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _text_match_score(user_value, job_value) -> float:
    """
    Score simple pour les variables qualitatives textuelles.

    On ne fait pas encore de NLP avance : pour une V0, on compare les libelles
    nettoyes et on calcule un petit recouvrement de mots.
    """
    user_text = _normalize_text(user_value)
    job_text = _normalize_text(job_value)
    if not user_text or not job_text:
        return 0.0
    if user_text in job_text or job_text in user_text:
        return 1.0

    user_words = set(user_text.replace(",", " ").split())
    job_words = set(job_text.replace(",", " ").split())
    return len(user_words & job_words) / len(user_words) if user_words else 0.0


def build_pair_features(user_input: dict, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Cree X pour un couple profil candidat / offre.

    Ces variables explicatives correspondent a une logique de recommandation :
    - proximite des competences ;
    - ecart d'experience ;
    - ecart de salaire ;
    - correspondance titre/localisation/contrat/remote/secteur/formation.
    """
    user_skills = {str(skill).strip().lower() for skill in user_input.get("skills", []) if str(skill).strip()}
    user_experience = float(user_input.get("experience", 0) or 0)
    user_salary = float(user_input.get("salary", 0) or 0)

    rows: list[dict] = []
    for _, job in jobs_df.iterrows():
        job_skills = {str(skill).strip().lower() for skill in job.get("skills", []) if str(skill).strip()}
        common_skills = user_skills & job_skills
        job_experience = float(job.get("experience", 0) or 0)
        job_salary = float(job.get("salary", 0) or 0)

        rows.append(
            {
                "skill_match_user": len(common_skills) / len(user_skills) if user_skills else 0.0,
                "skill_match_job": len(common_skills) / len(job_skills) if job_skills else 0.0,
                "experience_gap_abs": abs(user_experience - job_experience),
                "experience_ok": 1.0 if user_experience >= job_experience else 0.0,
                "salary_gap_ratio": abs(user_salary - job_salary) / max(user_salary, 1.0),
                "salary_ratio": job_salary / max(user_salary, 1.0),
                "title_match": _text_match_score(user_input.get("job_title"), job.get("title")),
                "location_match": _text_match_score(user_input.get("location"), job.get("location")),
                "contract_match": _text_match_score(user_input.get("contract_type"), job.get("contract_type")),
                "remote_match": _text_match_score(user_input.get("remote"), job.get("remote")),
                "industry_match": _text_match_score(user_input.get("industry"), job.get("industry")),
                "education_match": _text_match_score(user_input.get("education_level"), job.get("education_level")),
            }
        )

    return pd.DataFrame(rows)


def _job_row_to_user_input(job: pd.Series) -> dict:
    return {
        "skills": list(job["skills"]),
        "experience": float(job["experience"]),
        "salary": float(job["salary"]),
        "job_title": job.get("title"),
        "location": job.get("location"),
        "contract_type": job.get("contract_type"),
        "remote": job.get("remote"),
        "industry": job.get("industry"),
        "education_level": job.get("education_level"),
    }


def build_recommendation_training_set(
    training_df: pd.DataFrame,
    negative_samples: int = 3,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Construit un dataset supervise pour la recommandation.

    Comme on n'a pas de vrais clics/candidatures, on cree des labels synthetiques
    depuis PostgreSQL :
    - label 1 : le profil candidat derive d'une offre correspond a cette offre ;
    - label 0 : ce meme profil est associe a quelques offres aleatoires.

    Cela donne une vraie classification binaire avec X, y, .fit et .predict_proba,
    tout en restant base uniquement sur les offres stockees en base.
    """
    rng = np.random.default_rng(42)
    feature_blocks: list[pd.DataFrame] = []
    labels: list[int] = []
    all_indices = np.arange(len(training_df))

    for index, job in training_df.iterrows():
        user_input = _job_row_to_user_input(job)

        positive_job = training_df.iloc[[index]]
        feature_blocks.append(build_pair_features(user_input, positive_job))
        labels.append(1)

        available_negative_indices = all_indices[all_indices != index]
        sample_size = min(negative_samples, len(available_negative_indices))
        negative_indices = rng.choice(available_negative_indices, size=sample_size, replace=False)
        negative_jobs = training_df.iloc[negative_indices]
        feature_blocks.append(build_pair_features(user_input, negative_jobs))
        labels.extend([0] * len(negative_jobs))

    X = pd.concat(feature_blocks, ignore_index=True)
    y = pd.Series(labels, name="label")
    return X, y


def prepare_model_features(
    df: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    StandardScaler,
    StandardScaler,
    MultiLabelBinarizer,
]:
    """
    Prepare les matrices X pour les modeles.

    Variables explicatives retenues dans cette version :
    - competences : multi-hot encoding avec MultiLabelBinarizer ;
    - experience : variable ordinale junior/intermediaire/senior ;
    - salaire attendu : variable ordinale par tranche pour la recommandation.

    Encodage :
    - MultiLabelBinarizer transforme une liste de competences en colonnes 0/1.

    Standardisation :
    - StandardScaler centre/reduit les variables avant les modeles a distance.

    Pourquoi deux matrices ?
    - recommendation : utilise competences + experience + tranche de salaire ;
    - prediction de salaire : utilise competences + experience, car le salaire
      est la variable cible y et ne doit pas etre dans X.

    Pourquoi standardiser ?
    - le modele compare les offres avec des distances ;
    - les variables numeriques doivent donc etre mises sur une echelle comparable.
    """
    prepared = clean_training_data(df)
    top_skills = set(find_top_skills(limit=SKILL_LIMIT))
    prepared["skills"] = prepared["skills"].apply(lambda skills: [str(skill).lower() for skill in skills])
    prepared["skills"] = prepared["skills"].apply(lambda skills: [skill for skill in skills if skill in top_skills])
    prepared["skills"] = prepared["skills"].apply(lambda skills: skills if skills else ["other"])

    mlb = MultiLabelBinarizer()
    skills_encoded = mlb.fit_transform(prepared["skills"])
    skills_df = pd.DataFrame(skills_encoded, columns=mlb.classes_, index=prepared.index)

    prepared["exp_level"] = prepared["experience"].apply(encode_experience)
    prepared["salary_bucket"] = prepared["salary"].apply(salary_bucket)

    similarity_X = pd.concat([skills_df, prepared[["exp_level", "salary_bucket"]]], axis=1)
    salary_X = pd.concat([skills_df, prepared[["exp_level"]]], axis=1)

    similarity_scaler = StandardScaler()
    similarity_X_scaled = pd.DataFrame(
        similarity_scaler.fit_transform(similarity_X),
        columns=similarity_X.columns,
        index=similarity_X.index,
    )

    salary_scaler = StandardScaler()
    salary_X_scaled = pd.DataFrame(
        salary_scaler.fit_transform(salary_X),
        columns=salary_X.columns,
        index=salary_X.index,
    )

    return prepared, salary_X, similarity_X_scaled, salary_X_scaled, similarity_scaler, salary_scaler, mlb


def evaluate_recommendation_model(recommendation_X: pd.DataFrame, recommendation_y: pd.Series) -> dict[str, float]:
    """
    Evalue le modele de recommandation avec un train/test split.

    Le scaler est entraine uniquement sur X_train pour eviter une fuite
    d'information depuis le jeu de test.
    """
    stratify = recommendation_y if recommendation_y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        recommendation_X,
        recommendation_y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    return {
        "recommendation_accuracy": float(accuracy_score(y_test, y_pred)),
        "recommendation_precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recommendation_recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "recommendation_f1": float(f1_score(y_test, y_pred, zero_division=0)),
    }


def evaluate_salary_model(salary_X: pd.DataFrame, salary_y: pd.Series) -> dict[str, float]:
    """
    Evalue le modele de salaire avec un train/test split.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        salary_X,
        salary_y,
        test_size=0.2,
        random_state=42,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    n_neighbors = min(10, len(X_train))
    model = KNeighborsRegressor(n_neighbors=n_neighbors, weights="distance")
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    mse = mean_squared_error(y_test, y_pred)
    return {
        "salary_mae": float(mean_absolute_error(y_test, y_pred)),
        "salary_rmse": float(np.sqrt(mse)),
        "salary_r2": float(r2_score(y_test, y_pred)),
    }


def fit_similarity_model(similarity_X_scaled: pd.DataFrame, n_neighbors: int) -> NearestNeighbors:
    """
    Entraine le prefiltre de voisins sur toutes les offres.
    """
    effective_neighbors = min(n_neighbors, len(similarity_X_scaled))
    model = NearestNeighbors(n_neighbors=effective_neighbors, metric="euclidean")
    model.fit(similarity_X_scaled)
    return model


def fit_recommendation_model(recommendation_X: pd.DataFrame, recommendation_y: pd.Series) -> tuple[LogisticRegression, StandardScaler, pd.DataFrame]:
    """
    Entraine le modele final de recommandation sur toutes les donnees.
    """
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(recommendation_X), columns=recommendation_X.columns)

    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model.fit(X_scaled, recommendation_y)
    return model, scaler, X_scaled


def fit_salary_model(salary_X_scaled: pd.DataFrame, salary_y: pd.Series) -> KNeighborsRegressor:
    """
    Entraine le modele final de salaire sur toutes les donnees.
    """
    n_neighbors = min(10, len(salary_X_scaled))
    model = KNeighborsRegressor(n_neighbors=n_neighbors, weights="distance")
    model.fit(salary_X_scaled, salary_y)
    return model


def train_job_market_models(
    df: pd.DataFrame | None = None,
    n_neighbors: int = 50,
    model_dir: str | Path | None = None,
) -> JobMarketModelArtifacts:
    """
    Entraine les modeles a partir des offres PostgreSQL.

    Algo choisi pour les recommandations :
    - LogisticRegression, classification supervisee avec labels synthetiques ;
    - NearestNeighbors sert seulement a preselectionner les offres candidates.

    Algo choisi pour le salaire :
    - KNeighborsRegressor, regression supervisee simple avec y = salaire annuel.

    Pourquoi cet algo ?
    - le projet n'a pas de labels utilisateurs pour dire "bonne/mauvaise offre" ;
    - on peut quand meme apprendre sur les offres PostgreSQL existantes ;
    - simple a expliquer dans une presentation ;
    - suffisant pour une premiere version sans labels utilisateurs.

    Appels ML explicites :
    - train_test_split(...) pour evaluer les modeles ;
    - .fit(...) pour entrainer les modeles ;
    - .predict_proba(...) classe les recommandations ;
    - .predict(...) est utilise par predict_salary_from_profile().

    Apres evaluation, les modeles sauvegardes sont reentraines sur 100% des
    donnees pour maximiser les exemples disponibles cote API.
    """
    training_df = retrieve_features() if df is None else df.copy()
    if training_df.empty:
        raise ValueError("Impossible d'entrainer un modele sur un dataset vide.")

    (
        training_df,
        salary_X,
        similarity_X_scaled,
        salary_X_scaled,
        similarity_scaler,
        salary_scaler,
        mlb,
    ) = prepare_model_features(training_df)

    recommendation_X, recommendation_y = build_recommendation_training_set(training_df)
    metrics = {
        **evaluate_recommendation_model(recommendation_X, recommendation_y),
        **evaluate_salary_model(salary_X, training_df["salary"]),
    }

    similarity_model = fit_similarity_model(similarity_X_scaled, n_neighbors)
    recommendation_model, recommendation_scaler, recommendation_X_scaled = fit_recommendation_model(
        recommendation_X,
        recommendation_y,
    )
    salary_model = fit_salary_model(salary_X_scaled, training_df["salary"])

    artifacts = JobMarketModelArtifacts(
        training_df=training_df,
        mlb=mlb,
        similarity_scaler=similarity_scaler,
        salary_scaler=salary_scaler,
        recommendation_scaler=recommendation_scaler,
        similarity_model=similarity_model,
        recommendation_model=recommendation_model,
        salary_model=salary_model,
        similarity_columns=list(similarity_X_scaled.columns),
        salary_columns=list(salary_X_scaled.columns),
        recommendation_columns=list(recommendation_X_scaled.columns),
        metrics=metrics,
    )

    if model_dir is not None:
        save_job_market_artifacts(artifacts, model_dir)

    return artifacts


def encode_user_input(user_input: dict, mlb: MultiLabelBinarizer) -> pd.DataFrame:
    """
    Encode un profil candidat dans le meme format que les offres.

    Entree attendue :
    {
        "skills": ["python", "sql"],
        "experience": 3,
        "salary": 45000
    }
    """
    known_classes = set(mlb.classes_)
    known_skills = [skill for skill in user_input["skills"] if skill in known_classes]
    if not known_skills and "other" in known_classes:
        known_skills = ["other"]

    skills_vec = mlb.transform([known_skills])
    exp = encode_experience(user_input["experience"])
    sal = salary_bucket(user_input["salary"])
    columns = list(mlb.classes_) + ["exp_level", "salary_bucket"]
    user_vector = pd.DataFrame([np.concatenate([skills_vec[0], [exp, sal]])], columns=columns)
    return user_vector


def transform_similarity_input(user_input: dict, artifacts: JobMarketModelArtifacts) -> pd.DataFrame:
    """
    Standardise le profil candidat pour le modele de recommandation.
    """
    user_vector = encode_user_input(user_input, artifacts.mlb)
    scaled = artifacts.similarity_scaler.transform(user_vector[artifacts.similarity_columns])
    return pd.DataFrame(scaled, columns=artifacts.similarity_columns)


def transform_salary_input(user_input: dict, artifacts: JobMarketModelArtifacts) -> pd.DataFrame:
    """
    Standardise le profil candidat pour le modele de prediction de salaire.
    """
    user_vector = encode_user_input(user_input, artifacts.mlb)
    scaled = artifacts.salary_scaler.transform(user_vector[artifacts.salary_columns])
    return pd.DataFrame(scaled, columns=artifacts.salary_columns)


def get_similar_jobs(
    user_input: dict,
    artifacts: JobMarketModelArtifacts,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Retrouve les offres les plus proches du profil candidat.

    Principe :
    - on encode le candidat comme une offre ;
    - on calcule les distances avec les offres PostgreSQL encodees ;
    - on garde les offres les plus proches.

    Ce n'est pas encore une recommandation supervisee. C'est une reduction de
    l'espace de recherche avant une future logique plus avancee.
    """
    user_vector_scaled = transform_similarity_input(user_input, artifacts)
    effective_limit = min(max(limit, 1), len(artifacts.training_df))
    distances, indices = artifacts.similarity_model.kneighbors(user_vector_scaled, n_neighbors=effective_limit)
    candidates = artifacts.training_df.iloc[indices[0]].copy()
    candidates["distance"] = distances[0]
    return candidates.reset_index(drop=True)


def get_title_matched_jobs(
    user_input: dict,
    artifacts: JobMarketModelArtifacts,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Recupere des offres candidates a partir de l'intitule recherche.

    Le prefiltre de similarite utilise surtout competences, experience et
    salaire. Cette fonction ajoute un deuxieme rappel base sur le titre pour
    eviter de recommander un metier hors sujet quand les competences sont
    generiques.
    """
    if not _normalize_text(user_input.get("job_title")):
        return artifacts.training_df.iloc[0:0].copy()

    candidates = artifacts.training_df.copy()
    candidates["title_match"] = candidates["title"].apply(lambda title: _text_match_score(user_input.get("job_title"), title))
    candidates = candidates[candidates["title_match"] > 0]
    candidates = candidates.sort_values("title_match", ascending=False).head(limit)
    return candidates.reset_index(drop=True)


def get_recommendation_candidates(
    user_input: dict,
    artifacts: JobMarketModelArtifacts,
    limit: int = 100,
) -> pd.DataFrame:
    """
    Combine les candidats proches par profil et les candidats proches par titre.
    """
    profile_candidates = get_similar_jobs(user_input, artifacts, limit=limit)
    title_candidates = get_title_matched_jobs(user_input, artifacts, limit=limit)
    candidates = pd.concat([title_candidates, profile_candidates], ignore_index=True, sort=False)
    if candidates.empty:
        return candidates
    return candidates.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)


def predict_relevance_for_jobs(
    user_input: dict,
    jobs_df: pd.DataFrame,
    artifacts: JobMarketModelArtifacts,
) -> pd.DataFrame:
    """
    Score les offres candidates avec le modele de recommandation.

    C'est la partie prediction de la recommandation :
    - X user-job est cree avec build_pair_features ;
    - X est standardise avec le scaler appris au .fit ;
    - recommendation_model.predict_proba(X) renvoie la probabilite de label 1.
    """
    if jobs_df.empty:
        return jobs_df.copy()

    pair_features = build_pair_features(user_input, jobs_df)
    pair_features = pair_features[artifacts.recommendation_columns]
    pair_features_scaled = pd.DataFrame(
        artifacts.recommendation_scaler.transform(pair_features),
        columns=artifacts.recommendation_columns,
    )

    model_score = artifacts.recommendation_model.predict_proba(pair_features_scaled)[:, 1]
    title_match = pair_features["title_match"].to_numpy()

    scored_jobs = jobs_df.copy()
    scored_jobs["model_score"] = model_score
    scored_jobs["title_match"] = title_match
    if _normalize_text(user_input.get("job_title")):
        scored_jobs["score"] = 0.45 * scored_jobs["model_score"] + 0.55 * scored_jobs["title_match"]
    else:
        scored_jobs["score"] = scored_jobs["model_score"]
    scored_jobs["predicted_label"] = artifacts.recommendation_model.predict(pair_features_scaled)
    return scored_jobs


def predict_salary_from_profile(user_input: dict, artifacts: JobMarketModelArtifacts) -> float:
    """
    Predire un salaire avec le modele supervise.

    C'est l'etape .predict(...) attendue dans une logique ML classique :
    - X candidat est encode ;
    - X candidat est standardise ;
    - salary_model.predict(X) renvoie le salaire annuel estime.
    """
    user_vector_scaled = transform_salary_input(user_input, artifacts)
    return float(artifacts.salary_model.predict(user_vector_scaled)[0])
