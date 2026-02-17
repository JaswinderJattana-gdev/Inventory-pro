from django import forms
from .models import Product
from .models import Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "category",
            "cost",
            "price",
            "reorder_level",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        cost = cleaned.get("cost")
        price = cleaned.get("price")
        reorder = cleaned.get("reorder_level")

        if cost is not None and cost < 0:
            self.add_error("cost", "Cost cannot be negative.")

        if price is not None and price < 0:
            self.add_error("price", "Price cannot be negative.")

        if cost is not None and price is not None and price < cost:
            self.add_error("price", "Price should usually be >= cost.")

        if reorder is not None and reorder < 0:
            self.add_error("reorder_level", "Reorder level cannot be negative.")

        return cleaned

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Category name must be at least 2 characters.")
        return name