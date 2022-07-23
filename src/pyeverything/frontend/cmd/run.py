from functools import reduce
import sys
import argparse
import logging
import pathlib
import datetime
import re
from termcolor import colored
import subprocess

from pyeverything.core.indexing import Indexer


def parse_arguments(cmd_line_args):
  parser = argparse.ArgumentParser(prog='pyeverything')

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
  query_parser.add_argument('--path_only', action='store_true', default=False)
  query_parser.add_argument('-i',
                            '--ignore_case',
                            action='store_true',
                            default=False)
  query_parser.add_argument('--raw_pattern',
                            action='store_true',
                            default=False)
  query_parser.add_argument('--no_group', action='store_true', default=False)
  query_parser.add_argument('--limit', type=int, default=None)
  query_parser.add_argument('--page', type=int, default=None)
  query_parser.add_argument('--page_size', type=int, default=20)

  list_parser = sub_parsers.add_parser('list', help='list indexed path')

  helm_ag_parser = sub_parsers.add_parser('helm-ag',
                                          help='compatible with helm-ag')
  helm_ag_parser.add_argument('--ignore',
                              type=str,
                              action='append',
                              required=False,
                              default=None)
  helm_ag_parser.add_argument('--path-to-ignore',
                              type=str,
                              required=False,
                              default=None)
  helm_ag_parser.add_argument('pattern_and_path', type=str, nargs='+')

  return parser.parse_args(cmd_line_args)


def find_index_location(p):
  everything_path = find_pyeverything(p)

  if everything_path is not None:
    loc = everything_path.read_text(encoding='utf-8').strip('\n').strip('\r')
    if len(loc) > 0:
      return loc

  return None


def main():
  run_with_args(sys.argv[1:], False)


__g_Indexeres = {}
__g_DefaultIndexer = None


def run_with_args(cmd_line_args, cache=True, output=sys.stdout):
  global __g_DefaultIndexer
  global __g_Indexeres

  args = parse_arguments(cmd_line_args)

  if args.debug > 0:
    logging.getLogger('').setLevel(logging.DEBUG)
  else:
    logging.getLogger('').setLevel(logging.INFO)

  logging.getLogger('binaryornot').setLevel(logging.WARNING)
  logging.getLogger('chardet').setLevel(logging.WARNING)

  logging.debug(f'operation:{args.op}')

  if args.op == 'helm-ag':
    if len(args.pattern_and_path) > 2:
      logging.error(' '.join(sys.argv))
      parse_arguments(['helm-ag', '-h'])
      return

  if args.location is not None:
    logging.debug(f'index store location:{args.location.resolve().as_posix()}')
  elif args.op == 'helm-ag':
    args.location = find_index_location(pathlib.Path('.').cwd())

  if not cache:
    indexer = Indexer(args.location, False)
  elif args.location is None:
    if __g_DefaultIndexer is None:
      __g_DefaultIndexer = Indexer(args.location, False)

    indexer = __g_DefaultIndexer
  else:
    if args.location not in __g_Indexeres:
      __g_Indexeres[args.location] = Indexer(args.location, False)

    indexer = __g_Indexeres[args.location]

  indexer.refresh_cache()

  if args.op == 'index':
    do_index(indexer, args, output)
  elif args.op == 'query':
    do_query(indexer, args, output)
  elif args.op == 'list':
    for p, m in indexer.list_indexed_path():
      print(f'path:{p}, modified time:{m}', file=output)
  elif args.op == 'helm-ag':
    if not has_pyeverything_index(indexer, pathlib.Path('.').cwd()):
      call_ag(args)
      return

    args.path = pathlib.Path('.').cwd().as_posix()
    args.content = args.pattern_and_path[0]
    args.no_color = True
    args.ackmate = False
    args.path_only = False
    args.ignore_case = False
    args.raw_pattern = False
    args.limit = None
    args.page = None
    args.page_size = 20
    args.no_group = True

    do_query(indexer, args, output)
  else:
    parse_arguments(['-h'])


def do_index(indexer, args, output=sys.stdout):
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


def get_path_matcher(args):
  if args.path is None:
    return None

  path = args.path

  if args.raw_pattern:
    path = re.escape(path)

  if args.ignore_case:
    path = f'(?i){path}'

  path = f'(?m){path}'

  return re.compile(path)


def do_query(indexer, args, output=sys.stdout):
  # do not use args.path for index query if there is content query
  # will check path anyway later
  r = indexer.query(args.path if args.content is None else None, args.content,
                    args.ignore_case, args.raw_pattern)

  if args.ackmate:
    args.no_color = True

  path_matcher = get_path_matcher(args)

  if args.page is not None:
    results = r.query_paged(args.page, args.page_size)
  else:
    results = r.query(args.limit)

  for hit in results:
    path = hit['path']

    def output_path():
      if args.ackmate:
        print(f':{path}', file=output)
      elif args.no_color:
        print(path, file=output)
      else:
        print(colored(path, 'green', attrs=['bold']), file=output)

    p_path = pathlib.Path(path)

    if path_matcher is not None and path_matcher.search(path) is None:
      logging.debug(f'pat:{path} does not match pattern:{args.path}, skipping')
      continue

    if not p_path.exists():
      logging.debug(f'path:{path} does not exist, skipping')
      continue

    if args.path_only or args.content is None:
      output_path()
    else:
      matching_info_text = None
      line_text = None
      line_num = 0

      path_output_done = False
      for m in r.get_matching_info(hit, args.content):
        if not path_output_done and (not args.no_group or args.ackmate):
          output_path()
          path_output_done = True

        l, start, length, text = m

        if args.ackmate:
          if line_num != l + 1:
            if matching_info_text is not None:
              print(f'{matching_info_text}:{line_text}', file=output)

            matching_info_text = f'{l + 1};{start} {length}'
            line_text = text
            line_num = l + 1
          else:
            matching_info_text += f',{start} {length}'
        elif args.no_color:
          print(f'{path}:{l+1}: {text}', file=output)
        else:
          path_text = colored(path, 'green', attrs=['bold'])
          line_num = colored(l + 1, "yellow", attrs=["bold"])
          line_text = [
              text[:start],
              colored(text[start:start + length], "grey",
                      on_color="on_yellow"), text[start + length:]
          ]
          print(f'{path_text}:{line_num}: {"".join(line_text)}', file=output)

      if matching_info_text is not None:
        print(f'{matching_info_text}:{line_text}', file=output)

      if path_output_done and (not args.no_group or args.ackmate):
        print('', file=output)
      else:
        logging.debug(f'path:{path} no matching, skipping')


def find_pyeverything(path: pathlib.Path) -> pathlib.Path:
  found = list(path.glob('.pyeverything'))

  if len(found) > 0:
    return path.resolve() / '.pyeverything'

  if path.parent == path:
    return None

  return find_pyeverything(path.parent)


def has_pyeverything_index(indexer, path):
  for p, m in indexer.list_indexed_path():
    if path.resolve().as_posix().startswith(p):
      return True

  return False


def merge_list(x, y):
  x.extend(y)

  return x


def call_ag(args):
  ag_cmds = ['ag', '--no-color', '--no-group']

  if args.ignore:
    ag_cmds.extend(
        reduce(merge_list, map(lambda x: ['--ignore', x], args.ignore)))

  if args.path_to_ignore:
    ag_cmds.extend(['--path-to-ignore', args.path_to_ignore])

  ag_cmds.extend(args.pattern_and_path)

  subprocess.run(ag_cmds)


if __name__ == '__main__':
  main()
