from django.forms import ModelForm
from .models import Publication, Classes, Specialization,  Courses

from django.forms import ModelForm
from django import forms
from .models import Publication, Topic, Tag
from django.contrib.auth import get_user_model

User = get_user_model()

class ClassesForm(ModelForm):
    class Meta:
        model = Classes
        fields = ['name', 'label']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter class name'}),
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter class label'}),
        }

class SpecializationForm(ModelForm):
    class Meta:
        model = Specialization
        fields = ['name', 'label']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter specialization name'}),
            'label': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter specialization label'}),
        }  

class CoursesForm(ModelForm):
    class Meta:
        model = Courses
        fields = ['name', 'label', 'specialization', 'classe', 'semester']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter course name'}),
            'label': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter course label'}),
            'specialization': forms.Select(attrs={'class': 'form-control'}),
            'classe': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter semester'}),
        }