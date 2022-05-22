from flask import Flask

from .service import start_indexer
from .service import register_blueprints as service_register_blueprints


def create_app():
  app = Flask(__name__)

  start_indexer()

  service_register_blueprints(app)

  return app
