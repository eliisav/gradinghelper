from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import generic

from .models import Feedback, Exercise
from .forms import FeedbackForm
from .utils import *


COURSE = 31      # summer en 34, summer fi 31
EXERCISE = 5113  # melumittaus en 5302, fi 5113


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


class SubmissionsView(generic.ListView):
    template_name = "submissions/submissions.html"
    context_object_name = "submissions"
    
    def get(self, request, exercise_id):
        exercise = get_object_or_404(Exercise, exercise_id=exercise_id)
        subsdata = get_submissions(exercise_id)
        
        for sub in subsdata:
            try:
                feedback = exercise.feedback_set.get(sub_id=sub["SubmissionID"])
                
            except Feedback.DoesNotExist:
                exercise.feedback_set.create(sub_id=sub["SubmissionID"], 
                                             sub_url=sub["ohjelma.py"],
                                             submitter=sub["Email"])
                exercise.save()
                
        self.object_list = exercise.feedback_set.all()
        
        return self.render_to_response(self.get_context_data())


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

