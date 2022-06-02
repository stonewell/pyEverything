import logging
import datetime
import pathlib
import re
from binaryornot.check import is_binary

from whoosh.fields import Schema, ID, DATETIME, NGRAM, KEYWORD
from whoosh import index
from whoosh.filedb.filestore import FileStorage
from whoosh.qparser import MultifieldParser

from .. import IndexerImpl
from .query_result import QueryResult
from .regexp import regexp_to_query

FILE_INDEXING_SCHEMA = Schema(path=ID(stored=True, unique=True),
                              content=NGRAM(minsize=1, maxsize=3),
                              path_content=NGRAM(minsize=1, maxsize=3),
                              tag=KEYWORD,
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
        path_content=path.resolve().as_posix(),
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

  def query(self, path, content, ignore_case=True, raw_pattern=False):
    if path is None and content is None:
      raise ValueError('must provide either path or content to search')

    fields = []

    origin_path = path
    use_raw_match = raw_pattern

    query_str = "NOT tag:'indexed_path'"

    if path is not None:
      fields.append('path_content')

      if not use_raw_match:
        path_query_str = regexp_to_query(
            f'(?m){"(?i)" if ignore_case else ""}{path}', 1)
      else:
        path_query_str = path

      if len(path_query_str) == 0:
        logging.warning(f'unable to parse path query:{path} as regex')
        path_query_str = path

      if path != '.*':
        query_str += f' path_content:{path_query_str}'

    if content is not None:
      fields.append('content')

      if not use_raw_match:
        content_query_str = regexp_to_query(
            f'(?m){"(?i)" if ignore_case else ""}{content}', 1)
      else:
        content_query_str = content

      if len(content_query_str) == 0:
        logging.warning(f'unable to parse content query:{content} as regex')
        content_query_str = content
      query_str += f' content:{content_query_str}'

    qp = MultifieldParser(fields, schema=self.index_.schema)

    query = qp.parse(query_str)

    logging.debug(f'query str:{query_str}, query_parsed:{query}')

    return QueryResult(self.index_.searcher(), query, origin_path, ignore_case,
                       use_raw_match)

  def delete_path(self, path):
    if path is None:
      raise ValueError('must provide path to delete')

    results = self.query(path, None)

    pattern = re.compile(path)

    for hit in results.query():
      p = pathlib.Path(hit['path'])

      if pattern.search(p.as_posix()) is None:
        continue

      self.writer_.delete_by_term('path', p.as_posix())

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

      logging.debug(
          f'update indexed path:{pp.resolve().as_posix()} modified time')
      self.writer_.update_document(path=pp.resolve().as_posix(),
                                   create_time=datetime.datetime.fromtimestamp(
                                       pp.stat().st_ctime),
                                   modified_time=modified_time,
                                   content='',
                                   tag='indexed_path')

  def list_indexed_path(self):
    try:
      with self.index_.searcher() as sr:
        return [(fields['path'], fields['modified_time'])
                for fields in sr.documents(tag='indexed_path')]
    except:
      logging.exception('failed')
      return []

  def clear_non_exist(self, path):
    v = path.as_posix()

    results = self.query(v, None)

    exist_files = {}
    for hit in results.query():
      p = pathlib.Path(hit['path'])

      if not p.as_posix().startswith(v):
        continue

      if not p.exists():
        self.writer_.delete_by_term('path', p.as_posix())
      else:
        exist_files[p.as_posix()] = hit['modified_time']

    return exist_files

  def get_index_modified_time(self, path):
    try:
      with self.index_.searcher() as sr:
        for fields in sr.documents(tag='indexed_path'):
          if fields['path'] == path.as_posix():
            return fields['modified_time']
    except:
      return None
