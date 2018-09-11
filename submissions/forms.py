from django import forms
from .models import Exercise, Feedback, User
from django.db.models import Q


class ExerciseForm(forms.ModelForm):

    class Meta:
        model = Exercise
        fields = ["name", "min_points", "consent_exercise", "auto_div",
                  "feedback_base"]
        labels = {
            "min_points": "Vähimmäispisteet:",
            "consent_exercise": "Arvostelulupa annetaan tehtävässä:",
            "auto_div": "Automaattinen työnjako",
            "feedback_base": "Palautepohja:"
        }
        
    def __init__(self, *args, **kwargs):
        course = None

        if "course" in kwargs:
            course = kwargs.pop("course")

        super().__init__(*args, **kwargs)

        if course:
            self.fields["name"] = forms.ModelChoiceField(
                queryset=Exercise.objects.filter(
                    course=course
                ).filter(
                    in_grading=False)
            )
            self.fields["name"].label = "Tehtävä:"
            self.fields["consent_exercise"].queryset = Exercise.objects.filter(
                course=course
            )


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["points", "feedback", "status"]

        widgets = {
            "feedback": forms.Textarea(attrs={'cols': 70, 'rows': 20})
        }


class ChangeGraderForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["grader"]
        labels = {
            "grader": "Arvostelija"
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        course = kwargs["instance"].exercise.course
        self.fields["grader"].queryset = User.objects.filter(
            Q(my_courses=course) | Q(responsibilities=course)).distinct()


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Valitse arvosteltavaksi.",
        }
