import logging  
import time  
from typing import List, Optional, Dict, Any  
  
import openai  
from pymongo import MongoClient  
from pymongo.collection import Collection  
from pymongo.operations import SearchIndexModel  
from pymongo.errors import OperationFailure  
  
# Configure logging  
logger = logging.getLogger(__name__)  
logging.basicConfig(level=logging.INFO)  
  
def get_embedding(text: str, model: str = "text-embedding-3-small", dimensions: int = 256) -> List[float]:  
    text = text.replace("\n", " ")  
    try:  
        response = openai.OpenAI().embeddings.create(input=[text], model=model, dimensions=dimensions)  
        return response.data[0].embedding  
    except Exception as e:  
        logger.error(f"Error generating embedding: {str(e)}")  
        raise  
  
class PymongoPlus(MongoClient):  
    def __init__(self, *args, **kwargs):  
        super().__init__(*args, **kwargs)  
  
    def create_if_not_exists(self, database_name: str, collection_name: str) -> Collection:  
        database = self[database_name]  
        collection_names = database.list_collection_names()  
  
        if collection_name not in collection_names:  
            logger.info(f"Collection '{collection_name}' does not exist. Creating it now.")  
            collection = database[collection_name]  
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
        distance_metric: str = "euclidean",  
    ) -> None:  
        try:  
            self.create_if_not_exists(database_name, collection_name)  
  
            if self.index_exists(database_name, collection_name, index_name):  
                logger.info(f"Search index '{index_name}' already exists in collection '{collection_name}'.")  
                return  
  
            logger.info(f"Creating search index '{index_name}' for collection '{collection_name}'.")  
  
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
        try:  
            collection = self[database_name][collection_name]  
            indexes = list(collection.list_search_indexes())  
            exists = any(index["name"] == index_name for index in indexes)  
            return exists  
        except OperationFailure as e:  
            logger.error(f"Operation failure while checking index existence: {e}")  
            return False  
        except Exception as e:  
            logger.error(f"Error checking search index existence for '{index_name}': {e}")  
            return False  
  
    def search(  
        self,  
        query: str,  
        limit: int = 5,  
        database_name: str = "",  
        collection_name: str = "",  
        index_name: str = "",  
        filters: Optional[Dict[str, Any]] = None,  
    ) -> List[Dict]:  
        query_embedding = get_embedding(query)  
        if not self.index_exists(database_name, collection_name, index_name):  
            logger.error(f"Index {index_name} does not exist.")  
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
            logger.info(f"Search completed. Found {len(results)} documents.")  
            return results  
        except Exception as e:  
            logger.error(f"Error during search: {e}")  
            return []  
  
    def keyword_search(  
        self,  
        query: str,  
        limit: int = 5,  
        database_name: str = "",  
        collection_name: str = "",  
    ) -> List[Dict]:  
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
        limit: int = 5,  
        database_name: str = "",  
        collection_name: str = "",  
        index_name: str = "",  
        filters: Optional[Dict[str, Any]] = None,  
    ) -> List[Dict]:  
        logger.debug("Performing hybrid search is not yet implemented.")  
        return []  
  
if __name__ == "__main__":  
    client = PymongoPlus("mongodb://0.0.0.0/?directConnection=true")  
  
    database_name = "test_database"  
    collection_name = "test_collection"  
    index_name = "vector_search_index"  
    distance_metric = "cosine"  
  
    client._create_search_index(  
        database_name=database_name,  
        collection_name=collection_name,  
        index_name=index_name,  
        get_embedding=get_embedding,  
        distance_metric=distance_metric,  
    )  
  
    logger.info("Waiting for the search index to be available...")  
    max_attempts = 10  
    attempt = 0  
    while not client.index_exists(database_name, collection_name, index_name):  
        attempt += 1  
        if attempt > max_attempts:  
            logger.error("Search index creation timed out after waiting.")  
            break  
        logger.info(f"Attempt {attempt}: Search index '{index_name}' not ready yet. Waiting...")  
        time.sleep(1)  
  
    if client.index_exists(database_name, collection_name, index_name):  
        logger.info(f"Search index '{index_name}' is now available!")  
        print("Index is ready!")  
    else:  
        print("Index creation process exceeded wait limit.")  
