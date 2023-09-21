from flask import Blueprint, request, jsonify
import osmnx as ox
import networkx as nx
import geopandas as gpd
import json

modelo_blueprint = Blueprint('modelo_previsao', __name__)

graph_filename = "./app/api/v1/modelo_previsao/graph.graphml"

@modelo_blueprint.route('/geojson', methods=['POST'])
def handle_geojson():

    data = request.data

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    data = json.loads(data)

    graph = ox.load_graphml(graph_filename)
    
    
    data = request.get_json()
    point1 = data['features'][0]['geometry']['coordinates']
    point2 = data['features'][1]['geometry']['coordinates']
    
    
    node_start = ox.distance.nearest_nodes(graph, X=point1[1], Y=point1[0])
    node_end = ox.distance.nearest_nodes(graph, X=point2[1], Y=point2[0])
    
    route = nx.astar_path(graph, node_start, node_end, weight='length')

    coordenadas = [(graph.nodes[n]['x'], graph.nodes[n]['y']) for n in route]

    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coordenadas
        },
        "properties": {}
    }

    return jsonify(geojson), 200