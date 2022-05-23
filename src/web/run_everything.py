from . import create_app
from .service import start_indexer

if __name__ == '__main__':
  start_indexer()

  create_app().run(debug=True, port=8192)
