from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.routers.auth_router import router as auth_router
from .api.routers.configurations_router import router as configurations_router
from .api.routers.storage_router import router as storage_router
from .api.routers.jobs_router import router as jobs_router

app = FastAPI(title="App Backend (OOP Services)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# Routers
app.include_router(auth_router)
app.include_router(configurations_router, prefix=settings.api_prefix)
app.include_router(storage_router,  prefix=settings.api_prefix)
app.include_router(jobs_router,     prefix=settings.api_prefix)
