import argparse
import logging
import pathlib

from core.indexing import Indexer


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
  index_parser.add_argument("-f",
                            "--file",
                            help="file contains path to be indexed",
                            required=False,
                            type=argparse.FileType('r'),
                            default=None)
  index_parser.add_argument('args',
                            help="path to be indexed",
                            nargs='+',
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

  return parser.parse_args()


def main():
  args = parse_arguments()

  if args.debug > 0:
    logging.getLogger('').setLevel(logging.DEBUG)

  logging.debug(args.op)
  logging.debug(f'index store location:{args.location.resolve().as_posix()}')

  indexer = Indexer(args.location, False)

  if args.op == 'index':
    do_index(indexer, args)
  elif args.op == 'query':
    do_query(indexer, args)


def do_index(indexer, args):
  if args.file is not None:
    for line in args.file:
      indexer.index(line)

  for path in args.args:
    indexer.index(path)


def do_query(indexer, args):
  r = indexer.query(args.path, args.content)

  for hit in r.query():
    print(hit['path'])


if __name__ == '__main__':
  main()
