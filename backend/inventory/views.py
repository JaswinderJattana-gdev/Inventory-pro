from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import models
from django.db import transaction
from .models import InventoryTransaction
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ProductForm
from .models import Product, Category

class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ["transaction_type", "quantity", "reference", "note"]

    def clean_quantity(self):
        qty = self.cleaned_data["quantity"]
        if qty <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return qty

@login_required
def product_list(request):
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    low_stock = request.GET.get("low_stock", "") == "1"
    active = request.GET.get("active", "1")  # default active only

    products = Product.objects.select_related("category").all()

    if active == "1":
        products = products.filter(is_active=True)
    elif active == "0":
        products = products.filter(is_active=False)

    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))

    if category_id:
        products = products.filter(category_id=category_id)

    if low_stock:
        products = products.filter(quantity_on_hand__lte=models.F("reorder_level"))

    products = products.order_by("name")

    categories = Category.objects.order_by("name")

    return render(
        request,
        "inventory/product_list.html",
        {
            "products": products,
            "categories": categories,
            "q": q,
            "category_id": category_id,
            "low_stock": low_stock,
            "active": active,
        },
    )


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    transactions = product.transactions.all()
    return render(request, "inventory/product_detail.html", {"product": product, "transactions": transactions})


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form, "mode": "create"})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "mode": "edit", "product": product},
    )

@login_required
def stock_transaction(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                tx = form.save(commit=False)
                tx.product = product
                tx.created_by = request.user

                if tx.transaction_type == "OUT":
                    if product.quantity_on_hand < tx.quantity:
                        form.add_error("quantity", "Not enough stock available.")
                        return render(
                            request,
                            "inventory/stock_form.html",
                            {"form": form, "product": product},
                        )
                    product.quantity_on_hand -= tx.quantity
                else:
                    product.quantity_on_hand += tx.quantity

                product.save()
                tx.save()

            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = StockTransactionForm()

    return render(
        request,
        "inventory/stock_form.html",
        {"form": form, "product": product},
    )
