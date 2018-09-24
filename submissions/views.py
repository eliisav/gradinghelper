from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic

from .forms import *
from .utils import *


class CourseExerciseMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "course_id" in self.kwargs:
            context["course"] = get_object_or_404(
                Course, course_id=self.kwargs["course_id"]
            )
        elif "exercise_id" in self.kwargs:
            exercise = get_object_or_404(
                Exercise, exercise_id=self.kwargs["exercise_id"]
            )
            context["exercise"] = exercise
            context["course"] = exercise.course
            context["feedback_count"] = len(exercise.feedback_set.all())
            context["ready_count"] = len(exercise.feedback_set.filter(
                status=Feedback.READY
            ))

        return context


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
        
        
class ExerciseListView(CourseExerciseMixin, LoginRequiredMixin,
                       generic.ListView):
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

        context = self.get_context_data()
        
        if course.is_teacher(request.user):
            context["user_is_teacher"] = True
            context["form"] = ExerciseSetGradingForm(course=course)
            for exercise in self.object_list:
                exercise.form = ExerciseUpdateForm(instance=exercise,
                                                   course=course)

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


class UpdateSubmissionsRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään/päivitetään tehtävän palautukset tietokantaan.
    """
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise,
            exercise_id=kwargs["exercise_id"]
        )
        update_submissions(exercise)
        messages.success(request, "Palautukset päivitetty.")

        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        url = self.request.META.get("HTTP_REFERER", "")
        print(url)
        return url


class EnableExerciseGradingRedirectView(LoginRequiredMixin,
                                        generic.RedirectView):
    """
    Lisätään tehtävä tarkastukseen.
    """
    pattern_name = "submissions:exercises"
    
    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=request.POST["name"])
        form = ExerciseSetGradingForm(request.POST, request.FILES, instance=exercise)

        if form.is_valid():
            exercise = form.save(commit=False)
            if check_filetype(exercise.feedback_base):
                exercise.in_grading = True
                exercise.save(update_fields=["min_points", "consent_exercise",
                                             "work_div", "feedback_base",
                                             "in_grading"])
                messages.success(request, "Tehtävän lisääminen onnistui.")
            else:
                messages.error(request, "Ladatun tiedoston pääte ei ollut "
                                        ".txt tai tiedosto on liian suuri.")

        else:
            messages.error(request, "Virheellinen lomake!")
            
        return self.get(request, *args, **kwargs)
        

class UpdateExerciseInGradingView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Käsittelee lomakkeen, jolla muutetaan arvosteltavan tehtävän asetuksia.
    Huom. get-metodi ei renderöi lomaketta, vaan se tapahtuu luokassa 
    ExerciseListView. Get-metodi käsittelee tehtävän poistamisen 
    tarkastuslistalta. (Onko vastoin hyvää tyyliä?) Post-metodi käsittelee 
    lomakkeen lomakkeen normaalisti ilman ylimääräisiä kikkailuja
    """
    model = Exercise
    slug_field = "exercise_id"
    slug_url_kwarg = "exercise_id"
    form_class = ExerciseUpdateForm

    def form_valid(self, form):
        messages.success(self.request, "Muutokset tallennettu.")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.consent_exercise = None
        self.object.feedback_base.delete()
        self.object.feedback_set.all().delete()
        self.object.in_grading = False
        self.object.save()
        messages.success(request, "Tehtävä poistettu tarkastuslistalta.")

        return HttpResponseRedirect(self.get_success_url())


class GradingListView(CourseExerciseMixin, LoginRequiredMixin,
                      generic.ListView):
    """
    Listaa käyttäjälle hänen arvostelulistallaan olevat palautukset 
    sekä ne palautukset, joilla ei vielä ole lainkaan arvostelijaa. 
    Jos tehtävään on valittu automaattinen tasajako, kaikilla palautuksilla 
    pitäisi aina olla joku arvostelija.
    """
    template_name = "submissions/gradinglist.html"
    context_object_name = "gradinglist"
    model = Feedback
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        SetGraderFormset = modelformset_factory(Feedback, form=SetGraderMeForm,
                                                extra=0)
        no_grader_set = self.get_queryset().filter(
            exercise=context["exercise"]).filter(grader=None)
        context["formset"] = SetGraderFormset(queryset=no_grader_set)

        context["my_ready_count"] = len(
            self.object_list.filter(status=Feedback.READY)
        )
        context["my_feedback_count"] = len(self.object_list)
        
        return context
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        # update_submissions(exercise)
        self.object_list = self.get_queryset().filter(
            exercise=exercise).filter(grader=request.user)
        return self.render_to_response(self.get_context_data())


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


class SubmissionsFormView(CourseExerciseMixin, LoginRequiredMixin,
                          generic.FormView):
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

    def get_form_kwargs(self):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=self.kwargs["exercise_id"])
        # Päivitetään palautukset rajapinnasta, tämä on huono paikka,
        # homma hidasta.
        # update_submissions(exercise)
        kwargs = super().get_form_kwargs()
        kwargs["queryset"] = exercise.feedback_set.all()
        return kwargs
    
    def get_success_url(self):
        exercise_id = self.kwargs["exercise_id"]
        return reverse_lazy("submissions:submissions", args=(exercise_id,))


class FeedbackView(CourseExerciseMixin, LoginRequiredMixin,
                   generic.edit.UpdateView):
    """
    Näyttää yhden palautuksen koodin/urlin/kysymykset/vastauksekset ja 
    lomakkeen palautetta varten.
    """
    model = Feedback
    slug_field = "sub_id"
    slug_url_kwarg = "sub_id"
    form_class = FeedbackForm
    initial = {
        "status": Feedback.READY
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Haetaan palautuksen koodi/url/tekstimuotoinen vastaus jne.
        context["sub_data"] = get_submission_data(self.object)

        # Näkymään pääsee kahden eri sivun kautta, joten murupolkua
        # varten lisätään kontekstiin tieto siitä mistä tultiin.
        context["referer"] = "submissions/gradinglist.html"

        if "HTTP_REFERER" in self.request.META and self.request.META[
                "HTTP_REFERER"].endswith("update/"):
            context["referer"] = "submissions/submissions_form.html"

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
