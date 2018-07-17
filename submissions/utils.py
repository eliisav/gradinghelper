"""
Module for various utility functions
"""


import requests


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}
API_URL = "https://plus.cs.tut.fi/api/v2/"


def get_json(url):
    req = requests.get(url, headers=AUTH)
    return req.json()


def get_courses():
    """
    Hakee kaikki TUT+ -sivustolla olevat kurssi-instanssit.
    return: lista kursseista
    """
    courses_url = f"{API_URL}courses/"
    
    # HUOM! Tämä ei toimi pelkästään näin, jos kursseja on useita sivuja!!!!
    course_list = get_json(courses_url)["results"]
    return course_list
    
    
def get_exercises(course_id):
    """
    Hakee kaikki yhden kurssi-instanssin tehtävät.
    param course_id: (int) kurssin tunnus TUT+ -palvelussa
    return: lista tehtävistä
    """
    #course_url = f"{API_URL}courses/{course_id}/"
    #course_info = get_json(course_url)
    #exercises_url = course_info["exercises"]
    exercises_url = f"{API_URL}courses/{course_id}/exercises/"
    modules = get_json(exercises_url)["results"]
    
    
    """
        tulos = cache.get(avaimen)
    if not tulos:
      tulos = {}    
      cache.set(avaimen, tulos)
    """
    
    exercises = []
    
    # Module sisältää yhden moduulin kaikki materiaalit ja tehtävät.
    for module in modules:
        # Käydään läpi jokainen materiaali/tehtävä ja tutkitaan onko kyseessä
        # palautetava tehtävä. Jos on, niin lisätään listaan.
        for exercise in module["exercises"]:
            details = get_json(exercise["url"])
            if "is_submittable" in details and details["is_submittable"] == True:
                print("Laitetaan talteen")
                exercises.append(details)
                
        #exercises += module["exercises"]
        
    return exercises
    

def get_submissions(exercise_id):
    # Etsitään tehtävän id:n perusteella url, jolla saadaan pyydettyä tiedot
    # tämän tehtävän viimeisimmistä/parhaista palautuksista.
    exercise_url = f"{API_URL}exercises/{exercise_id}/"
    req = requests.get(exercise_url, headers=AUTH)
    exercise_info = req.json()
    course_url = exercise_info["course"]["url"]
    data_url = f"{course_url}submissiondata/?exercise_id={exercise_id}&format=json"
    
    # print("SUB_DATA_URL:", data_url)
    
    req = requests.get(data_url, headers=AUTH)
    return req.json()
    
