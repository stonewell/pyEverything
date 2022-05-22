from flask import Blueprint

index_api = Blueprint('index_api', __name__)


@index_api.route('/i', methods=['POST'])
def add_index():
  pass


@index_api.route('/i', methods=['DELETE'])
def delete_index():
  pass


@index_api.route('/q', methods=['GET'])
def query_index():
  pass


@index_api.route('/i/refresh', methods=['POST'])
def refresh_index():
  pass
