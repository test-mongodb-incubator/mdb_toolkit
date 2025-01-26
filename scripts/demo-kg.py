# demo.py

import logging

# If your package is installed (e.g. pip install -e .),
# you can do: from mdb_toolkit import CustomMongoClient, Node, Edge
# Otherwise, if you're developing locally:
from mdb_toolkit import CustomMongoClient, Node, Edge

# 1) Define a dummy embedding function
def dummy_embedding(text: str):
    """
    Returns a simple numeric vector of length 5.
    For instance, each element is just float(len(text)).
    This is purely for demonstration, not for real semantic search.
    """
    length = float(len(text))
    return [length, length, length, length, length]

def main():
    # Setup logging for our demo
    logging.basicConfig(level=logging.DEBUG)

    # 2) Create a CustomMongoClient instance
    client = CustomMongoClient(
        get_embedding=dummy_embedding,
        host="mongodb://0.0.0.0/?directConnection=true",
        port=27017
    )
    
    # ----------------------------------------------------------------
    # Knowledge Graph Demo
    # ----------------------------------------------------------------
    # Create a few Node/Edge objects
    n1 = Node("Alice", "person")
    n2 = Node("AcmeCorp", "company")
    n3 = Node("Bob", "person")

    e1 = Edge(n1, n2, "works at")
    e2 = Edge(n3, n2, "works at")
    e3 = Edge(n1, n3, "knows")

    # Put them in a dictionary/list
    nodes_dict = {
        "Alice": n1,
        "AcmeCorp": n2,
        "Bob": n3
    }
    edges_list = [e1, e2, e3]

    # Store them in Mongo
    KG_DB = "demo_db"
    KG_COLL = "demo_kg"
    client.kg.store_nodes_and_edges(
        db_name=KG_DB,
        collection_name=KG_COLL,
        nodes=nodes_dict,
        edges=edges_list
    )

    # Query the graph
    related_to_alice = client.kg.find_related_nodes(
        start_node_id="Alice",
        db_name=KG_DB,
        collection_name=KG_COLL
    )
    print("\n--- Knowledge Graph: find_related_nodes('Alice') ---")
    print(related_to_alice)

    # ----------------------------------------------------------------
    # Vector/Keyword/Hybrid Search Demo
    # ----------------------------------------------------------------
    DOCS_DB = "demo_db"
    DOCS_COLL = "demo_docs"
    INDEX_NAME = "demo_index"

    # Example documents
    my_documents = [
        {"_id": 1, "content": "Alice is a software engineer at AcmeCorp."},
        {"_id": 2, "content": "Bob works at AcmeCorp. He is a data scientist."},
        {"_id": 3, "content": "Alice and Bob are co-workers at AcmeCorp."},
    ]

    # Insert them (each doc gets an embedding for 'content')
    client.insert_documents(
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        documents=my_documents,
        fields_to_embed=["content"]
    )

    # Create an Atlas Search Vector Index (or local if running 7.0+)
    client._create_search_index(
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        index_name=INDEX_NAME,
        distance_metric="cosine"
    )

    # Wait for index to be ready
    client.wait_for_index_ready(
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        index_name=INDEX_NAME,
        max_attempts=5,
        wait_seconds=1
    )

    # ----------------------------------------------------------------
    # Vector Search #1 (query is a string, we embed it automatically)
    # ----------------------------------------------------------------
    print("\n--- Vector Search (string query) ---")
    results_vector_str = client.vector_search(
        query="Alice at AcmeCorp",  # string => will be embedded via dummy_embedding
        limit=2,
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        index_name=INDEX_NAME
    )
    for doc in results_vector_str:
        print(doc)

    # ----------------------------------------------------------------
    # Vector Search #2 (query is precomputed embedding, skip embedding)
    # ----------------------------------------------------------------
    print("\n--- Vector Search (precomputed embedding) ---")
    my_precomputed_emb = [12.34, 12.34, 12.34, 12.34, 12.34]
    results_vector_emb = client.vector_search(
        query=my_precomputed_emb,  # directly use as embedding
        limit=2,
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        index_name=INDEX_NAME
    )
    for doc in results_vector_emb:
        print(doc)

    # ----------------------------------------------------------------
    # Keyword Search
    # ----------------------------------------------------------------
    print("\n--- Keyword Search ---")
    results_keyword = client.keyword_search(
        query="co-workers",  # regex-based match in 'content' field
        limit=2,
        database_name=DOCS_DB,
        collection_name=DOCS_COLL
    )
    for doc in results_keyword:
        print(doc)

    # ----------------------------------------------------------------
    # Hybrid Search (vector + keyword filter)
    # ----------------------------------------------------------------
    print("\n--- Hybrid Search ---")
    results_hybrid = client.hybrid_search(
        query="Alice is at AcmeCorp",  # string => will embed
        keyword="engineer",            # must appear in content
        limit=2,
        database_name=DOCS_DB,
        collection_name=DOCS_COLL,
        index_name=INDEX_NAME
    )
    for doc in results_hybrid:
        print(doc)

if __name__ == "__main__":
    main()
