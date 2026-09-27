from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from litellm import completion
import law_content
from pathlib import Path

load_dotenv(override=True)

import os

openrouter = OpenAI(
       api_key=os.getenv("OPENROUTER_API_KEY"),
       base_url="https://openrouter.ai/api/v1",
   )

MODEL = "gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent.parent / "law_db")
collection_name = "docs"
# embedding_model = "openai/text-embedding-3-large"
embedding_model = "openai/text-embedding-3-small"   #Performed best relative to price
# embedding_model = "voyageai/voyage-4-large"
# embedding_model =  "google/gemini-embedding-2"
AVERAGE_CHUNK_SIZE = 3000
AVERAGE_CHUNK_OVERLAP = 300

openai = OpenAI()

class Result(BaseModel):
    page_content: str
    metadata: dict

class Chunk(BaseModel):
    headline: str = Field(description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query")
    summary: str = Field(description="A few sentences summarizing the content of this chunk to answer common questions")
    original_text: str = Field(description="The original text of this chunk from the provided document, exactly as is, not changed in any way")

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,metadata=metadata)

class Chunks(BaseModel):
    chunks: list[Chunk]

LAW_BLOCKS = {
    "personal_service": law_content.rmc_personal_service,
    "control": law_content.rmc_control,
    "financial": law_content.rmc_financial,
    "organisation": law_content.rmc_organisation,
}

documents = []
for gate, text in LAW_BLOCKS.items():
    documents.append(Result(page_content=text.strip(), metadata={"gate": gate}))

splitter = RecursiveCharacterTextSplitter(chunk_size=AVERAGE_CHUNK_SIZE, chunk_overlap=150, add_start_index=True) #Add start index allows us to identify the first CHunk with a summary of the relevant law
chunks = splitter.split_documents(documents)

def create_embeddings(chunks):
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    emb = openrouter.embeddings.create(model=embedding_model, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created with {collection.count()} documents")

if __name__ == "__main__":   #Used to prevent the file from running everytime when its imported
    create_embeddings(chunks)


