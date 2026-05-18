"""
Prepare data for clustering phase to reduce search space for the matching model.
This involves creating a user-job interaction matrix and applying dimensionality
reduction techniques to identify latent features that capture user preferences and job characteristics.
The resulting features will be used to cluster users and jobs into groups with similar profiles,
which can then be fed into the matching model for more efficient and accurate recommendations.

    - For our feature of job recommendation, we will limit at first the skill vobulary to take into account only
about 40-50 most common skills. This will help us to reduce the dimensionality of our feature space and avoid
overfitting in our model. We will also create a multi-hot encoding for the skills, where each skill is represented
as a binary feature indicating whether it is present or not in the job description.
This way, we can capture the presence of multiple skills in a single job offer and use this information to better
match users with relevant job offers.
    - As for the experience feature, we will encode it as a categorical variable with three levels: junior (0-2 years),
mid (3-5 years), and senior (6+ years).
    - For the salary feature, we will create buckets to group similar salary ranges together. For example, we can start 
with three buckets (<30k, 30-60k, >60k) and adjust them based on the distribution of salaries in our dataset. This has
to be adapted to the seniority level and the market, but it will help us to capture the relative salary expectations of
users and job offers without being too granular.
"""

import pandas as pd
import numpy as np

from sqlalchemy import func
from sqlmodel import select
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.cluster import KMeans

from src.api.models import Contract, JobOffer, Salary, JobSkill, Skill
from src.models.utils import _encode_experience, _salary_bucket, find_top_skills

def retrieve_features_clustering(engine) -> pd.DataFrame:
    job_id = JobOffer.job_id.label("job_id")
    contract_type = Contract.contract_type.label("contract_type")
    experience_years = JobOffer.experience_years.label("experience_years")
    salary_amount = (func.coalesce((Salary.salary_min + Salary.salary_max) / 2)).label("mid_salary")
    skills = func.array_agg(Skill.skill_name).label("skills")
    top_skills = find_top_skills(engine, limit=50)

    query = (
        select(job_id, contract_type, experience_years, salary_amount, skills)
        .select_from(JobOffer)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .where(Skill.skill_name.in_(top_skills))
        .group_by(JobOffer.job_id, JobOffer.experience_years, salary_amount)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(query, engine)
    print(f"Retrieved {len(df)} job offers with features for clustering.")
    return df

def encode_user_input(
    user_input: pd.DataFrame, mlbs: dict[str, MultiLabelBinarizer],
    scaler: StandardScaler) -> np.ndarray:
    # Skills
    skills_vec = mlbs["skills"].transform([user_input["skills"]])
    # Experience
    exp = _encode_experience(user_input["experience"])
    # Salary
    sal = _salary_bucket(user_input["salary"])
    # Contract type
    contract_vec = mlbs["contract_type"].transform([[user_input["contract_type"]]])
    # Combine
    user_vector = np.concatenate([
        skills_vec[0],
        [exp, sal]
    ])
    # Scale
    user_vector_scaled = scaler.transform([user_vector])
    return user_vector_scaled

# This function will be used to find candidate jobs for a user based on their input.
import joblib
def load_clustering_model():
    kmeans = joblib.load("kmeans.pkl")
    scaler = joblib.load("scaler.pkl")
    mlbs = joblib.load("mlbs.pkl")
    return kmeans, scaler, mlbs

# kmeans, scaler, mlbs = load_clustering_model()

def get_candidate_jobs(encoded_user_input: np.ndarray, df: pd.DataFrame, kmeans: KMeans) -> pd.DataFrame:
    # Predict cluster
    cluster_id = kmeans.predict(encoded_user_input)[0]
    candidates = df[df["cluster"] == cluster_id]
    return candidates

def prepare_features_for_prediction(user_input, df, kmeans, mlbs, scaler) -> pd.DataFrame:
    # Get clustering results to reduce search space
    encoded_user = encode_user_input(user_input, mlbs, scaler, kmeans)
    reduced_jobs = get_candidate_jobs(encoded_user, df, kmeans)
    return reduced_jobs
