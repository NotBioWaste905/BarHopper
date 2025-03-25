import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

URI = "neo4j://localhost"
AUTH = ("neo4j", "drink_beer_have_fun")
driver = GraphDatabase.driver(URI, auth=AUTH)

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


with driver.session() as session:
    find_way("way/151077519", "node/3522041789")
