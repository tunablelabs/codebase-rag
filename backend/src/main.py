from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from api.routes import router
import uvicorn
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from config.logging_config import info

app = FastAPI(
    title="Code Analysis API",
    description="API for analyzing code repositories using Tree-sitter and vector embeddings",
    version="1.0.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)
app.include_router(router, prefix="/codex")


if __name__ == "__main__":
    info("Starting Code Analysis API server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
