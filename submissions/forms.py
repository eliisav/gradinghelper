from django import forms
from .models import Exercise, Feedback, User
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ExerciseUpdateForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ["min_points", "max_points", "add_penalty", "add_auto_grade",
                  "work_div", "graders", "graders_en", "num_of_graders",
                  "feedback_base", "grading_ready"]
        labels = {
            "min_points": "Minimum points to accept submission for grading:",
            "max_points": "Maximum points of Plussa automated evaluation:",
            # "consent_exercise": "Arvostelulupa annetaan tehtävässä:",
            "add_penalty": "Late penalty is deducted from staff points",
            "add_auto_grade": "Plussa points and staff points are added "
                              "together",
            "work_div": "Work division:",
            "graders": "Graders Finnish/English:",
            "graders_en": "Graders English only:",
            "num_of_graders": "Total number of graders:",
            "feedback_base": "Feedback template:",
            "grading_ready": "Grading ready, stop polling new submissions"
        }
        widgets = {
            "work_div": forms.RadioSelect,
            "max_points": forms.NumberInput(attrs={
                "placeholder": "Needed only if grading is not completely done "
                               "through this service"
            }),
            "num_of_graders": forms.NumberInput(attrs={
                "placeholder": "Needed only for equal division if the final "
                               "number of graders is greater than currently "
                               "selected"
            }),
            "feedback_base": forms.FileInput(attrs={"accept": ".txt"})
        }
        help_texts = {
            "graders_en": "If the desired user is not available in the lists "
                          "above, ask him/her to log in once",
            "feedback_base": "Only text (.txt) files are accepted"
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

            self.fields["graders_en"].queryset = User.objects.filter(
                Q(
                    courses_assistant=self.course.base_course
                ) | Q(
                    courses_teacher=self.course.base_course
                )
            ).distinct()

    def clean_feedback_base(self):
        fileobject = self.cleaned_data["feedback_base"]

        # It's ok if there is no file
        if not fileobject:
            return fileobject
        # Let's assume that it is a textfile if extension is .txt and
        # file size is less than 500 kB
        elif fileobject.name.endswith("txt") and fileobject.size < 500000:
            return fileobject
        else:
            raise ValidationError(_("File is not a text file"))

    def clean_graders_en(self):
        graders_en_only = self.cleaned_data["graders_en"]
        graders_fi_en = self.cleaned_data["graders"]

        for grader in graders_en_only:
            if grader in graders_fi_en:
                raise ValidationError(
                    _("Grader cannot belong to both categories Fi/En and "
                      "En only")
                )

        return graders_en_only


class ExerciseSetGradingForm(ExerciseUpdateForm):
    class Meta(ExerciseUpdateForm.Meta):
        fields = ["name", "min_points", "max_points", "add_penalty",
                  "add_auto_grade", "work_div", "graders", "graders_en",
                  "num_of_graders", "feedback_base"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["name"] = forms.ModelChoiceField(
                queryset=Exercise.objects.filter(
                    course=self.course
                ).filter(
                    in_grading=False)
            )
            self.fields["name"].label = "Select exercise to add:"


class ChangeGraderForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["grader"]
        labels = {
            "grader": "Grader"
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
            "grader": "Grader",
            "staff_grade": "Points without late penalty ",
            "feedback": "Feedback",
            "status": "Feedback status"
        }
        widgets = {
            "staff_grade": forms.NumberInput(attrs={
                "placeholder": "Points without late penalty"
            }),
            "feedback": forms.Textarea(attrs={"cols": 80, "rows": 17}),
            "students": forms.MultipleHiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = kwargs["instance"].get_students()

    def clean(self):
        cleaned_data = super().clean()
        points = cleaned_data.get("staff_grade")
        auto_grade = self.instance.auto_grade
        max_points = self.instance.exercise.total_max_points

        if self.instance.exercise.add_auto_grade:
            if points + auto_grade > max_points:
                self.add_error(
                    "staff_grade",
                    ValidationError(
                        _("Points exceed maximum points"),
                        code="max_points_exceeded"
                    )
                )
        else:
            if points > max_points:
                self.add_error(
                    "staff_grade",
                    ValidationError(
                        _("Points exceed maximum points"),
                        code="max_points_exceeded"
                    )
                )

        return cleaned_data


class SetGraderMeForm(forms.ModelForm):
    check_this = forms.BooleanField(required=False)
    
    class Meta:
        model = Feedback
        fields = ["check_this"]
        help_texts = {
            "check_this": "Select for grading",
        }


class BatchAssessForm(forms.Form):
    points = forms.IntegerField(
        label="Points",
        min_value=0,
        help_text="Amount of points to be added to all of the submissions "
                  "with status UNSTARTED"
                  "<p>Joukkoarvostele kaikki UNSTARTED"
                  "-tilassa olevat palautukset tällä pistemäärällä."
    )
    feedback = forms.CharField(
        widget=forms.Textarea,
        label="Feedback",
        required=False,
        help_text="Brief feedback text, can be left blank"
    )


class ErrorHandlerForm(forms.Form):
    HANDLE_CHOICES = [
        ("keep", "Ignore warning and keep the exercise"),
        ("delete", "Delete this exercise including all "
                   "submissions and feedbacks related to it"
)
    ]

    handle_error = forms.ChoiceField(
        label="", widget=forms.RadioSelect,
        choices=HANDLE_CHOICES, initial="keep"
    )
