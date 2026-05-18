
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

from .features_prep_clustering import find_top_skills, _encode_experience, _salary_bucket

def train_clustering_model(engine: object, df: pd.DataFrame) -> tuple[KMeans, StandardScaler, dict[str, MultiLabelBinarizer], pd.DataFrame]:
    # 1. Skills encoding (multi-hot)
    top_skills = find_top_skills(engine, limit=30)
    df["skills"] = df["skills"].apply(lambda s: [x for x in s if x in top_skills])

    # filter empty skills an repalace with "other"
    df["skills"] = df["skills"].apply(lambda s: s if len(s) > 0 else ["other"])

    mlb_skills = MultiLabelBinarizer()
    skills_encoded = mlb_skills.fit_transform(df["skills"])
    skills_df = pd.DataFrame(skills_encoded, columns=mlb_skills.classes_)

    mlb_contract = MultiLabelBinarizer()
    contract_encoded = mlb_contract.fit_transform(df["contract_type"].apply(lambda x: [x] if x else []))
    contract_df = pd.DataFrame(contract_encoded, columns=mlb_contract.classes_)

    df["exp_level"] = df["experience_years"].apply(_encode_experience)
    df["salary_bucket"] = df["mid_salary"].apply(_salary_bucket)

    # 4. Final feature matrix
    X = pd.concat([
        skills_df,
        contract_df,
        df[["exp_level", "salary_bucket"]]
    ], axis=1)

    # 5. Scaling features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 6. Clustering
    kmeans = KMeans(n_clusters=15, random_state=42)
    df["cluster"] = kmeans.fit_predict(X_scaled)

    mlbs = {
        "skills": mlb_skills,
        "contract": mlb_contract
    }

    return kmeans.fit(X_scaled), scaler, mlbs, df

# df = retrieve_features_clustering(engine)
# kmeans, scaler, mlb, df = train_clustering_model(engine, df)

# print(df[["id", "cluster"]].head())

# joblib.dump(kmeans, "kmeans.pkl")
# joblib.dump(scaler, "scaler.pkl")
# joblib.dump(mlb, "mlb.pkl")

