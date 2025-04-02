import os
import json
import logging

from utils import (
    milvus_insert,
    milvus_search,
    init_embedding_model,
    milvus_query,
    init_milvus_client,
)

from flask import Flask, Response, request
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

SERVER_HOST = os.environ.get('SERVER_HOST')
SERVER_PORT = os.environ.get('SERVER_PORT')

_logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

init_embedding_model()
init_milvus_client()

@app.route('/')
def main():
    return_dict = {'code': 200, 'status': 'OK'}
    return Response(json.dumps(return_dict))

@app.route('/insert', methods=['POST'])
def insert():
    data = json.loads(request.data)
    collection_name = data['collection_name']
    entities = data['entities']
    try:
        res = milvus_insert(collection_name=collection_name, entities=entities)
        return_dict = {'code': 200, 'status': 'OK', 'data': json.dumps(res)}
    except Exception as e:
        return_dict = {'code': 500, 'error': str(e)}
        _logger.error(f"Milvus insert failed: {e}", exc_info=True)
    return Response(json.dumps(return_dict))

@app.route('/search', methods=['POST'])
def search():
    question = json.loads(request.data)
    collection_name = question['collection_name']
    output_fields = question['output_fields']
    limit = question.get('limit', 2)
    lang=question.get('lang', 'vi'),
    try:
        res = milvus_search(
            question=question['question'],
            collection_name=collection_name,
            output_fields=output_fields,
            lang=lang,
            limit=limit,
        )
        return_dict = {'code': 200, 'status': 'OK', 'data': res}
    except Exception as e:
        return_dict = {'code': 500, 'error': str(e)}
        _logger.error(f"Milvus search failed: {e}", exc_info=True)
    return Response(json.dumps(return_dict, ensure_ascii=False))

@app.route('/query', methods=['POST'])
def query():
    question = json.loads(request.data)
    collection_name = question['collection_name']
    output_fields = question['output_fields']
    lang=question.get('lang', 'vi'),
    try:
        res = milvus_query(collection_name, output_fields, lang=lang)
        return_dict = {'code': 200, 'status': 'OK', 'data': res}
    except Exception as e:
        return_dict = {'code': 500, 'error': str(e)}
        _logger.error(f"Milvus query failed: {e}", exc_info=True)
    return Response(json.dumps(return_dict, ensure_ascii=False))

@app.route('/download', methods=['GET'])
def download_file():
    file_path = './data.db'
    if os.path.exists(file_path):
        return Response(
            open(file_path, 'rb'),
            headers={
                'Content-Disposition': f'attachment; filename={os.path.basename(file_path)}',
                'Content-Type': 'application/octet-stream'
            }
        )
    else:
        return_dict = {'code': 404, 'error': 'File not found'}
        return Response(json.dumps(return_dict), status=404)

if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)