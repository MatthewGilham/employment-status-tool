from dotenv import load_dotenv
from openai import OpenAI
from chromadb import PersistentClient
from rag.ingest import DB_NAME, collection_name, embedding_model, Result
from litellm import completion
from pathlib import Path
import os



load_dotenv(override=True)

openai = OpenAI()
openrouter = OpenAI(
       api_key=os.getenv("OPENROUTER_API_KEY"),
       base_url="https://openrouter.ai/api/v1",
   )

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_collection(collection_name)
K = 5



MODEL = "openai/gpt-4.1-nano"

def retrieve_law(query, gate, k=K, pin_rule=True): #Query is the facts to search with, Gate refers to which gate/factors and k is number of chunks returned
    query_vector = openrouter.embeddings.create(model=embedding_model, input=[query]).data[0].embedding #Model must put query facts into vectors to compare it in vector database

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=k, #Amount of chunks returned
        where={"gate": gate}, #Where the database can be searched, filters only specific gate
    )

    chunks = []
    for text, metadata in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=text, metadata=metadata))  #Chroma returns a dictionary with text and metadata in seperate lists  
    
    if pin_rule:
        rule = collection.get(where={"$and": [{"gate": gate}, {"start_index": 0}]})
        rule_chunk = Result(page_content=rule["documents"][0], metadata=rule["metadatas"][0])
        chunks = [c for c in chunks if c.page_content != rule_chunk.page_content]
        chunks.insert(0, rule_chunk)
    return chunks


if __name__ == "__main__":
    tests = [
        ("personal_service",
         """Contract states a right of substitution: yes
Right is fettered: no
Who would pay a substitute: worker
Account in practice: the worker once asked to send a substitute and the engager refused."""),

        ("control",
         """Who decides what work and what order: the engager
Who decides how work is performed: the worker, as a skilled specialist
Who sets the hours and location: the engager
Report to a manager or not: no"""),

        ("financial",
         """Does defective work need correcting: yes, at the worker's own cost and in their own time
Can they make a loss on engagement: yes, they quote a fixed price for the job"""),

        ("organisation",
         """Are they presented as part of the organisation: yes, company email address and on the staff list
Do they have staff benefits or training: attends internal training, no holiday pay"""),

    ]

    for gate, facts in tests:
        print(f"\n===== {gate} =====")
        for chunk in retrieve_law(facts, gate):
            first_line = chunk.page_content.split("\n")[0]
            print("  ", first_line[:90])
