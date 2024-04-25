# forms.py

from django import forms
from .models import UserCSS

class RSSFeedForm(forms.Form):
    link = forms.URLField(label='RSS Feed Link')

class ImportedRSSFeedForm(forms.Form):
    link = forms.URLField(label='Imported RSS Feed Link')

class UserCSSForm(forms.Form):
    link = forms.URLField(label='Imported CSS Link')
