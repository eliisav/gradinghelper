"""
Module for various utility functions
"""


import requests
from .models import Exercise, Feedback, Student
from django.conf import settings


AUTH = {'Authorization': settings.TOKEN}
API_URL = "https://plus.cs.tut.fi/api/v2/"


def get_json(url):
    resp = requests.get(url, headers=AUTH)
    return resp.json()


def get_courses():
    """
    Hakee kaikki TUT+ -sivustolla olevat kurssi-instanssit. TARPEETON!?!?
    return: lista kursseista
    """
    courses_url = f"{API_URL}courses/"
    
    # HUOM! Tämä ei toimi pelkästään näin, jos kursseja on useita sivuja!!!!
    course_list = get_json(courses_url)["results"]
    return course_list
    
    
def get_exercises(course):
    """
    Hakee kaikki yhden kurssi-instanssin tehtävät.
    param course: (Course) kurssiobjekti
    return: lista tehtävistä
    """
    #course_url = f"{API_URL}courses/{course_id}/"
    #course_info = get_json(course_url)
    #exercises_url = course_info["exercises"]
    exercises_url = f"{API_URL}courses/{course.course_id}/exercises/"
    modules = get_json(exercises_url)["results"]
    
    # Module sisältää yhden moduulin kaikki materiaalit ja tehtävät.
    for module in modules:
        # Käydään läpi jokainen materiaali/tehtävä ja tutkitaan onko kyseessä
        # palautetava tehtävä. Jos on, niin lisätään listaan.
        for exercise in module["exercises"]:
            details = get_json(exercise["url"])
            #print(details)
            if "is_submittable" in details and details["is_submittable"] == True:
            
                try:
                    exercise = course.exercise_set.get(exercise_id=details["id"])
                    
                except Exercise.DoesNotExist:
                    exercise = course.exercise_set.create(exercise_id=details["id"])
                                    
                exercise.name = details["display_name"]
                exercise.save()
    

def get_submissions(exercise_id, exercise):
    # Etsitään tehtävän id:n perusteella url, jolla saadaan pyydettyä tiedot
    # tämän tehtävän viimeisimmistä/parhaista palautuksista.
    exercise_url = f"{API_URL}exercises/{exercise_id}/"
    exercise_info = get_json(exercise_url)
    course_url = exercise_info["course"]["url"]
    data_url = f"{course_url}submissiondata/?exercise_id={exercise_id}&format=json"
    
    # print("SUB_DATA_URL:", data_url)
    subsdata = get_json(data_url)
    
    for sub in subsdata:
        print(sub)
        # Huomioidaan vain palautukset, jotka ovat läpäisseet testit
        # TODO: huomioi max-pisteet tai jotenkin muuten se jos palautus 
        #       on jo arvioitu.
        if sub["Grade"] < exercise.min_points:
            continue
        
        try:
            feedback = Feedback.objects.get(sub_id=sub["SubmissionID"])
            
        except Feedback.DoesNotExist:
            # Etsitään palautetun tiedoston/gitrepon url. HUOM! Kaikilla 
            # tehtävillä ei ole mitään urlia ja kentät voivat olla eri nimisiä!!!
            if "ohjelma.py" in sub:
                sub_url = sub["ohjelma.py"]
            elif "git" in sub:
                sub_url = sub["git"]
            else:
                sub_url = ""

            feedback = Feedback(exercise=exercise, sub_id=sub["SubmissionID"], 
                                sub_url=sub_url)
            feedback.save()

        try:
            student = Student.objects.get(email=sub["Email"])
        except Student.DoesNotExist:
            student = Student(email=sub["Email"])
            student.save()
            
        student.my_feedbacks.add(feedback)

