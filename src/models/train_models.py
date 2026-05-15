from __future__ import annotations

import argparse
from pathlib import Path

from src.models.features_preparation import get_model_artifacts_path, predict_salary_from_profile, train_job_market_models


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Job Market ML models from PostgreSQL analytics tables.")
    parser.add_argument("--model-dir", default="models", help="Directory where trained artifacts are written.")
    parser.add_argument("--n-neighbors", type=int, default=50, help="Number of neighbors used for candidate preselection.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_dir = Path(args.model_dir)
    artifacts = train_job_market_models(model_dir=model_dir, n_neighbors=args.n_neighbors)

    first_job = artifacts.training_df.iloc[0]
    sample_profile = {
        "skills": list(first_job["skills"]),
        "experience": float(first_job["experience"]),
        "salary": float(first_job["salary"]),
        "job_title": first_job.get("title"),
        "location": first_job.get("location"),
        "contract_type": first_job.get("contract_type"),
        "remote": first_job.get("remote"),
        "industry": first_job.get("industry"),
        "education_level": first_job.get("education_level"),
    }
    sample_salary = predict_salary_from_profile(sample_profile, artifacts)

    print("ML training OK")
    print("- source: PostgreSQL analytics tables")
    print(f"- training rows: {len(artifacts.training_df)}")
    print(f"- encoded skills: {len(artifacts.mlb.classes_)}")
    print(f"- recommendation features: {len(artifacts.recommendation_columns)}")
    print(f"- salary features: {len(artifacts.salary_columns)}")
    print("- evaluation metrics:")
    print(f"  - recommendation accuracy: {artifacts.metrics['recommendation_accuracy']:.3f}")
    print(f"  - recommendation precision: {artifacts.metrics['recommendation_precision']:.3f}")
    print(f"  - recommendation recall: {artifacts.metrics['recommendation_recall']:.3f}")
    print(f"  - recommendation f1: {artifacts.metrics['recommendation_f1']:.3f}")
    print(f"  - salary MAE: {artifacts.metrics['salary_mae']:.2f}")
    print(f"  - salary RMSE: {artifacts.metrics['salary_rmse']:.2f}")
    print(f"  - salary R2: {artifacts.metrics['salary_r2']:.3f}")
    print(f"- sample salary prediction: {sample_salary:.2f}")
    print(f"- artifacts written to: {model_dir.resolve()}")
    print(f"- API artifact: {get_model_artifacts_path(model_dir).resolve()}")


if __name__ == "__main__":
    main()
