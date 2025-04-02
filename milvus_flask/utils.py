from pymilvus import MilvusClient
from functools import lru_cache
from sentence_transformers import SentenceTransformer


import logging
_logger = logging.getLogger(__name__)

QUERY_COLLECTION_NAME = "samples"
GUIDE_COLLECTION_NAME = "guides"
TABLE_COLLECTION_NAME = "tables"

def init_embedding_model():
    """Initialize SentenceTransformer model."""
    global _ef_model
    _logger.info("Initializing SentenceTransformer model")
    _ef_model = SentenceTransformer(
        "jinaai/jina-embeddings-v3", trust_remote_code=True, revision="main"
    )
    _logger.info("SentenceTransformer model initialized")
    return _ef_model

def init_milvus_client():
    """Initialize Milvus client."""
    _logger.info("Initializing Milvus client")
    global _milvus_client
    _milvus_client = MilvusClient(uri='./data.db')
    _logger.info("Milvus client initialized")
    return _milvus_client

def get_ef() -> SentenceTransformer:
    """Get OpenAI client instance.""" 
    global _ef_model
    if not _ef_model:
        _ef_model = init_embedding_model()
    return _ef_model

def get_milvus_client() -> MilvusClient:
    """Get Milvus client instance."""
    global _milvus_client
    if not _milvus_client:
        _milvus_client = init_milvus_client()
    return _milvus_client

@lru_cache(maxsize=1024)
def embedding_fn(text: str) -> list[float]:
    em_model = get_ef()
    return em_model.encode(text).tolist()

def get_collection_name(collection):
    if collection == 'sample':
        return QUERY_COLLECTION_NAME
    elif collection == 'guide':
        return GUIDE_COLLECTION_NAME
    elif collection == 'table':
        return TABLE_COLLECTION_NAME

def milvus_insert(
    data: dict, 
    collection_name: str
):
    """Insert vectors into Milvus collection.
    
    Args:
        data: Dictionary containing vectors
        collection_name: Name of collection to insert into
    """
    milvus_client = get_milvus_client()
    data['vector'] = embedding_fn(data['query'])
    
    try:
        return milvus_client.insert(
            collection_name=collection_name,
            entities=data
        )
    except Exception as e:
        _logger.error(f"Milvus insert failed: {e}", exc_info=True)

def milvus_query(
    collection_name: str, output_fields: list[str], lang: str
) -> list[dict]:
    milvus_client = get_milvus_client()

    try:
        search_res = milvus_client.query(
            collection_name=get_collection_name(collection_name),
            filter="lang == '%s'" % lang,
            output_fields=output_fields,
        )

        return search_res
    except Exception as e:
        _logger.error(f"Milvus query failed: {e}", exc_info=True)
        return []

def milvus_search(
    question: list[float],
    collection_name: str, 
    output_fields: list[str],
    lang: str = "vi",
    limit: int = 2,
) -> list[dict]:
    """Search vectors in Milvus collection.
    
    Args:
        question: Query
        collection_name: Name of collection to search
        output_fields: Fields to return in results
        limit: Maximum number of results
        
    Returns:
        List of matching documents
    """
    milvus_client = get_milvus_client()

    _logger.info("ef_model: %s", _ef_model)

    try:
        search_res = milvus_client.search(
            collection_name=get_collection_name(collection_name),
            data=[embedding_fn(question)],
            limit=limit,
            filter="lang == '%s'" % lang,
            search_params={"metric_type": "COSINE", "params": {}}, 
            output_fields=output_fields
        )

        return [
            item['entity'] 
            for item in search_res[0] 
        ]
    except Exception as e:
        _logger.error(f"Milvus search failed: {e}", exc_info=True)
        return []  