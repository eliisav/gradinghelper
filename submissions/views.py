from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin


from .models import Feedback, Exercise, Course
from .forms import ExerciseForm
from .utils import *


def kirjautumistesti(request):
    if request.user.is_authenticated:
        print("Kirjautunut käyttäjä:", request.user.email)
    else:
        print("Ei ketään!")


class IndexView(LoginRequiredMixin, generic.TemplateView):
    """
    HUOM! Tämä sivu on aika turha tällä hetkellä.
    """
    template_name = "submissions/index.html"


class GradingListView(LoginRequiredMixin, generic.ListView):
    """
    Listataan kaikki tarkastettavat tehtävät kurssista riippumatta.
    HUOM! Tätä ei varmaan tarvita mihinkään.
    """
    model = Exercise
    template_name = "submissions/grading.html"
    context_object_name = "exercises"

    def get_queryset(self):
        return Exercise.objects.all().filter(trace=True) 


class CourseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa kaikki kurssit, joihin käyttäjä on liitetty.
    return: Lista käyttäjän kursseista.
    """
    model = Course
    template_name = "submissions/courses.html"
    context_object_name = "courses"
    
    def get(self, request):
        if request.user.is_staff:
            self.object_list = self.get_queryset()
        else:
            self.object_list = request.user.my_courses.all()
        kirjautumistesti(request)
        #print(self.object_list)
        return self.render_to_response(self.get_context_data())
        
        
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
    Listaa yhden tehtävän viimeisimmät/parhaat palautukset, staffille kaikki ja 
    assareille vain heille osoitetut tehtävät.
    TODO: mieti, miten työt saadaan jaettua assareille tarvittaessa manuaalisesti.
    TODO: Arvosteltujen palautusten huomiotta jättäminen. Tämä toimii ehkä jo, 
          silloin jos arvostelu on tehty alusta lähtien tämän palvelun kautta.

    """
    template_name = "submissions/submissions.html"
    context_object_name = "submissions"
    model = Feedback
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exercise_id"] = self.kwargs["exercise_id"]
        return context
    
    def get(self, request, exercise_id):
    
        kirjautumistesti(request)
    
        exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
        update_submissions(exercise)
        
        if request.user.is_staff:
            self.object_list = self.get_queryset().filter(exercise=exercise)
        else:
            self.object_list = request.user.feedback_set.filter(exercise=exercise)
        
        return self.render_to_response(self.get_context_data())


class FeedbackView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Näyttää yhden palautuksen koodin ja lomakkeen palautetta varten.
    """
    model = Feedback
    slug_field = "sub_id"
    slug_url_kwarg = "sub_id"
    fields = ["points", "feedback"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feedback = context["object"]
        
        if feedback.sub_url != "" and not "git" in feedback.sub_url:
            resp = requests.get(feedback.sub_url, headers=AUTH)
            resp.encoding = "utf-8"
            context["sub_code"] = resp.text

        return context
        
    def get_success_url(self):
        exercise_id = self.kwargs["exercise_id"]
        return reverse("submissions:submissions", args=(exercise_id,))
    
    def post(self, request, *args, **kwargs):
        feedback = self.get_object()
        feedback.done = True
        feedback.save()
        return super().post(request, *args, **kwargs)
        
        
def release(request, exercise_id):
    exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
    feedbacks = Exercise.objects.get(exercise_id=exercise_id).feedback_set.filter(grader=request.user, done=True, released=False)
    
    if create_json(feedbacks):
        messages.success(request, "Palautteet julkaistu!")
    else:
        messages.info(request, "Julkaistavia palautteita ei löytynyt.")
        
    
    return HttpResponseRedirect(reverse("submissions:submissions", 
                                        kwargs={ "exercise_id": exercise_id }))
    





















        

