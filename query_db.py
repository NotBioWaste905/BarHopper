import logging
import asyncio
from neo4j import GraphDatabase
from fastapi import FastAPI

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

URI = "neo4j://localhost"
AUTH = ("neo4j", "drink_beer_have_fun")
driver = GraphDatabase.driver(URI, auth=AUTH)

def find_shortest_path(session, start_id, end_id):
    result = session.run(
        """
        MATCH (start:Place {id: $start_id}), (end:Place {id: $end_id})
        
        // Use dijkstra with max depth to prevent memory issues
        CALL apoc.algo.dijkstra(start, end, 'NEAR', 'distance', 10) 
        YIELD path, weight
        
        RETURN path, weight
        """,
        start_id=start_id,
        end_id=end_id,
    )
    return result.data()


def find_dijkstra_path(session, start_id, end_id):
    # First, create the graph projection
    session.run(
        """
        CALL gds.graph.project(
          'pathGraph',
          'MATCH (p:Place) RETURN id(p) AS id',
          'MATCH (a:Place)-[r:NEAR]-(b:Place) RETURN id(a) AS source, id(b) AS target, r.distance AS weight'
        )
        YIELD graphName, nodeCount, relationshipCount
        """)
    
    # Then run the algorithm on the projected graph
    result = session.run(
        """
        MATCH (start:Place {id: $start_id}), (end:Place {id: $end_id})
        CALL gds.shortestPath.dijkstra.stream('pathGraph', {
          sourceNode: start,
          targetNode: end,
          relationshipWeightProperty: 'weight'
        })
        YIELD index, sourceNode, targetNode, totalCost, nodeIds, path
        RETURN totalCost, gds.util.asNodes(path) AS path
        """,
        start_id=start_id,
        end_id=end_id,
    )
    
    # Optionally, drop the graph projection when done
    session.run("CALL gds.graph.drop('pathGraph') YIELD graphName")
    
    return result.data()


@app.get("/find_way_id/{start_id}/{end_id}")
async def find_way_id(start_id, end_id):
    response = {}
    try:
        with driver.session() as session:
            # Get two example node IDs from your data
            # start_id = "relation/17984069"
            # end_id = "relation/another_id"

            paths = find_shortest_path(session, start_id, end_id)
            # print(paths)
            for path in paths:
                response["totalDistance"] = path["totalDistance"]
                response["path"] = []
                for node in path["path"]:
                    response["path"].append({"name": node["name"],
                                            "id": node["id"],
                                            "lon": node["longitude"],
                                            "lat": node["latitude"]})
                print(f"Total distance: {path['totalDistance']} meters")
                print("Path:")
                for node in path["path"]:
                    print(f"  - {node['name']} ({node['id']})")
    except Exception as e:
        print(e)
        response = {"error": str(e)}

    return response

def find_way(start_id, end_id):
    with driver.session() as session:
        paths = find_shortest_path(session, start_id, end_id)
        
        if not paths:
            print(f"No path found between {start_id} and {end_id}")
            return
            
        for p in paths:
            print(f"Total distance: {p['weight']} meters")
            print("Path:")
            for node in p['path']:
                print(f"  - {node} ({node})")


async def main():
    find_way("way/151077519", "node/3522041789")

if __name__ == "__main__":
    asyncio.run(main())