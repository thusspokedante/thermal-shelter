from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.simulation import router as simulation_router
from app.api.routes.materials import router as materials_router
from app.api.routes.climate import router as climate_router
from app.db import init_db, SessionLocal
from app.seed_data import seed

app = FastAPI(
    title="Area Specific Thermal Shelter Simulation API",
    version="1.0.0",
    description="Reduced-order transient thermal simulation backend for SIH shelter design."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to your frontend URL in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router, prefix="/api")
app.include_router(materials_router, prefix="/api")
app.include_router(climate_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    # Create the materials table if needed and make sure the 14 default
    # materials are present, so the API works right after a fresh clone.
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

@app.get("/")
def root():
    return {"name": "Thermal Shelter Simulation API", "version": "1.0.0", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}
