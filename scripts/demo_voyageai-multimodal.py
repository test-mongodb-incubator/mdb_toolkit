import logging
import openai
from typing import List

# load .ENV file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import voyageai
voyageai_api_key = "pa-"
vo = voyageai.Client(api_key=voyageai_api_key)
MODEL_NAME = "voyage-multimodal-3"

import requests
from pdf2image import convert_from_bytes

def pdf_url_to_screenshots(url: str) -> list[any]:
    """Extract all pages as screenshots from a PDF."""

    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad responses

    images = convert_from_bytes(response.content)
    return images

# Get Embedding Function
def get_embedding(text: any) -> List[float]:
    try:
        # Embed the documents
        return vo.multimodal_embed(
            [[text]], model=MODEL_NAME, input_type="document"
        ).embeddings[0]
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

# Example usage
from mdb_toolkit import CustomMongoClient
print("mdb_toolkit package imported successfully")

# Define database and collection names
database_name = "test_database"
collection_name = "test_collection"
index_name = "vs_1"  # Ensure this matches your intended index name
distance_metric = "cosine"

client = CustomMongoClient(
    "mongodb://localhost:27017/?directConnection=true&serverSelectionTimeoutMS=2000",
    get_embedding=get_embedding
)
# Create the search index
client._create_search_index(
    database_name=database_name,
    collection_name=collection_name,
    index_name=index_name,
    distance_metric=distance_metric,
    embedding_field="content_embedding", #voyageai :)
)

# Wait for the search index to be READY
logger.info("Waiting for the search index to be READY...")
index_ready = client.wait_for_index_ready(
    database_name=database_name,
    collection_name=collection_name,
    index_name=index_name,
    max_attempts=10,
    wait_seconds=1
)

if index_ready:
    logger.info(f"Search index '{index_name}' is now READY and available!")
    print("Index is ready!")
else:
    logger.error("Index creation process exceeded wait limit or failed.")
    print("Index creation process exceeded wait limit.")
    exit()

# Insert documents
pdf_url = "https://www.fdrlibrary.org/documents/356632/390886/readingcopy.pdf"
document_images = pdf_url_to_screenshots(pdf_url)

# turn those documents into objects with _id and content
documents = [
    {"_id": i, "content": doc} for i, doc in enumerate(document_images)
]
# Insert documents into the collection
for doc in documents:
    doc["content_embedding"] = get_embedding(doc["content"])
    doc["content"] = str(doc["content"])
    client[database_name][collection_name].insert_one(doc)

print("Inserted documents into the collection.")

# insert pause to allow index update
import time
time.sleep(5)
print("Searching for documents...")
# Perform searches
# 1. Vector-Based Search
query = "The consequences of a dictator's peace"
logger.info(f"Performing vector-based search with query: '{query}'")
vector_results = client.vector_search(
    query=query,
    limit=3,
    database_name=database_name,
    collection_name=collection_name,
    index_name=index_name,
    embedding_field="content_embedding", #voyageai :)
)
print("\n--- Vector-Based Search Results ---")
for doc in vector_results:
    print(f"ID: {doc.get('_id')}\nContent: {doc.get('content')}\nMeta Data: {doc.get('meta_data')}\nScore: {doc.get('score')}\n")


"""
INFO:mdb_toolkit:Initializing mdb_toolkit package
INFO:mdb_toolkit.core:Importing core module
mdb_toolkit package imported successfully
INFO:mdb_toolkit.core:Collection 'test_collection' does not exist. Creating it now.
INFO:mdb_toolkit.core:Collection 'test_collection' created successfully.
INFO:mdb_toolkit.core:Index 'vs_1' does not exist in collection 'test_collection'.
INFO:mdb_toolkit.core:Creating search index 'vs_1' for collection 'test_collection'.
INFO:mdb_toolkit.core:Search index 'vs_1' created successfully for collection 'test_collection'.
INFO:__main__:Waiting for the search index to be READY...
INFO:mdb_toolkit.core:Index 'vs_1' status: PENDING
INFO:mdb_toolkit.core:Attempt 1: Search index 'vs_1' not READY yet. Waiting 1 second(s)...
INFO:mdb_toolkit.core:Search index 'vs_1' is READY.
INFO:__main__:Search index 'vs_1' is now READY and available!
Index is ready!
Inserted documents into the collection.
Searching for documents...
INFO:__main__:Performing vector-based search with query: 'The consequences of a dictator's peace'
INFO:mdb_toolkit.core:Found existing index 'vs_1'.
INFO:mdb_toolkit.core:Vector search completed. Found 3 documents.

--- Vector-Based Search Results ---
ID: 5
Content: <PIL.PpmImagePlugin.PpmImageFile image mode=RGB size=488x667 at 0x133C7F5E0>
Meta Data: None
Score: 0.6876784563064575

ID: 20
Content: <PIL.PpmImagePlugin.PpmImageFile image mode=RGB size=502x667 at 0x133C7F8B0>
Meta Data: None
Score: 0.6666251420974731

ID: 3
Content: <PIL.PpmImagePlugin.PpmImageFile image mode=RGB size=504x667 at 0x133C7F580>
Meta Data: None
Score: 0.664629340171814
"""