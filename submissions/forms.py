from django import forms
from .models import Exercise, Feedback


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        # Lisää field auto_div
        fields = ["min_points", "consent_exercise", "feedback_base"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consent_exercise"].queryset = Exercise.objects.filter(
            course=kwargs["instance"].course
        )


class ChangeGraderForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["grader"]
        labels = {
            "grader": "Arvostelija"
        }


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Valitse arvosteltavaksi.",
        }