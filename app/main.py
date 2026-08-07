from fastapi import FastAPI
from app.core.db import engine
from sqlalchemy import text

app = FastAPI(
    title="Credit Card Advisor API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {"message": "Backend is running successfully"}


@app.get("/test-db")
def test_db():

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "database": "Connected",
        "result": value
    }