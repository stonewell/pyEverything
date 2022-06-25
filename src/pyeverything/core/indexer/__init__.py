class IndexerImpl(object):

  def __init__(self, data_path):
    super().__init__()

    self.data_path_ = data_path
    self.index_dir_ = self.data_path_.resolve().as_posix()

  def add_document(self, path, full_indexing=False):
    raise NotImplementedError()

  def begin_index(self):
    raise NotImplementedError()

  def end_index(self, index_updated=True):
    raise NotImplementedError()

  def query(self, path, content, ignore_case=True, raw_pattern=False):
    raise NotImplementedError()

  def delete_path(self, path):
    raise NotImplementedError()

  def touch_path(self, path, modified_time):
    raise NotImplementedError()

  def clear_non_exist(self, path):
    raise NotImplementedError()

  def get_index_modified_time(self, path):
    raise NotImplementedError()

  def refresh_cache(self):
    raise NotImplementedError()

  def list_indexed_path(self):
    raise NotImplementedError()


def get_indexer_impl(data_path):
  from .whoosh import WhooshIndexerImpl

  return WhooshIndexerImpl(data_path)
