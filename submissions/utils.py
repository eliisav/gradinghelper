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


def add_user_to_course(user, html_url):
    """
    
    return: 
    """
    try:
        course = Course.objects.get(html_url=html_url)
        
    except Course.DoesNotExist:
        course = create_course(html_url)
    
    if course:   
        course.teachers.add(user)


def create_course(html_url):
    # Html_urlin pitäisi olla muotoa: plus.cs.tut.fi/{kurssi}/{instanssi}/
    # Tallennetaan nimeksi kurssin ja instanssin tunnisteet
    name = "".join(html_url.split("/")[1:3])
    
    courses_url = f"{API_URL}courses/"
    course_id = None
    
    while True:
        course_list = get_json(courses_url)
        for course in course_list["results"]:
            if html_url in course["html_url"]:
                course_id = course["id"]
                break
                
        if not course_list["next"]:
            break
        else:
            courses_url = course_list["next"]
    
    if course_id is None:
        return None
    else:        
        course = Course(course_id=course_id, name=name, html_url=html_url)
        course.save()
        return course


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
                    exercise = Exercise.objects.get(exercise_id=details["id"])
                    
                except Exercise.DoesNotExist:
                    exercise = Exercise(course = course, 
                                        exercise_id=details["id"],
                                        module_id=module["id"])
                                    
                exercise.name = details["display_name"]
                exercise.save()
    

def get_submissions(exercise):
    """
    Askarrellaan kurssin ja tehtävän id:n perusteella url, jolla saadaan 
    pyydettyä tiedot kyseisen tehtävän viimeisimmistä/parhaista palautuksista.
    param exercise: (models.Exercise) tehtäväobjekti
    """
        
    #exercise_url = f"{API_URL}exercises/{exercise_id}/"
    #exercise_info = get_json(exercise_url)
    #course_url = exercise_info["course"]["url"]
    #data_url = f"{course_url}submissiondata/?exercise_id={exercise_id}&format=json"
        
    data_url = f"{API_URL}courses/{exercise.course.course_id}/submissiondata/"
    query_url = f"{data_url}?exercise_id={exercise.exercise_id}&format=json"
    
    # print("SUB_DATA_URL:", data_url)
    
    return get_json(query_url)


def update_submissions(exercise):
    subsdata = get_submissions(exercise)
    deadline_passed = check_deadline(exercise)

    for sub in subsdata:
        
        #print(sub)
        
        # Huomioidaan vain palautukset, jotka ovat läpäisseet testit
        # TODO: huomioi max-pisteet tai jotenkin muuten se jos palautus 
        #       on jo arvioitu. Toimii ehkä jo...?
        if sub["Grade"] < exercise.min_points:
            continue
        
        if not deadline_passed and not check_consent(sub["Email"], exercise):
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
        
        add_students(sub["Email"], feedback)
        
    divide_submissions(exercise)


def check_deadline(exercise):
    course_url = f"{API_URL}courses/{exercise.course.course_id}/"
    module_url = f"{course_url}exercises/{exercise.module_id}"
    module = get_json(module_url)
    
    if module["is_open"]:
        #print("Moduuli on vielä auki!")
        return False
        
    return True


def check_consent(student_email, exercise):
    if exercise.consent_exercise is not None:
        subsdata = get_submissions(exercise.consent_exercise)
        
        for sub in subsdata:
            if sub["Email"] == student_email:
                return True

    return False


def add_students(student_email, new_feedback):
    try:
        student = Student.objects.get(email=student_email)
        
        try:
            old_feedback = student.my_feedbacks.get(exercise=new_feedback.exercise)
            
            if old_feedback != new_feedback:
                print("Ei ole samat! Poista vanha ja lisää uusi tilalle:", end=" ")
                if not old_feedback.done:
                    old_feedback.delete()
                    student.my_feedbacks.add(new_feedback)
                else:
                    print("Eipäs poisteta. Arvostelu oli jo tehty!", end=" ")
                    new_feedback.delete()
                
            else:
                print("Ne on samat, ei tartte tehdä mitään:", end=" ")
                
            print(student.email)
                
        except Feedback.DoesNotExist:
            print("Eka hyväksytty palautus tähän tehtävään:", student.email)
            student.my_feedbacks.add(new_feedback)
            
    except Student.DoesNotExist:
        student = Student(email=student_email)
        student.save()
        student.my_feedbacks.add(new_feedback)
        print("Eka hyväksytty palautus tähän tehtävään:", student.email)


def divide_submissions(exercise):
    """
    Jakaa palautukset kurssille merkittyjen assareiden kesken.
    param exercise: (models.Exercise) Tehtäväobjekti
    """
    graders = Course.objects.get(course_id=exercise.course.course_id).teachers.all()
    subs = exercise.feedback_set.all()
        
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


def choose_grader(exercise, graders):
    """
    Jonkinlainen algoritmi töiden jakamiseen. Jakaa työ tasan kaikkien kurssiin 
    liitettyjen assareiden kesken. Ei ole kunnolla testattu ja saattaa 
    toimia väärin. 
    HUOM! Tämä ottaa nyt arvosteluun kaiken, myös assarien omat sekä 
    testitunnuksilla tehdyt palautukset.
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
    
    
def create_json(feedbacks):
    if feedbacks:
        print("\nNyt pitäisi askarrella ja postata jsoni.\n")
        return True
    else:
        print("Ei arvosteltuja palautuksia.")
        return False
    















    
