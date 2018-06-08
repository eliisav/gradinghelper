from django.forms import ModelForm
from submissions.models import Feedback
from submissions.models import Exercise


class FeedbackForm(ModelForm):
    class Meta:
        model = Feedback
        fields = ["grader", "points", "feedback"]

