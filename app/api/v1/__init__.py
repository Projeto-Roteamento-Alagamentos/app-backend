from flask import Blueprint

api_v1_blueprint = Blueprint('api_v1', __name__)

from .cge_data import cge_blueprint

api_v1_blueprint.register_blueprint(cge_blueprint, url_prefix='/cge_data')

