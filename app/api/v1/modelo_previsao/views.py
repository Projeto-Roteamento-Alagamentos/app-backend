from flask import Blueprint, request, jsonify
import osmnx as ox
import networkx as nx
import geopandas as gpd
import json

modelo_blueprint = Blueprint('modelo_previsao', __name__)

graph_filename = "./app/api/v1/modelo_previsao/graph.graphml"


# Remeber to put in other file
class Grafo:

    def __init__ (self, lat0, latoo, lon0, lonoo, graph_filename):
        """
        Initializes a graph object with latitude and longitude boundaries.
        Downloads and processes the graph data from OpenStreetMap within the
        specified boundaries.

        :param lat0 (float): Minimum latitude boundary.
        :param latoo (float): Maximum latitude boundary.
        :param lon0 (float): Minimum longitude boundary.
        :param lonoo (float): Maximum longitude boundary.
        """

        self.lat0 = lat0
        self.latoo = latoo
        self.lon0 = lon0
        self.lonoo = lonoo
        self.graph_filename = graph_filename

        self.graph = ox.load_graphml(graph_filename)

    def return_graph(self):
        return self.graph
        
    def get_nearest_node (self, lat, lon):
        """
        Finds the nearest node in the graph to the given latitude and
        longitude coordinates.

        :param lat (float): Latitude coordinate.
        :param lon (float): Longitude coordinate.

        :return node (int): Nearest node ID.
        """

        # Project the graph to enable us to use the nearest_nodes method
        graph_proj = ox.project_graph(self.graph)

        # Project the coordinates of the given point
        coords = [(lon, lat)]
        point = ox.projection.project_geometry(Point(coords))[0]
        x, y = point.x, point.y

        # Find the nearest node
        node = ox.distance.nearest_nodes(graph_proj, x, y, return_dist=False)

        return node

    def crop (self, initial_point, final_point):
        """
        Crops the graph based on the fastest path between two given nodes.

        :param initial_point (int): ID of the initial node.
        :param final_point (int): ID of the final node.

        :return cropped_graph (networkx.MultiDiGraph): Cropped graph
            containing only the nodes and edges around the fastest path.
        """

        # Find the fastest path between the initial and final nodes
        gmaps_path = nx.astar_path(self.graph, initial_point, final_point, weight='travel_time')

        # Retrieve latitude and longitude coordinates of the nodes along the
        # fastest path (aka Google Maps route)
        lats = [self.graph.nodes[node]['y'] for node in gmaps_path]
        lons = [self.graph.nodes[node]['x'] for node in gmaps_path]

        # Determine a tight bounding box around the path
        lat_min = min(lats)
        lat_max = max(lats)
        lon_min = min(lons)
        lon_max = max(lons)

        # Adjust the bounding box to ensure it contains the graph properly and
        # falls within the initial boundaries
        bbox_lat_min = max(self.lat0, lat_min - (lat_max - lat_min))
        bbox_lat_max = min(self.latoo, lat_max + (lat_max - lat_min))
        bbox_lon_min = max(self.lon0, lon_min - (lon_max - lon_min))
        bbox_lon_max = min(self.lonoo, lon_max + (lon_max - lon_min))

        # Crop the graph based on the adjusted bounding box
        self.graph = ox.truncate.truncate_graph_bbox(self.graph, bbox_lat_max, bbox_lat_min, bbox_lon_max, bbox_lon_min)

        return self.graph

    def find_edge_by_nodes (self, node1, node2):
        """
        Finds an edge in the graph that links node1 to node2.

        :param node1 (int): Starting node ID.
        :param node2 (int): Ending node ID.

        :return None or edges[0] (None or tuple): Edge that links node1 to
            node2.
        """

        # Gather all the edges of the graph that start at node1 and end at node2,
        # or start at node2 and end at node1
        e1 = [e for e in self.graph.edges if e[0] == node1 and e[1] == node2]
        e2 = [e for e in self.graph.edges if e[0] == node2 and e[1] == node1]
        edges = [*e1, *e2]

        # If no edges were found, then print a message and return None.
        if len(edges) == 0:
            print(f"There are no edges linking {node1} to {node2} in graph.")
            return None

        # Otherwise, return the first edge that was found.
        else:
            return edges[0]

class Agora:

    def __init__ (self, year, month, day, hour, minute, second=0):
        """
        Initializes a time-like object with the specified date and time.

        :param year (int): Year.
        :param month (int): Month.
        :param day (int): Day.
        :param hour (int): Hour.
        :param minute (int): Minute.
        :param second (int): Second (default: 0).
        """

        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def __repr__( self):
        """
        Returns a string representation of the time in the format
        'YYYYMMDDHHMM'.
        """

        return f"{self.year:04d}{self.month:02d}{self.day:02d}{self.hour:02d}{self.minute:02d}"

    def step (self, integer):
        """
        Adds a specified number of seconds ('integer') to the current time.

        :param integer (int): Number of seconds to add.
        """

        total_seconds = self.second + integer

        # Update the seconds, minutes, and hours accordingly
        self.second = total_seconds % 60
        total_minutes = (total_seconds - self.second) // 60 + self.minute

        self.minute = total_minutes % 60
        total_hours = (total_minutes - self.minute) // 60 + self.hour

        self.hour = total_hours % 24

        # Update the day if necessary
        self.day += (total_hours - self.hour) // 24

    def get_flooding_points (self, url='https://github.com/liviatomas/floods_saopaulo/raw/main/1_input/e_Floods_2019.xlsx'):
        """
        Returns a list of flooding points at the current time.

        :param url (str): URL of the Excel file containing flooding data
            (default: 'https://github.com/liviatomas/floods_saopaulo/raw/main/1_input/e_Floods_2019.xlsx')

        :return flooding_points (list): List of flooding points. Each point is
            represented as a tuple (x, y) of coordinates.
        """

        # Formatting the date and time
        date = f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        start_time = f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"

        # Downloading the Excel file containing flooding data
        flood_df = pd.read_excel(url)

        # Filtering the data based on the current time
        my_floods = flood_df.loc[(flood_df['DATE'] == date) & (flood_df['START_T'] < start_time) & (flood_df['END_T'] > start_time)]

        # Extracting the coordinates
        flooding_points = my_floods[['X', 'Y']].values.tolist()

        # Converting coordinates
        flooding_points = [convert_coordinates(x, y) for x, y in flooding_points]

        return flooding_points


class Radar:

    def __init__ (self, lat0, lon0, dlat, dlon):
        """
        Initializes a radar object with latitude and longitude information.
        This class represents the radar that provides the information on
        precipitation.

        :param lat0 (float): Minimum latitude boundary.
        :param lon0 (float): Minimum longitude boundary.
        :param dlat (float): Spacing in the latitude grid.
        :param dlon (float): Spacing in the longitude grid.
        """

        self.lat0 = lat0
        self.lon0 = lon0
        self.dlat = dlat
        self.dlon = dlon

        self.source = "https://raw.githubusercontent.com/RPvMM-2023-S1/Rain-and-flood-informed-vehicle-routing-problem/main/radar_data/R13537439_"

    def rain_by_time (self, agora):
        """
        Reads rainfall data (mm) from a text file and returns it as a matrix.

        :param agora (Agora): An instance of the Agora class that represents
            the time.

        :return A (list or None): Matrix of rainfall data. Each element
            represents the rainfall in millimeters at a specific location. If
            the data is not available, returns None.
        """
        # Check if the 'Rain_Cache' folder exists and create it if necessary
        if not os.path.isdir('Rain_Cache'):
                os.mkdir('Rain_Cache')

        filename = self.source + repr(agora) + ".txt"

        # Local filename to save the downloaded file
        local_filename = os.path.join('Rain_Cache', "R13537439_" + repr(agora) + ".txt")

        # Check if the local file already exists
        if os.path.isfile(local_filename):
                # If the file exists, open it and read the data
                with open(local_filename, 'r') as file:
                        data = file.readlines()
        else:
                try:
                        # If the file doesn't exist locally, try to download it
                        response = requests.get(filename)

                        # Check if the download was successful (status code 200)
                        if response.status_code == 200:
                                # Extract the text data from the response and split it into lines
                                data = response.text.splitlines()

                                # Save the downloaded data to the local file
                                with open(local_filename, 'w') as file:
                                        file.write('\n'.join(data))
                        else:
                                # If the file doesn't exist on the server, print an error message
                                print(f"File {filename} does not exist.")
                                data = None

                except FileNotFoundError:
                        # If there was an error with file handling, print an error message
                        print(f"File {filename} does not exist.")
                        data = None

        # Data processing to create matrix A
        if data:
                # Create a matrix A by splitting each line and converting entries to integers
                # If the entry is "-99", it is replaced with 0
                A = [[0 if entry == "-99" else int(entry) for entry in line.split()] for line in data]
        else:
                A = None

        # Print the resulting matrix A
        return A

    def rain_at_edge (self, graph, edge, agora):
        """
        Reads the rain data from a matrix and returns the maximum rainfall in
        a given edge of a given graph.

        :param graph (networkx.Graph): Graph object.
        :param edge (tuple): Edge in the graph.
        :param agora (Agora): An instance of the Agora class that represents
            the time.

        :return (int): Maximum rainfall on the edge.
        """

        # Gather the coordinates of several points along the edge
        if 'geometry' in graph.edges[edge]:
            lonlats = list(graph.edges[edge]['geometry'].coords)
        else:
            lonlats = []

        initial = edge[0]
        lon, lat = graph.nodes[initial]['x'], graph.nodes[initial]['y']
        lonlats.append((lon, lat))

        final = edge[1]
        lon, lat = graph.nodes[final]['x'], graph.nodes[final]['y']
        lonlats.append((lon, lat))

        # List the rows and columns of the points of the edge
        rowcols = [(int((lat - self.lat0) / self.dlat), int((lon - self.lon0) / self.dlon)) for lon, lat in lonlats]

        # List the mms of rain in the points of the edge
        matrix = self.rain_by_time(agora)
        rainfall = [matrix[row][col] for row, col in rowcols]

        return max(rainfall)

dlat = -0.0090014
dlon = 0.009957

@modelo_blueprint.route('/geojson', methods=['POST'])
def handle_geojson():

    data = request.data

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Getting the json object e transform to dict
    data = request.get_json()
    
    # Getting the data from request
    point1 = data['features'][0]['geometry']['coordinates']
    point2 = data['features'][1]['geometry']['coordinates']

    # Getting grafo from disk
    graph = Grafo(point1[1], point2[0], point1[1], point2[0], graph_filename)

    graph = graph.return_graph()
    
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