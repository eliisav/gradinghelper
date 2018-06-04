from django.forms import ModelForm
from submissions.models import Feedback

class FeedbackForm(ModelForm):
    class Meta:
        model = Feedback
        fields = ['grader', 'points', 'feedback']
        
        #feedback = forms.CharField(label='', widget=forms.Textarea)

