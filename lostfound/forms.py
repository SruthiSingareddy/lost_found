
from django import forms
from .models import Item


class ItemForm(forms.ModelForm):

    class Meta:
        model = Item

        fields = [
            'item_name',
            'category',
            'description',
            'location',
            'date',
            'item_type',
            'image'
        ]

        widgets = {
            'date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}
            )
        }
