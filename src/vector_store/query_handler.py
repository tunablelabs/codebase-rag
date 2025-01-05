from qdrant_client import QdrantClient
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY
from openai import OpenAI
import os


openai_client = OpenAI(api_key=OPENAI_API_KEY)

client = QdrantClient(
    url=QDRANT_HOST,
    api_key=QDRANT_API_KEY
)


def query_with_context(query, limit):
    POC_COLLECTION_NAME = "code_chunks"

    # Fetch context from Qdrant
    search_result = client.query(
        collection_name=POC_COLLECTION_NAME, query_text=query, limit=limit)

    contexts = [f"document: {r.document}, type: {r.metadata['type']}, file: {os.path.basename(r.metadata['file_path'])}, dependencies: {r.metadata['dependencies']}, imports: {r.metadata['imports']}" for r in search_result]
    
    prompt_start = (
        """ You're assisting a user who has a question based on the documentation.
        Your goal is to provide a clear and concise response that addresses their query while referencing relevant information
        from the documentation.
        Remember to:
        Understand the user's question thoroughly.
        If the user's query is general (e.g., "hi," "good morning"),
        greet them normally and avoid using the context from the documentation.
        If the user's query is specific and related to the documentation, locate and extract the pertinent information.
        Craft a response that directly addresses the user's query and provides accurate information
        referring the relevant source and page from the 'source' field of fetched context from the documentation to support your answer.
        Use a friendly and professional tone in your response.
        If you cannot find the answer in the provided context, do not pretend to know it.
        Instead, respond with "I don't know".

        Context:\n"""
    )

    prompt_end = (
        f"\n\nQuestion: {query}\nAnswer:"
    )

    prompt = (
        prompt_start + "\n\n---\n\n".join(contexts) +
        prompt_end
    )

    res = openai_client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        temperature=0,
        max_tokens=636,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )
    return (contexts, res.choices[0].text)