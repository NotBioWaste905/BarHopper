import requests
from opening_hours import OpeningHours
import datetime

def is_place_open(opening_hours, check_time):
    # Use pyosm-opening-hours to parse and check
    if not opening_hours:
        return True  # Assume open if no hours provided
    
    parser = OpeningHours(opening_hours)
    return parser.is_open(check_time)



# response = requests.get(
#     "http://localhost:8000/find_path_by_name/Mitzva Bar/Powerhouse Moscow"
# )
# print(response.json())

if __name__=="__main__":
    # parse datetime from string like DD-MM-YYYY HH
    date = datetime.datetime.strptime("25-03-2025 20", "%d-%m-%Y %H")
    print(is_place_open("Mo-Fr 08:00-17:00", date))