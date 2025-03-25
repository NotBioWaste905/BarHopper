import logging
import asyncio
from neo4j import GraphDatabase
from fastapi import FastAPI

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Move configuration to environment variables later
URI = "neo4j://neo4j_db"  # Updated to use docker service name
AUTH = ("neo4j", "drink_beer_have_fun")
driver = GraphDatabase.driver(URI, auth=AUTH)

def find_shortest_path(session, start_name, end_name):
    result = session.run(
        """
        MATCH (start:Place)
        WHERE start.name = $start_name
        WITH start
        MATCH (end:Place)
        WHERE end.name = $end_name
        
        // Use dijkstra with max depth to prevent memory issues
        CALL apoc.algo.dijkstra(start, end, 'NEAR', 'distance', 10) 
        YIELD path, weight
        
        RETURN path, weight
        """,
        start_name=start_name,
        end_name=end_name,
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


@app.get("/find_path_by_name/{start_name}/{end_name}")
async def find_path_by_name(start_name: str, end_name: str):
    try:
        with driver.session() as session:
            paths = find_shortest_path(session, start_name, end_name)
            
            if not paths:
                return {"error": f"No path found between '{start_name}' and '{end_name}'"}
                
            path_data = paths[0]  # Get first path
            print(path_data)
            return {
                "totalDistance": path_data["weight"],
                "path": [{
                    "name": node["name"],
                    "id": node["id"],
                    "lon": node["longitude"],
                    "lat": node["latitude"]
                } for node in path_data["path"] if not isinstance(node, str)]
            }
    except Exception as e:
        logger.error(f"Error finding path: {str(e)}")
        return {"error": str(e)}

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

# Add a helper endpoint to list available places
@app.get("/places")
async def get_places():
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (p:Place)
                RETURN p.name AS name
                ORDER BY p.name
                """
            )
            places = [record["name"] for record in result]
            return {"places": places}
    except Exception as e:
        logger.error(f"Error getting places: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)