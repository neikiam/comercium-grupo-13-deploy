import io

from django import forms
from django.core.exceptions import ValidationError
from PIL import Image

from .models import Product


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ProductForm(forms.ModelForm):
    additional_images = MultipleFileField(
        required=False,
        help_text='Puedes subir hasta 8 imágenes adicionales (máx. 5MB cada una)'
    )
    
    class Meta:
        model = Product
        fields = ['title', 'category', 'description', 'marca', 'price', 'stock', 'image', 'active']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Nombre del producto',
                'required': True,
            }),
            'category': forms.Select(attrs={
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Describe tu producto en detalle',
                'rows': 4,
                'required': True,
            }),
            'marca': forms.TextInput(attrs={
                'placeholder': 'Marca del producto (opcional)',
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True,
            }),
            'stock': forms.NumberInput(attrs={
                'placeholder': 'Cantidad disponible',
                'min': '1',
                'required': True,
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        help_texts = {
            'title': 'Máximo 200 caracteres',
            'description': 'Describe características, estado, etc.',
            'price': 'Precio en pesos argentinos (ARS)',
            'stock': 'Cantidad de unidades disponibles',
            'image': 'Imagen principal del producto (máx. 5MB)',
            'active': 'Desactiva tu producto si quieres pausar su publicación temporalmente',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['title'].disabled = True
            self.fields['title'].widget.attrs['readonly'] = True
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError("El título es obligatorio.")
        return title.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or not description.strip():
            raise forms.ValidationError("La descripción es obligatoria.")
        return description.strip()
    
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category or not category.strip():
            raise forms.ValidationError("La categoría es obligatoria.")
        return category.strip()
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if not price or price <= 0:
            raise forms.ValidationError("El precio debe ser mayor a 0.")
        return price
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None:
            try:
                stock = int(stock)
                if stock < 0:
                    raise ValidationError('El stock no puede ser negativo.')
            except (TypeError, ValueError):
                raise ValidationError('El stock debe ser un número válido.')
        return stock
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError("La imagen principal es obligatoria.")
        
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar los 5MB.")
        
        try:
            img = Image.open(image)
            img.verify()
            
            allowed_formats = ['JPEG', 'PNG', 'GIF', 'WEBP']
            if img.format not in allowed_formats:
                raise forms.ValidationError(
                    f"Formato de imagen no permitido. Formatos aceptados: {', '.join(allowed_formats)}"
                )
            
            max_dimension = 10000
            if img.width > max_dimension or img.height > max_dimension:
                raise forms.ValidationError(
                    f"Las dimensiones de la imagen son demasiado grandes. Máximo: {max_dimension}x{max_dimension} píxeles."
                )
            
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError(
                "El archivo no es una imagen válida o está corrupto."
            )
        
        image.seek(0)
        return image
    
    def clean_additional_images(self):
        return None
