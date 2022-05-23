from core.indexing import Indexer

__g_indexer = None


def indexer():
  global __g_indexer

  if __g_indexer is None:
    __g_indexer = Indexer()

  return __g_indexer
