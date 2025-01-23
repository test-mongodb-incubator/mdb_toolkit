# mdb_toolkit

![](demo.png)

---

Integrating advanced search capabilities into your applications can often be complex and time-consuming. However, our latest MongoDB integration changes the game by **streamlining the process, reducing the amount of code you need to write, and making embedding effortless**. 

#### **1. Effortless Embedding Integration**
Embedding AI functionalities into your MongoDB database has never been simpler. Our custom `MongoClient` handles the generation and storage of embeddings seamlessly. This means you can focus on building features rather than managing the intricacies of embedding processes.

#### **2. Clean and Maintainable Codebase**
Say goodbye to cluttered and hard-to-maintain code! Our implementation consolidates essential operations—like creating search indexes, inserting documents with embeddings, and performing various types of searches—into a single, well-organized class. This not only reduces the number of lines you need to write but also enhances the readability and maintainability of your code.

#### **3. Versatile Search Capabilities**
Whether you need vector-based searches, keyword searches, or a combination of both, our integration has you covered. The `vector_search`, `keyword_search`, and `hybrid_search` methods provide flexible options to retrieve the most relevant documents efficiently. This versatility ensures that you can meet a wide range of search requirements with ease.

#### **4. Robust and Reliable Performance**
Built on MongoDB’s solid infrastructure, our client ensures reliable performance from index creation to search execution. With comprehensive logging and error handling, you can trust that your searches will run smoothly and any issues will be promptly identified and addressed.

#### **5. Quick and Easy Deployment**
Configuration is a breeze with support for environment variables and seamless integration with OpenAI’s embedding API. Whether you’re deploying locally or scaling up in the cloud, our setup is designed to fit effortlessly into your existing workflow, allowing you to get started quickly without unnecessary hassle.

---

## Code

```
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
```

---

## Output

```
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
```
