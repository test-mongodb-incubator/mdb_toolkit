# mdb_toolkit

![](https://github.com/ranfysvalle02/mdb_toolkit/raw/main/demo.png)

# Less Code, More Power  

MongoDB's flexibility and PyMongo's robust driver make it a popular choice for database management in Python applications. While PyMongo's `MongoClient` class provides rich functionality, there are scenarios where adding custom methods can simplify repetitive tasks or enhance the developer experience. 

---  
      
### **Why Customize MongoClient?**
- **Streamlined Operations**: Simplify frequent tasks like listing databases and collections.
- **Encapsulation**: Abstract additional functionality into a single, reusable class.
- **Extensibility**: Add new methods to tailor MongoDB operations to your project’s needs.

---

### **Setting Up the Environment**
Before diving into code, we’ll need a MongoDB instance to work with. A simple command to start a local MongoDB container:

```bash
docker run -d -p 27017:27017 --restart unless-stopped mongodb/mongodb-atlas-local
```

**OR** 

if you already have a MongoDB Atlas cluster, keep the MongoDB URI handy as you will need it :)

---

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

# mdb_toolkit

**mdb_toolkit** is a custom MongoDB client that integrates seamlessly with OpenAI's embedding models to provide advanced vector-based search capabilities. It enables semantic searches, keyword searches, and hybrid searches within your MongoDB collections.

## Features

- **Vector-Based Search**: Perform semantic searches using OpenAI embeddings.
- **Keyword Search**: Execute traditional text-based searches with regular expressions.
- **Hybrid Search**: Combine semantic relevance with keyword filtering for precise results.
- **Easy Integration**: Simple setup with MongoDB and OpenAI APIs.
- **Comprehensive Logging**: Detailed logs for monitoring and debugging.

## Installation

Install `mdb_toolkit` using `pip`:

```bash
pip install mdb-toolkit
```

*Requires Python 3.7 or higher.*

## Example Usage

Here's a sample script demonstrating how to use `mdb_toolkit` to create a search index, insert documents, and perform various search operations.

```python
import logging
import openai
from typing import List

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Embedding Function
def get_embedding(text: str, model: str = "text-embedding-ada-002", dimensions: int = 256) -> List[float]:
    text = text.replace("\n", " ")
    try:
        response = openai.Embedding.create(
            input=[text],
            model=model
        )
        return response['data'][0]['embedding']
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

# Perform searches
# 1. Vector-Based Search
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

# 2. Keyword Search
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

# 3. Hybrid Search
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

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## Support

If you encounter any issues or have questions, please open an issue on the [GitHub repository](git@github.com:ranfysvalle02/mdb_toolkit.git).

---

*Happy Coding!*
