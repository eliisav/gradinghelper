"""
Module for various utility functions
"""


import requests


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}
API_URL = "https://plus.cs.tut.fi/api/v2/"


def get_submissions(exercise_id):
    # Etsitään tehtävän id:n perusteella url, jolla saadaa pyydettyä tiedot
    # tämän tehtävän viimeisimmistä/parhaista palautuksista.
    exercise_url = f"{API_URL}exercises/{exercise_id}"
    req = requests.get(exercise_url, headers=AUTH)
    exercise_info = req.json()
    course_url = exercise_info["course"]["url"]
    data_url = f"{course_url}submissiondata/?exercise_id={exercise_id}&format=json"
    
    print("SUB_DATA_URL:", data_url)
    
    req = requests.get(data_url, headers=AUTH)
    return req.json()
    
