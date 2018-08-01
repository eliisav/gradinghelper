from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin


from .models import Feedback, Exercise, Course
from .forms import FeedbackForm, ExerciseForm
from .utils import *


#COURSE = 31      # summer en 34, summer fi 31
#EXERCISE = 5113  # melumittaus en 5302, fi 5113


def kirjautumistesti(request):
    if request.user.is_authenticated:
        print("Kirjautunut käyttäjä:", request.user.email)
    else:
        print("Ei ketään!")


class IndexView(LoginRequiredMixin, generic.TemplateView):
    template_name = "submissions/index.html"


class CourseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa kaikki kurssit, jotka rajapinnasta on saatavilla.
    return: Lista kaikista kursseista
    """
    model = Course
    template_name = "submissions/courses.html"
    context_object_name = "courses"
    
    def get(self, request):
        self.object_list = request.user.my_courses.all()
        kirjautumistesti(request)
        print(self.object_list)
        return self.render_to_response(self.get_context_data())
        

class GradingListView(LoginRequiredMixin, generic.ListView):
    """
    Listataan kaikki tarkastettavat tehtävät (toistaiseksi kurssista riippumatta).
    """
    model = Exercise
    template_name = "submissions/grading.html"
    context_object_name = "exercises"

    def get_queryset(self):
        return Exercise.objects.all().filter(trace=True)

    

class ExerciseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa yhden kurssin kaikki tehtävät
    """
    model = Exercise
    template_name = "submissions/exercises.html"
    context_object_name = "exercises"
    
    def get(self, request, course_id):
        kirjautumistesti(request)
    
        course = get_object_or_404(Course, course_id=course_id)
        queryset = self.get_queryset().filter(course=course)
        self.object_list = queryset.filter(trace=False)
        tracing = queryset.filter(trace=True)
        
        for exercise in self.object_list:
            print("Luodaan lomake tehtävälle:", exercise)
            exercise.form = ExerciseForm(instance=exercise)
        
        context = self.get_context_data()
        context["tracing"] = tracing
        context["course_id"] = course_id
        
        print("Renderöidään html...")
        return self.render_to_response(context)


"""        
    
        exercises = cache.get(course_id)
        if not exercises:
            exercises = get_exercises(course_id)
            cache.set(course_id, exercises)
        
"""
        
        
"""
class ExerciseCreate(generic.edit.CreateView):
    model = Exercise
    fields = ["min_points", "max_points", "deadline"]
    success_url = reverse_lazy("submissions:exercises")
    

    # MITEN TÄN SAA TOIMIMAAN?!
    def get(self, request, course_id, exercise_id):
        return super().get(request)
"""    


def update_exercise_view(request, course_id):
    """
    Lisätään/päivitetään kurssin tehtävät tietokantaan.
    """
    
    # TODO: Kirjautuminen pitäisi vaatia myös tähän???
    # TODO: Pitäisikö tämän olla RedirectView???
    kirjautumistesti(request)
    
    course = get_object_or_404(Course, course_id=course_id)
    get_exercises(course)
    
    return HttpResponseRedirect(reverse("submissions:exercises", 
                                        kwargs={ "course_id": course_id }))
                                        

def enable_exercise_trace(request, course_id, exercise_id):
    """
    Lisätään tehtävä tarkastukseen.
    """
    
    # TODO: Kirjautuminen pitäisi vaatia myös tähän???
    # TODO: Pitäisikö tämän olla RedirectView???
    kirjautumistesti(request)
    
    if request.method == "POST":
        exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
        filled_form = ExerciseForm(request.POST, instance=exercise)
        
        if filled_form.is_valid():
            exercise.trace = True
            exercise.save()
            filled_form.save()
            messages.success(request, "Tehtävän lisääminen onnistui.")
            
        else:
            messages.error(request, "Virheellinen lomakekenttä.")
    
    #print("Tehtävä lisätty, palataan listaukseen...")    
    return HttpResponseRedirect(reverse("submissions:exercises", 
                                        kwargs={ "course_id": course_id }))


class SubmissionsView(LoginRequiredMixin, generic.ListView):
    """
    Listaa yhden tehtävän viimeisimmät/parhaat palautukset.
    """
    template_name = "submissions/submissions.html"
    context_object_name = "submissions"
    
    def get(self, request, course_id, exercise_id):
    
        kirjautumistesti(request)
    
        exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
        subsdata = get_submissions(exercise_id)
        
        for sub in subsdata:
        
            print(sub)
        
            try:
                feedback = exercise.feedback_set.get(sub_id=sub["SubmissionID"])
                
            except Feedback.DoesNotExist:
                # Laitetaan talteen palautukset, jotka ovat läpäisseet testit
                #if sub["Grade"] >= exercise.min_points:
                
                
                if "ohjelma.py" in sub:
                    sub_url = sub["ohjelma.py"]
                elif "git" in sub:
                    sub_url = sub["git"]
                else:
                    sub_url = None
                    
                if sub_url is not None:
                    exercise.feedback_set.create(sub_id=sub["SubmissionID"], 
                                                     sub_url=sub_url,
                                                     submitter=sub["Email"])
                    exercise.save()
            
                
        self.object_list = exercise.feedback_set.all()
        
        return self.render_to_response(self.get_context_data())


def get_feedback(request, course_id, exercise_id, sub_id):
    """
    Näyttää yhden palautuksen koodin ja lomakkeen palautetta varten.
    """
    
    # TODO: kirjautuminen pitäisi vaatia myös tähän näkymään.
    # TODO: pitäisikö tästäkin tehdä jokin CBV???
    kirjautumistesti(request)
    
    if request.method == "POST":
        feedback = get_object_or_404(Feedback, sub_id=sub_id)
        feedback.done = True
        filled_form = FeedbackForm(request.POST, instance=feedback)
        filled_form.save()
        return HttpResponseRedirect(reverse("submissions:submissions", 
                                            args=(course_id, exercise_id)))
        
    else:
        feedback = get_object_or_404(Feedback, sub_id=sub_id)
        
        print(feedback.sub_url)
        
        sub_code = ""
        
        if not "git" in feedback.sub_url:
            resp = requests.get(feedback.sub_url, headers=AUTH)
            resp.encoding = "utf-8"
            sub_code = resp.text
            
        form = FeedbackForm(instance=feedback)

        return render(request, "submissions/feedback.html", {"sub_url": feedback.sub_url,
                                                             "sub_code": sub_code,
                                                             "form": form,
                                                             "sub_id": sub_id,
                                                             "exercise": exercise_id,
                                                             "course_id": course_id})


