from . import create_app
from .service import start_indexer

import argparse
import logging
import pathlib


def parse_arguments():
  parser = argparse.ArgumentParser()

  parser.add_argument("-d",
                      "--debug",
                      help="print debug information",
                      action="count",
                      default=0)
  parser.add_argument("-p", "--port", help="the server port", default=8192)
  parser.add_argument("-l",
                      "--location",
                      help="location which index file stores in",
                      type=pathlib.Path,
                      required=False,
                      default=None)

  return parser.parse_args()


def main():
  args = parse_arguments()

  if args.debug > 0:
    logging.getLogger('').setLevel(logging.DEBUG)

  if args.location is not None:
    logging.debug(f'index store location:{args.location.resolve().as_posix()}')

  start_indexer(args.location)

  create_app().run(debug=(args.debug > 0), port=args.port)


if __name__ == '__main__':
  main()
