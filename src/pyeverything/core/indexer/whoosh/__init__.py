import logging
import datetime
import pathlib
from binaryornot.check import is_binary

from whoosh.fields import Schema, ID, DATETIME, NGRAMWORDS, TEXT
from whoosh import index
from whoosh.filedb.filestore import FileStorage
from whoosh.qparser import MultifieldParser

from .. import IndexerImpl
from .query_result import QueryResult

FILE_INDEXING_SCHEMA = Schema(path=ID(stored=True, unique=True),
                              content=NGRAMWORDS,
                              tag=TEXT(stored=True),
                              create_time=DATETIME(stored=True),
                              modified_time=DATETIME(stored=True))


class WhooshIndexerImpl(IndexerImpl):

  def __init__(self, data_path):
    super().__init__(data_path)

    self.__initialize()

  def __initialize(self):
    self.storage_ = FileStorage(self.index_dir_)

    if index.exists_in(self.index_dir_):
      self.index_ = self.storage_.open_index(schema=FILE_INDEXING_SCHEMA)
      logging.debug(f'open existing index in {self.index_dir_}')
    else:
      self.index_ = self.storage_.create_index(FILE_INDEXING_SCHEMA)
      logging.debug(f'create new index in {self.index_dir_}')

    self.writer_ = None

  def add_document(self, path, full_indexing=False):
    if self.writer_ is None:
      return

    content = ''
    if not is_binary(path.resolve().as_posix()):
      content = path.read_text(encoding='utf-8', errors='ignore')

    self.writer_.update_document(
        path=path.resolve().as_posix(),
        create_time=datetime.datetime.fromtimestamp(path.stat().st_ctime),
        modified_time=datetime.datetime.fromtimestamp(path.stat().st_mtime),
        content=content)

  def begin_index(self):
    if self.writer_ is not None:
      return

    self.writer_ = self.index_.writer(proc=4, limitmb=512, multisegment=True)

  def end_index(self):
    if self.writer_ is None:
      return

    self.writer_.commit(optimize=True)
    self.writer_ = None

  def query(self, path, content):
    if path is None and content is None:
      raise ValueError('must provide either path or content to search')

    fields = []

    if path is not None:
      fields.append('path')

    if content is not None:
      fields.append('content')

    qp = MultifieldParser(fields, schema=self.index_.schema)

    query_str = "NOT tag:'indexed_path'"

    if content is not None:
      query_str += f' content:\'{content}\''

    if path is not None:
      query_str += f' path:*{path}*'

    query = qp.parse(query_str)

    logging.debug(f'query str:{query_str}, query_parsed:{query}')

    return QueryResult(self.index_.searcher(), query)

  def delete_path(self, path):
    if path is None:
      raise ValueError('must provide path to delete')

    qp = MultifieldParser(['path'], schema=self.index_.schema)

    query_str = f'path:*{path}*'

    query = qp.parse(query_str)

    logging.debug(f'query str:{query_str}, query_parsed:{query}')

    with self.index_.searcher() as sr:
      self.writer_.delete_by_query(query, sr)

  def touch_path(self, path, modified_time):
    if path is None:
      indexed_path = self.list_indexed_path()

      path = [x[0] for x in indexed_path]
    else:
      path = [path]

    for p in path:
      pp = pathlib.Path(p)

      if not pp.exists():
        continue

      logging.debug(f'update indexed path:{pp.resolve().as_posix()} modified time')
      self.writer_.update_document(
        path=pp.resolve().as_posix(),
        create_time=datetime.datetime.fromtimestamp(pp.stat().st_ctime),
        modified_time=modified_time,
        content='',
        tag='indexed_path')

  def list_indexed_path(self):
    try:
      with self.index_.searcher() as sr:
        return [(fields['path'], fields['modified_time']) for fields in sr.documents(tag='indexed_path')]
    except:
      return []

  def clear_non_exist(self, path):
    v = path.as_posix()

    if v.find(':') >= 0:
      v = v[v.find(':') + 1:]

    results = self.query(v, None)

    for hit in results.query():
      p = pathlib.Path(hit['path'])

      if not p.as_posix().startswith(path.as_posix()):
        continue

      if not p.exists():
        self.writer_.delete_by_term('path', p.as_posix())


  def get_index_modified_time(self, path):
    try:
      with self.index_.searcher() as sr:
        for fields in sr.documents(tag='indexed_path'):
          if fields['path'] == path.as_posix():
            return fields['modified_time']
    except:
      return None
