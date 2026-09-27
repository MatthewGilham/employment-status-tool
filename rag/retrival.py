from dotenv import load_dotenv
from openai import OpenAI
from chromadb import PersistentClient
from rag.ingest import DB_NAME, collection_name, embedding_model, Result
from litellm import completion
from pathlib import Path

load_dotenv(override=True)

openai = OpenAI()

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_collection(collection_name)



MODEL = "openai/gpt-4.1-nano"

def retrieve_law(query, gate, k=4): #Query is the facts to search with, Gate refers to which gate/factors and k is number of chunks returned
    query_vector = openai.embeddings.create(model=embedding_model, input=[query]).data[0].embedding #Model must put query facts into vectors to compare it in vector database

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k, #Amount of chunks returned
        where={"gate": gate}, #Where the database can be searched, filters only specific gate
    )

    chunks = []
    for text, metadata in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=text, metadata=metadata))  #Chroma returns a dictionary with text and metadata in seperate lists  
    
    rule = collection.get(where={"$and": [{"gate": gate}, {"start_index": 0}]}) #Collection get fetches chunks by their labels, and means both conditions must match gate and start index
    rule_chunk = Result(page_content=rule["documents"][0], metadata=rule["metadatas"][0]) #Returns the first chunk

    already_found = any(chunk.page_content == rule_chunk.page_content for chunk in chunks) 
    if not already_found:
        chunks.insert(0, rule_chunk)
    return chunks


if __name__ == "__main__":
    found = retrieve_law("the engager refused to accept a substitute", "personal_service")
    print(len(found))
    for chunk in found:
        print(chunk.metadata)

