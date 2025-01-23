import logging
import openai
from typing import List

# load .ENV file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Embedding Function
def get_embedding(text: str, model: str = "text-embedding-3-small", dimensions: int = 256) -> List[float]:
    text = text.replace("\n", " ")
    try:
        return openai.OpenAI().embeddings.create(input=[text], model=model, dimensions=dimensions).data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

## Example usage
from mdb_toolkit import CustomMongoClient
print("mdb_toolkit package imported successfully")