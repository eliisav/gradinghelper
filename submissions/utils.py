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

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound
from pygments.formatters.html import HtmlFormatter

from .models import Course, Exercise, Feedback, Student
from django.core.cache import cache

util_logger = logging.getLogger(__name__)
debug_feedbacks = []


def get_json(url, token):
    resp = requests.get(url, headers={"Authorization": f"Token {token}"})

    if resp.status_code == requests.codes.ok:
        return resp.json()
    else:
        resp.raise_for_status()


def add_user_to_course(user, login_info):
    """
    Add user to course. Course is created first if it doesn't exist. This
    function is called after the user has successfully logged in.
    :param user: (User) User object
    :param login_info: (dict) required fields from LTI login
    """

    try:
        course = Course.objects.get(
            course_id=login_info["custom_context_api_id"]
        )
    except Course.DoesNotExist:
        if login_info["roles"] != "Instructor":
            return False

        course = create_course(
            login_info["custom_context_api_id"],
            login_info["custom_context_api"],
            login_info["context_label"],
            login_info["context_title"],
            login_info["custom_user_api_token"]
        )

    if login_info["roles"] == "Instructor":
        course.teachers.add(user)
    if login_info["roles"] == "TA,TeachingAssistant":
        course.assistants.add(user)

    return True


def create_course(api_id, api_url, course_label, course_name, token):
    course_instance = get_json(api_url, token)["instance_name"]
    name = f"{course_label} {course_name} {course_instance}"
    course = Course(course_id=api_id, name=name,
                    api_url=api_url, api_token=token)
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

    modules = get_json(f"{course.api_url}exercises/", course.api_token)["results"]

    # cache.set(course.course_id, modules)

    # Module consists of material pages and exercises
    for sub_module in modules:
        # Loop through "exercises" list and check if an exercise really is
        # submittable exercise.
        for exercise in sub_module["exercises"]:
            try:
                details = get_json(exercise["url"], course.api_token)
            except requests.HTTPError:
                # It's not a submittable exercise if details are not found.
                continue

            # print(details)
            # Make sure that we really got a submittable exercise
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
    data_url = f"{exercise.course.api_url}submissiondata/"
    query_url = f"{data_url}?exercise_id={exercise.exercise_id}&format=json"
    return get_json(query_url, exercise.course.api_token)


def update_submissions(exercise):
    """
    submissiondata = cache.get(exercise.exercise_id)
    if submissiondata:
        return
    """

    util_logger.debug(f"{datetime.datetime.now()} updating submissions: {exercise}")

    deadline_passed = check_deadline(exercise)
    submissiondata = get_submissions(exercise)

    # print(submissiondata)

    # cache.set(exercise.exercise_id, submissiondata)

    accepted = sort_submissions(submissiondata, exercise, deadline_passed)

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

            if exercise.feedback_base:
                add_feedback_base(exercise, feedback)

            feedback.save()

        for student in accepted[sub]["students"]:
            if not add_student(student, feedback):
                break

    if exercise.work_div == Exercise.EVEN_DIV:
        divide_submissions(exercise)


def check_deadline(exercise):
    module_url = f"{exercise.course.api_url}exercises/{exercise.module_id}"

    # Get info related to exercise module and check if module is open or not
    if get_json(module_url, exercise.course.api_token)["is_open"]:
        util_logger.debug(f"{exercise} moduuli on vielä auki!")
        return False
        
    return True


def sort_submissions(submissions, exercise, deadline_passed):
    """
    Käydään läpi jsonin palautukset ja lisätään hyväksytyt accepted-dictiin. 
    Pääsääntöisesti täysin turhaa ajan tuhlausta, mutta tarvitaan jos 
    ryhmäpalautuksen ryhmä on jälkikäteen tehty henkilökunnan toimesta.
    :param submissions: (dict) tehtävän viimeisimmät/parhaat palautukset 
    :param exercise: (Exercise model object) tarkastettavan tehtävän tiedot
    :param deadline_passed: (boolean) True, jos tehtävän deadline on mennyt
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
        if sub["Grade"] < exercise.min_points:
            continue

        if exercise.max_points is not None and sub["Grade"] > exercise.max_points:
            continue

        if not deadline_passed and "ready_for_review" not in sub:
            continue

        if sub["SubmissionID"] not in accepted:
            accepted[sub["SubmissionID"]] = {
                "grade": sub["Grade"],
                "penalty": sub["Penalty"],
                "students": [
                    {
                        "email": sub["Email"],
                        "student_id": sub["StudentID"],
                        "user_id": sub["UserID"]
                    }
                ]
            }
        else:
            accepted[sub["SubmissionID"]]["students"].append(
                {
                    "email": sub["Email"],
                    "student_id": sub["StudentID"],
                    "user_id": sub["UserID"]
                }
            )

        if sub["UserID"] not in students:
            students[sub["UserID"]] = [sub["SubmissionID"]]
        else:
            # Parityösähläyksissä opiskelijalle on voinut tallentua
            # useampi kuin yksi palautus. Laitetaan tuplat talteen
            # ja poistetaan tarpeettomat palautukset seuraavassa vaiheessa.
            students[sub["UserID"]].append(sub["SubmissionID"])
            duplicates.append(sub["UserID"])

    # print(duplicates)
    # print(students)
    # print(accepted)

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
    Lisätään/päivitetään palautepohja mikäli palautetta ei ole vielä muokattu.
    :param exercise: (Exercise model object)
    :param feedback: (Feedback model object)
    """
    if feedback.status == feedback.BASE:
        try:
            feedback.feedback = exercise.feedback_base.open().read().decode(
                "utf-8"
            )
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
        #student_obj = Student.objects.get(email=student_dict["email"])
        student_obj = Student.objects.get(aplus_user_id=student_dict["user_id"])

        # Update student_id and email. Email can change and student_id
        # is sometimes given later
        student_obj.student_id = student_dict["student_id"]
        student_obj.email = student_dict["email"]

        #student_obj.aplus_user_id = student_dict["user_id"]

        student_obj.save()

        try:
            old_feedback = student_obj.my_feedbacks.get(
                exercise=new_feedback.exercise
            )
            
            if old_feedback != new_feedback:

                util_logger.debug(f"Uudempi palautus tulossa: {student_obj}")
                util_logger.debug(f"tehtävään: {new_feedback.exercise}")

                if old_feedback.status == Feedback.BASE:
                    new_feedback.grader = old_feedback.grader
                    new_feedback.save()

                    util_logger.debug(f"poistetaan vanha: {old_feedback} "
                                 f"{old_feedback.grader}")

                    old_feedback.delete()

                    util_logger.debug(f"lisätään uusi: {new_feedback} "
                                 f"{new_feedback.grader}")

                    debug_feedbacks.append(new_feedback)

                    student_obj.my_feedbacks.add(new_feedback)
                else:
                    # TODO: huomautus arvostelijalle siitä, että uudempi
                    # palautus olisi olemassa.

                    util_logger.debug(f"Arvostelu oli aloitettu, poistetaan uusi.")

                    # Uutta palautusta ei hyväksytä jos arvostelu aloitettu
                    new_feedback.delete()
                    return False

        except Feedback.DoesNotExist:
            student_obj.my_feedbacks.add(new_feedback)
            
    except Student.DoesNotExist:
        student_obj = Student(
            email=student_dict["email"],
            student_id=student_dict["student_id"],
            aplus_user_id=student_dict["user_id"]
        )
        student_obj.save()
        student_obj.my_feedbacks.add(new_feedback)
        util_logger.debug(f"Luotiin uusi opiskelija: {student_obj}")

    return True


def divide_submissions(exercise):
    """
    Jakaa palautukset kurssille merkittyjen assareiden kesken.
    param exercise: (models.Exercise) Tehtäväobjekti
    """
    if exercise.num_of_graders == 0:
        return

    graders = exercise.graders.all()
    subs = exercise.feedback_set.all()
    grader_max_now = subs.count() // exercise.num_of_graders
    no_grader = []

    for sub in subs:
        if sub.grader is None:
            if sub in debug_feedbacks:
                util_logger.debug(f"TÄLLÄ PITI OLLA JO GRADER: {sub} {sub.grader}")

            grader = choose_grader(exercise, graders, grader_max_now)

            if grader:
                grader.feedback_set.add(sub)
            elif graders.count() == exercise.num_of_graders:
                no_grader.append(sub)
            else:
                break

    for sub in no_grader:
        grader = choose_grader(exercise, graders)
        grader.feedback_set.add(sub)

    util_logger.debug(f"Arvosteltavia palautuksia: {subs.count()}")
    util_logger.debug(f"Palautusta per assari: "
                 f"{subs.count()/exercise.num_of_graders}")
    util_logger.debug("Assareilla arvostelussa:")
    for grader in graders:
        util_logger.debug(f"{grader.feedback_set.filter(exercise=exercise).count()}")


def choose_grader(exercise, graders, max_sub_count=None):
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
        if max_sub_count and grader.feedback_set.filter(
                exercise=exercise).count() >= max_sub_count:
            continue

        # Valitaan pienimmän arvostelumäärän omaavaksi ensimmäinen
        # vastaantuleva
        elif first:
            min_sub_count = grader.feedback_set.filter(
                exercise=exercise).count()
            grader_to_add = grader
            first = False

        # Jos ensimmäinen alkio on jo käsitelty,
        # tutkitaan löytyykö sitä pienempää
        elif grader.feedback_set.filter(
                exercise=exercise).count() < min_sub_count:
            min_sub_count = grader.feedback_set.filter(
                exercise=exercise).count()
            grader_to_add = grader
            
    # Tässä pitäisi ny olla se, jolla on vähiten arvosteltavaa, tai yksi
    # niistä jolla on vähiten, jos usealla yhtä vähän. Tasatilanteessa ei ole
    # väliä kuka valitaan.
    return grader_to_add


def get_submission_data(feedback):
    # TODO: Pitäisikö kuitenkin yrittää tehtävän api urli  kaivaa apista ja
    # tallentaa tietokantaan, sen sijaan että askarrelleen näin?!?!
    api_root = feedback.exercise.course.api_root
    exercise_url = f"{api_root}exercises/{feedback.exercise.exercise_id}/"
    api_token = feedback.exercise.course.api_token
    form_spec = get_json(exercise_url, api_token)["exercise_info"]["form_spec"]

    sub_url = f"{api_root}submissions/{feedback.sub_id}/"
    sub_info = get_json(sub_url, api_token)

    inspect_url = sub_info["html_url"] + "inspect"
    sub_data = []

    # Kun palautetaan git-url, "form_spec" näyttää jäävän tyhjäksi
    if len(form_spec) == 0 and sub_info["submission_data"]:
        get_git_url(sub_data, sub_info["submission_data"][0][1])

    # Jos palautus ei ole git-url, se voi olla tekstiä tai tiedosto
    # (tai monivalintatehtävän valintavaihtoehto ("option_n"), joita ei
    # yleensä arvioida käsin, joten jätetään tyyppi "radio" huomiotta).
    for field in form_spec:
        if field["type"] == "file":
            get_filecontent(sub_data, field, sub_info["files"], api_token)

        elif field["type"] == "textarea":
            get_text(sub_data, field, sub_info["submission_data"])

    return {
        "inspect_url": inspect_url,
        "sub_data": sub_data,
        "grading_data": sub_info["grading_data"]
    }


def get_git_url(sub_data, url):
    if url.startswith("git@"):
        url = url.replace(":", "/").replace("git@", "https://", 1)

    sub_data.append(
        {
            "title": None,
            "url": url,
            "text": "Siirry opiskelijan repositorioon oheisesta linkistä",
            "code": None
        }
    )


def get_filecontent(sub_data, form_field, files, token):
    """
    Etsii halutun tiedoston ja tallentaa sen tiedot listaan sanakirjamuodossa.
    :param sub_data: (list) Opiskelijan palautuksen olennaiset tiedot dicteinä.
    :param form_field: (dict) Tehtävän (yaml-tiedosto) palautuskentän tiedot.
    :param files: (dict) Palautettujen tiedostojen nimet, urlit jne.
    :return: None
    """
    for file in files:
        if file["param_name"] == form_field["key"]:
            resp = requests.get(file["url"],
                                headers={"Authorization": f"Token {token}"})
            resp.encoding = "utf-8"

            title = None
            text = None
            style = None

            try:
                lexer = get_lexer_for_filename(file["filename"])
                code = highlight(resp.text, lexer,
                                 HtmlFormatter(linenos="inline"))
            except ClassNotFound:
                code = None

            # Run PEP8 style check for Python file
            if code and file["filename"].endswith(".py"):
                lines = resp.text.rstrip("\n").split("\n")
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

            elif code is None:
                title = form_field["title"]
                text = "Lataa tiedosto oheisesta linkistä"

            sub_data.append(
                {
                    "title": title,
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
    if textareas:
        for area in textareas:
            if area[0] == form_field["key"]:

                title = form_field["title"]

                if title == "":
                    title = form_field["key"]

                sub_data.append(
                    {
                        "title": title,
                        "url": None,
                        "text": area[1],
                        "code": None
                    }
                )

                return
    else:
        sub_data.append(
            {
                "title": None,
                "url": None,
                "text": "Tekstiä ei löytynyt, tarkastele palautusta Plussassa",
                "code": None
            }
        )


def calculate_points(feedback):
    """
    Calculate a grade for a submission.
    :param feedback: (models.Feedback) database object
    :return: (int) points, (str) info
    """
    if feedback.exercise.add_penalty:
        penalty = int(feedback.staff_grade * feedback.penalty)
        penalty_info = f"Late penalty for grader points: -{penalty}\n"
    else:
        penalty = 0
        penalty_info = ""

    if feedback.exercise.add_auto_grade:
        points = feedback.auto_grade + feedback.staff_grade - penalty
        auto_grade = f"Automatic evaluation: {feedback.auto_grade}\n"
        total = f"Total points: {points}\n"
    else:
        points = feedback.staff_grade - penalty
        auto_grade = ""
        total = ""

    grader = f"Grader: {feedback.grader}\n\n"
    staff_grade = f"Grader points: {feedback.staff_grade}\n"
    info = f"{grader}{auto_grade}{staff_grade}{penalty_info}{total}\n"

    return points, info


def create_json_to_batch_assess(feedbacks):
    """
    Create a json to copy and paste to course page in Plussa
    :param feedbacks: (Queryset) Feedbacks to be released
    :return: json
    """
    object_list = []

    for feedback in feedbacks:
        students = []

        for student in feedback.students.all():
            students.append(student.email)

        points, info = calculate_points(feedback)

        obj = {
            "students_by_email": students,
            "feedback": f"<pre>{info}{feedback.feedback}</pre>",
            "exercise_id": feedback.exercise.exercise_id,
            "submission_time": f"{datetime.datetime.now()}",
            "points": points  # TODO: pyöristys?
        }

        object_list.append(obj)
        feedback.exercise.latest_release.append(feedback.sub_id)
        feedback.released = True
        feedback.save()

    objects = {"objects": object_list}
    return json.dumps(objects, indent=2)


def create_json_to_post(feedback):
    """
    Form a json object to create a new submission by POST
    :param feedback: (models.Feedback) database object
    :return: (dict) information needed to form a submission by POST
    """
    students = []

    for student in feedback.students.all():
        students.append(student.email)

    points, info = calculate_points(feedback)

    json_object = {
        "students_by_email": students,
        "feedback": f"<pre>{info}{feedback.feedback}</pre>",
        "points": points  # TODO: pyöristys?
    }

    return json_object
