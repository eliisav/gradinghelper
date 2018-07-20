from django.forms import ModelForm
from submissions.models import Feedback
from submissions.models import Exercise


class FeedbackForm(ModelForm):
    class Meta:
        model = Feedback
        fields = ["grader", "points", "feedback"]

class ExerciseForm(ModelForm):
    class Meta:
        model = Exercise
        fields =  ["name", "min_points", "max_points", "deadline", "consent_exercise"]
