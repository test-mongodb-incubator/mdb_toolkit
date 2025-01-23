from langchain_ollama import OllamaEmbeddings    
from typing import List

def get_embedding(text: str, model: str = "nomic-embed-text") -> List[float]:
    embeddings = OllamaEmbeddings(model=model)   
    text = text.replace("\n", " ")
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise
