from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profile

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(attrs={'class': 'w-full bg-brand-dark border border-brand-border rounded-md p-3 text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary transition-all', 'placeholder': 'Введите текущий пароль'}),
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'w-full bg-brand-dark border border-brand-border rounded-md p-3 text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary transition-all', 'placeholder': 'Создайте новый пароль'}),
    )
    new_password2 = forms.CharField(
        label="Подтверждение нового пароля",
        widget=forms.PasswordInput(attrs={'class': 'w-full bg-brand-dark border border-brand-border rounded-md p-3 text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary transition-all', 'placeholder': 'Повторите новый пароль'}),
    )

class ProfileUpdateForm(forms.ModelForm):
    telegram_username = forms.CharField(
        label="Telegram Username",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-brand-dark border border-brand-border rounded-md p-3 text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary transition-all', 'placeholder': 'Например, @username'})
    )
    wallet = forms.CharField(
        label="USDT TRC-20 Кошелек",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-brand-dark border border-brand-border rounded-md p-3 text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary transition-all', 'placeholder': 'Введите ваш TRC-20 адрес'})
    )

    class Meta:
        model = Profile
        fields = ['telegram_username', 'wallet']