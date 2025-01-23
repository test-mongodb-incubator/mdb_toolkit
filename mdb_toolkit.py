import logging
import time
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel
from pymongo.errors import OperationFailure

from embeddings.openai import get_embedding  # Ensure this module is correctly implemented

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CustomMongoClient(MongoClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_if_not_exists(self, database_name: str, collection_name: str) -> Collection:
        """
        Creates a collection if it does not exist in the specified database.
        """
        database = self[database_name]
        collection_names = database.list_collection_names()

        if collection_name not in collection_names:
            logger.info(f"Collection '{collection_name}' does not exist. Creating it now.")
            collection = database[collection_name]
            # Insert and remove a placeholder document to create the collection
            collection.insert_one({"_id": 0, "placeholder": True})
            collection.delete_one({"_id": 0})
            logger.info(f"Collection '{collection_name}' created successfully.")
        else:
            collection = database[collection_name]

        return collection

    def _create_search_index(
        self,
        database_name: str,
        collection_name: str,
        index_name: str,
        get_embedding: callable,
        distance_metric: str = "cosine",
    ) -> None:
        """
        Creates a search index on the specified collection if it does not already exist.
        """
        try:
            self.create_if_not_exists(database_name, collection_name)

            if self.index_exists(database_name, collection_name, index_name):
                logger.info(f"Search index '{index_name}' already exists in collection '{collection_name}'.")
                return

            logger.info(f"Creating search index '{index_name}' for collection '{collection_name}'.")

            # Generate a sample embedding to determine the number of dimensions
            num_dimensions = len(get_embedding("sample text"))
            search_index_model = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "numDimensions": num_dimensions,
                            "path": "embedding",
                            "similarity": distance_metric,
                        },
                    ]
                },
                name=index_name,
                type="vectorSearch",
            )

            collection = self[database_name][collection_name]
            collection.create_search_index(model=search_index_model)
            logger.info(f"Search index '{index_name}' created successfully for collection '{collection_name}'.")

        except OperationFailure as e:
            logger.error(f"Operation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create search index '{index_name}': {e}")
            raise

    def index_exists(self, database_name: str, collection_name: str, index_name: str) -> bool:
        """
        Checks if a specific search index exists in the collection.
        """
        try:
            collection = self[database_name][collection_name]
            indexes = list(collection.list_search_indexes())
            logger.debug(f"Retrieved indexes: {indexes}")  # Debugging line

            # Iterate through the indexes to check for a matching name
            for index in indexes:
                retrieved_name = index.get("name", "")
                logger.debug(f"Checking index: {retrieved_name}")
                if retrieved_name == index_name:
                    logger.info(f"Found existing index '{index_name}'.")
                    return True

            logger.info(f"Index '{index_name}' does not exist in collection '{collection_name}'.")
            return False

        except OperationFailure as e:
            logger.error(f"Operation failure while checking index existence: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking search index existence for '{index_name}': {e}")
            return False

    def is_index_ready(self, database_name: str, collection_name: str, index_name: str) -> bool:
        """
        Checks if the specified search index status is 'READY'.
        """
        try:
            collection = self[database_name][collection_name]
            indexes = list(collection.list_search_indexes())

            for index in indexes:
                if index.get("name") == index_name:
                    status = index.get("status", "").upper()
                    logger.debug(f"Index '{index_name}' status: {status}")
                    if status == "READY":
                        return True
                    else:
                        logger.info(f"Index '{index_name}' status: {status}")
                        return False

            logger.warning(f"Index '{index_name}' not found in collection '{collection_name}'.")
            return False

        except OperationFailure as e:
            logger.error(f"Operation failure while checking index status: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking search index status for '{index_name}': {e}")
            return False

    def wait_for_index_ready(
        self,
        database_name: str,
        collection_name: str,
        index_name: str,
        max_attempts: int = 10,
        wait_seconds: int = 1,
    ) -> bool:
        """
        Waits until the specified search index status is 'READY' or until max_attempts is reached.
        """
        attempt = 0
        while attempt < max_attempts:
            if self.is_index_ready(database_name, collection_name, index_name):
                logger.info(f"Search index '{index_name}' is READY.")
                return True
            attempt += 1
            logger.info(f"Attempt {attempt}: Search index '{index_name}' not READY yet. Waiting {wait_seconds} second(s)...")
            time.sleep(wait_seconds)
        logger.error(f"Search index '{index_name}' did not reach READY status after {max_attempts} attempts.")
        return False

    def insert_documents(
        self,
        database_name: str,
        collection_name: str,
        documents: List[Dict[str, Any]],
        fields_to_embed: List[str],
    ) -> None:
        """
        Inserts documents into the specified collection with embeddings for specified fields.
        Each document must include the fields specified in fields_to_embed.
        """
        try:
            collection = self[database_name][collection_name]
            existing_count = collection.count_documents({})
            if existing_count > 0:
                logger.info(f"Collection '{collection_name}' already has data. Skipping document insertion.")
                return

            logger.info(f"Inserting documents into '{collection_name}'.")

            documents_to_insert = []
            for doc in documents:
                for field in fields_to_embed:
                    if field in doc:
                        embedding = get_embedding(doc[field])
                        if embedding is None:
                            logger.warning(f"Skipping document '{doc.get('name', 'Unnamed')}' due to failed embedding for field '{field}'.")
                            break
                        doc[f"{field}_embedding"] = embedding
                else:
                    documents_to_insert.append(doc)

            if documents_to_insert:
                collection.insert_many(documents_to_insert)
                logger.info(f"Inserted {len(documents_to_insert)} documents into '{collection_name}'.")
            else:
                logger.warning("No documents were inserted due to embedding failures.")

        except Exception as e:
            logger.error(f"Error inserting documents: {e}")

    def vector_search(
        self,
        query: str,
        limit: int = 5,
        database_name: str = "",
        collection_name: str = "",
        index_name: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """
        Performs a vector-based search using the specified search index.
        """
        query_embedding = get_embedding(query)
        if not self.index_exists(database_name, collection_name, index_name):
            logger.error(f"Index '{index_name}' does not exist.")
            return []
        if query_embedding is None:
            logger.error(f"Failed to generate embedding for query: {query}")
            return []

        try:
            collection = self[database_name][collection_name]
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "limit": limit,
                        "numCandidates": limit,
                        "queryVector": query_embedding,
                        "path": "embedding",
                    }
                },
                {"$set": {"score": {"$meta": "vectorSearchScore"}}},
                {"$project": {"embedding": 0}},
            ]
            results = list(collection.aggregate(pipeline))
            logger.info(f"Vector search completed. Found {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            return []

    def keyword_search(
        self,
        query: str,
        limit: int = 5,
        database_name: str = "",
        collection_name: str = "",
    ) -> List[Dict]:
        """
        Performs a keyword-based search using a regular expression.
        """
        try:
            collection = self[database_name][collection_name]
            cursor = collection.find(
                {"content": {"$regex": query, "$options": "i"}},
                {"_id": 1, "name": 1, "content": 1, "meta_data": 1},
            ).limit(limit)
            results = list(cursor)
            logger.info(f"Keyword search completed. Found {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during keyword search: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        keyword: str,
        limit: int = 5,
        database_name: str = "",
        collection_name: str = "",
        index_name: str = "",
        distance_metric: str = "cosine",
    ) -> List[Dict]:
        """
        Performs a hybrid search combining vector-based search and keyword filtering.
        Returns documents that are semantically relevant and match the keyword.
        """
        query_embedding = get_embedding(query)
        if not self.index_exists(database_name, collection_name, index_name):
            logger.error(f"Index '{index_name}' does not exist.")
            return []
        if query_embedding is None:
            logger.error(f"Failed to generate embedding for query: {query}")
            return []

        try:
            collection = self[database_name][collection_name]
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "limit": limit * 2,  # Fetch more to account for filtering
                        "numCandidates": limit * 2,
                        "queryVector": query_embedding,
                        "path": "embedding",
                    }
                },
                {"$set": {"score": {"$meta": "vectorSearchScore"}}},
                {"$match": {"content": {"$regex": keyword, "$options": "i"}}},
                {"$sort": {"score": -1}},  # Sort by relevance score
                {"$limit": limit},
                {"$project": {"embedding": 0}},
            ]
            results = list(collection.aggregate(pipeline))
            logger.info(f"Hybrid search completed. Found {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}")
            return []


def main():
    # Initialize the custom MongoDB client
    client = CustomMongoClient("mongodb://0.0.0.0/?directConnection=true")

    # Define database and collection names
    database_name = "test_database"
    collection_name = "test_collection"
    index_name = "vector_search_index_1"  # Ensure this matches your intended index name
    distance_metric = "cosine"

    # Create the search index
    client._create_search_index(
        database_name=database_name,
        collection_name=collection_name,
        index_name=index_name,
        get_embedding=get_embedding,
        distance_metric=distance_metric,
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
        return  # Exit if the index is not ready

    # Insert documents (generic method)
    documents = [
        {
            "name": "Document 1",
            "content": "OpenAI develops artificial intelligence technologies.",
            "meta_data": {"category": "AI", "tags": ["openai", "ai", "technology"]},
        },
        {
            "name": "Document 2",
            "content": "MongoDB is a popular NoSQL database.",
            "meta_data": {"category": "Database", "tags": ["mongodb", "nosql", "database"]},
        },
        {
            "name": "Document 3",
            "content": "Python is a versatile programming language.",
            "meta_data": {"category": "Programming", "tags": ["python", "programming", "language"]},
        },
        {
            "name": "Document 4",
            "content": "Artificial intelligence and machine learning are transforming industries.",
            "meta_data": {"category": "AI", "tags": ["ai", "machine learning", "transformation"]},
        },
        {
            "name": "Document 5",
            "content": "OpenAI's ChatGPT is a language model for generating human-like text.",
            "meta_data": {"category": "AI", "tags": ["openai", "chatgpt", "language model"]},
        },
    ]

    fields_to_embed = ["content"]  # Specify which fields to generate embeddings for

    client.insert_documents(
        database_name=database_name,
        collection_name=collection_name,
        documents=documents,
        fields_to_embed=fields_to_embed,
    )

    # Demonstrate the search features with a compelling story
    # 1. Vector-Based Search: Discovering AI advancements
    vector_query = "Tell me about artificial intelligence advancements."
    logger.info(f"Performing vector-based search with query: '{vector_query}'")
    vector_results = client.vector_search(
        query=vector_query,
        limit=3,
        database_name=database_name,
        collection_name=collection_name,
        index_name=index_name
    )
    print("\n--- Vector-Based Search Results ---")
    for doc in vector_results:
        print(f"Name: {doc.get('name')}\nContent: {doc.get('content')}\nMeta Data: {doc.get('meta_data')}\nScore: {doc.get('score')}\n")

    # 2. Keyword Search: Finding documents related to Python
    keyword_query = "Python"
    logger.info(f"Performing keyword search with query: '{keyword_query}'")
    keyword_results = client.keyword_search(
        query=keyword_query,
        limit=3,
        database_name=database_name,
        collection_name=collection_name
    )
    print("\n--- Keyword Search Results ---")
    for doc in keyword_results:
        print(f"Name: {doc.get('name')}\nContent: {doc.get('content')}\nMeta Data: {doc.get('meta_data')}\n")

    # 3. Hybrid Search: Combining semantic relevance with keyword filtering
    hybrid_vector_query = "Advancements in machine learning."
    hybrid_keyword = "transforming"
    logger.info(f"Performing hybrid search with vector query: '{hybrid_vector_query}' and keyword: '{hybrid_keyword}'")
    hybrid_results = client.hybrid_search(
        query=hybrid_vector_query,
        keyword=hybrid_keyword,
        limit=3,
        database_name=database_name,
        collection_name=collection_name,
        index_name=index_name
    )
    print("\n--- Hybrid Search Results ---")
    for doc in hybrid_results:
        print(f"Name: {doc.get('name')}\nContent: {doc.get('content')}\nMeta Data: {doc.get('meta_data')}\nScore: {doc.get('score')}\n")


if __name__ == "__main__":
    main()

"""
INFO:__main__:Found existing index 'vector_search_index_1'.
INFO:__main__:Search index 'vector_search_index_1' already exists in collection 'test_collection'.
INFO:__main__:Waiting for the search index to be READY...
INFO:__main__:Search index 'vector_search_index_1' is READY.
INFO:__main__:Search index 'vector_search_index_1' is now READY and available!
Index is ready!
INFO:__main__:Collection 'test_collection' already has data. Skipping document insertion.
INFO:__main__:Performing vector-based search with query: 'Tell me about artificial intelligence advancements.'
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
INFO:__main__:Found existing index 'vector_search_index_1'.
INFO:__main__:Vector search completed. Found 3 documents.

--- Vector-Based Search Results ---
Name: Document 1
Content: OpenAI develops artificial intelligence technologies.
Meta Data: {'category': 'AI', 'tags': ['openai', 'ai', 'technology']}
Score: 0.7991563081741333

Name: Document 4
Content: Artificial intelligence and machine learning are transforming industries.
Meta Data: {'category': 'AI', 'tags': ['ai', 'machine learning', 'transformation']}
Score: 0.7392491102218628

Name: Document 5
Content: OpenAI's ChatGPT is a language model for generating human-like text.
Meta Data: {'category': 'AI', 'tags': ['openai', 'chatgpt', 'language model']}
Score: 0.6569141149520874

INFO:__main__:Performing keyword search with query: 'Python'
INFO:__main__:Keyword search completed. Found 1 documents.

--- Keyword Search Results ---
Name: Document 3
Content: Python is a versatile programming language.
Meta Data: {'category': 'Programming', 'tags': ['python', 'programming', 'language']}

INFO:__main__:Performing hybrid search with vector query: 'Advancements in machine learning.' and keyword: 'transforming'
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
INFO:__main__:Found existing index 'vector_search_index_1'.
INFO:__main__:Hybrid search completed. Found 1 documents.

--- Hybrid Search Results ---
Name: Document 4
Content: Artificial intelligence and machine learning are transforming industries.
Meta Data: {'category': 'AI', 'tags': ['ai', 'machine learning', 'transformation']}
Score: 0.7872726321220398
"""