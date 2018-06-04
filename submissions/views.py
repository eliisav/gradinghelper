from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic

from .models import Feedback
from .forms import FeedbackForm

import requests
import os


TOKEN = "Token 2b92117b410cad8708fff3bfd7473340a69bfaac"  # Eliisan token
AUTH =  {'Authorization': TOKEN}

COURSE = 31      # summer en 34, summer fi 31
EXERCISE = 5113  # melumittaus en 5302, fi 5113
BASE_URL = "https://plus.cs.tut.fi/api/v2/courses"


def index(request):
    url = f"{BASE_URL}/{COURSE}/submissiondata/?exercise_id={EXERCISE}&format=json"
    
    req = requests.get(url, headers=AUTH)
    subsdata = req.json()
    
    exercise_name = subsdata[0]["Exercise"]
    
    for sub in subsdata:
        try:
            feedback = Feedback.objects.get(sub_id=sub["SubmissionID"])
            
        except Feedback.DoesNotExist:
            feedback = Feedback(sub_id=sub["SubmissionID"], 
                                sub_url=sub["ohjelma.py"],
                                submitter=sub["Email"])
            feedback.save()
            
    return render(request, "submissions/index.html", {"name": exercise_name})


class ExerciseView(generic.ListView):
    template_name = 'submissions/exercise.html'
    context_object_name = 'submissions'
    
    def get_queryset(self):
        return Feedback.objects.order_by('done')


def get_sub_info(request, sub_id):
    if request.method == "POST":
        feedback = get_object_or_404(Feedback, sub_id=sub_id)
        feedback.done = True
        filled_form = FeedbackForm(request.POST, instance=feedback)
        filled_form.save()
        return HttpResponseRedirect(reverse('submissions:exercise'))
        
    else:
        feedback = get_object_or_404(Feedback, sub_id=sub_id)
        #print(feedback.sub_url)
        req = requests.get(feedback.sub_url, headers=AUTH)
        req.encoding = "utf-8"
        sub_code = req.text
        form = FeedbackForm(instance=feedback)

        return render(request, "submissions/sub_code.html", {"sub_code": sub_code,
                                                             "form": form,
                                                             "sub_id": sub_id})
                                                         
