from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from src.vector_store.config import QDRANT_URL, QDRANT_API_KEY, POC_COLLECTION_NAME
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingsHandler:
    """
    Handles the process of chunking code and storing it in the vector database.
    Currently uses LangChain for chunking, but designed to easily integrate with Tree-sitter later.
    """

    def __init__(self, collection_name: str = POC_COLLECTION_NAME):
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        self.collection_name = collection_name

        # Initialize LangChain text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            add_start_index=True,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def process_and_store_code(self, code: str, file_path: str) -> bool:
        """
        Process code into chunks and store in vector database.

        Args:
            code: The source code to process
            file_path: Path to the source file (used for metadata)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create initial document
            doc = LangchainDocument(
                page_content=code,
                metadata={"source": file_path}
            )

            # Split into chunks using LangChain
            chunks = self.text_splitter.split_documents([doc])

            # Prepare for storage
            docs_contents = []
            docs_metadatas = []

            for chunk in chunks:
                docs_contents.append(chunk.page_content)
                docs_metadatas.append({
                    **chunk.metadata,
                    "file_path": file_path
                })

            # Store in Qdrant
            self.client.add(
                collection_name=self.collection_name,
                documents=docs_contents,
                metadata=docs_metadatas
            )

            logger.info(f"Successfully processed and stored {
                        len(chunks)} chunks from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing code: {str(e)}")
            return False

    def get_collection_info(self):
        """Get information about the current collection"""
        try:
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None
