import pathlib
from io import StringIO


def __set_matched_filter(tokens, termset):
  for t in tokens:
    t.matched = t.text in termset

    if t.matched:
      yield t


def __highlight_hit(hitobj, fieldname, text):
  results = hitobj.results
  schema = results.searcher.schema
  field = schema[fieldname]
  from_bytes = field.from_bytes

  # Get the terms searched for/matched in this field
  if results.has_matched_terms():
    bterms = (term for term in results.matched_terms() if term[0] == fieldname)
  else:
    bterms = results.query_terms(expand=True, fieldname=fieldname)

  # Convert bytes to unicode
  words = frozenset(from_bytes(term[1]) for term in bterms)

  # Retokenize the text
  analyzer = results.searcher.schema[fieldname].analyzer
  tokens = analyzer(text,
                    positions=True,
                    chars=True,
                    mode="index",
                    removestops=False)
  # Set Token.matched attribute for tokens that match a query term
  tokens = __set_matched_filter(tokens, words)
  tokens = __merge_matched_tokens(tokens)

  return tokens


def __merge_matched_tokens(tokens):
  # Merges consecutive matched tokens together, so they are highlighted
  # as one

  token = None

  for t in tokens:
    if not t.matched:
      if token is not None:
        yield token
        token = None
      yield t
      continue

    if token is None:
      token = t.copy()
    elif t.startchar <= token.endchar:
      if t.endchar > token.endchar:
        token.text += t.text[token.endchar - t.endchar:]
        token.endchar = t.endchar
    else:
      yield token
      token = t.copy()

  if token is not None:
    yield token


def get_matching_info(hit):
  text = pathlib.Path(hit['path']).read_text()

  matched_tokens = []
  for t in __highlight_hit(hit, 'content', text=text):
    if t.matched:
      matched_tokens.append(t)

  if len(matched_tokens) == 0:
    return

  line_start = 0
  line_count = 0

  token_iter = iter(matched_tokens)
  t = next(token_iter)

  for line in StringIO(text):
    line_end = line_start + len(line)

    while t.startchar >= line_start and t.endchar < line_end:
      yield (line_count, t.startchar - line_start, t.endchar - t.startchar,
             line.replace('\n', '').replace('\r', ''))

      try:
        t = next(token_iter)
      except (StopIteration):
        return

    line_count += 1
    line_start = line_end
