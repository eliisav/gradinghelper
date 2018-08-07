"""
Module for various utility functions
"""


import requests
from .models import Course, Exercise, Feedback, Student
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
        
        #print(sub)
        
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
            
            try:
                old = student.my_feedbacks.get(exercise=exercise)
                
                if old != feedback:
                    print("Ei ole samat! Poista vanha ja lisää uusi tilalle.")
                    if not old.done:
                        old.delete()
                        student.my_feedbacks.add(feedback)
                    else:
                        print("Eipäs poisteta. Arvostelu oli jo tehty!")
                        feedback.delete()
                    
                else:
                    print("Ne on samat, ei tartte tehdä mitään.")
                    
            except Feedback.DoesNotExist:
                student.my_feedbacks.add(feedback)
                
        except Student.DoesNotExist:
            student = Student(email=sub["Email"])
            student.save()
            student.my_feedbacks.add(feedback)
        
    divide_submissions(exercise)
        

def choose_grader(exercise, graders):
    """
    Jonkinlainen algoritmi töiden jakamiseen. Ei vielä testattu ja saattaa 
    toimia väärin.
    """
    
    min_sub_count = 0
    grader_to_add = None
    first = True
    
    for grader in graders:
        # Valitaan pienimmän arvostelumäärän omaavaksi ensimmäinen vastaantuleva
        if first:
            min_sub_count = len(grader.feedback_set.filter(exercise=exercise))
            grader_to_add = grader
            first = False
        # Jos ensimmäinen alkio on jo käsitelty, tutkitaan löytyykö sitä pienempää
        elif len(grader.feedback_set.filter(exercise=exercise)) < min_sub_count:
            min_sub_count = len(grader.feedback_set.filter(exercise=exercise))
            grader_to_add = grader
            
    # Tässä pitäisi ny olla se, jolla on vähiten arvosteltavaa, tai yksi niistä 
    # jolla on vähiten, jos usealla yhtä vähän. Tasatilanteessa ei ole väliä 
    # kuka valitaan.
    return grader_to_add
    
        
def divide_submissions(exercise):
    """
    Jakaa palautukset kurssille merkittyjen assareiden kesken.
    param exercise: (models.Exercise) Tehtäväobjekti
    """
    graders = Course.objects.get(course_id=exercise.course.course_id).teachers.all()
    #assarit = kurssi.teachers.all()
    subs = exercise.feedback_set.all()
    sub_per_grader = len(subs) // len(graders)
    res = len(subs) % len(graders)
        
    for sub in subs:
        if sub.grader is None:
            grader = choose_grader(exercise, graders)
            grader.feedback_set.add(sub)
        else:
            print(sub, sub.grader)
    
    print("Palautusta per assari:", len(subs) / len(graders))
    print("Assareilla arvostelussa:")
    for grader in graders:
        print(len(grader.feedback_set.filter(exercise=exercise)))
    


































