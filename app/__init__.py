from flask import Flask
from flask import Blueprint

from .api.v1 import api_v1_blueprint

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_v1_blueprint, url_prefix='/api/v1')
    return app