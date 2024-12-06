from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

print(qdrant_client.get_collections())
