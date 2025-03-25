import logging
import asyncio
from neo4j import GraphDatabase
from fastapi import FastAPI
from datetime import datetime
from opening_hours import OpeningHours

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Move configuration to environment variables later
URI = "neo4j://neo4j_db"  # Updated to use docker service name
AUTH = ("neo4j", "drink_beer_have_fun")
driver = GraphDatabase.driver(URI, auth=AUTH)

def is_place_open(opening_hours, check_time):
    date = datetime.strptime(check_time, "%d-%m-%Y %H")
    if not opening_hours:
        return True  # Assume open if no hours provided
    try:
        parser = OpeningHours(opening_hours)
    except Exception as e:
        print(f"Error parsing opening hours: {str(opening_hours)}")
        return False
    return parser.is_open(date)


def find_shortest_path(session, start_name, end_name, date_time=None):
    # If a date/time is provided, create a lookup table for open places
    open_places = []
    if date_time:
        result = session.run(
            """
            MATCH (p:Place)
            WHERE p.opening_hours IS NOT NULL
            RETURN id(p) AS id, p.opening_hours AS hours
            """
        )
        for record in result:
            if is_place_open(record["hours"], date_time):
                open_places.append(record["id"])
        result = session.run(
        """
        MATCH (start:Place)
        WHERE start.name = $start_name
        WITH start
        MATCH (end:Place)
        WHERE end.name = $end_name

        // create subgraph with only open places
        MATCH (p1:Place)-[r:NEAR]->(p2:Place)
        WHERE id(p1) IN $open_places AND id(p2) IN $open_places

        // Use dijkstra with max depth to prevent memory issues
        CALL apoc.algo.dijkstra(start, end, 'NEAR', 'distance', 10) 
        YIELD path, weight
        
        RETURN path, weight
        """,
        start_name=start_name,
        end_name=end_name,
        open_places=open_places
    )
    else:
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
        end_name=end_name
    )

    print(f"Open places: {len(open_places)}")
    
    return result.data()

def get_closest_place(session, lon, lat):
    result = session.run(
        """
        MATCH (p:Place)
        """)


@app.get("/find_path_by_name/{start_name}/{end_name}")
async def find_path_by_name(start_name: str, end_name: str, date_time: str = None):
    try:
        with driver.session() as session:
            paths = find_shortest_path(session, start_name, end_name, date_time)
            
            if not paths:
                return {"error": f"No path found between '{start_name}' and '{end_name}'"}
                
            path_data = paths[0]  # Get first path
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