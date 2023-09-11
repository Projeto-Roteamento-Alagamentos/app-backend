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

    point1 = data['features'][0]['geometry']['coordinates']
    point2 = data['features'][1]['geometry']['coordinates']

    linestring =  {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[point1[1], point1[0]], [point2[1], point2[0]]]
        }
    }
    ]
  } 

    return jsonify(linestring), 200