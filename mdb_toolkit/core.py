import logging
import time
from typing import List, Optional, Dict, Any, Callable, Union
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel
from pymongo.errors import OperationFailure

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("Importing core module")


# --------------------------------------------------------------------
# Node & Edge classes for Knowledge Graph
# --------------------------------------------------------------------
class Node:
    """Represents a node in the knowledge graph."""
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type

class Edge:
    """Represents an edge in the knowledge graph."""
    def __init__(self, source_node: Node, target_node: Node, relation: str):
        self.source_node = source_node
        self.target_node = target_node
        self.relation = relation

    def __eq__(self, other):
        if isinstance(other, Edge):
            return (
                self.source_node.name == other.source_node.name
                and self.target_node.name == other.target_node.name
                and self.relation == other.relation
            )
        return False

    def __hash__(self):
        return hash((self.source_node.name, self.target_node.name, self.relation))


# --------------------------------------------------------------------
# Knowledge Graph API - Sub-namespace for the CustomMongoClient
# --------------------------------------------------------------------
class _KGClient:
    """
    _KGClient encapsulates Knowledge Graph methods:
      - store_nodes_and_edges()
      - find_related_nodes()
      (any other KG-related queries / $graphLookup logic can be added here)
    """
    def __init__(self, parent_client: "CustomMongoClient"):
        """
        :param parent_client: reference to the main CustomMongoClient
        """
        self._client = parent_client  # the actual underlying MongoClient

    def store_nodes_and_edges(
        self,
        db_name: str,
        collection_name: str,
        nodes: Dict[str, Node],
        edges: List[Edge]
    ) -> None:
        """
        Stores the knowledge graph (nodes + edges) in MongoDB.
        Each node gets inserted as one document with _id == node.name,
        plus an 'edges' array containing { relation, target }.
        """
        try:
            db = self._client[db_name]
            collection = db[collection_name]

            # Clear existing data
            collection.delete_many({})

            # Insert node docs
            for node_name, node_obj in nodes.items():
                doc = {
                    "_id": node_name,
                    "type": node_obj.type,
                    "edges": []
                }

                # For each edge starting from this node
                for edge in edges:
                    if edge.source_node.name == node_name:
                        doc["edges"].append({
                            "relation": edge.relation,
                            "target": edge.target_node.name
                        })

                collection.insert_one(doc)

            logger.info(f"store_nodes_and_edges: Inserted {len(nodes)} nodes into '{collection_name}'.")

        except Exception as e:
            logger.error(f"Error in store_nodes_and_edges: {e}")
            raise

    def find_related_nodes(
        self,
        start_node_id: str,
        db_name: str,
        collection_name: str
    ) -> List[Dict[str, Any]]:
        """
        Performs a generic $graphLookup, starting from the document `_id == start_node_id`,
        traversing 'edges.target' -> '_id', collecting them into an array 'related_nodes'.

        Returns a list like:
          [
            {
                "related_nodes": [
                    {"_id": "Apple", "type": "company", "depth": 1},
                    ...
                ]
            },
            ...
          ]
        Typically there's only 1 doc in the top-level list, but it can vary.
        """
        try:
            db = self._client[db_name]
            coll = db[collection_name]

            pipeline = [
                {"$match": {"_id": start_node_id}},
                {
                    "$graphLookup": {
                        "from": collection_name,
                        "startWith": "$edges.target",
                        "connectFromField": "edges.target",
                        "connectToField": "_id",
                        "as": "related_nodes",
                        "depthField": "depth"
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "related_nodes._id": 1,
                        "related_nodes.type": 1,
                        "related_nodes.depth": 1
                    }
                }
            ]

            result = list(coll.aggregate(pipeline))
            logger.info(f"find_related_nodes: found {len(result)} doc(s) for '{start_node_id}'.")
            return result

        except Exception as e:
            logger.error(f"Error in find_related_nodes: {e}")
            return []


# --------------------------------------------------------------------
# Main CustomMongoClient
# --------------------------------------------------------------------
class CustomMongoClient(MongoClient):
    def __init__(self, *args, get_embedding: Callable[[str], List[float]], **kwargs):
        """
        Initializes the CustomMongoClient with a get_embedding function.
        """
        super().__init__(*args, **kwargs)
        self.get_embedding = get_embedding

        # Attach Knowledge Graph sub-namespace
        self.kg = _KGClient(self)

    def create_if_not_exists(
        self,
        database_name: str,
        collection_name: str
    ) -> Collection:
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
            num_dimensions = len(self.get_embedding("sample text"))
            search_index_model = SearchIndexModel(
                definition={
                    "mappings": {
                        "dynamic": False,
                        "fields": {
                            "embedding": {
                                "type": "knnVector",
                                "dimensions": num_dimensions,
                                "similarity": distance_metric,
                            }
                        },
                    }
                },
                name=index_name,
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
            logger.debug(f"Retrieved indexes: {indexes}")

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
            logger.info(
                f"Attempt {attempt}: Search index '{index_name}' not READY yet. "
                f"Waiting {wait_seconds} second(s)..."
            )
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
                skip_doc = False
                for field in fields_to_embed:
                    if field in doc:
                        embedding = self.get_embedding(doc[field])
                        if embedding is None:
                            logger.warning(
                                f"Skipping document '{doc.get('name', 'Unnamed')}' "
                                f"due to failed embedding for field '{field}'."
                            )
                            skip_doc = True
                            break
                        doc[f"{field}_embedding"] = embedding
                    else:
                        logger.warning(
                            f"Field '{field}' not found in document '{doc.get('name', 'Unnamed')}'. "
                            "Skipping document."
                        )
                        skip_doc = True
                        break
                if not skip_doc:
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
        query: Union[str, List[float]],
        limit: int = 5,
        database_name: str = "",
        collection_name: str = "",
        index_name: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """
        Performs a vector-based search using the specified search index.
          - If `query` is a string, we call self.get_embedding(query).
          - If `query` is a list/tuple, we assume it's already the embedding.
        """
        # Determine query embedding
        if isinstance(query, str):
            query_embedding = self.get_embedding(query)
        elif isinstance(query, (list, tuple)):
            query_embedding = query  # assume user supplied embedding
        else:
            logger.error(f"Query type {type(query)} not supported for vector search.")
            return []

        if not self.index_exists(database_name, collection_name, index_name):
            logger.error(f"Index '{index_name}' does not exist.")
            return []
        if query_embedding is None:
            logger.error(f"Failed to generate or receive embedding for query: {query}")
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
                {"embedding": 0}  # Exclude the embedding from the results
            ).limit(limit)
            results = list(cursor)
            logger.info(f"Keyword search completed. Found {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during keyword search: {e}")
            return []

    def hybrid_search(
        self,
        query: Union[str, List[float]],
        keyword: str,
        limit: int = 5,
        database_name: str = "",
        collection_name: str = "",
        index_name: str = "",
        distance_metric: str = "cosine",
    ) -> List[Dict]:
        """
        Performs a hybrid search combining vector-based search and keyword filtering.
        Returns documents that are semantically relevant AND match the keyword.
          - If `query` is a string, we call self.get_embedding(query).
          - If `query` is a list/tuple, we assume it's already the embedding.
        """
        if isinstance(query, str):
            query_embedding = self.get_embedding(query)
        elif isinstance(query, (list, tuple)):
            query_embedding = query
        else:
            logger.error(f"Query type {type(query)} not supported for hybrid search.")
            return []

        if not self.index_exists(database_name, collection_name, index_name):
            logger.error(f"Index '{index_name}' does not exist.")
            return []
        if query_embedding is None:
            logger.error(f"Failed to generate or receive embedding for query: {query}")
            return []

        try:
            collection = self[database_name][collection_name]
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "limit": limit * 2,  # fetch more to account for filtering
                        "numCandidates": limit * 2,
                        "queryVector": query_embedding,
                        "path": "embedding",
                    }
                },
                {"$set": {"score": {"$meta": "vectorSearchScore"}}},
                {"$match": {"content": {"$regex": keyword, "$options": "i"}}},
                {"$sort": {"score": -1}},  # sort by relevance score
                {"$limit": limit},
                {"$project": {"embedding": 0}},
            ]
            results = list(collection.aggregate(pipeline))
            logger.info(f"Hybrid search completed. Found {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}")
            return []
