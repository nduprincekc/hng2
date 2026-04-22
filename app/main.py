from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine
from app import models
from app.routers import profiles

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HNG Stage 2 - Intelligence Query Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

app.include_router(profiles.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "ok", "message": "Intelligence Query Engine is running"}