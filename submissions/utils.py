"""
Module for various utility functions
"""


# import filetype, jos käytät tätä muista lisätä tiedostoon requirements.txt
import requests
from .models import Course, Exercise, Feedback, Student
from django.conf import settings
from django.core.cache import cache


AUTH = {'Authorization': settings.TOKEN}
API_URL = "https://plus.cs.tut.fi/api/v2/"


def get_json(url):
    resp = requests.get(url, headers=AUTH)
    return resp.json()


def add_user_to_course(user, user_role, course_html_url):
    """
    Lisätään käyttäjä kurssille LTI-kirjautumisessa saatujen tietojen mukaan.
    :param user: (User) käyttäjäobjekti
    :param user_role: (str) Kirjautumistietojen mukainen rooli kurssilla.
    :param course_html_url: (str) Kurssisivuston verkko-osoite.
    :return: 
    """
    try:
        course = Course.objects.get(html_url=course_html_url)
        
    except Course.DoesNotExist:
        course = create_course(course_html_url)
    
    if course:
        if user_role == "Instructor":
            course.teachers.add(user)
        if user_role == "TA,TeachingAssistant":
            course.assistants.add(user)


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
    # TODO: pitäisikö sellaiset tehtävät poistaa, jotka on poistettu kurssilta
    # eli niitä ei enää löydy kurssin rajapinnasta. (Jos poistetaan, niin ei
    # voida kuitenkaan sokeasti poistaa niitä, jotka on merkitty arvosteluun.)


    modules = cache.get(course.course_id)
    if modules:
        return


    exercises_url = f"{API_URL}courses/{course.course_id}/exercises/"
    modules = get_json(exercises_url)["results"]
    cache.set(course.course_id, modules)

    # Module sisältää yhden moduulin kaikki materiaalit ja tehtävät.
    for sub_module in modules:
        # Käydään läpi jokainen materiaali/tehtävä ja tutkitaan onko kyseessä
        # palautetava tehtävä. Jos on, niin lisätään listaan.
        for exercise in sub_module["exercises"]:
            details = get_json(exercise["url"])
            # print(details)
            if "is_submittable" in details and details["is_submittable"]:
                try:
                    exercise = Exercise.objects.get(exercise_id=details["id"])
                    
                except Exercise.DoesNotExist:
                    exercise = Exercise(course=course,
                                        exercise_id=details["id"],
                                        module_id=sub_module["id"])
                                    
                exercise.name = details["display_name"]
                exercise.save()
    

def get_submissions(exercise):
    """
    Askarrellaan kurssin ja tehtävän id:n perusteella url, jolla saadaan 
    pyydettyä tiedot kyseisen tehtävän viimeisimmistä/parhaista palautuksista.
    param exercise: (models.Exercise) tehtäväobjekti
    """
    data_url = f"{API_URL}courses/{exercise.course.course_id}/submissiondata/"
    query_url = f"{data_url}?exercise_id={exercise.exercise_id}&format=json"
    return get_json(query_url)


def update_submissions(exercise):

    subsdata = cache.get(exercise.exercise_id)
    if subsdata:
        return


    subsdata = get_submissions(exercise)
    cache.set(exercise.exercise_id, subsdata)

    consent_data = []
    if exercise.consent_exercise is not None:
        consent_data = get_submissions(exercise.consent_exercise)

    deadline_passed = check_deadline(exercise)

    accepted = {}
    students = {}
    duplicates = []

    for sub in subsdata:
        
        # print(sub)
        
        # Huomioidaan vain palautukset, jotka ovat läpäisseet testit
        # TODO: huomioi max-pisteet tai jotenkin muuten se jos palautus 
        #       on jo arvioitu. Toimii ehkä jo...?
        if sub["Grade"] < exercise.min_points:
            continue
        
        if not deadline_passed and not check_consent(sub["Email"],
                                                     consent_data):
            continue

        if sub["SubmissionID"] not in accepted:
            accepted[sub["SubmissionID"]] = {
                "grade": sub["Grade"],
                "penalty": sub["Penalty"],
                "students": {
                    sub["Email"]: sub["StudentID"]
                }
            }
        else:
            accepted[sub["SubmissionID"]]["students"][sub["Email"]] = sub["StudentID"]



        try:
            feedback = Feedback.objects.get(sub_id=sub["SubmissionID"])
            
        except Feedback.DoesNotExist:
            feedback = Feedback(exercise=exercise, sub_id=sub["SubmissionID"])
            feedback.save()

        add_feedback_base(exercise, feedback)
        add_student(sub, feedback)

    if exercise.work_div == Exercise.EVEN_DIV:
        divide_submissions(exercise)


def check_deadline(exercise):
    course_url = f"{API_URL}courses/{exercise.course.course_id}/"
    module_url = f"{course_url}exercises/{exercise.module_id}"
    exercise_module = get_json(module_url)
    
    if exercise_module["is_open"]:
        # print("Moduuli on vielä auki!")
        return False
        
    return True


def check_consent(student_email, consent_data):
    for sub in consent_data:
        if sub["Email"] == student_email:
            return True

    return False


def add_feedback_base(exercise, feedback):
    # Lisätään palautepohja, jos sellainen on tehtävään liitetty.
    if exercise.feedback_base:
        # print(exercise.feedback_base.name)
        try:
            feedback.feedback = exercise.feedback_base.open("r").read()
        except ValueError as e:
            feedback.feedback = f"Virhe luettaessa palautepohjaa: {e}"

        exercise.feedback_base.close()
        feedback.save()


def add_student(sub, new_feedback):
    try:
        student = Student.objects.get(email=sub["Email"])
        # Päivitetään varmuuden vuoksi opnum. Joissain tapauksissa on
        # mahdollista, että opiskelija saa opnumin vasta myöhemmin.
        student.student_id = sub["StudentID"]
        student.save()
        
        try:
            old_feedback = student.my_feedbacks.get(
                exercise=new_feedback.exercise)
            
            if old_feedback != new_feedback:
                print("Ei ole samat! Poista vanha ja lisää uusi tilalle:",
                      end=" ")
                if old_feedback.status is None:
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
        student = Student(email=sub["Email"], student_id=sub["StudentID"])
        student.save()
        student.my_feedbacks.add(new_feedback)
        print("Eka hyväksytty palautus tähän tehtävään:", student.email)


def divide_submissions(exercise):
    """
    Jakaa palautukset kurssille merkittyjen assareiden kesken.
    param exercise: (models.Exercise) Tehtäväobjekti
    """
    graders = Course.objects.get(
        course_id=exercise.course.course_id).assistants.all()
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
    Jonkinlainen algoritmi töiden jakamiseen. Jakaa työ tasan kaikkien 
    kurssiin liitettyjen assareiden kesken. Ei ole kunnolla testattu ja 
    saattaa toimia väärin. 
    HUOM! Tämä ottaa nyt arvosteluun kaiken, myös assarien omat sekä 
    testitunnuksilla tehdyt palautukset.
    """
    
    min_sub_count = 0
    grader_to_add = None
    first = True
    
    for grader in graders:
        # Valitaan pienimmän arvostelumäärän omaavaksi ensimmäinen
        # vastaantuleva
        if first:
            min_sub_count = len(grader.feedback_set.filter(exercise=exercise))
            grader_to_add = grader
            first = False
        # Jos ensimmäinen alkio on jo käsitelty,
        # tutkitaan löytyykö sitä pienempää
        elif len(grader.feedback_set.filter(
                exercise=exercise)) < min_sub_count:
            min_sub_count = len(grader.feedback_set.filter(exercise=exercise))
            grader_to_add = grader
            
    # Tässä pitäisi ny olla se, jolla on vähiten arvosteltavaa, tai yksi
    # niistä jolla on vähiten, jos usealla yhtä vähän. Tasatilanteessa ei ole
    # väliä kuka valitaan.
    return grader_to_add


def get_submission_data(feedback):
    exercise_url = f"{API_URL}exercises/{feedback.exercise.exercise_id}/"
    form_spec = get_json(exercise_url)["exercise_info"]["form_spec"]

    sub_url = f"{API_URL}submissions/{feedback.sub_id}/"
    sub_info = get_json(sub_url)

    sub_data = []

    # Kun palautetaan git-url, "form_spec" näyttää jäävän tyhjäksi
    if len(form_spec) == 0 and sub_info["submission_data"]:
        get_git_url(sub_data, sub_info["submission_data"][0][1])

    # Jos palautus ei ole git-url, se voi olla tekstiä tai tiedosto
    # (tai monivalintatehtävän valintavaihtoehto ("option_n"), joita ei
    # yleensä arvioida käsin, joten jätetään tyyppi "radio" huomiotta).
    for field in form_spec:
        if field["type"] == "file":
            get_filecontent(sub_data, field, sub_info["files"])

        elif field["type"] == "textarea":
            get_text(sub_data, field, sub_info["submission_data"])

    # print(sub_data)
    return sub_data


def get_git_url(sub_data, url):
    if url.startswith("git@"):
        url = url.replace(":", "/").replace("git@", "https://", 1)

    sub_data.append(
        {
            "title": None,
            "url": url,
            "text": "Siirry opiskelijan repositorioon oheisesta linkistä.",
            "code": None
        }
    )


def get_filecontent(sub_data, form_field, files):
    """
    Etsii halutun tiedoston ja tallentaa sen tiedot listaan sanakirjamuodossa.
    :param sub_data: (list) Opiskelijan palautuksen olennaiset tiedot dicteinä.
    :param form_field: (dict) Tehtävän (yaml-tiedosto) palautuskentän tiedot.
    :param files: (dict) Palautettujen tiedostojen nimet, urlit jne.
    :return: None
    """
    for file in files:
        if file["param_name"] == form_field["key"]:
            resp = requests.get(file["url"], headers=AUTH)

            text = ""
            code = None

            if file["filename"].endswith(".py"):
                resp.encoding = "utf-8"
                code = resp.text
            else:
                text = "Lataa tiedosto oheisesta linkistä."

            sub_data.append(
                {
                    "title": None,
                    "url": file["url"],
                    "text": text,
                    "code": code
                }
            )

            return


def get_text(sub_data, form_field, textareas):
    """
    Hakee tekstimuotoisen tehtävän kysymykset ja vastaukset.
    :param sub_data: (list) Opiskelijan palautuksen olennaiset tiedot dicteinä.
    :param form_field: (dict) Tehtävän (yaml-tiedosto) palautuskentän tiedot.
    :param textareas: 
    :return: 
    """
    for area in textareas:
        if area[0] == form_field["key"]:
            sub_data.append(
                {
                    "title": form_field["title"],
                    "url": "",
                    "text": area[1],
                    "code": None
                }
            )

            return


def create_json(feedbacks):
    if feedbacks:
        print("\nNyt pitäisi askarrella ja postata jsoni.\n")
        return True
    else:
        print("Ei arvosteltuja palautuksia.")
        return False


def save_file(fileobject):
    with open(f"files/{fileobject.name}.txt", "wb") as file:
        for chunk in fileobject.chunks():
            file.write(chunk)


def check_filetype(fileobject):
    """
    Tarkastellaan ladatun tiedoston kokoa ja tiedostopäätettä.
    :param fileobject: (InMemoryUploadedFile)
    :return: True jos tiedostoa ei ole lainkaan tai se on pääteltävissä 
    tekstitiedostoksi.
    """

    # print(fileobject.size)

    # Jos tiedostoa ei ole annettu, kyseessä ei ole virhe
    if not fileobject:
        return True

    # Oletetaan tiedoston olevan tekstitiedosto, jos tiedoston koko on
    # alle 500 kB ja tiedostopääte on .txt.
    elif fileobject.name.endswith("txt") and fileobject.size < 500000:
        return True

    else:
        return False
