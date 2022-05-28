import pathlib
import logging

from whoosh.query import Regex

from . import matching
from .regexp import regexp_match_info


class QueryResult(object):

  def __init__(self, searcher, query, origin_path, use_raw_match):
    super().__init__()

    self.searcher_ = searcher
    self.query_ = query
    self.origin_path_ = origin_path
    self.use_raw_match_ = use_raw_match

  def close(self):
    self.searcher_.close()

  def query(self, limit=None):
    doc_filter = self.__get_doc_filter()

    if doc_filter:
      logging.debug(f'filter path with:{doc_filter}')
      return self.searcher_.search(self.query_, limit=limit, filter=doc_filter)
    else:
      return self.searcher_.search(self.query_, limit=limit)

  def query_paged(self, page, page_len=10):
    doc_filter = self.__get_doc_filter()

    if doc_filter:
      return self.searcher_.search_page(self.query_,
                                        page,
                                        page_len=page_len,
                                        filter=doc_filter)
    else:
      return self.searcher_.search_page(self.query_, page, page_len=page_len)

  def __get_doc_filter(self):
    check = self.origin_path_ is not None and self.origin_path_.find(':') >= 0

    if check:
      return Regex(
          'path', f'^{pathlib.Path(self.origin_path_).resolve().as_posix()}.*')

    return None

  def get_matching_info(self, hit, content):
    if self.use_raw_match_:
      return matching.get_matching_info(hit)
    else:
      return regexp_match_info(hit, content)
