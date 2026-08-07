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


