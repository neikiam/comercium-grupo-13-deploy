from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["bio", "avatar", "website"]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Cuéntanos sobre ti...'}),
            'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'bio': 'Biografía',
            'avatar': 'Foto de perfil',
            'website': 'Sitio web',
        }
