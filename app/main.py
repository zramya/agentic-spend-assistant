from fastapi import FastAPI
from app.routes import SpendSummaryRequest


app = FastAPI()




@app.get("/")
async def root():
   return {"message": "Hello World"}




@app.get("/health")
def health_check():
   return {"status": "ok"}




app.include_router(SpendSummaryRequest.router)
