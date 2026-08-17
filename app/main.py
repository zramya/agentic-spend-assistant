from fastapi import FastAPI
from app.routes.query_route import router as query_router
from app.routes.upload_route import router as upload_router


app = FastAPI()




@app.get("/")
async def root():
   return {"message": "Hello World"}




@app.get("/health")
def health_check():
   return {"status": "ok"}




app.include_router(upload_router)
app.include_router(query_router)

