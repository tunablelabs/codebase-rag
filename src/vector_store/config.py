import os
from dotenv import load_dotenv

load_dotenv()

# Vector store configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
POC_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate required environment variables
required_vars = [
    "QDRANT_URL",
    # "QDRANT_API_KEY",
    "QDRANT_COLLECTION",
    "OPENAI_API_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")