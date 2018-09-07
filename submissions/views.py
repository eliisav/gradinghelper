from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.forms import modelformset_factory, Textarea


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
    context_object_name = "exercises"
    
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])
        self.object_list = self.get_queryset().filter(
            course=course).filter(in_grading=True)

        context = self.get_context_data(course_id=kwargs["course_id"])
        
        if course.is_teacher(request.user):
            context["user_is_teacher"] = True
            context["form"] = ExerciseForm(course=course)

        return self.render_to_response(context)


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


class EnableExerciseGradingRedirectView(LoginRequiredMixin,
                                        generic.RedirectView):
    """
    Lisätään tehtävä tarkastukseen.
    """
    pattern_name = "submissions:exercises"
    
    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=request.POST["name"])
        form = ExerciseForm(request.POST, request.FILES, instance=exercise)

        if form.is_valid():
            exercise = form.save(commit=False)
            if check_filetype(exercise.feedback_base):
                exercise.in_grading = True
                exercise.save(update_fields=["min_points", "consent_exercise",
                                             "auto_div", "feedback_base",
                                             "in_grading"])
                messages.success(request, "Tehtävän lisääminen onnistui.")
            else:
                messages.error(request, "Ladatun tiedoston pääte ei ollut "
                                        ".txt tai tiedosto on liian suuri.")

        else:
            messages.error(request, "Virheellinen lomake!")
            
        return self.get(request, *args, **kwargs)
        
        
class DisableExerciseGradingRedirectView(LoginRequiredMixin,
                                       generic.RedirectView):
    """
    Perutaan tehtävän tarkastus.
    """
    # TODO: nyt mitään tehtävään liittyvää ei poisteta. Pitäisikö?

    pattern_name = "submissions:exercises"
    
    def get_redirect_url(self, *args, **kwargs):
        del kwargs["exercise_id"]
        return super().get_redirect_url(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        exercise.in_grading = False
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
        exercise = kwargs.pop("exercise")
        context = super().get_context_data(**kwargs)
        context["exercise_id"] = exercise.exercise_id
        SetGraderFormset = modelformset_factory(Feedback, form=SetGraderMeForm,
                                                extra=0)
        queryset = self.get_queryset().filter(
            exercise=exercise).filter(grader=None)
        context["formset"] = SetGraderFormset(queryset=queryset)
        
        return context
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        update_submissions(exercise)
        self.object_list = self.get_queryset().filter(
            exercise=exercise).filter(grader=request.user)
        return self.render_to_response(
            self.get_context_data(exercise=exercise))


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
                                      "tarkastuslistalle.")
        else:
            messages.error(request, "Virheellinen lomake!")

        return self.get(request, *args, **kwargs)


class SubmissionsFormView(LoginRequiredMixin, generic.FormView):
    """
    Lomakenäkymä, jolla palautuksen arvostelija voidaan vaihtaa/asettaa.

    """

    # TODO: palautusten päivittäminen tähän näkymään tultaessa

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

    widgets = {

        'feedback': {Textarea(attrs={'cols': 80, 'rows': 10000})}

    }
    
    def get_context_data(self, **kwargs):
        feedback = self.object
        context = super().get_context_data(**kwargs)
        context["sub_data"] = get_submission_data(feedback)
        return context
        
    def get_success_url(self):
        exercise_id = self.object.exercise.exercise_id
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
        return Exercise.objects.all().filter(in_grading=True)

"""
class SubmissionsView(LoginRequiredMixin, generic.ListView):

    Listaa yhden tehtävän viimeisimmät/parhaat palautukset.
    TODO: mieti, miten työt saadaan jaettua assareille tarvittaessa 
    manuaalisesti.
    TODO: Arvosteltujen palautusten huomiotta jättäminen. Tämä toimii ehkä jo, 
          silloin jos arvostelu on tehty alusta lähtien tämän palvelun kautta.


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
"""
