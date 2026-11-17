from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Expense, Budget


class ExpenseForm(forms.ModelForm):
    """ModelForm to create / edit an expense. Bootstrap classes added to widgets."""

    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Lunch'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes'}),
        }


class SignUpForm(UserCreationForm):
    """Signup form with Bootstrap styling on every field."""

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class BudgetForm(forms.ModelForm):
    """Form to set the user's monthly budget."""

    class Meta:
        model = Budget
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'placeholder': 'e.g. 10000',
            }),
        }


class ImportForm(forms.Form):
    """Upload a CSV bank/expense statement to import many expenses at once."""

    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        label='Statement (.csv)',
    )
    use_ai = forms.BooleanField(
        required=False,
        initial=True,
        label='Let AI auto-detect the category for each expense',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
