import atexit

from core.indexing import Indexer

from .index import index_api

__g_indexer = None


def indexer():
  global __g_indexer

  return __g_indexer


def start_indexer():
  global __g_indexer

  __g_indexer = Indexer()
  __g_indexer.start()

  atexit.register(stop_indexer)


def stop_indexer():
  global __g_indexer

  __g_indexer.stop()


def register_blueprints(app):
  app.register_blueprint(index_api)
