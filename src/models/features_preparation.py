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
    scaler: StandardScaler, kmeans: KMeans) -> np.ndarray:
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

    return user_vector_scaled


# 50,000 → cluster → 1,000 → ML ranking
def get_candidate_jobs(
    user_input: pd.DataFrame, df: pd.DataFrame, mlb: MultiLabelBinarizer,
    scaler: StandardScaler, kmeans: KMeans) -> pd.DataFrame:
    user_vector_scaled = encode_user_input(user_input, mlb, scaler, kmeans)

    # Predict cluster
    cluster_id = kmeans.predict(user_vector_scaled)[0]

    candidates = df[df["cluster"] == cluster_id]

    return candidates


joblib.dump(kmeans, "kmeans.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(mlb, "mlb.pkl")


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
skill_match_score
experience_gap
location_score
salary_ratio
contract_match
remote_match
# job_popularity
# market_demand_score

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

# 1. What is your training set (concretely)

Your training set is a **table you build offline**:

```text
(user_query_i, job_j, X_ij, y_ij)
```

Where:

* `user_query_i` = synthetic user (skills, salary, etc.)
* `job_j` = real job
* `X_ij` = features (skill_match, salary_ratio, …)
* `y_ij` = relevance label

---

## How you actually construct it

You generate:

```text
for each job J:
    create synthetic user U (derived from J)

    → (U, J) → positive example (y = 1)

    for k random jobs J':
        → (U, J') → negative examples (y = 0)
```

👉 That’s your dataset.

So your **training set is not given** —
👉 it is **engineered from your job dataset**

"""

def retrieve_jobs():
    query = """
        SELECT jo.job_id, jo.job_type_id, jt.title, jo.experience_years, concat(lo.city, ',', lo.region) AS location,
                (ds.salary_max+ds.salary_min)/2 AS avg_salary, array_agg(ds.skill_name) AS skills
        FROM job_offers jo
        JOIN dim_salary ds ON jo.salary_id = ds.salary_id
        JOIN bridge_job_skill bjs ON jo.job_id = bjs.job_id
        JOIN dim_skill ds ON bjs.skill_id = ds.skill_id
        JOIN dim_job_type jt ON jo.job_type_id = jt.job_type_id
        JOIN dim_location lo ON jo.location_id = lo.location_id
        WHERE ds.frequency == 'yearly'
        GROUP BY jo.job_id, jo.job_type_id, jt.title, jo.experience_years, location, avg_salary
    """

    # Execute query and load data into DataFrame
    # df = pd.read_sql(query, connection)
    # return df

    return pd.DataFrame([
        {
            "id": 1,
            "skills": ["python", "sql", "airflow"],
            "experience": 3,
            "salary": 45000
        },
        {
            "id": 2,
            "skills": ["java", "kubernetes"],
            "experience": 5,
            "salary": 60000
        }
    ])

def generate_training_data(jobs):
    training_data = []
    for job in jobs:
        # Create synthetic user based on job
        user = {
            "skills": job["skills"],
            "location": job["location"],
            "region": job["region"],
            "expected_salary": job["salary"],
            "contract_preference": job["contract_type"]
        }
        # Positive example
        training_data.append((user, job, relevance_score(user, job), 1))

        # Negative examples
        for _ in range(5):  # 5 random jobs
            random_job = get_random_job(job["job_type_id"])  # Function to fetch a random job
            training_data.append((user, random_job, relevance_score(user, random_job), 0))

    return training_data

def get_random_job(job_id: str) -> dict:
    # This function should return a random job from your dataset
    # For demonstration, we return a dummy job
    return {
        "skills": ["random_skill"],
        "location": "random_location",
        "region": "random_region",
        "salary": 50000,
        "contract_type": "full-time"
    }


# match(user, job) → probability of interest

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
        0.2 * salary_ratio(job["salary"], user["expected_salary"]) +
        0.1 * contract_match(user["contract_preference"], job["contract_type"])
    )

# 2. How do you prepare your features for the matching model? Encodings and cleaning and normalization, etc.
def prepare_features_regression(training_data):
    # This function will take your raw training data and convert it into a feature matrix X and label vector y
    # For example, you can create a DataFrame from training_data and then apply the necessary transformations
    df = pd.DataFrame(training_data, columns=["user", "job", "relevance_score", "label"])

    # Get top skills
    top_skills = find_top_skills(50)

    # Create feature skill score match
    df["skill_match_score"] = df.apply(lambda row: skill_match_score(row["user"]["skills"], row["job"]["skills"]), axis=1)
    feature_cols = ["skill_match_score"]

    # Normalize salaries
    df['user_salary_norm'] = (df['user'].apply(lambda u: u['expected_salary']) - df['user'].apply(lambda u: u['expected_salary']).mean()) / df['user'].apply(lambda u: u['expected_salary']).std()
    df['job_salary_norm'] = (df['job'].apply(lambda j: j['salary']) - df['job'].apply(lambda j: j['salary']).mean()) / df['job'].apply(lambda j: j['salary']).std()
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
    # For example, you can use Logistic Regression or LightGBM
    from sklearn.linear_model import LogisticRegression
    model = LogisticRegression()
    model.fit(X, y)
    return model

def predict(user_input, model, mlb, scaler):
    result = model.predict_proba(prepare_features_for_prediction(user_input, mlb, scaler))[:, 1]  # Get probability of relevance
    return [("job_id_1", 0.9), ("job_id_2", 0.8), ("job_id_3", 0.7)]

def prepare_features_for_prediction(user_input, mlb, scaler):
    # Get clustering results to reduce search space
    encoded_user = encode_user_input(user_input, mlb, scaler, kmeans)
    reduced_jobs = get_candidate_jobs(user_input, df, mlb, scaler, kmeans)
    return [[0.5, 0.0, 1.0, 0.0]]  # Example feature vector for prediction



"""
New model to predict salary for a specific job description (job type, skills, location, experience level, etc.)
Features:
    - job_type (one-hot)
    - skills (multi-hot)
    - location (one-hot)
    - experience_level (categorical)
    - contract_type (one-hot)
"""

