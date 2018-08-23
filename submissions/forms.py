from django import forms
from .models import Exercise, Feedback


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields =  ["min_points", "consent_exercise", "feedback_base"]
        
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consent_exercise"].queryset = Exercise.objects.filter(course=kwargs["instance"].course)


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["sub_id", "students", "grader"]
        
        # widgets = {
        #    "students": forms.SelectMultiple(attrs={"readonly": True, "disabled": True})
        #    }

    
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sub_id"].widget.attrs["readonly"] = True
        # self.fields["students"].widget.attrs["readonly"] = True
        self.fields["students"].widget.attrs["disabled"] = True
        
        #print(kwargs)
    
        self.fields['students'].queryset = kwargs['instance'].students
        
        
    
