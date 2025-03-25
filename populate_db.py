import json
from tqdm import tqdm
from neo4j import GraphDatabase

URI = "neo4j://localhost"
AUTH = ("neo4j", "drink_beer_have_fun")
driver = GraphDatabase.driver(URI, auth=AUTH)


def add_node(tx, data):
    tx.run(
        """
        CREATE (n:Place)
        SET n = $data,
            n.location = point({longitude: $lon, latitude: $lat})
        """,
        data=data,
        lon=data["longitude"],
        lat=data["latitude"],
    )


def find_shortest_path(session, start_id, end_id):
    result = session.run(
        """
        MATCH (start:Place {id: $start_id}), (end:Place {id: $end_id})
        MATCH p = shortestPath((start)-[:NEAR*]-(end))
        WITH p, reduce(weight = 0, r in relationships(p) | weight + r.distance) AS totalDistance
        RETURN nodes(p) AS path, totalDistance
        """,
        start_id=start_id,
        end_id=end_id,
    )
    return result.data()


def setup_graph():
    with driver.session() as session:
        # Delete existing data
        session.run("MATCH (n) DETACH DELETE n")

        # Populate nodes
        print("Creating nodes...")
        with open("moscow_bars_pubs.geojson", "r", encoding="utf-8") as file:
            data: dict = json.load(file)
            for feature in data["features"]:
                place_data: dict = feature["properties"]
                # geometry = feature["geometry"]
                coords = feature["geometry"]["coordinates"][0]
                if isinstance(coords, list):
                    place_data.update(
                        {
                            "longitude": coords[0][0],
                            "latitude": coords[0][1],
                            "id": feature["id"],  # Ensure unique ID for pathfinding
                        }
                    )
                elif isinstance(coords, float):
                    place_data.update(
                        {
                            "longitude": feature["geometry"]["coordinates"][0],
                            "latitude": feature["geometry"]["coordinates"][1],
                            "id": feature["id"],  # Ensure unique ID for pathfinding
                        }
                    )
                session.execute_write(add_node, place_data)

        # Create spatial index
        print("Creating index...")
        session.run("CREATE POINT INDEX place_location FOR (p:Place) ON (p.location)")

        # Create relationships (using APOC)
        print("Creating NEAR relationships...")
        session.run("""
            MATCH (a:Place)
            MATCH (b:Place) 
            WHERE a <> b AND point.distance(a.location, b.location) <= 2000
            WITH a, b, point.distance(a.location, b.location) AS dist
            ORDER BY a, dist
            WITH a, collect({node: b, distance: dist})[0..5] AS nearest
            UNWIND nearest AS neighbor
            WITH a, neighbor.node AS b, neighbor.distance AS dist
            MERGE (a)-[r:NEAR]-(b)
            SET r.distance = dist
        """)

        print("Graph ready for pathfinding!")


def find_way(start_id, end_id):
    with driver.session() as session:
        # Get two example node IDs from your data
        # start_id = "relation/17984069"
        # end_id = "relation/another_id"

        paths = find_shortest_path(session, start_id, end_id)
        # print(paths)
        for path in paths:
            print(f"Total distance: {path['totalDistance']} meters")
            print("Path:")
            for node in path["path"]:
                print(f"  - {node['name']} ({node['id']})")


if __name__ == "__main__":
    # setup_graph()
    find_way("way/151077519", "node/3522041789")
