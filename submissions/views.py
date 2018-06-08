from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic

from .models import Feedback, Exercise
from .forms import FeedbackForm

import requests
import os


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}

COURSE = 31      # summer en 34, summer fi 31
EXERCISE = 5113  # melumittaus en 5302, fi 5113
BASE_URL = "https://plus.cs.tut.fi/api/v2/courses"


class IndexView(generic.ListView):
    model = Exercise
    template_name = 'submissions/index.html'
    context_object_name = "exercises"
    
    def get_queryset(self):
        return Exercise.objects.order_by("exercise_id")
        
        
class ExerciseCreate(generic.edit.CreateView):
    model = Exercise
    fields = ["exercise_id", "min_points", "max_points", "deadline"]
    success_url = reverse_lazy("submissions:index")


def get_submissions(request, exercise_id):
    # Etsitään tehtävän id:n perusteella url, jolla saadaa pyydettyä tiedot
    # tämän tehtävän viimeisimmistä/parhaista palautuksista.
    exercise_url = f"https://plus.cs.tut.fi/api/v2/exercises/{exercise_id}"
    req = requests.get(exercise_url, headers=AUTH)
    exercise_info = req.json()
    course_url = exercise_info["course"]["url"]
    data_url = f"{course_url}submissiondata/?exercise_id={exercise_id}&format=json"
    
    print("SUB_DATA_URL:", data_url)
    
    req = requests.get(data_url, headers=AUTH)
    subsdata = req.json()
    
    exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
    
    for sub in subsdata:
        try:
            feedback = exercise.feedback_set.get(sub_id=sub["SubmissionID"])
            
        except Feedback.DoesNotExist:
            exercise.feedback_set.create(sub_id=sub["SubmissionID"], 
                                         sub_url=sub["ohjelma.py"],
                                         submitter=sub["Email"])
            exercise.save()
            
    return HttpResponseRedirect(reverse("submissions:submissions", 
                                        args=(exercise_id,)))


class ExerciseView(generic.DetailView):
    model = Exercise
    template_name = "submissions/submissions.html"
    slug_field = "exercise_id"


def get_feedback(request, exercise_id, sub_id):
    if request.method == "POST":
        feedback = get_object_or_404(Feedback, sub_id=sub_id)
        feedback.done = True
        filled_form = FeedbackForm(request.POST, instance=feedback)
        filled_form.save()
        return HttpResponseRedirect(reverse("submissions:submissions", 
                                            args=(exercise_id,)))
        
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
                                                             "exercise": exercise_id})
                                                             



