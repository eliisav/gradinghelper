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
        fields = ["sub_id", "students", "grader"]
        labels = {
            "sub_id": "Palautuksen id plussassa",
            "students": "Opiskelijat",
            "grader": "Arvostelija"
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sub_id"].widget.attrs["required"] = False
        self.fields["sub_id"].widget.attrs["readonly"] = True
        self.fields["students"].widget.attrs["required"] = False
        self.fields["students"].widget.attrs["readonly"] = True
        self.fields['students'].queryset = kwargs['instance'].students


class SetGraderMeForm(ChangeGraderForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        fields = ["sub_id", "students", "check_this"]
