import logging
logger = logging.getLogger(__name__)
logger.info("Initializing mdb_toolkit package")

from .core import CustomMongoClient

__all__ = ['CustomMongoClient']