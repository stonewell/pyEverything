from core.indexing import Indexer

__g_indexer = None


def indexer(location=None):
  global __g_indexer

  if __g_indexer is None:
    __g_indexer = Indexer(location)

  return __g_indexer
