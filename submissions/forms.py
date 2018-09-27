from django import forms
from .models import Exercise, Feedback, User
from django.db.models import Q


class ExerciseUpdateForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ["min_points", "consent_exercise", "work_div",
                  "feedback_base"]
        labels = {
            "min_points": "Pisteet, joilla tehtävä hyväksytään arvosteluun:",
            "consent_exercise": "Arvostelulupa annetaan tehtävässä:",
            "work_div": "Työnjako:",
            "feedback_base": "Palautepohja:"
        }
        widgets = {
            "work_div": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        self.course = None

        if "course" in kwargs:
            self.course = kwargs.pop("course")

        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["consent_exercise"].queryset = Exercise.objects.filter(
                course=self.course
            )


class ExerciseSetGradingForm(ExerciseUpdateForm):
    class Meta(ExerciseUpdateForm.Meta):
        fields = ["name", "min_points", "consent_exercise", "work_div",
                  "feedback_base"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["name"] = forms.ModelChoiceField(
                queryset=Exercise.objects.filter(
                    course=self.course
                ).filter(
                    in_grading=False)
            )
            self.fields["name"].label = "Tehtävä:"


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


class FeedbackForm(ChangeGraderForm):
    class Meta(ChangeGraderForm.Meta):
        fields = ["grader", "staff_grade", "feedback", "status"]
        labels = {
            "grader": "Arvostelija",
            "staff_grade": "Arvostelijan antamat pisteet",
            "feedback": "Palaute",
            "status": "Palautteen tila"
        }
        widgets = {
            "staff_grade": forms.NumberInput(attrs={
                "placeholder": "Kirjaa pisteet ilman myöhästymissakkoa"
            }),
            "feedback": forms.Textarea(attrs={"cols": 70, "rows": 17})
        }


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Valitse arvosteltavaksi.",
        }
