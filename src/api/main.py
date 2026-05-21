from fastapi import FastAPI

from src.api.routers import lookups, predict, stats

app = FastAPI(
    title="Job Market API",
    description="API Job Market pour les prédictions ML et les données dashboard.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict:
    return {
        "message": "Job Market API",
        "docs": "/docs",
        "endpoints": {
            "predict": ["/predict", "/predict/salary", "/predict/recommendation"],
            "lookups": [
                "/lookups",
                "/lookups/skills",
                "/lookups/contracts",
                "/lookups/remote",
                "/lookups/education",
                "/lookups/industries",
                "/lookups/locations",
                "/lookups/job-titles",
            ],
            "stats": [
                "/stats",
                "/stats/summary",
                "/stats/breakdown",
                "/stats/salary_breakdown",
                "/stats/ml",
            ],
        },
    }


app.include_router(predict.router)
app.include_router(lookups.router)
app.include_router(stats.router)
