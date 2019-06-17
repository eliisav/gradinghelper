"""
Module comment here
"""

import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
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
    Lists the exercises which have been set for grading.
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

        # There are two tabs in the template and this
        # information tells which one to show.
        if "show_set_grading" in request.session:
            show_set_grading = request.session["show_set_grading"]
            request.session["show_set_grading"] = False
        else:
            show_set_grading = False

        context = self.get_context_data(
            user=request.user,
            course=course,
            show_set_grading=show_set_grading
        )

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not kwargs["course"].is_teacher(kwargs["user"]):
            context["show_set_grading"] = False

        else:
            context["user_is_teacher"] = True
            context["form"] = ExerciseSetGradingForm(course=kwargs["course"])

            for exercise in self.object_list:
                exercise.form = ExerciseUpdateForm(instance=exercise,
                                                   course=kwargs["course"])

            # If user is teacher and exercise list is empty
            # the ExerciseSetGradinForm will be viewed.
            if self.object_list.count() == 0:
                context["show_set_grading"] = True

        return context


class GetExercisesRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Retrieve exercises of the specific course from Plussa.
    """
    pattern_name = "submissions:exercises"

    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, course_id=kwargs["course_id"])

        # TODO: voiko jotain mennä pieleen, että tehtäviä ei päivitetäkään?
        # get exercises from Plussa and save them to database
        get_exercises(course)

        # Information passed to template which tab to show
        request.session["show_set_grading"] = True
        messages.success(request, "Kurssin sisältö päivitetty.")

        return self.get(request, *args, **kwargs)


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
    Handles the request to enable exercise grading with submitted settings.
    """
    pattern_name = "submissions:exercises"
    
    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=request.POST["name"])
        form = ExerciseSetGradingForm(request.POST, request.FILES,
                                      instance=exercise)

        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.in_grading = True
            form.save_m2m()

            if exercise.num_of_graders is None or \
                    exercise.num_of_graders < exercise.graders.count():
                exercise.num_of_graders = exercise.graders.count()

            exercise.save(update_fields=["min_points", "max_points",
                                         "add_penalty", "add_auto_grade",
                                         "work_div", "num_of_graders",
                                         "feedback_base", "in_grading"])

            messages.success(request, "Tehtävän lisääminen onnistui.")

        else:
            message = "Virheellinen kenttä."

            if "file_error" in form.errors:
                message = form.errors["file_error"]

            messages.error(self.request, f"{message} Muutoksia ei tallennettu.")

            # Information passed to template which tab to show
            request.session["show_set_grading"] = True

        return self.get(request, *args, **kwargs)
        

class UpdateExerciseInGradingView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Handle the request to update exercise grading settings.
    """
    model = Exercise
    slug_field = "exercise_id"
    slug_url_kwarg = "exercise_id"
    form_class = ExerciseUpdateForm

    def form_valid(self, form):
        self.object = form.save()

        if self.object.num_of_graders is None or \
                self.object.num_of_graders < self.object.graders.count():
            self.object.num_of_graders = self.object.graders.count()
            self.object.save()

        self.object.feedback_set.filter(
            status=Feedback.BASE,
            auto_grade__lt=self.object.min_points
        ).delete()

        if self.object.max_points is not None:
            self.object.feedback_set.filter(
                status=Feedback.BASE,
                auto_grade__gt=self.object.max_points
            ).delete()

        # Update feedback base if it exists. Update is done only
        # if Feedback object's status is Feedback.BASE
        if self.object.feedback_base:
            for feedback in self.object.feedback_set.all():
                add_feedback_base(self.object, feedback)

        messages.success(self.request, "Muutokset tallennettu.")
        return super().form_valid(form)

    def form_invalid(self, form):
        message = "Virheellinen kenttä."

        if "file_error" in form.errors:
            message = form.errors["file_error"]

        messages.error(self.request, f"{message} Muutoksia ei tallennettu.")

        return HttpResponseRedirect(self.object.get_absolute_url())


class DisableExerciseGradingRedirectView(LoginRequiredMixin,
                                         generic.RedirectView):
    """
    Handles the request to remove the exercise from grading list.
    """
    pattern_name = "submissions:exercises"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(
            Exercise,
            exercise_id=kwargs.pop("exercise_id")
        )
        exercise.set_defaults()
        exercise.feedback_base.delete()
        exercise.feedback_set.all().delete()
        exercise.save()
        messages.success(request, "Tehtävä poistettu tarkastuslistalta.")

        return self.get(request, *args, **kwargs)


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
        inspect_url, sub_data, grading_data = get_submission_data(self.object)
        context["inspect_url"] = inspect_url
        context["sub_data"] = sub_data
        context["grading_data"] = grading_data

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

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)

        except Http404:
            # Feecback object doesn't exist anymore if student(s) have made
            # a new submission. This is possible in rare cases.
            # TODO: Tässä voisi yrittää etsiä mahdollista uudempaa
            # palautusta ja näyttää suoraan se

            students = []

            for student in request.POST.getlist("students"):
                students.append(str(Student.objects.get(pk=student)))

            return render(
                request, "submissions/feedback_404.html",
                {
                    "text": request.POST["feedback"],
                    "students": students,
                    "exercise_id": kwargs["exercise_id"]
                }
            )


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
    # TODO: näytä errorviestissä mistä palautuksesta error tuli
    # TODO: pitää tehdä koko julkaisujuttu kokonaan toisella tavalla
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
        url = f"{api_root}exercises/{exercise.exercise_id}/submissions/"
        
        if feedbacks:
            for i in range(0, len(feedbacks)):
                json_object = create_json_to_post(feedbacks[i])

                try:
                    LOGGER.debug(f"POST {i}")
                    resp = requests.post(url, json=json_object, headers=AUTH)
                except Exception as e:
                    LOGGER.debug(e)
                    messages.error(
                        request,
                        f"{e}\nJulkaistiin {i} VALMIS-tilassa ollutta "
                        f"palautetta.\nJulkaisematta jäi "
                        f"{feedbacks.count()-i} palautetta."
                    )
                    break

                if resp.status_code == 201:
                    LOGGER.debug(f"Onnistui, tallennetaan {i}")
                    feedbacks[i].released = True
                    feedbacks[i].save()
                else:
                    messages.error(
                        request,
                        f"{resp.status_code} {resp.text}\n"
                        f"Julkaistiin {i} VALMIS-tilassa ollutta "
                        f"palautetta.\nJulkaisematta jäi "
                        f"{feedbacks.count()-i} palautetta."
                    )
                    break
            else:
                messages.success(request,
                                 f"Julkaistiin {feedbacks.count()} "
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


class DownloadCsvView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise,
                                     exercise_id=kwargs["exercise_id"])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="grading.csv"'

        header = ["SubmissionID", "StudentID", "StudentEmail",
                   "FeedbackStatus", "GraderEmail", "GraderPoints"]

        writer = csv.writer(response)
        writer.writerow(header)

        for feedback in exercise.feedback_set.all():
            status = Feedback.STATUS_CHOICES[feedback.status][1]

            for student in feedback.students.all():
                writer.writerow([feedback.sub_id, student.student_id,
                                 student.email, status, feedback.grader,
                                 feedback.staff_grade])

        return response
