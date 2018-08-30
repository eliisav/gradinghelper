from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.forms import modelformset_factory

# from django.core.cache import cache
# from django.http import HttpResponseRedirect

from .forms import ExerciseForm, ChangeGraderForm, SetGraderMeForm
from .utils import *


class IndexView(LoginRequiredMixin, generic.RedirectView):
    """
    Aplikaation juuriosoite, uudelleenohjaa kurssilistaukseen.
    """
    pattern_name = "submissions:courses"


class CourseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa kaikki kurssit, joihin käyttäjä on liitetty.
    return: Lista käyttäjän kursseista.
    """
    model = Course
    template_name = "submissions/courses.html"
    context_object_name = "courses"
    
    def get(self, request, *args, **kwargs):
       
        self.object_list = Course.objects.filter(
            Q(assistants=request.user) | Q(teachers=request.user)).distinct()

        return self.render_to_response(self.get_context_data())
        
        
class ExerciseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa yhden kurssin kaikki tehtävät
    """
    model = Exercise
    template_name = "submissions/exercises.html"
    context_object_name = "exercises_in_grading"
    
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])
        queryset = self.get_queryset().filter(course=course)
        
        self.object_list = queryset.filter(trace=True)
        
        context = self.get_context_data()
        context["course_id"] = kwargs["course_id"]
        
        if course.is_teacher(request.user):
            context["user_is_teacher"] = True
            other_exercises = queryset.filter(trace=False)
        
            for exercise in other_exercises:
                print("Luodaan lomake tehtävälle:", exercise)
                exercise.form = ExerciseForm(instance=exercise)
                
            context["other_exercises"] = other_exercises

        print("Renderöidään html...")
        return self.render_to_response(context)


"""        
    
        exercises = cache.get(course_id)
        if not exercises:
            exercises = get_exercises(course_id)
            cache.set(course_id, exercises)
        
"""


class UpdateExerciseListRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään/päivitetään kurssin tehtävät tietokantaan.
    """
    pattern_name = "submissions:exercises"
    
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])
        get_exercises(course)
        messages.success(request, "Kurssin sisältö päivitetty.")
            
        return super().get(request, *args, **kwargs)
                                        

class EnableExerciseTraceRedirectView(LoginRequiredMixin,
                                      generic.RedirectView):
    """
    Lisätään tehtävä tarkastukseen.
    """
    pattern_name = "submissions:exercises"
    
    def get_redirect_url(self, *args, **kwargs):
        del kwargs["exercise_id"]
        return super().get_redirect_url(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        filled_form = ExerciseForm(request.POST, request.FILES,
                                   instance=exercise)
        
        if filled_form.is_valid():
            # Tää on tyhmästi tehty? On olemassa joku save(commit=False)
            exercise.trace = True
            exercise.save()
            filled_form.save()
            messages.success(request, "Tehtävän lisääminen onnistui.")
            
        return self.get(request, *args, **kwargs)
        
        
class DisableExerciseTraceRedirectView(LoginRequiredMixin,
                                       generic.RedirectView):
    """
    Perutaan tehtävän tarkastus.
    """
    pattern_name = "submissions:exercises"
    
    def get_redirect_url(self, *args, **kwargs):
        del kwargs["exercise_id"]
        return super().get_redirect_url(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        exercise.trace = False
        exercise.save()
        messages.success(request, "Tehtävä poistettu tarkastuslistalta.")
            
        return super().get(request, *args, **kwargs)
        

class GradingListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa käyttäjälle hänen arvostelulistallaan olevat palautukset 
    sekä ne palautukse, joilla ei vielä ole lainkaan arvostelijaa. 
    Jos tehtävään on valittu automaattinen jako, kaikilla palautuksilla 
    pitäisi aina olla joku arvostelija.
    """
    template_name = "submissions/gradinglist.html"
    context_object_name = "gradinglist"
    model = Feedback
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exercise_id"] = self.kwargs["exercise_id"]

        SetGraderFormset = modelformset_factory(Feedback,
                                                   form=SetGraderMeForm,
                                                   extra=0)
        queryset = self.get_queryset().filter(grader=None)
        context["formset"] = SetGraderFormset(queryset=queryset)
        
        return context
    
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset().filter(grader=request.user)
        return self.render_to_response(self.get_context_data())

    def get_queryset(self):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=self.kwargs["exercise_id"])
        update_submissions(exercise)
        return Feedback.objects.filter(exercise=exercise)


class SetGraderRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään palautus käyttäjän tarkastuslistalle.
    """
    pattern_name = "submissions:grading"

    def post(self, request, *args, **kwargs):
        SetGraderFormset = modelformset_factory(Feedback, form=SetGraderMeForm)
        formset = SetGraderFormset(request.POST)

        if formset.is_valid():
            for form in formset.forms:
                if form.cleaned_data.get("check_this"):
                    feedback_obj = form.save(commit=False)
                    feedback_obj.grader = request.user
                    feedback_obj.save()

            messages.success(request, "Palautukset lisätty "
                                      "tarkastuslisatalle.")
        else:
            messages.error(request, "Virheellinen lomake!")

        return self.get(request, *args, **kwargs)


class SubmissionsFormView(LoginRequiredMixin, generic.FormView):
    """
    Lomakenäkymä, jolla palautuksen arvostelija voidaan vaihtaa/asettaa.

    """
    form_class = modelformset_factory(Feedback, form=ChangeGraderForm, extra=0)
    template_name = "submissions/submissions_form.html"
    
    def form_valid(self, form):
        for sub_form in form:
            if sub_form.has_changed():
                sub_form.save()
        messages.success(self.request, "Muutokset tallennettu.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exercise_id"] = self.kwargs["exercise_id"]
        return context
    
    def get_form_kwargs(self):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=self.kwargs["exercise_id"])
        update_submissions(exercise)
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = Feedback.objects.filter(exercise=exercise)
        return kwargs
    
    def get_success_url(self):
        exercise_id = self.kwargs["exercise_id"]
        return reverse_lazy("submissions:submissions", args=(exercise_id,))


class FeedbackView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Näyttää yhden palautuksen koodin ja lomakkeen palautetta varten.
    """
    model = Feedback
    slug_field = "sub_id"
    slug_url_kwarg = "sub_id"
    fields = ["points", "feedback", "status"]
    initial = {"status": Feedback.READY}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feedback = context["object"]
        
        if feedback.sub_url != "" and "git" not in feedback.sub_url:
            resp = requests.get(feedback.sub_url, headers=AUTH)
            resp.encoding = "utf-8"
            context["sub_code"] = resp.text

        return context
        
    def get_success_url(self):
        exercise_id = self.kwargs["exercise_id"]
        return reverse("submissions:grading", args=(exercise_id,))
          

class ReleaseFeedbacksRedirectView(LoginRequiredMixin, generic.RedirectView):
    pattern_name = "submissions:grading"
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        feedbacks = exercise.feedback_set.filter(grader=request.user,
                                                 status=Feedback.READY, 
                                                 released=False)
        
        if create_json(feedbacks):
            messages.success(request, "Palautteet julkaistu!")
        else:
            messages.info(request, "Julkaistavia palautteita ei löytynyt.")
            
        return super().get(request, *args, **kwargs)


# -----------------------------------------------------------------
# Hylättyjä funktioita, testailua, kokeiluja jne.

def kirjautumistesti(request):
    if request.user.is_authenticated:
        print("Kirjautunut käyttäjä:", request.user.email)
    else:
        print("Ei ketään!")

class GradingView(LoginRequiredMixin, generic.ListView):
    """
    Listataan kaikki tarkastettavat tehtävät kurssista riippumatta.
    HUOM! Tätä ei varmaan tarvita mihinkään.
    """
    model = Exercise
    template_name = "submissions/grading.html"
    context_object_name = "exercises"

    def get_queryset(self):
        return Exercise.objects.all().filter(trace=True) 





class SubmissionsView(LoginRequiredMixin, generic.ListView):
    """
    Listaa yhden tehtävän viimeisimmät/parhaat palautukset.
    TODO: mieti, miten työt saadaan jaettua assareille tarvittaessa 
    manuaalisesti.
    TODO: Arvosteltujen palautusten huomiotta jättäminen. Tämä toimii ehkä jo, 
          silloin jos arvostelu on tehty alusta lähtien tämän palvelun kautta.

    """
    template_name = "submissions/submissions.html"
    context_object_name = "submissions"
    model = Feedback
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exercise_id"] = self.kwargs["exercise_id"]
        
        ChangeGraderFormset = modelformset_factory(Feedback, 
                                                   form=ChangeGraderForm, 
                                                   extra=0)
        context["formset"] = ChangeGraderFormset(
            queryset=self.get_queryset().filter(
                exercise=kwargs["exercise_id"]
            )
        )
        
        return context
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        
        update_submissions(exercise)
        
        self.object_list = self.get_queryset().filter(
            exercise=exercise).filter(grader=request.user)
        
        return self.render_to_response(self.get_context_data())
