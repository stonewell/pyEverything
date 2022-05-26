import argparse
import logging
import pathlib
import datetime
from termcolor import colored

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
  query_parser.add_argument('--no_color', action='store_true', default=False)
  query_parser.add_argument('--ackmate', action='store_true', default=False)

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


def do_query(indexer, args):
  r = indexer.query(args.path, args.content)

  if args.ackmate:
    args.no_color = True

  for hit in r.query():
    path = hit['path']

    if args.ackmate:
      print(f':{path}')
    elif args.no_color:
      print(path)
    else:
      print(colored(path, 'green', attrs=['bold']))

    if args.content is not None and pathlib.Path(path).exists():
      text = pathlib.Path(path).read_text()

      matching_info_text = None
      line_text = None
      line_num = 0

      for m in r.get_matching_info(hit):
        l, start, length, text = m

        if args.ackmate:
          if line_num != l + 1:
            if matching_info_text is not None:
              print(f'{matching_info_text}:{line_text}')

            matching_info_text = f'{l + 1};{start} {length}'
            line_text = text
            line_num = l + 1
          else:
            matching_info_text += f',{start} {length}'
        elif args.no_color:
          print(f'{l+1}: {text}')
        else:
          line_num = colored(l + 1, "yellow", attrs=["bold"])
          line_text = [
              text[:start],
              colored(text[start:start + length], "grey",
                      on_color="on_yellow"), text[start + length:]
          ]
          print(f'{line_num}: {"".join(line_text)}')

      if matching_info_text is not None:
        print(f'{matching_info_text}:{line_text}')
      print('')


if __name__ == '__main__':
  main()
