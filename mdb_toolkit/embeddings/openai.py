
import openai  
from typing import List, Optional, Dict, Any  

def get_embedding(text: str, model: str = "text-embedding-3-small", dimensions: int = 256) -> List[float]:  
    text = text.replace("\n", " ")  
    try:  
        response = openai.OpenAI().embeddings.create(input=[text], model=model, dimensions=dimensions)  
        return response.data[0].embedding  
    except Exception as e:  
        logger.error(f"Error generating embedding: {str(e)}")  
        raise  