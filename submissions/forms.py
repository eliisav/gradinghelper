from django import forms
from .models import Exercise, Feedback, User
from django.db.models import Q


class ExerciseUpdateForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ["min_points", "max_points", "add_penalty", "add_auto_grade",
                  "work_div", "graders", "num_of_graders", "feedback_base",
                  "grading_ready"]
        labels = {
            "min_points": "Pisteet, joilla palautus hyväksytään arvosteluun:",
            "max_points": "Automaattitarkastuksen maksimipisteet:",
            # "consent_exercise": "Arvostelulupa annetaan tehtävässä:",
            "add_penalty": "Arvostelijan antamista pisteistä "
                           "vähennetään myöhästymissakko",
            "add_auto_grade": "Automaatin pisteet ja arvostelijan pisteet "
                              "lasketaan yhteen",
            "work_div": "Työnjako:",
            "graders": "Valitse arvostelijat:",
            "num_of_graders": "Arvostelijoiden kokonaislukumäärä:",
            "feedback_base": "Palautepohja:",
            "grading_ready": "Arvostelu valmis, "
                             "lopetetaan palautusten hakeminen"
        }
        widgets = {
            "work_div": forms.RadioSelect,
            "max_points": forms.NumberInput(attrs={
                "placeholder": "Tarvitaan, jos osa palautuksista on arvioitu "
                               "jotenkin muuten kuin tämän palvelun kautta"
            }),
            "num_of_graders": forms.NumberInput(attrs={
                "placeholder": "Tarvitaan tasajakoa varten, jos suurempi kuin "
                               "edellä valittujen määrä"
            }),
            "feedback_base": forms.FileInput(attrs={"accept": ".txt"})
        }
        help_texts = {
            "graders": "Kaikki arvostelijat eivät välttämättä näy listassa, "
                       "jos he eivät ole vielä kirjautuneet kurssille.",
            "feedback_base": "Tiedoston tulee olla tekstitiedosto (.txt)"
        }

    def __init__(self, *args, **kwargs):
        self.course = None

        if "course" in kwargs:
            self.course = kwargs.pop("course")

        super().__init__(*args, **kwargs)

        if self.course:
            """
            self.fields["consent_exercise"].queryset = Exercise.objects.filter(
                course=self.course
            )
            """
            self.fields["graders"].queryset = User.objects.filter(
                Q(
                    courses_assistant=self.course.base_course
                ) | Q(
                    courses_teacher=self.course.base_course
                )
            ).distinct()

    def is_valid(self):
        valid = super().is_valid()

        if not valid:
            return valid

        fileobject = self.cleaned_data["feedback_base"]

        # It's ok if there is no file
        if not fileobject:
            return True
        # Let's assume that it is a textfile if extension is .txt and
        # file size is less than 500 kB
        elif fileobject.name.endswith("txt") and fileobject.size < 500000:
            return True
        else:
            self._errors["file_error"] = "Tiedosto ei ollut tekstitiedosto."
            return False


class ExerciseSetGradingForm(ExerciseUpdateForm):
    class Meta(ExerciseUpdateForm.Meta):
        fields = ["name", "min_points", "max_points", "add_penalty",
                  "add_auto_grade", "work_div", "graders", "num_of_graders",
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
            Q(
                courses_assistant=course.base_course
            ) | Q(
                courses_teacher=course.base_course
            )
        ).distinct()


class FeedbackForm(ChangeGraderForm):
    class Meta(ChangeGraderForm.Meta):
        fields = ["grader", "staff_grade", "feedback", "status", "students"]
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
            "feedback": forms.Textarea(attrs={"cols": 80, "rows": 17}),
            "students": forms.MultipleHiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = kwargs["instance"].get_students()


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Valitse arvosteltavaksi.",
        }


class BatchAssessForm(forms.Form):
    points = forms.IntegerField(
        label="Pisteet",
        min_value=0,
        help_text="Joukkoarvostele kaikki 'Ei aloitettu'-tilassa olevat "
                  "palautukset tällä pistemäärällä."
    )
    feedback = forms.CharField(
        label="Palauteteksti",
        required=False,
        help_text="Lyhyt palauteteksi, ei pakollinen."
    )


class ErrorHandlerForm(forms.Form):
    HANDLE_CHOICES = [
        ("delete", "Poista tehtävä ja siihen liittyvät arvostelut"),
        ("keep", "Säilytä tehtävä ja ohita virheilmoitus")
    ]

    handle_error = forms.ChoiceField(
        label="", widget=forms.RadioSelect, choices=HANDLE_CHOICES
    )
