from django import forms
from .models import Feedback
from django import forms
from django.contrib.auth.models import User
from .models import Profile

class RegisterForm(forms.ModelForm):
    name = forms.CharField(max_length=150)
    mobile = forms.CharField(max_length=15)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["email", "password", "name", "mobile"]

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        name = self.cleaned_data["name"]
        mobile = self.cleaned_data["mobile"]
        password = self.cleaned_data["password"]

        user = User(username=email, email=email)
        user.set_password(password)
        user.first_name = name
        if commit:
            user.save()
            Profile.objects.create(user=user, mobile=mobile)
        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = [
            'rating', 'liked_most', 'to_improve', 'would_recommend'
        ]
        widgets = {
            'rating': forms.RadioSelect(),
            'liked_most': forms.Textarea(attrs={'rows': 3}),
            'to_improve': forms.Textarea(attrs={'rows': 3}),
        }
