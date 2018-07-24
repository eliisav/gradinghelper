from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.core.cache import cache
from django.contrib import messages

from .models import Feedback, Exercise
from .forms import FeedbackForm, ExerciseForm
from .utils import *


#COURSE = 31      # summer en 34, summer fi 31
#EXERCISE = 5113  # melumittaus en 5302, fi 5113


class IndexView(generic.ListView):
    """
    Listaa kaikki kurssit, jotka rajapinnasta on saatavilla.
    return: Lista kaikista kursseista
    """
    template_name = "submissions/index.html"
    context_object_name = "courses"
    
    def get(self, request):
        self.object_list = get_courses()
        return self.render_to_response(self.get_context_data())


class ExerciseListView(generic.ListView):
    """
    Listaa yhden kurssin kaikki tehtävät
    """
    model = Exercise
    template_name = "submissions/exercises.html"
    context_object_name = "exercises"
    
    def get(self, request, course_id):
        self.object_list = self.get_queryset().filter(course_id=course_id)
        
        for exercise in self.object_list:
            exercise.form = ExerciseForm(instance=exercise)
            
        context = self.get_context_data()
        context["course_id"] = course_id
        
        return self.render_to_response(context)
    
"""        
    def get(self, request, course_id):
        self.object_list = self.get_queryset()
      
        all_exercises = cache.get(course_id)
        if not all_exercises:
            all_exercises = get_exercises(course_id)
            cache.set(course_id, all_exercises)
        
        context = self.get_context_data()
        
        context["course_id"] = course_id
        context["form"] = ExerciseForm()
        context["all_exercises"] = all_exercises
        
        return self.render_to_response(context)
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
    
    get_exercises(course_id)
    
    return HttpResponseRedirect(reverse("submissions:exercises", 
                                        kwargs={ "course_id": course_id }))
        
    


def enable_exercise_trace(request, course_id, exercise_id):
    
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
        
    return HttpResponseRedirect(reverse("submissions:exercises", 
                                        kwargs={ "course_id": course_id }))


class SubmissionsView(generic.ListView):
    """
    Listaa yhden tehtävän viimeisimmät/parhaat palautukset.
    """
    template_name = "submissions/submissions.html"
    context_object_name = "submissions"
    
    def get(self, request, course_id, exercise_id):
        exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
        subsdata = get_submissions(exercise_id)
        
        for sub in subsdata:
        
            print(sub)
        
            try:
                feedback = exercise.feedback_set.get(sub_id=sub["SubmissionID"])
                
            except Feedback.DoesNotExist:
                # Laitetaan talteen palautukset, jotka ovat läpäisseet testit
                if sub["Grade"] >= exercise.min_points and "ohjelma.py" in sub:
                    exercise.feedback_set.create(sub_id=sub["SubmissionID"], 
                                                 sub_url=sub["ohjelma.py"],
                                                 submitter=sub["Email"])
                    exercise.save()
                
        self.object_list = exercise.feedback_set.all()
        
        return self.render_to_response(self.get_context_data())


def get_feedback(request, course_id, exercise_id, sub_id):
    """
    Näyttää yhden palautuksen koodin ja lomakkeen palautetta varten.
    """
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
        req = requests.get(feedback.sub_url, headers=AUTH)
        req.encoding = "utf-8"
        sub_code = req.text
        form = FeedbackForm(instance=feedback)

        return render(request, "submissions/feedback.html", {"sub_code": sub_code,
                                                             "form": form,
                                                             "sub_id": sub_id,
                                                             "exercise": exercise_id,
                                                             "course_id": course_id})


"""
class ExercisesView(generic.ListView):
    model = Exercise
    template_name = "submissions/index.html"
    context_object_name = "exercises"
    
    def get_queryset(self):
        return Exercise.objects.order_by("exercise_id")
"""

