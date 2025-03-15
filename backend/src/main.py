# Code Block to clean tree-sitter-build files and create new .so files everytime we start the server
import os
import shutil
from config.logging_config import info

# When working in local comment this code if you alredy had .so files for your OS in tree_build
target_folder = "../tree_build"
# Clean the folder before any other imports
if os.path.exists(target_folder):
    shutil.rmtree(target_folder)
    os.makedirs(target_folder)
    info(f"Cleaned and recreated folder: {target_folder}")
else:
    os.makedirs(target_folder)
    info(f"Created folder: {target_folder}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from api.routes import router
import uvicorn
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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
    # Local
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # Production
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
