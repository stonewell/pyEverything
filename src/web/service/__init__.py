import atexit

from .index import index_api
from .indexer import indexer


def start_indexer():
  indexer().start()

  atexit.register(stop_indexer)


def stop_indexer():
  indexer().stop()


def register_blueprints(app):
  app.register_blueprint(index_api)
