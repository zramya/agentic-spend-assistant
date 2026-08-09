from fastapi import FastAPI, Depends
from app.routes.upload_route import router as upload_router

# from app.routes.query_route import router as query_router

app = FastAPI()


# localhost:8000/
@app.post("/")
def root():
    return "Welcome to the Compliance IQ Bot API!"


app.include_router(upload_router)
# app.include_router(query_router)

# To run
# uv run uvicorn app.main:app --reload

# to activate venv
# .venv\Scripts\activate.bat
