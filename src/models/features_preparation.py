"""
- MODEL CHOICE : Logistic Regression or LightGBM
Step 1: “true relevance score”
    relevance_score =
        0.5 * skill_match
    + 0.15 * location_match
    + 0.15 * salary_match
    + 0.1 * experience_match
    + 0.1 * contract_match

Step 2: convert to label
    Option A
        label = 1 if relevance_score > 0.7
        label = 0 otherwise
    Option B
        top 10 jobs per user → label = 1
        rest → label = 0

{
    "user": {
        "skills": ["python", "sql"],
        "location": "Paris",
        "region": "Ile-de-France",
        "expected_salary": 50000,
        "contract_preference": "full-time"
        "experience_years": 3
    },
}
"""

import pandas as pd

from sqlalchemy import Engine, engine, func, desc
from sqlmodel import select
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from src.api.models import Contract, JobOffer, Location, Salary, JobSkill, Skill
from src.models.utils import (
    find_top_skills,
    skill_match_score,
    experience_years_score,
    salary_match_score,
    relevance_score
)

LABEL_THRESHOLD = 0.7

def retrieve_jobs_regression(engine: Engine) -> pd.DataFrame:
    job_id = JobOffer.job_id.label("job_id")
    experience_years = JobOffer.experience_years.label("experience_years")
    contract_type = Contract.contract_type.label("contract_type")
    salary_amount = (func.coalesce((Salary.salary_min + Salary.salary_max) / 2)).label("mid_salary")
    skills = func.array_agg(Skill.skill_name).label("skills")
    location = func.concat(Location.city, ",", Location.region).label("location")

    query = (
        select(job_id, experience_years, contract_type, salary_amount, skills, location)
        .select_from(JobOffer)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .join(Location, JobOffer.location_id == Location.location_id)
        .where(Salary.frequency == 'yearly')
        .group_by(JobOffer.job_id, JobOffer.experience_years, Contract.contract_type, salary_amount, location)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql(query, engine)
    return df

def train_model(X, y):
    # This function will take your feature matrix X and label vector y and train a machine learning model
    # Logistic Regression or LightGBM
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression()
    model.fit(X, y)
    return model

def generate_training_data(jobs: pd.DataFrame) -> pd.DataFrame:
    training_rows = []

    for _, job in jobs.iterrows():
        user = {
            "skills": job["skills"],
            "location": job["city"],
            "region": job["region"],
            "expected_salary": job["mid_salary"],
            "contract_preference": job["contract_type"]
        }

        # Perfect match
        score = relevance_score(user, job)

        training_rows.append({
            "skill_match_score": skill_match_score(
                user["skills"],
                job["skills"]
            ),
            "location_match": int(user["location"] == job["city"]),
            "region_match": int(user["region"] == job["region"]),
            "salary_match_score": salary_match_score(
                job["mid_salary"],
                user["expected_salary"]
            ),
            "contract_match": int(
                user["contract_preference"] == job["contract_type"]
            ),
            "experience_years_score": experience_years_score(user["experience_years"], job["experience_years"]),
            "label": int(score >= LABEL_THRESHOLD)
        })

        # Different jobs for sampling
        negative_jobs = jobs.sample(5)

        for _, neg_job in negative_jobs.iterrows():
            neg_score = relevance_score(user, neg_job)
            training_rows.append({
                "skill_match_score": skill_match_score(
                    user["skills"],
                    neg_job["skills"]
                ),
                "location_match": int(
                    user["location"] == neg_job["city"]
                ),
                "region_match": int(
                    user["region"] == neg_job["region"]
                ),
                "salary_match_score": salary_match_score(
                    user["expected_salary"],
                    neg_job["mid_salary"]
                ),
                "contract_match": int(
                    user["contract_preference"] == neg_job["contract_type"]
                ),
                "experience_years_score": experience_years_score(user["experience_years"], neg_job["experience_years"]),
                "label": int(neg_score >= LABEL_THRESHOLD)
            })
    return pd.DataFrame(training_rows)

jobs = retrieve_jobs_regression(engine)
df_train = generate_training_data(jobs)

X = df_train.drop(columns=["label"])
y = df_train["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def train_model(X_train, y_train) -> Pipeline:
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            max_iter=1000,
            class_weight="balanced"
        ))
    ])

    pipeline.fit(X_train, y_train)
    return pipeline

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report
)

def evaluate_model(pipeline, X_test, y_test) -> None:
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Precision:", precision_score(y_test, y_pred))
    print("Recall:", recall_score(y_test, y_pred))
    print("F1:", f1_score(y_test, y_pred))
    print("ROC AUC:", roc_auc_score(y_test, y_prob))

    print(classification_report(y_test, y_pred))


from lightgbm import LGBMClassifier

def train_predict_lightgbm(X_train, y_train) -> LGBMClassifier:
    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("F1:", f1_score(y_test, y_pred))
    print("ROC AUC:", roc_auc_score(y_test, y_prob))

    return model

# """
# New model to predict salary for a specific job description (job type, skills, location, experience level, etc.)
# Features:
#     - job_type (one-hot)
#     - skills (multi-hot)
#     - location (one-hot)
#     - experience_level (categorical)
#     - contract_type (one-hot)
# """
