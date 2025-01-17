from openai import OpenAI
from get_local_db import fetch_user_data, check_and_create_table, add_user, update_conversation, user_exists

from config import OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY, POC_COLLECTION_NAME

openai_client = OpenAI(api_key=OPENAI_API_KEY)

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

# checks & creates user localdb if not already
check_and_create_table()

def query_with_context(query: str, limit: int, user_id:str):
    try:
        search_result = qdrant_client.query(
            collection_name=POC_COLLECTION_NAME, query_text=query, limit=limit)

        contexts = [
            "document: "+r.document+",source: "+r.metadata['source'] for r in search_result
        ]

        prompt_start = (
            """You're assisting a user who has a question based on the documentation.
            Your goal is to provide a clear and concise response that addresses their query while referencing relevant information
            from the documentation.
            Remember to:
            - Understand the user's question thoroughly.
            - If the user's query is general (e.g., "hi," "good morning"),
              greet them normally and avoid using the context from the documentation.
            - If the user's query is specific and related to the documentation, locate and extract the pertinent information.
            - Craft a response that directly addresses the user's query and provides accurate information
              referring to the relevant source and page from the 'source' field of fetched context from the documentation to support your answer.
            - Use a friendly and professional tone in your response.
            - If you cannot find the answer in the provided context, do not pretend to know it.
              Instead, respond with "I don't know".
            
            Context:\n"""
        )

        if user_exists(user_id):
            user_context = fetch_user_data(user_id)['context_window']
            prompt_start = prompt_start + "\n\n" + user_context
        else:
            add_user(user_id)

        prompt_end = f"\n\nQuestion: {query}\nAnswer:"
        prompt = prompt_start + "\n\n---\n\n".join(contexts) + prompt_end 

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

        llm_response = res.choices[0].text
        update_conversation(user_id, question=query , answer=llm_response, turn=3)

        return {
            "contexts": contexts,
            "response": llm_response
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}")
