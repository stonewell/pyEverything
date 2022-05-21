class QueryResult(object):

  def __init__(self, searcher, query):
    super().__init__()

    self.searcher_ = searcher
    self.query_ = query

  def close(self):
    self.searcher_.close()

  def query(self, limit=None):
    return self.searcher_.search(self.query_, limit=limit)

  def query_paged(self, page, page_len=10):
    return self.searcher_.search_page(self.query_, page, page_len=page_len)
