from . import create_app
from .service import start_indexer

def main():
  start_indexer()

  create_app().run(debug=True, port=8192)

if __name__ == '__main__':
  main()
