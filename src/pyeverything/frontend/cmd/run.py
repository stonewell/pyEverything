import argparse
import logging
import pathlib
import datetime

from pyeverything.core.indexing import Indexer


def parse_arguments():
  parser = argparse.ArgumentParser()

  parser.add_argument("-d",
                      "--debug",
                      help="print debug information",
                      action="count",
                      default=0)
  parser.add_argument("-l",
                      "--location",
                      help="location which index file stores in",
                      type=pathlib.Path,
                      required=False,
                      default=None)

  sub_parsers = parser.add_subparsers(dest='op')

  index_parser = sub_parsers.add_parser('index', help='index operations')

  index_parser.add_argument("-r",
                            "--remove",
                            help="delete index with path",
                            action="store_true",
                            default=False)
  index_parser.add_argument(
      "-t",
      "--touch",
      help="mark index last update time with given arg or current time",
      nargs='?',
      default='',
      metavar='<modified time>')
  index_parser.add_argument(
      "-u",
      "--update",
      help=
      "update indexed files, remove deleted file, add new and update modified files",
      action="store_true",
      default=False)
  index_parser.add_argument("-f",
                            "--file",
                            help="file contains path to be indexed",
                            required=False,
                            type=argparse.FileType('r'),
                            default=None)
  index_parser.add_argument('args',
                            help="path to be indexed",
                            nargs='*',
                            metavar='<path>')

  query_parser = sub_parsers.add_parser('query', help='query operations')
  query_parser.add_argument('-p',
                            '--path',
                            type=str,
                            required=False,
                            default=None)
  query_parser.add_argument('-c',
                            '--content',
                            type=str,
                            required=False,
                            default=None)

  list_parser = sub_parsers.add_parser('list', help='list indexed path')

  return parser.parse_args()


def main():
  args = parse_arguments()

  if args.debug > 0:
    logging.getLogger('').setLevel(logging.DEBUG)

  logging.debug(args.op)

  if args.location is not None:
    logging.debug(f'index store location:{args.location.resolve().as_posix()}')

  indexer = Indexer(args.location, False)

  if args.op == 'index':
    do_index(indexer, args)
  elif args.op == 'query':
    do_query(indexer, args)
  elif args.op == 'list':
    for p, m in indexer.list_indexed_path():
      print(f'path:{p}, modified time:{m}')


def do_index(indexer, args):
  touch_time = get_touch_time(args)

  logging.debug(
      f'f={args.file} p={args.args} t={touch_time}, r={args.remove}, u={args.update}'
  )
  if args.file is not None:
    for line in args.file:
      if args.remove:
        indexer.remove(line)
      elif touch_time is not None:
        indexer.touch(line, touch_time)
      elif args.update:
        indexer.update(line)
      else:
        indexer.index(line)

  for path in args.args:
    if args.remove:
      indexer.remove(path)
    elif touch_time is not None:
      indexer.touch(path, touch_time)
    elif args.update:
      indexer.update(path)
    else:
      indexer.index(path)

  if (len(args.args) == 0 and args.file is None):
    if touch_time is not None:
      indexer.touch(None, touch_time)
    elif args.update:
      for p, m in indexer.list_indexed_path():
        indexer.update(p)


def get_touch_time(args):
  if args.touch == '':
    return None

  if args.touch is None:
    return datetime.datetime.now()

  try:
    return datetime.datetime.fromisoformat(args.touch)
  except:
    logging.warning(f'invalid datetime string:{args.touch}')
    return datetime.datetime.now()

def set_matched_filter(tokens, termset):
  for t in tokens:
    t.matched = t.text in termset
    yield t

def highlight_hit(hitobj, fieldname, text=None, top=3, minscore=1):
  results = hitobj.results
  schema = results.searcher.schema
  field = schema[fieldname]
  to_bytes = field.to_bytes
  from_bytes = field.from_bytes

  if text is None:
    if fieldname not in hitobj:
      raise KeyError("Field %r is not stored." % fieldname)
    text = hitobj[fieldname]

  # Get the terms searched for/matched in this field
  if results.has_matched_terms():
    bterms = (term for term in results.matched_terms()
                      if term[0] == fieldname)
  else:
    bterms = results.query_terms(expand=True, fieldname=fieldname)

  # Convert bytes to unicode
  words = frozenset(from_bytes(term[1]) for term in bterms)

  # Retokenize the text
  analyzer = results.searcher.schema[fieldname].analyzer
  tokens = analyzer(text, positions=True, chars=True, mode="index",
                              removestops=False)
  # Set Token.matched attribute for tokens that match a query term
  tokens = set_matched_filter(tokens, words)
  tokens = _merge_matched_tokens(tokens)

  return tokens

def _merge_matched_tokens(tokens):
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
        token.text += t.text[token.endchar-t.endchar:]
        token.endchar = t.endchar
    else:
      yield token
      token = None
      # t was not merged, also has to be yielded
      yield t

  if token is not None:
    yield token

def do_query(indexer, args):
  r = indexer.query(args.path, args.content)

  for hit in r.query():
    print(hit['path'])

    text = pathlib.Path(hit['path']).read_text()

    for t in highlight_hit(hit, 'content', text=text):
      print(t)

    if args.content is not None:
      print(hit.highlights('content', text=text))


if __name__ == '__main__':
  main()
