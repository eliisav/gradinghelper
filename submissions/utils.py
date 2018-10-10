"""
Module for various utility functions
"""


# import filetype, jos käytät tätä muista lisätä tiedostoon requirements.txt
import io
import json
import datetime
import logging
import pep8
import requests
import sys

from .models import Course, Exercise, Feedback, Student
from django.conf import settings
from django.core.cache import cache


AUTH = {'Authorization': settings.TOKEN}
API_URL = "https://plus.cs.tut.fi/api/v2/"

LOGGER = logging.getLogger(__name__)
debug_feedbacks = []


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
    name = "".join(html_url.replace("https://plus.cs.tut.fi/", "").split("/"))

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

    """
    modules = cache.get(course.course_id)
    if modules:
        return
    """

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
    """
    submissiondata = cache.get(exercise.exercise_id)
    if submissiondata:
        return
    """

    consent_data = None
    if exercise.consent_exercise is not None:
        consent_data = get_submissions(exercise.consent_exercise)

    deadline_passed = check_deadline(exercise)

    if deadline_passed or consent_data:
        submissiondata = get_submissions(exercise)

        # print(submissiondata)

        cache.set(exercise.exercise_id, submissiondata)

        accepted = sort_submissions(submissiondata, exercise.min_points,
                                    deadline_passed, consent_data)

        for sub in accepted:
            try:
                feedback = Feedback.objects.get(sub_id=sub)

            except Feedback.DoesNotExist:
                feedback = Feedback(
                    exercise=exercise,
                    sub_id=sub,
                    auto_grade=accepted[sub]["grade"],
                )

                if accepted[sub]["penalty"]:
                    feedback.penalty = accepted[sub]["penalty"]

                feedback.save()

            add_feedback_base(exercise, feedback)

            for student in accepted[sub]["students"]:
                if not add_student(student, feedback):
                    break

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


def sort_submissions(submissions, min_points, deadline_passed, consent_data):
    """
    Käydään läpi jsonin palautukset ja lisätään hyväksytyt accepted-dictiin. 
    Pääsääntöisesti täysin turhaa ajan tuhlausta, mutta tarvitaan jos 
    ryhmäpalautuksen ryhmä on jälkikäteen tehty henkilökunnan toimesta.
    
    :param submissions: (dict) tehtävän viimeisimmät/parhaat palautukset 
    :param min_points: (int) minimipisteet joilla tehtävä otetaan arvosteluun
    :param deadline_passed: (boolean) True, jos tehtävän deadline on mennyt
    :param consent_data: (dict) hyväksyntätehtävään tehdyt palautukset
    :return: (dict) hyväksytyt palautukset, jotka otetaan arvosteluun
    """

    accepted = {}    # Hyväksyttyjen palautusten oleellinen informaatio
    students = {}    # Opiskelijat ja heidän tekemänsä palautukset
    duplicates = []  # Lista opiskelijoista, joilla enemmän kuin yksi palautus

    for sub in submissions:

        # print(sub)

        # Huomioidaan vain palautukset, jotka ovat läpäisseet testit
        # TODO: huomioi max-pisteet tai jotenkin muuten se jos palautus
        #       on jo arvioitu. Toimii ehkä jo...?
        if sub["Grade"] < min_points:
            continue

        # TODO: Ota tämä pois! Väliaikainen viritys askelmittaria varten
        if sub["Penalty"] is None and sub["Grade"] < 20:
            continue

        if not deadline_passed and not check_consent(sub["Email"],
                                                     consent_data):
            continue

        if sub["SubmissionID"] not in accepted:
            accepted[sub["SubmissionID"]] = {
                "grade": sub["Grade"],
                "penalty": sub["Penalty"],
                "students": [
                    {
                        "email": sub["Email"],
                        "id": sub["StudentID"]
                    }
                ]
            }
        else:
            accepted[sub["SubmissionID"]]["students"].append(
                {
                    "email": sub["Email"],
                    "id": sub["StudentID"]
                }
            )

        if sub["Email"] not in students:
            students[sub["Email"]] = [sub["SubmissionID"]]
        else:
            # Parityösähläyksissä opiskelijalle on voinut tallentua
            # useampi kuin yksi palautus. Laitetaan tuplat talteen
            # ja poistetaan tarpeettomat palautukset seuraavassa vaiheessa.
            students[sub["Email"]].append(sub["SubmissionID"])
            duplicates.append(sub["Email"])

    for student in duplicates:
        for sub in students[student]:
            # Poistetaan opiskelijalta se palautus, joka EI ole paripalautus.
            # Tällöin opiskelijatietoja siis 1 kpl
            if len(accepted[sub]["students"]) == 1:
                # print("Poistetaan tupla:", sub, accepted[sub])
                del accepted[sub]

    return accepted


def add_feedback_base(exercise, feedback):
    """
    Lisätään/päivitetään palautepohja, jos sellainen on tehtävään liitetty.
    :param exercise: (Exercise model object)
    :param feedback: (Feedback model object)
    """
    if exercise.feedback_base:
        # print(exercise.feedback_base.name)
        try:
            feedback.feedback = exercise.feedback_base.open("r").read()
        except ValueError as e:
            feedback.feedback = f"Virhe luettaessa palautepohjaa: {e}"

        exercise.feedback_base.close()
        feedback.save()


def add_student(student_dict, new_feedback):
    """
    Liitetään opiskelija palautukseen. Jos opiskelijalla on edellinen palautus 
    samaan tehtävään, se poistetaan mikäli arviointia ei ole aloitettu.
    :param student_dict: (dict) opiskelijan s-posti ja opiskelijanumero
    :param new_feedback: (Feedback model object)
    :return: (bool) False, jos opiskelijalla on jo palautus arvostelussa.
    """
    try:
        student_obj = Student.objects.get(email=student_dict["email"])
        # Päivitetään varmuuden vuoksi opnum. Joissain tapauksissa on
        # mahdollista, että opiskelija saa opnumin vasta myöhemmin.
        student_obj.student_id = student_dict["id"]
        student_obj.save()
        
        try:
            old_feedback = student_obj.my_feedbacks.get(
                exercise=new_feedback.exercise
            )
            
            if old_feedback != new_feedback:
                print("Ei ole samat! Poista vanha ja lisää uusi tilalle:")
                if old_feedback.status is None:

                    #grader = User.objects.get(pk=old_feedback.grader.pk)

                    new_feedback.grader = old_feedback.grader
                    new_feedback.save()

                    LOGGER.debug(f"{student_obj} {new_feedback.exercise}")
                    LOGGER.debug(f"Vanha: {old_feedback} "
                                 f"{old_feedback.grader}")

                    old_feedback.delete()

                    LOGGER.debug(f"Uusi: {new_feedback} {new_feedback.grader}")

                    debug_feedbacks.append(new_feedback)

                    student_obj.my_feedbacks.add(new_feedback)
                else:
                    # TODO: huomautus arvostelijalle siitä, että uudempi
                    # palautus olisi olemassa.
                    print("Eipäs poisteta. Arvostelu oli jo aloitettu!",
                          end=" ")
                    new_feedback.delete()
                    return False
                
            else:
                print("Ne on samat, ei tartte tehdä mitään:", end=" ")
                
            # print(student_obj.email)

        except Feedback.DoesNotExist:
            print("Aikaisempaa palautusta ei löytynyt:", student_obj.email)
            student_obj.my_feedbacks.add(new_feedback)
            
    except Student.DoesNotExist:
        student_obj = Student(
            email=student_dict["email"],
            student_id=student_dict["id"]
        )
        student_obj.save()
        student_obj.my_feedbacks.add(new_feedback)
        print("Eka hyväksytty palautus opiskelijalle:", student_obj.email)

    return True


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
            if sub in debug_feedbacks:
                LOGGER.debug(f"TÄLLÄ PITI OLLA JO GRADER: {sub} {sub.grader}")
            grader = choose_grader(exercise, graders)
            grader.feedback_set.add(sub)

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
            style = None

            if file["filename"].endswith(".py"):
                resp.encoding = "utf-8"
                code = resp.text
                lines = code.rstrip("\n").split("\n")
                lines = [line + "\n" for line in lines]
                style_checker = pep8.Checker(lines=lines, show_source=True)

                # check_all -metodi printtaa tulokset stdouttiin,
                # joten luodaan bufferi, johon saadaan tulokset talteen
                buffer = io.StringIO()
                sys.stdout = buffer

                style_checker.check_all()

                # Palautetaan alkuperäinen stdout ja
                # haetaan tarkastuksen tulokset bufferista
                sys.stdout = sys.__stdout__
                style = buffer.getvalue()

            else:
                text = "Lataa tiedosto oheisesta linkistä."

            sub_data.append(
                {
                    "title": None,
                    "url": file["url"],
                    "text": text,
                    "code": code,
                    "style": style
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


def create_json(feedbacks):
    """
    HUOM! Tämä on väliaikainen purkkaliima. 
    
    Nyt kaikkiin palautteisiin menee arvostelijaksi aps.
    
    Rästiprojekteja ajatellen ei voida laittaa useita opiskelijoita samaan 
    arvosteluobjektiin, koska ryhmän jäsenet saattavat saada eri pisteet.
    """

    otsikko = "TIE-02101 OHJELMOINTI 1: JOHDANTO / ASKELMITTARI\n"
    selite = "Arvostelua koskevat mahdolliset tiedustelut voit lähettää " \
             "työsi tarkastajalle.\nHUOM! Muista sisällyttää viestisi " \
             "otsikkoon myös opiskelijanumerosi!\n"

    object_list = []

    for feedback in feedbacks:
        students = []

        for student in feedback.students.all():
            students.append(student.email)

        penalty = int(feedback.staff_grade * feedback.penalty)
        points = feedback.auto_grade + feedback.staff_grade - penalty

        header = f"{otsikko}\n{selite}\nTARKASTAJA: {feedback.grader}\n\n"
        auto_grade = f"Automaatin pisteet: {feedback.auto_grade}\n"
        staff_grade = f"Tarkastajan pisteet: {feedback.staff_grade}\n"
        sakko = f"Myöhästymissakko tarkastajan pisteistä: -{penalty}\n"
        yht = f"Pisteet yhteensä: {points}\n\n"
        grade = f"{auto_grade}{staff_grade}{sakko}{yht}"

        obj = {
            "students_by_email": students,
            "feedback": f"<pre>{header}{grade}{feedback.feedback}</pre>",
            "grader": 191,
            "exercise_id": feedback.exercise.exercise_id,
            "submission_time": f"{datetime.datetime.now()}",
            "points": points  # TODO: pyöristys?
        }

        object_list.append(obj)

    objects = {"objects": object_list}
    return json.dumps(objects, indent=2)
