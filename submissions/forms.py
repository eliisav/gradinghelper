from django import forms

class FeedbackForm(forms.Form):
    feedback = forms.CharField(label='', widget=forms.Textarea)

