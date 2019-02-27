from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic

from .forms import *
from .utils import *


class ExerciseMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "exercise_id" in self.kwargs:
            exercise = get_object_or_404(
                Exercise, exercise_id=self.kwargs["exercise_id"]
            )
            context["exercise"] = exercise
            context["course"] = exercise.course
            context["user_is_teacher"] = exercise.course.is_teacher(
                self.request.user
            )
            context["feedback_count"] = exercise.feedback_set.all().count()
            context["ready_count"] = exercise.feedback_set.filter(
                status=Feedback.READY
            ).count()

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
        
        
class ExerciseListView(LoginRequiredMixin, generic.ListView):
    """
    Listaa yhden kurssin kaikki tehtävät
    """
    model = Exercise
    template_name = "submissions/exercises.html"
    context_object_name = "exercises"
    
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])

        if not course.is_staff(request.user):
            raise PermissionDenied

        self.object_list = self.get_queryset().filter(
            course=course).filter(in_grading=True)
        context = self.get_context_data(user=request.user, course=course)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = kwargs["course"]

        if kwargs["course"].is_teacher(kwargs["user"]):
            context["user_is_teacher"] = True
            context["form"] = ExerciseSetGradingForm(course=kwargs["course"])

            for exercise in self.object_list:
                exercise.form = ExerciseUpdateForm(instance=exercise,
                                                   course=kwargs["course"])

        return context


class UpdateExerciseListRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään/päivitetään kurssin tehtävät tietokantaan.
    """
    pattern_name = "submissions:exercises"

    # TODO: muuttaa tietokannan tilaa, joten muuta postiksi
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])
        get_exercises(course)
        messages.success(request, "Kurssin sisältö päivitetty.")
            
        return super().get(request, *args, **kwargs)


class UpdateSubmissionsRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään/päivitetään tehtävän palautukset tietokantaan.
    """

    # TODO: muuttaa tietokannan tilaa, joten muuta postiksi
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
        return url


class EnableExerciseGradingRedirectView(LoginRequiredMixin,
                                        generic.RedirectView):
    """
    Lisätään tehtävä tarkastukseen.
    """
    pattern_name = "submissions:exercises"
    
    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=request.POST["name"])
        form = ExerciseSetGradingForm(request.POST, request.FILES,
                                      instance=exercise)

        if form.is_valid():
            exercise = form.save(commit=False)
            if check_filetype(exercise.feedback_base):
                exercise.in_grading = True

                form.save_m2m()

                if exercise.num_of_graders is None or \
                        exercise.num_of_graders < exercise.graders.all().count():
                    exercise.num_of_graders = exercise.graders.all().count()

                exercise.save(update_fields=["min_points", "max_points",
                                             "add_penalty", "add_auto_grade",
                                             "work_div", "num_of_graders",
                                             "feedback_base", "in_grading"])

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
    # TODO: palautepohjan tiedostotyypin tarkastus
    # TODO: get ei oikeastaan saisi koskaan muuttaa tietokannan tilaa
    model = Exercise
    slug_field = "exercise_id"
    slug_url_kwarg = "exercise_id"
    form_class = ExerciseUpdateForm

    def form_valid(self, form):
        self.object = form.save()

        if self.object.num_of_graders is None or \
                self.object.num_of_graders < self.object.graders.all().count():
            self.object.num_of_graders = self.object.graders.all().count()

        # Jos tehtävällä on palautepohja, niin päivitetään se
        # kaikkiin muokkaamattomiin palautteisiin
        if self.object.feedback_base:
            for feedback in self.object.feedback_set.all():
                add_feedback_base(self.object, feedback)

        messages.success(self.request, "Muutokset tallennettu.")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.set_defaults()
        self.object.feedback_base.delete()
        self.object.feedback_set.all().delete()
        self.object.save()
        messages.success(request, "Tehtävä poistettu tarkastuslistalta.")

        return HttpResponseRedirect(self.get_success_url())


class GradingListView(ExerciseMixin, LoginRequiredMixin,
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

        context["my_ready_count"] = self.object_list.filter(
            status=Feedback.READY
        ).count()

        context["my_feedback_count"] = self.object_list.count()
        context["batch_assess_form"] = BatchAssessForm()
        
        return context
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

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


class SubmissionsFormView(ExerciseMixin, LoginRequiredMixin,
                          generic.FormView):
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

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        if not context["course"].is_staff(request.user):
            raise PermissionDenied

        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self):
        # Päivitetään palautukset rajapinnasta, tämä on huono paikka,
        # homma hidasta.
        # update_submissions(exercise)

        kwargs = super().get_form_kwargs()
        exercise = get_object_or_404(Exercise,
                                     exercise_id=self.kwargs["exercise_id"])
        kwargs["queryset"] = exercise.feedback_set.all()
        return kwargs
    
    def get_success_url(self):
        exercise_id = self.kwargs["exercise_id"]
        return reverse_lazy("submissions:submissions", args=(exercise_id,))


class FeedbackView(ExerciseMixin, LoginRequiredMixin,
                   generic.edit.UpdateView):
    """
    Näyttää yhden palautuksen koodin/urlin/kysymykset/vastaukset ja
    lomakkeen palautetta varten.
    """
    model = Feedback
    slug_field = "sub_id"
    slug_url_kwarg = "sub_id"
    form_class = FeedbackForm
    initial = {
        "status": Feedback.READY
    }

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.exercise.course.is_staff(request.user):
            raise PermissionDenied

        if request.user != self.object.grader:
            messages.warning(request, "Palautus ei ole omalla työlistallasi!")

        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the information about the submission and add it to the context.
        inspect_url, sub_data = get_submission_data(self.object)
        context["inspect_url"] = inspect_url
        context["sub_data"] = sub_data

        # Näkymään pääsee kahden eri sivun kautta, joten murupolkua
        # varten lisätään kontekstiin tieto siitä mistä tultiin.
        context["referer_template"] = "submissions/gradinglist.html"
        context["referer_url"] = "submissions:grading"

        if "HTTP_REFERER" in self.request.META and self.request.META[
                "HTTP_REFERER"].endswith("all/"):
            context["referer_template"] = "submissions/submissions_form.html"
            context["referer_url"] = "submissions:submissions"

        return context

    def get_success_url(self):
        exercise_id = self.object.exercise.exercise_id
        return reverse("submissions:grading", args=(exercise_id,))

    """
    def post(self, request, *args, **kwargs):
        try:
            pass
            # return super().post(request, *args, **kwargs)
        except Http404:

            # TODO: Tässä pitäisi etsiä opiskelija ja mahd. myös hänen
            # uudempi palautuksensa, johon palauutten voisi kopioida.
            print()
            for students in request.POST["students"]:
                for student in students:
                    print(student)

            return render(
                request, "submissions/404.html",
                {
                    "text": request.POST["feedback"]
                }
            )
    """


class BatchAssessRedirectView(LoginRequiredMixin, generic.RedirectView):
    pattern_name = "submissions:grading"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        form = BatchAssessForm(request.POST)

        if form.is_valid():
            points = form.cleaned_data["points"]
            feedback_text = form.cleaned_data["feedback"]

            feedbacks = exercise.feedback_set.filter(grader=request.user,
                                                     status=Feedback.BASE,
                                                     released=False
                                                     )
            if feedbacks:
                for feedback in feedbacks:
                    feedback.staff_grade = points
                    feedback.feedback = feedback_text
                    feedback.status = Feedback.READY
                    feedback.save()

                messages.success(
                    request,
                    f"Joukkoarvosteltiin {feedbacks.count()} palautusta "
                    f"pistemäärällä {points}."
                )
            else:
                messages.info(request, "Arvosteltavia palautuksia ei löytynyt.")

        else:
            messages.error(request, "Virheellinen lomake.")

        return self.get(request, *args, **kwargs)


class ReleaseFeedbacksRedirectView(LoginRequiredMixin, generic.RedirectView):
    pattern_name = "submissions:grading"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        feedbacks = exercise.feedback_set.filter(grader=request.user,
                                                 status=Feedback.READY,
                                                 released=False)
        api_root = exercise.course.api_root
        url = f"{api_root}/exercises/{exercise.exercise_id}/submissions/"
        
        if feedbacks:
            i = 0
            while i < len(feedbacks):
                json_object = create_json_to_post(feedbacks[i])

                try:
                    LOGGER.debug(f"POST {i}")
                    resp = requests.post(url, json=json_object, headers=AUTH)
                except Exception as e:
                    LOGGER.debug(e)
                    continue

                if resp.status_code == 201:
                    LOGGER.debug(f"Onnistui, tallennetaan {i}")
                    feedbacks[i].released = True
                    feedbacks[i].save()
                    i += 1
                else:
                    messages.error(request, f"{resp.status_code} {resp.text}")
                    break

            messages.success(request, f"Julkaistiin {feedbacks.count()} "
                                      f"VALMIS-tilassa ollutta palautetta.")
        else:
            messages.info(request, "Julkaistavia palautteita ei löytynyt.")
            
        return self.get(request, *args, **kwargs)


class CreateJsonFromFeedbacksView(LoginRequiredMixin, generic.TemplateView):
    template_name = "submissions/json.html"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])
        feedbacks = exercise.feedback_set.filter(status=Feedback.READY,
                                                 released=False)
        context = super().get_context_data()

        if feedbacks:
            exercise.latest_release.clear()
            context["json"] = create_json_to_batch_assess(feedbacks)
            exercise.save()
        else:
            context["json"] = "JULKAISTAVIA PALAUTTEITA EI LÖYTYNYT!"

        return self.render_to_response(context)


class UndoLatestReleaseRedirectView(LoginRequiredMixin, generic.RedirectView):
    pattern_name = "submissions:submissions"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        for sub_id in exercise.latest_release:
            feedback = get_object_or_404(Feedback, sub_id=sub_id)
            feedback.released = False
            feedback.save()

        messages.success(request, "Julkaisu peruutettu.")

        return self.get(request, *args, **kwargs)


# -----------------------------------------------------------------
# Hylättyjä funktioita, testailua, kokeiluja jne.

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
