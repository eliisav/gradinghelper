"""
Module comment here
"""

import csv
import logging
import requests

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views import generic

from .models import Course, Exercise, Feedback, Student
import submissions.forms as forms
import submissions.utils as utils


view_logger = logging.getLogger(__name__)


class ExerciseMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "exercise_id" in self.kwargs:
            exercise = get_object_or_404(Exercise, pk=self.kwargs["pk"])
            context["exercise"] = exercise
            context["course"] = exercise.course
            context["user_is_teacher"] = exercise.course.is_teacher(
                self.request.user
            )
            context["feedback_count"] = exercise.feedback_set.all().count()
            context["ready_count"] = exercise.feedback_set.filter(
                status=Feedback.READY
            ).count()
            context["grader_lang_en"] = exercise.feedback_set.filter(
                grader_lang_en=True
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

        #TODO: Show all courses if user is superuser
        self.object_list = Course.objects.filter(
            Q(
                base_course__assistants=request.user
            ) | Q(
                base_course__teachers=request.user
            )
        ).distinct()

        return self.render_to_response(self.get_context_data())
        
        
class ExerciseListView(LoginRequiredMixin, generic.ListView):
    """
    Lists the exercises which have been set for grading.
    """
    model = Exercise
    template_name = "submissions/exercises.html"
    context_object_name = "exercises"
    
    def get(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs["pk"])

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
            context["form"] = forms.ExerciseSetGradingForm(
                course=kwargs["course"]
            )
            context["error_handler"] = forms.ErrorHandlerForm()

            for exercise in self.object_list:
                exercise.form = forms.ExerciseUpdateForm(
                    instance=exercise, course=kwargs["course"]
                )

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
        course = get_object_or_404(Course, pk=kwargs["pk"])

        # TODO: voiko jotain mennä pieleen, että tehtäviä ei päivitetäkään?
        # get exercises from Plussa and save them to database
        utils.get_exercises(course)

        # Information passed to template which tab to show
        request.session["show_set_grading"] = True
        messages.success(request, "Course content updated")

        return self.get(request, *args, **kwargs)


class UpdateSubmissionsRedirectView(LoginRequiredMixin, generic.RedirectView):
    """
    Lisätään/päivitetään tehtävän palautukset tietokantaan.
    """

    # TODO: muuttaa tietokannan tilaa, joten muuta postiksi
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])
        try:
            utils.update_submissions(exercise)
            messages.success(request, "Submissions updated")
        except requests.HTTPError as e:
            messages.error(request, f"Failed to retrieve submissions: {e}")

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
        form = forms.ExerciseSetGradingForm(request.POST, request.FILES,
                                            instance=exercise)

        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.in_grading = True
            form.save_m2m()
            graders_all = \
                exercise.graders.count() + exercise.graders_en.count()

            if exercise.num_of_graders is None or \
                    exercise.num_of_graders < graders_all:
                exercise.num_of_graders = graders_all

            exercise.total_max_points = utils.get_json(
                exercise.api_url, exercise.course.api_token
            )["max_points"]

            exercise.save(update_fields=["min_points", "max_points",
                                         "total_max_points", "add_penalty",
                                         "add_auto_grade", "work_div",
                                         "num_of_graders", "feedback_base_fi",
                                         "feedback_base_en", "in_grading"])

            messages.success(request, "Exercise added for grading")

        else:
            #messages.error(self.request, "Invalid fields:")

            for error in form.errors:
                messages.error(self.request, form.errors[error])

            # Information passed to template which tab to show
            request.session["show_set_grading"] = True

        return self.get(request, *args, **kwargs)
        

class UpdateExerciseInGradingView(LoginRequiredMixin, generic.edit.UpdateView):
    """
    Handle the request to update exercise grading settings.
    """
    model = Exercise
    pk_url_kwarg = "pk_e"
    slug_field = "exercise_id"
    slug_url_kwarg = "exercise_id"
    query_pk_and_slug = True
    form_class = forms.ExerciseUpdateForm

    def get_success_url(self):
        return reverse(
            "submissions:exercises", kwargs={
                "pk": self.kwargs["pk"],
                "course_id": self.kwargs["course_id"]
            }
        )

    def form_valid(self, form):
        self.object = form.save()

        all_graders = \
            self.object.graders.count() + self.object.graders_en.count()

        if self.object.num_of_graders is None or \
                self.object.num_of_graders < all_graders:
            self.object.num_of_graders = all_graders
            self.object.save()

        # Minimum points of accepted submission have been increased.
        # Remove submissions with points lesser than new limit but
        # only if the feedback status is still template.
        self.object.feedback_set.filter(
            status=Feedback.BASE,
            auto_grade__lt=self.object.min_points
        ).delete()

        # Maximum points for auto grade have been decreased.
        # Remove submissions with points greater than new limit but
        # only if the feedback status is still template.
        if self.object.max_points is not None:
            self.object.feedback_set.filter(
                status=Feedback.BASE,
                auto_grade__gt=self.object.max_points
            ).delete()

        # Update feedback base if it exists. Update is done only
        # if Feedback object's status is Feedback.BASE
        if self.object.feedback_base_fi or self.object.feedback_base_en:
            for feedback in self.object.feedback_set.all():
                utils.add_feedback_base(self.object, feedback)

        messages.success(self.request, "Changes saved successfully")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid fields:")

        for error in form.errors:
            messages.error(self.request, form.errors[error])

        return HttpResponseRedirect(self.get_success_url())


class DisableExerciseGradingRedirectView(LoginRequiredMixin,
                                         generic.RedirectView):
    """
    Handles the request to remove the exercise from grading list.
    """
    pattern_name = "submissions:exercises"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs.pop("pk_e"))

        if exercise.error_state:
            exercise.delete()
        else:
            exercise.set_defaults()
            exercise.feedback_base_fi.delete()
            exercise.feedback_base_en.delete()
            exercise.feedback_set.all().delete()
            exercise.save()

        messages.success(request, "Exercise removed")
        return self.get(request, *args, **kwargs)


class HandleExerciseErrorRedirectView(LoginRequiredMixin,
                                      generic.RedirectView):

    pattern_name = "submissions:exercises"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs.pop("pk_e"))

        form = forms.ErrorHandlerForm(request.POST)

        if form.is_valid():
            handle_exercise = form.cleaned_data["handle_error"]

            if handle_exercise == "keep":
                exercise.error_state = None
                exercise.save()
                messages.success(request, "Warning ignored")
            elif handle_exercise == "delete":
                exercise.delete()
                messages.success(request, "Exercise removed")

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
        SetGraderFormset = modelformset_factory(Feedback,
                                                form=forms.SetGraderMeForm,
                                                extra=0)
        no_grader_set = self.get_queryset().filter(
            exercise=context["exercise"]).filter(grader=None)
        context["formset"] = SetGraderFormset(queryset=no_grader_set)

        context["my_ready_count"] = self.object_list.filter(
            status=Feedback.READY
        ).count()

        context["my_feedback_count"] = self.object_list.count()
        context["batch_assess_form"] = forms.BatchAssessForm()
        
        return context
    
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])

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
        SetGraderFormset = modelformset_factory(Feedback,
                                                form=forms.SetGraderMeForm)
        formset = SetGraderFormset(request.POST)

        if formset.is_valid():
            for form in formset.forms:
                if form.cleaned_data.get("check_this"):
                    feedback_obj = form.save(commit=False)
                    feedback_obj.grader = request.user
                    feedback_obj.save()

            messages.success(request, "Submissions added to my grading list")
        else:
            messages.error(request, "Invalid form")

        return self.get(request, *args, **kwargs)


class SubmissionsFormView(ExerciseMixin, LoginRequiredMixin,
                          generic.FormView):
    """
    Lomakenäkymä, jolla palautuksen arvostelija voidaan vaihtaa/asettaa.

    """
    form_class = modelformset_factory(Feedback, form=forms.ChangeGraderForm,
                                      extra=0)
    template_name = "submissions/submissions_form.html"
    
    def form_valid(self, form):
        for sub_form in form:
            if sub_form.has_changed():
                sub_form.save()
        messages.success(self.request, "Changes saved successfully")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        if not context["course"].is_staff(request.user):
            raise PermissionDenied

        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        exercise = get_object_or_404(Exercise, pk=self.kwargs["pk"])
        kwargs["queryset"] = exercise.feedback_set.all()
        return kwargs

    def get_success_url(self):
        return reverse(
            "submissions:submissions", kwargs={
                "pk": self.kwargs["pk"],
                "exercise_id": self.kwargs["exercise_id"]
            }
        )


class FeedbackView(ExerciseMixin, LoginRequiredMixin,
                   generic.edit.UpdateView):
    """
    Näyttää yhden palautuksen koodin/urlin/kysymykset/vastaukset ja
    lomakkeen palautetta varten.
    """
    model = Feedback
    slug_field = "sub_id"
    slug_url_kwarg = "sub_id"
    pk_url_kwarg = "pk_s"
    query_pk_and_slug = True
    form_class = forms.FeedbackForm
    initial = {
        "status": Feedback.READY
    }

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.exercise.course.is_staff(request.user):
            raise PermissionDenied

        if request.user != self.object.grader:
            messages.warning(request, "Submission is not on your grading list!")

        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the information about the submission and add it to the context.
        context.update(utils.get_submission_data(self.object))

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
        return reverse(
            "submissions:grading", kwargs={
                "pk": self.kwargs["pk"],
                "exercise_id": self.kwargs["exercise_id"]
            }
        )

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
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        form = forms.BatchAssessForm(request.POST)

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
                    f"{feedbacks.count()} submissions assessed with "
                    f"{points} points"
                )
            else:
                messages.info(request, "No feedbacks with status TEMPLATE")

        else:
            messages.error(request, "Invalid form")

        return self.get(request, *args, **kwargs)


class ReleaseFeedbacksRedirectView(LoginRequiredMixin, generic.RedirectView):
    # TODO: näytä errorviestissä mistä palautuksesta error tuli
    # TODO: pitää tehdä koko julkaisujuttu kokonaan toisella tavalla
    pattern_name = "submissions:grading"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        feedbacks = exercise.feedback_set.filter(grader=request.user,
                                                 status=Feedback.READY,
                                                 released=False)

        url = f"{exercise.api_url}/submissions/"
        auth = {"Authorization": f"Token {exercise.course.api_token}"}
        
        if feedbacks:
            for i in range(0, len(feedbacks)):
                json_object = utils.create_json_object(feedbacks[i])

                try:
                    view_logger.debug(f"POST {i}")
                    resp = requests.post(url, json=json_object, headers=auth)
                except Exception as e:
                    view_logger.debug(e)
                    messages.error(
                        request,
                        f"{e}\nReleased {i} feedbacks with status READY"
                        f"\n{feedbacks.count()-i} left unreleased"
                    )
                    break

                if resp.status_code == 201:
                    view_logger.debug(f"Success, saved {i}")
                    feedbacks[i].released = True
                    feedbacks[i].save()
                else:
                    messages.error(
                        request,
                        f"{resp.status_code} {resp.text}\n"
                        f"Released {i} feedbacks with status READY"
                        f"\n{feedbacks.count()-i} left unreleased"
                    )
                    break
            else:
                messages.success(request,
                                 f"Released {feedbacks.count()} feedbacks"
                                 f" with status READY")
        else:
            messages.info(request, "No feedbacks with status READY")
            
        return self.get(request, *args, **kwargs)


class CreateJsonFromFeedbacksView(LoginRequiredMixin, generic.TemplateView):
    template_name = "submissions/json.html"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])
        feedbacks = exercise.feedback_set.filter(status=Feedback.READY,
                                                 released=False)
        context = super().get_context_data()

        if feedbacks:
            exercise.latest_release.clear()
            context["json"] = utils.create_json_to_batch_assess(feedbacks)
            exercise.save()
        else:
            context["json"] = "NO FEEDBACKS WITH STATUS READY"

        return self.render_to_response(context)


class UndoLatestReleaseRedirectView(LoginRequiredMixin, generic.RedirectView):
    pattern_name = "submissions:submissions"

    def post(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])

        if not exercise.course.is_staff(request.user):
            raise PermissionDenied

        if len(exercise.latest_release) > 0:
            for id in exercise.latest_release:
                feedback = get_object_or_404(Feedback, pk=id)
                feedback.released = False
                feedback.save()

            exercise.latest_release.clear()
            exercise.save()
            messages.success(request, "Status restored")

        else:
            messages.info(request, "Previous json data couldn't be found")

        return self.get(request, *args, **kwargs)


class DownloadCsvView(LoginRequiredMixin, generic.View):
    def get(self, request, *args, **kwargs):
        exercise = get_object_or_404(Exercise, pk=kwargs["pk"])

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
