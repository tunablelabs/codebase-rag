# src/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
POC_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

# Validate required environment variables
required_vars = [
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "QDRANT_COLLECTION_NAME",
    "OPENAI_API_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {
                           ', '.join(missing_vars)}")
