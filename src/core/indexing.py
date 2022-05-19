import multiprocessing as mp
from mp import Process, Queue

from . import FILE_INDEXING_SCHEMA
from .file_system_helper import walk_directory

mp.set_start_method('forkservr')


class Indexer(object):

    def __init__(self, data_path):
        super().__init__()

        self.data_path_ = data_path
        self.data_queue_ = None
        self.indexing_process_ = None

    def start(self):
        self.data_queue_ = Queue()

    def stop(self):
        pass

    def index_directory(path, full_indexing=False):
        pass

    def index_file(path, full_indexing=False):
        pass


if __name__ == '__main__':
    ix = Indexer('')
    ix.start()
