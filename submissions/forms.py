from django.forms import ModelForm
from submissions.models import Exercise


class ExerciseForm(ModelForm):
    class Meta:
        model = Exercise
        fields =  ["min_points", "consent_exercise", "feedback_base"]

