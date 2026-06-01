from fastapi import FastAPI
from api.v1.router import router as v1_router

app = FastAPI(title="Knowledge Base API")

app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
