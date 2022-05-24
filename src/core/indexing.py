import logging

import sys
import pathlib
import multiprocessing as mp
from multiprocessing import Process, Queue, Value
from appdirs import AppDirs

from .file_system_helper import walk_directory
from .indexer import get_indexer_impl

if sys.platform != 'win32':
  try:
    mp.set_start_method('forkserver')
  except:
    pass


class Indexer(object):

  def __init__(self, data_path=None, use_service=True):
    super().__init__()

    self.appdirs_ = AppDirs('pyeverything', 'angsto-tech')
    self.data_path_ = data_path
    self.data_queue_ = None
    self.indexing_process_ = None
    self.shutdown_ = Value('d', 0)
    self.use_service_ = use_service

    self.__initialize()

  def __initialize(self):
    if isinstance(self.data_path_, str):
      self.data_path_ = pathlib.Path(self.data_path_)
    elif self.data_path_ is None:
      self.data_path_ = self.__get_default_datapath()

    self.data_path_ = self.data_path_.expanduser().resolve()

    self.data_path_.mkdir(parents=True, exist_ok=True)
    logging.debug(
        f'indexing data stored in {self.data_path_.resolve().as_posix()}')

    self.indexer_impl_ = get_indexer_impl(self.data_path_)

    if not self.use_service_:
      self.data_queue_ = Queue()

  def __get_default_datapath(self):
    return pathlib.Path(self.appdirs_.user_config_dir) / 'cache'

  def start(self):
    if self.indexing_process_ is not None or not self.use_service_:
      return

    self.data_queue_ = Queue()
    self.shutdown_.value = 0

    self.indexing_process_ = Process(target=Indexer.indexing_func,
                                     args=(self, ))
    self.indexing_process_.start()

  def stop(self):
    if self.indexing_process_ is None or not self.use_service_:
      return

    self.shutdown_.value = 1
    self.data_queue_.put_nowait(None)
    self.indexing_process_.join()

  def index(self, path, full_indexing=False):
    if isinstance(path, str):
      path = pathlib.Path(path)

    self.data_queue_.put_nowait((path, full_indexing, False))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def remove(self, path):
    self.data_queue_.put_nowait((path, False, True))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def query(self, path, content):
    return self.indexer_impl_.query(path, content)

  @staticmethod
  def indexing_func(indexer):
    while True:
      if indexer.shutdown_.value == 1:
        logging.info('1.quit indexing function process')
        break

      task = indexer.data_queue_.get()

      if task is None or indexer.shutdown_.value == 1:
        logging.info('2.quit indexing function process')
        break

      try:
        path, full_indexing, remove = task

        if remove:
          logging.debug(f'remove index for: {path}')

          indexer.indexer_impl_.begin_index()
          try:
            indexer.indexer_impl_.delete_path(path)
          finally:
            indexer.indexer_impl_.end_index()
            logging.debug(f'done remove index for: {path}')

          continue

        path = path.resolve()

        if path.is_dir() and path.exists():
          entries = walk_directory(path)
        elif path.is_file() and path.exists():
          entries = [path]
        else:
          logging.warning(
              f'get a index request with invalid path:{path.as_posix()}'
          )
          continue

        logging.debug(f'begin index for: {path.as_posix()}')

        indexer.indexer_impl_.begin_index()

        for entry in entries:
          if indexer.shutdown_.value == 1:
            logging.info('3.quit indexing function process')
            break

          logging.debug(f'indexing document:{entry.as_posix()}')
          indexer.indexer_impl_.add_document(entry, full_indexing)
      except:
        logging.exception(f'failed index {task}')
      finally:
        indexer.indexer_impl_.end_index()
        logging.debug(f'done index for: {path.as_posix() if not isinstance(path, str) else path}')

if __name__ == '__main__':
  ix = Indexer()

  r = ix.query('core', 'editor')

  for item in r.query():
    print(item['path'])
