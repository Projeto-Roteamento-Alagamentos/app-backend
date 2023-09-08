from flask import Blueprint, jsonify, request 
import json

modelo_blueprint = Blueprint('modelo_previsao', __name__)

@modelo_blueprint.route('/geojson', methods=['POST'])
def handle_geojson():

    data = request.data

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    data = json.loads(data)

    if 'type' not in data or data['type'] != 'FeatureCollection':
        return jsonify({"error": "Invalid GeoJSON"}), 400

    if 'properties' not in data or 'horario_saida' not in data['properties']:
        return jsonify({"error": "Missing horario_saida in properties"}), 400

    return jsonify({"message": "GeoJSON received successfully"}), 200