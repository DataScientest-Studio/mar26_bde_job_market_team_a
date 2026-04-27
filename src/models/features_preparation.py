"""
User inputs:
    - skills
    - preferred location
    - expected salary
    - experience
    - contract preference
    - industry preference
Outputs:
    - recommended job offers
    - predicted salary


match(user, job) → probability of interest

skill_match_score = # overlap ratio |user_skills ∩ job_skills| / |job_skills|
experience_gap = user_experience - required_experience
location_score =    |  1 = same city  
                    |  0.5 = same region  
                    |  0 = different

salary_ratio = job_salary / expected_salary
contract_match (0/1)
remote_match (0/1)


job_popularity = # number of interactions in last X days
market_demand_score = # how often similar jobs appear


# SQL Tables structure:
features_user_job
-----------------
user_id
job_id

skill_match_score
experience_gap
location_score
salary_ratio
contract_match
remote_match
job_popularity
market_demand_score

label
label = 1 → applied / clicked  
label = 0 → ignored

positive = top matches
negative = random jobs


- MODEL CHOICE : Logistic Regression or LightGBM (if you want slight upgrade)
Step 1: create a “true relevance score”
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

If you stop here, it’s basic.
To make it credible:
    - add randomness (noise)
    - don’t make rules too perfect
label = 1 if relevance_score + random_noise > threshold
"""


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

def find_top_skills(limit=50):
    query = f"""
        SELECT skill_name, COUNT(*) AS skill_count
        FROM bridge_job_skill bjs
        JOIN dim_skill ds ON bjs.skill_id = ds.skill_id
        GROUP BY skill_name
        ORDER BY skill_count DESC
        LIMIT {limit}
    """

    # Execute query and load data into DataFrame
    # df = pd.read_sql(query, connection)
    # return df["skill_name"].tolist()

    # For demonstration purposes, using a sample list of skills
    return ["python", "sql", "airflow", "aws", "docker", "kubernetes", "spark", "hadoop", "scala", "java"]

def retrieve_features():
    query = """
        SELECT jo.job_id, jo.experience_years, (ds.salary_max+ds.salary_min)/2 AS avg_salary, array_agg(ds.skill_name) AS skills
        FROM job_offers jo
        JOIN dim_salary ds ON jo.salary_id = ds.salary_id
        JOIN bridge_job_skill bjs ON jo.job_id = bjs.job_id
        JOIN dim_skill ds ON bjs.skill_id = ds.skill_id
        WHERE ds.frequency == 'yearly'
        GROUP BY jo.job_id, jo.experience_years, avg_salary
    """

    # Execute query and load data into DataFrame
    # df = pd.read_sql(query, connection)
    # return df

    # For demonstration purposes, using a sample DataFrame
    jobs = [
        {
            "id": 1,
            "skills": ["python", "sql", "airflow"],
            "experience": 3,
        "salary": 45000
        }
    ]
    return pd.DataFrame(jobs)

import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.cluster import KMeans

# -----------------------
# Load data
# -----------------------
df = retrieve_features()

# -----------------------
# 1. Skills encoding (multi-hot)
# -----------------------

# Limit skill vocabulary
# Before MultiLabelBinarizer:

top_skills = find_top_skills(limit=30)
df["skills"] = df["skills"].apply(lambda s: [x for x in s if x in top_skills])

# Avoid empty vectors
# If job has no skills after filtering:

df["skills"] = df["skills"].apply(lambda s: s if len(s) > 0 else ["other"])

mlb = MultiLabelBinarizer()
skills_encoded = mlb.fit_transform(df["skills"])

skills_df = pd.DataFrame(skills_encoded, columns=mlb.classes_)

# -----------------------
# 2. Experience encoding
# -----------------------
def encode_experience(x):
    if x <= 2:
        return 0  # junior
    elif x <= 5:
        return 1  # mid
    else:
        return 2  # senior

df["exp_level"] = df["experience"].apply(encode_experience)

# -----------------------
# 3. Salary bucket
# -----------------------
def salary_bucket(x):
    if x < 30000:
        return 0
    elif x < 60000:
        return 1
    else:
        return 2

df["salary_bucket"] = df["salary"].apply(salary_bucket)

# -----------------------
# 4. Final feature matrix
# -----------------------
X = pd.concat([
    skills_df,
    df[["exp_level", "salary_bucket"]]
], axis=1)

# -----------------------
# 5. Scaling (important for KMeans)
# -----------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -----------------------
# 6. Clustering
# -----------------------
kmeans = KMeans(n_clusters=15, random_state=42)
df["cluster"] = kmeans.fit_predict(X_scaled)

# -----------------------
# Output
# -----------------------
print(df[["id", "cluster"]].head())


def encode_user_input(
    user_input: pd.DataFrame, mlb: MultiLabelBinarizer,
    scaler: StandardScaler, kmeans: KMeans) -> int:
    # user_input example:
    # {"skills": [...], "experience": 3, "salary": 40000}

    # Skills
    skills_vec = mlb.transform([user_input["skills"]])

    # Experience
    exp = encode_experience(user_input["experience"])

    # Salary
    sal = salary_bucket(user_input["salary"])

    # Combine
    user_vector = np.concatenate([
        skills_vec[0],
        [exp, sal]
    ])

    # Scale
    user_vector_scaled = scaler.transform([user_vector])

    # Predict cluster
    cluster_id = kmeans.predict(user_vector_scaled)[0]

    return cluster_id


# 50,000 → cluster → 1,000 → ML ranking
def get_candidate_jobs(
    user_input: pd.DataFrame, df: pd.DataFrame, mlb: MultiLabelBinarizer,
    scaler: StandardScaler, kmeans: KMeans) -> pd.DataFrame:
    cluster = encode_user_input(user_input, mlb, scaler, kmeans)

    candidates = df[df["cluster"] == cluster]

    return candidates


joblib.dump(kmeans, "kmeans.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(mlb, "mlb.pkl")
