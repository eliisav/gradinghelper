from django import forms
from .models import Exercise, Feedback, User
from django.db.models import Q


class ExerciseUpdateForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ["min_points", "consent_exercise", "penalty", "work_div",
                  "graders", "num_of_graders", "feedback_base"]
        labels = {
            "min_points": "Pisteet, joilla tehtävä hyväksytään arvosteluun:",
            "consent_exercise": "Arvostelulupa annetaan tehtävässä:",
            "penalty": "Arvostelijan antamista pisteistä "
                       "vähennetään myöhästymissakko",
            "work_div": "Työnjako:",
            "graders": "Valitse arvostelijat:",
            "num_of_graders": "Arvostelijoiden lukumäärä",
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
            self.fields["graders"].queryset = User.objects.filter(
                Q(
                    my_courses=self.course
                ) | Q(
                    responsibilities=self.course
                )).distinct()
            self.fields["num_of_graders"].widget = forms.NumberInput(attrs={
                "placeholder": "Tarvitaan jos eri kuin edellä "
                               "valittujen määrä"
            })


class ExerciseSetGradingForm(ExerciseUpdateForm):
    class Meta(ExerciseUpdateForm.Meta):
        fields = ["name", "min_points", "consent_exercise", "penalty",
                  "work_div", "graders", "num_of_graders", "feedback_base"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["name"] = forms.ModelChoiceField(
                queryset=Exercise.objects.filter(
                    course=self.course
                ).filter(
                    in_grading=False)
            )
            self.fields["name"].label = "Lisättävä tehtävä:"


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
            "staff_grade": "Arvostelijan antamat pisteet "
                           "ilman myöhästymissakkoa",
            "feedback": "Palaute",
            "status": "Palautteen tila"
        }
        widgets = {
            "staff_grade": forms.NumberInput(attrs={
                "placeholder": "Kirjaa pisteet ilman myöhästymissakkoa"
            }),
            "feedback": forms.Textarea(attrs={"cols": 80, "rows": 17})
        }


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Valitse arvosteltavaksi.",
        }
