import pathlib
import logging

from whoosh.query import Regex

from . import matching
from .regexp import regexp_match_info


class QueryResult(object):

  def __init__(self, searcher, query, origin_path, ignore_case, use_raw_match):
    super().__init__()

    self.searcher_ = searcher
    self.query_ = query
    self.origin_path_ = origin_path
    self.use_raw_match_ = use_raw_match
    self.ignore_case_ = ignore_case

  def close(self):
    self.searcher_.close()

  def query(self, limit=None):
    return self.searcher_.search(self.query_, limit=limit)

  def query_paged(self, page, page_len=10):
    return self.searcher_.search_page(self.query_, page, page_len=page_len)

  def get_matching_info(self, hit, content):
    if self.use_raw_match_:
      return matching.get_matching_info(hit)
    else:
      return regexp_match_info(hit, content, self.ignore_case_)
