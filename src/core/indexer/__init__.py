class IndexerImpl(object):

  def __init__(self, data_path):
    super().__init__()

    self.data_path_ = data_path
    self.index_dir_ = self.data_path_.resolve().as_posix()

  def add_document(self, path, full_indexing=False):
    raise NotImplementedError()

  def begin_index(self):
    raise NotImplementedError()

  def end_index(self):
    raise NotImplementedError()

  def query(self, path, content):
    raise NotImplementedError()


def get_indexer_impl(data_path):
  from .whoosh import WhooshIndexerImpl

  return WhooshIndexerImpl(data_path)
