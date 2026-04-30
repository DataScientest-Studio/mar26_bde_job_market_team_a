from fastapi import FastAPI

from src.api.routers import predict, stats

app = FastAPI(
    title="Job Market API",
    description="API Job market pour les predictions ML et les donnees dashboard.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict:
    return {
        "message": "Job Market API",
        "docs": "/docs",
        "endpoints": {
            "predict": ["/predict", "/predict/salary", "/predict/recommendation"],
            "stats": ["/stats", "/stats/sector", "/stats/region", "/stats/contract", "/stats/by_salary"],
        },
    }


app.include_router(predict.router)
app.include_router(stats.router)
