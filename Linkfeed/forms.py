# forms.py

from django import forms

class RSSFeedForm(forms.Form):
    link = forms.URLField(label='RSS Feed Link')

class ImportedRSSFeedForm(forms.Form):
    link = forms.URLField(label='Imported RSS Feed Link')