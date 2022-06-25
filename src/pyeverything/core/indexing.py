import logging
import datetime
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

    self.data_queue_.put_nowait((path, full_indexing, False, None, False))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def remove(self, path):
    self.data_queue_.put_nowait((path, False, True, None, False))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def query(self, path, content, ignore_case=True, raw_pattern=False):
    return self.indexer_impl_.query(path, content, ignore_case, raw_pattern)

  def touch(self, path, modify_time):
    self.data_queue_.put_nowait((path, False, False, modify_time, False))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def update(self, path):
    if isinstance(path, str):
      path = pathlib.Path(path)

    self.data_queue_.put_nowait((path, False, False, None, True))

    if not self.use_service_:
      self.data_queue_.put_nowait(None)
      Indexer.indexing_func(self)

  def list_indexed_path(self):
    return self.indexer_impl_.list_indexed_path()

  def refresh_cache(self):
    return self.indexer_impl_.refresh_cache()

  def __remove_index_func(self, path):
    logging.debug(f'remove index for: {path}')

    self.indexer_impl_.begin_index()
    try:
      self.indexer_impl_.delete_path(path)
    except:
      logging.exception(f'error removing index:{path}')
    finally:
      self.indexer_impl_.end_index()
      logging.debug(f'done remove index for: {path}')

  def __touch_index_func(self, path, modified_time):
    logging.debug(f'touch index for: {path}')

    self.indexer_impl_.begin_index()
    try:
      self.indexer_impl_.touch_path(path, modified_time)
    except:
      logging.exception(f'error touch index:{path}')
    finally:
      self.indexer_impl_.end_index()
      logging.debug(f'done touch index for: {path}')

  @staticmethod
  def indexing_func(indexer):
    while True:
      if indexer.shutdown_.value == 1:
        logging.debug('1.quit indexing function process')
        break

      task = indexer.data_queue_.get()

      if task is None or indexer.shutdown_.value == 1:
        logging.debug('2.quit indexing function process')
        break

      path, full_indexing, remove, touch, update = task

      if remove:
        indexer.__remove_index_func(path)
        continue

      if touch is not None:
        indexer.__touch_index_func(path, touch)
        continue

      index_updated = False

      try:
        path = path.resolve()

        modified_time = None
        exist_files = {}

        logging.info(f'indexing path:{path.as_posix()}, update:{update}')

        if update:
          indexer.indexer_impl_.begin_index()
          exist_files, delete_file_count = indexer.indexer_impl_.clear_non_exist(path)
          modified_time = indexer.indexer_impl_.get_index_modified_time(path)
          index_updated = index_updated or (delete_file_count > 0)

        if path.is_dir() and path.exists():
          entries = walk_directory(path)
        elif path.is_file() and path.exists():
          entries = [path]
        else:
          logging.warning(
              f'get a index request with invalid path:{path.as_posix()}')
          continue

        logging.debug(f'begin index for: {path.as_posix()}')

        if not update:
          indexer.indexer_impl_.begin_index()

        for entry in entries:
          if indexer.shutdown_.value == 1:
            logging.debug('3.quit indexing function process')
            break

          e_mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime)
          if modified_time is not None and e_mtime <= modified_time:
            skip_file = True

            try:
              s_mtime = exist_files[entry.as_posix()]

              if s_mtime < e_mtime:
                skip_file = False
            except (KeyError):
              skip_file = False

            if skip_file:
              logging.debug(
                  f'skip {entry.as_posix()} since not modified, {e_mtime} < {modified_time}'
              )
              continue

          logging.debug(f'indexing document:{entry.as_posix()}')
          indexer.indexer_impl_.add_document(entry, full_indexing)
          index_updated = True

        indexer.indexer_impl_.touch_path(path.as_posix(),
                                         datetime.datetime.now())
      except:
        logging.exception(f'failed index {task}')
      finally:
        indexer.indexer_impl_.end_index(index_updated)
        logging.debug(
            f'done index for: {path.as_posix() if not isinstance(path, str) else path}'
        )


if __name__ == '__main__':
  ix = Indexer()

  r = ix.query('core', 'editor')

  for item in r.query():
    print(item['path'])
