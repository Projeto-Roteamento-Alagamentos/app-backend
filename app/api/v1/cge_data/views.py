from flask import Blueprint, jsonify
import json
import os

def load_specific_json(year, month, day, root_directory):
    
    file_name = f"{year}_{month:02}_{day:02}.json"
    file_path = os.path.join(root_directory, str(year), f"{month:02}", file_name)
    print(file_path)

    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    else:
        print(f"O arquivo {file_name} não foi encontrado.")
        return None

cge_blueprint = Blueprint('recurso1', __name__)

@cge_blueprint.route('/recurso1', methods=['GET'])
def get_all_ocurrencies():
    directory =  os.getcwd() + "/app/api/v1/cge_data/cge_json_files"
    json_file = load_specific_json(2022, 1, 2, directory)
    return jsonify(json_file)