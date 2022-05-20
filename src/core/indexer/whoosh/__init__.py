import logging

from .. import IndexerImpl

from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh import index
from whoosh.filedb.filestore import FileStorage

FILE_INDEXING_SCHEMA = Schema(path=ID(stored=True),
                              content=TEXT,
                              create_time=DATETIME(stored=True),
                              modified_time=DATETIME(stored=True))


class WhooshIndexerImpl(IndexerImpl):

  def __init__(self, data_path):
    super().__init__(data_path)

    self.__initialize()

  def __initialize(self):
    self.storage_ = FileStorage(self.index_dir_)

    if index.exists_in(self.index_dir_):
      self.index_ = self.storage_.open_index()
      logging.debug(f'open existing index in {self.index_dir_}')
    else:
      self.index_ = self.storage_.create_index(FILE_INDEXING_SCHEMA)
      logging.debug(f'create new index in {self.index_dir_}')

    self.writer_ = None

  def add_document(self, path, full_indexing=False):
    pass

  def begin_index(self):
    if self.writer_ is not None:
      return

    self.writer_ = self.index_.writer()

  def end_index(self):
    if self.writer_ is None:
      return

    self.writer_.commit()
    self.writer_ = None
