from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from datasets import load_dataset
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY, POC_COLLECTION_NAME

dataset = load_dataset("atitaarora/qdrant_doc", split="train")
langchain_docs = [
    LangchainDocument(page_content=doc["text"], metadata={
                      "source": doc["source"]})
    for doc in dataset
]

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    add_start_index=True,
    separators=["\n\n", "\n", ".", " ", ""],
)

docs_processed = []
for doc in langchain_docs:
    docs_processed += text_splitter.split_documents([doc])
print(f'len of data process : {len(docs_processed)}')

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

docs_contents = []
docs_metadatas = []

for doc in docs_processed:
    if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
        docs_contents.append(doc.page_content)
        docs_metadatas.append(doc.metadata)
    else:
        # Handle the case where attributes are missing
        print(
            "Warning: Some documents do not have 'page_content' or 'metadata' attributes.")

print(len(docs_contents))
print(len(docs_metadatas))

client.add(collection_name=POC_COLLECTION_NAME,
           metadata=docs_metadatas, documents=docs_contents)

print(f'{POC_COLLECTION_NAME} exsist -> {client.count(collection_name=POC_COLLECTION_NAME).count}')
