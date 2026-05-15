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

from sqlalchemy import Engine, Integer, case, desc, engine, func
from sqlmodel import select

from src.api.models import Contract, Industry, JobOffer, JobType, Location, Salary, JobSkill, Skill


from sqlalchemy import Engine, Integer, case, desc, engine, func
from sqlmodel import select

import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.cluster import KMeans

from src.api.models import Contract, Industry, JobOffer, JobType, Location, Salary, JobSkill, Skill

def _encode_experience(x):
    if x <= 2:
        return 0  # junior
    elif x <= 5:
        return 1  # mid
    else:
        return 2  # senior

def _salary_bucket(x):
    if x < 30000:
        return 0
    elif x < 60000:
        return 1
    else:
        return 2

def _find_top_skills(engine, limit=50) -> list[str]:
    skill_name = Skill.skill_name.label("skill_name")
    skill_count = func.count().label("skill_count")
    query = (
        select(skill_name, skill_count).select_from(JobSkill)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .group_by(Skill.skill_name)
        .order_by(desc(skill_count))
        .limit(limit)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(query, engine)
    return df["skill_name"].tolist()

def retrieve_features_clustering(engine) -> pd.DataFrame:
    job_id = JobOffer.job_id.label("job_id")
    experience_years = JobOffer.experience_years.label("experience_years")
    salary_amount = (func.coalesce((Salary.salary_min + Salary.salary_max) / 2)).label("mid_salary")
    skills = func.array_agg(Skill.skill_name).label("skills")

    query = (
        select(job_id, experience_years, salary_amount, skills)
        .select_from(JobOffer)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        # .where(Salary.frequency == 'yearly')
        .group_by(JobOffer.job_id, JobOffer.experience_years, salary_amount)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(query, engine)
    print(f"Retrieved {len(df)} job offers with features for clustering.")
    return df

def encode_user_input(
    user_input: pd.DataFrame, mlb: MultiLabelBinarizer,
    scaler: StandardScaler) -> np.ndarray:
    # Skills
    skills_vec = mlb.transform([user_input["skills"]])
    # Experience
    exp = _encode_experience(user_input["experience"])
    # Salary
    sal = _salary_bucket(user_input["salary"])
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
    mlb = joblib.load("mlb.pkl")
    return kmeans, scaler, mlb

# kmeans, scaler, mlb = load_clustering_model()

def get_candidate_jobs(encoded_user_input: np.ndarray, df: pd.DataFrame, kmeans: KMeans) -> pd.DataFrame:
    # Predict cluster
    cluster_id = kmeans.predict(encoded_user_input)[0]
    candidates = df[df["cluster"] == cluster_id]
    return candidates


"""
- MODEL CHOICE : Logistic Regression or LightGBM
Step 1: “true relevance score”
    relevance_score =
        0.5 * skill_match
    + 0.2 * location_match
    + 0.2 * salary_match
    + 0.1 * contract_match

Step 2: convert to label
    Option A (simplest, good enough)
        label = 1 if relevance_score > 0.7
        label = 0 otherwise
    Option B (better)
        top 10 jobs per user → label = 1
        rest → label = 0

{
    "user": {
        "skills": ["python", "sql"],
        "location": "Paris",
        "region": "Ile-de-France",
        "expected_salary": 50000,
        "contract_preference": "full-time"
    },
}
"""


def retrieve_jobs_regression(engine: Engine) -> pd.DataFrame:
    job_id = JobOffer.job_id.label("job_id")
    job_type_id = JobOffer.job_type_id.label("job_type_id")
    experience_years = JobOffer.experience_years.label("experience_years")
    contract_type = Contract.contract_type.label("contract_type")
    salary_amount = (func.coalesce((Salary.salary_min + Salary.salary_max) / 2)).label("mid_salary")
    skills = func.array_agg(Skill.skill_name).label("skills")
    location = func.concat(Location.city, ",", Location.region).label("location")

    query = (
        select(job_id, job_type_id, experience_years, contract_type, salary_amount, skills, location)
        .select_from(JobOffer)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Location, JobOffer.location_id == Location.location_id)
        .where(Salary.frequency == 'yearly')
        .group_by(JobOffer.job_id, JobOffer.job_type_id, JobOffer.experience_years, Contract.contract_type, salary_amount, location)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql(query, engine)
    return df

def generate_training_data(jobs: pd.DataFrame, engine: Engine) -> list[tuple]:
    training_data = []
    for job in jobs.itertuples():
        # Create synthetic user based on job
        user = {
            "skills": job.skills,
            "location": job.location,
            "region": job.region,
            "expected_salary": job.salary,
            "contract_preference": job.contract_type
        }
        # Positive example
        training_data.append((user, job, relevance_score(user, job), 1))

        # Negative examples
        for _ in range(5):
            random_job = get_random_job(job["job_type_id"], jobs, engine)
            training_data.append((user, random_job, relevance_score(user, random_job), 0))

    return training_data

def get_random_job(job_type_id: int, jobs: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    query = select(JobOffer).where(JobOffer.job_type_id != job_type_id).order_by(func.random()).limit(5)
    random_job_ids = [row.job_id for row in pd.read_sql(query, engine).itertuples()]
    random_jobs = jobs.loc[jobs["job_id"].isin(random_job_ids)]
    return random_jobs


def skill_match_score(user_skills, job_skills) -> float:
    return len(set(user_skills) & set(job_skills)) / len(set(job_skills)) if job_skills else 0

def experience_gap(user_experience, required_experience) -> float:
    return user_experience - required_experience

def location_score(user_location, job_location, user_region, job_region) -> float:
    if user_location == job_location:
        return 1.0
    elif user_region == job_region:
        return 0.5
    else:
        return 0.0

def salary_ratio(job_salary, expected_salary) -> float:
    return job_salary / expected_salary if expected_salary != 0 else 0

def contract_match(user_contract_preference, job_contract_type) -> float:
    return 1.0 if user_contract_preference == job_contract_type else 0.0

def remote_match(user_remote_preference, job_remote_option) -> float:
    return 1.0 if user_remote_preference == job_remote_option else 0.0

def relevance_score(user, job) -> float:
    return (
        0.5 * skill_match_score(user["skills"], job["skills"]) +
        0.2 * location_score(user["location"], job["location"], user["region"], job["region"]) +
        0.2 * salary_ratio(job["mid_salary"], user["expected_salary"]) +
        0.1 * contract_match(user["contract_preference"], job["contract_type"])
    )

# 2. How do you prepare your features for the matching model? Encodings and cleaning and normalization, etc.
def prepare_features_regression(training_data):
    # This function will take your raw training data and convert it into a feature matrix X and label vector y
    df = pd.DataFrame(training_data, columns=["user", "job", "relevance_score", "label"])

    # Get top skills
    top_skills = _find_top_skills(50)

    # Create feature skill score match
    df["skill_match_score"] = df.apply(lambda row: skill_match_score(row["user"]["skills"], row["job"]["skills"]), axis=1)
    feature_cols = ["skill_match_score"]

    # Normalize salaries
    df['user_salary_norm'] = (df['user']['expected_salary'] - df['user']['expected_salary'].mean()) / df['user']['expected_salary'].std()
    df['job_salary_norm'] = (df['job']['salary'] - df['job']['salary'].mean()) / df['job']['salary'].std()
    feature_cols.extend(['user_salary_norm', 'job_salary_norm'])

    # Location and region matches
    df['location_match'] = df.apply(lambda row: 1 if row['user']['location'] == row['job']['location'] else 0, axis=1)
    df['region_match'] = df.apply(lambda row: 1 if row['user']['region'] == row['job']['region'] else 0, axis=1)
    feature_cols.extend(['location_match', 'region_match'])

    # Contract match
    df['contract_match'] = df.apply(lambda row: 1 if row['user']['contract_preference'] == row['job']['contract_type'] else 0, axis=1)
    feature_cols.append('contract_match')

    # Feature matrix X and label vector y
    X = df[feature_cols]
    y = df["label"]

    return X, y

def train_model(X, y):
    # This function will take your feature matrix X and label vector y and train a machine learning model
    # Logistic Regression or LightGBM
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression()
    model.fit(X, y)
    return model

def predict(user_input, model, mlb, scaler):
    result = model.predict_proba(prepare_features_for_prediction(user_input, mlb, scaler))[:, 1]
    return result # [("job_id_1", 0.9), ("job_id_2", 0.8), ("job_id_3", 0.7)]

def prepare_features_for_prediction(user_input, df, kmeans, mlb, scaler) -> pd.DataFrame:
    # Get clustering results to reduce search space
    encoded_user = encode_user_input(user_input, mlb, scaler, kmeans)
    reduced_jobs = get_candidate_jobs(encoded_user, df, kmeans)
    return reduced_jobs



"""
New model to predict salary for a specific job description (job type, skills, location, experience level, etc.)
Features:
    - job_type (one-hot)
    - skills (multi-hot)
    - location (one-hot)
    - experience_level (categorical)
    - contract_type (one-hot)
"""
