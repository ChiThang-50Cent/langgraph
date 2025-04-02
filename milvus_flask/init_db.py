from sentence_transformers import SentenceTransformer
from pymilvus import (
    MilvusClient,
    FieldSchema,
    CollectionSchema,
    DataType
)
from tqdm import tqdm
import json

def load_model():
    return SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)

def create_schemas():
    sample_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="query", dtype=DataType.VARCHAR, max_length=8000),
        FieldSchema(name="tables", dtype=DataType.JSON),
        FieldSchema(name="lang", dtype=DataType.VARCHAR, max_length=20)
    ]

    guide_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=8000),
        FieldSchema(name="keyword", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="lang", dtype=DataType.VARCHAR, max_length=20)
    ]

    table_fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=8000),
        FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="lang", dtype=DataType.VARCHAR, max_length=20),
    ]

    sample_schema = CollectionSchema(
        fields=sample_fields,
        description="Collection for storing document embeddings"
    )

    guide_schema = CollectionSchema(
        fields=guide_fields,
        description="Collection for storing document embeddings"
    )

    table_schema = CollectionSchema(
        fields=table_fields,
        description="Collection for storing table embeddings"
    )

    return sample_schema, guide_schema, table_schema

def init_collections(client, collection_names, schemas):
    for name, schema in zip(collection_names, schemas):
        if client.has_collection(name):
            client.drop_collection(name)
        client.create_collection(
            collection_name=name,
            schema=schema
        )

def create_index(client, collection_names):
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        metric_type="COSINE",
        index_type="IVF_FLAT",
        index_name="vector_index",
        params={"nlist": 128}
    )
    
    for name in collection_names:
        client.create_index(
            collection_name=name,
            index_params=index_params,
        )

def load_and_insert_samples(client, model, collection_name):
    with open('./samples.json', 'r') as f:
        text_lines = json.load(f)

    data = []
    for line in tqdm(text_lines, desc="Creating embeddings for samples"):
        data.append({
            "vector": model.encode(str(line["description"])).tolist(),
            "description": line["description"],
            "query": line["query"],
            "tables": line["tables"],
            "lang": line["lang"]
        })

    client.insert(collection_name=collection_name, data=data)

def load_and_insert_keywords(client, model, collection_name):
    with open('./keywords.json', 'r') as f:
        text_lines = json.load(f)

    data = []
    for line in tqdm(text_lines, desc="Creating embeddings for keywords"):
        text = (
            f"{line['keyword']} có nghĩa là {line['description']}"
            if line["lang"] == "vi"
            else f"{line['keyword']} means {line['description']}"
        )
        data.append({
            "vector": model.encode(text).tolist(),
            "description": line["description"],
            "keyword": line["keyword"],
            "lang": line["lang"],
        })

    client.insert(collection_name=collection_name, data=data)

def load_and_insert_tables(client, model, collection_name):
    with open('./tables.json', 'r') as f:
        text_lines = json.load(f)

    data = []
    for line in tqdm(text_lines, desc="Creating embeddings for tables"):
        text = f'{line["name"]}: {line["description"]}'
        data.append({
            "vector": model.encode(text).tolist (),
            "description": line["description"],
            "name": line["name"],
            "lang": line["lang"],
        })

    client.insert(collection_name=collection_name, data=data)

def main():
    print("Initializing database...")
    
    # Initialize model and client
    model = load_model()
    client = MilvusClient(uri="./data.db")
    
    # Collection names
    guide_collection = "guides"
    query_collection = "samples"
    table_collection = "tables"
    collection_names = [query_collection, guide_collection, table_collection]

    # Create and initialize collections
    sample_schema, guide_schema, table_schema = create_schemas()
    init_collections(client, collection_names, [sample_schema, guide_schema, table_schema])
    
    # Create indexes
    create_index(client, collection_names)

    # Load and insert data
    load_and_insert_samples(client, model, query_collection)
    load_and_insert_keywords(client, model, guide_collection)
    load_and_insert_tables(client, model, table_collection)
    
    print("Database initialization complete!")

if __name__ == "__main__":
    main()
