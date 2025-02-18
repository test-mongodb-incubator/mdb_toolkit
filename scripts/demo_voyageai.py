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

# Get Embedding Function
def get_embedding(text: str) -> List[float]:
    text = text.replace("\n", " ")
    try:
        # Embed the documents
        return vo.embed(
            [text], model="voyage-3", input_type="document"
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
documents = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]
# turn those documents into objects with _id and content
documents = [
    {"_id": i, "content": doc} for i, doc in enumerate(documents)
]
# Insert documents into the collection
client.insert_documents(
    database_name=database_name,
    collection_name=collection_name,
    documents=documents,
    fields_to_embed=["content"]
)
print("Inserted documents into the collection.")

# insert pause to allow index update
import time
time.sleep(5)
print("Searching for documents...")
# Perform searches
# 1. Vector-Based Search
query = "When is Apple's conference call scheduled?"
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
INFO:mdb_toolkit.core:Inserting documents into 'test_collection'.
INFO:mdb_toolkit.core:Inserted 6 documents into 'test_collection'.
Inserted documents into the collection.
Searching for documents...
INFO:__main__:Performing vector-based search with query: 'When is Apple's conference call scheduled?'
INFO:mdb_toolkit.core:Found existing index 'vs_1'.
INFO:mdb_toolkit.core:Vector search completed. Found 3 documents.

--- Vector-Based Search Results ---
ID: 4
Content: Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
Meta Data: None
Score: 0.8040727376937866

ID: 5
Content: Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature.
Meta Data: None
Score: 0.7103409767150879

ID: 2
Content: 20th-century innovations, from radios to smartphones, centered on electronic advancements.
Meta Data: None
Score: 0.6980117559432983
"""