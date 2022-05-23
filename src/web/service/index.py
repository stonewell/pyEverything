from flask import Blueprint, request

from .indexer import indexer

index_api = Blueprint('index_api', __name__)


@index_api.route('/i', methods=['POST'])
def add_index():
  data = request.get_json()

  for p in data:
    indexer().index(p)

  return {'result':'ok'}


@index_api.route('/i', methods=['DELETE'])
def delete_index():
  path = None

  if 'path' in request.args:
    path = request.args['path']

  if path and len(path) == 0:
    path = None

  if path is None:
    abort(500)
    return

  indexer().remove(path)

  return {'result':'ok'}


@index_api.route('/q', methods=['GET'])
def query_index():
  path = None
  content = None

  if 'path' in request.args:
    path = request.args['path']

  if 'content' in request.args:
    content = request.args['content']

  if path and len(path) == 0:
    path = None

  if content and len(content) == 0:
    content = None

  result = indexer().query(path, content)

  items = result.query()

  return {"result": [x['path'] for x in items]}

@index_api.route('/i/refresh', methods=['POST'])
def refresh_index():
  pass
