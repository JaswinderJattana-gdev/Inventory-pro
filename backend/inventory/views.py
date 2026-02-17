from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import models
from django.db import transaction
from .models import InventoryTransaction
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ProductForm
from .models import Product, Category

import csv
from datetime import datetime
from django.http import HttpResponse
from django.utils.timezone import make_aware

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from core.permissions import require_group

from .audit import log
from .models import AuditLog

from django.db.models import Q
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
    transactions = product.transactions.all() [:10]
    return render(request, "inventory/product_detail.html", {"product": product, "transactions": transactions})

@require_group("Admin")
@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            log(request.user, "PRODUCT_CREATE", "Product", product.id, f"Created {product.name} ({product.sku})")
            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form, "mode": "create"})

@require_group("Admin")
@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            log(request.user, "PRODUCT_UPDATE", "Product", product.id, f"Updated {product.name} ({product.sku})")
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
                action = "STOCK_IN" if tx.transaction_type == "IN" else "STOCK_OUT"
                log(request.user, action, "Product", product.id, f"{action} {tx.quantity} for {product.sku}")

            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = StockTransactionForm()

    return render(
        request,
        "inventory/stock_form.html",
        {"form": form, "product": product},
    )

@login_required
def reports_home(request):
    # default range: last 30 days
    return render(request, "inventory/reports_home.html")


@login_required
def export_products_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "SKU", "Name", "Category", "Cost", "Price",
        "Qty On Hand", "Reorder Level", "Active", "Created", "Updated"
    ])

    qs = Product.objects.select_related("category").order_by("name")

    for p in qs:
        writer.writerow([
            p.sku,
            p.name,
            p.category.name,
            f"{p.cost:.2f}",
            f"{p.price:.2f}",
            p.quantity_on_hand,
            p.reorder_level,
            "Yes" if p.is_active else "No",
            p.created_at.isoformat(),
            p.updated_at.isoformat(),
        ])

    return response


def _parse_date(value: str):
    """
    Parses YYYY-MM-DD into an aware datetime at 00:00 local time.
    Returns None if empty/invalid.
    """
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return make_aware(dt)
    except ValueError:
        return None


@login_required
def export_transactions_csv(request):
    # Optional filters
    start = _parse_date(request.GET.get("start", ""))
    end = _parse_date(request.GET.get("end", ""))

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Date", "Type", "SKU", "Product",
        "Quantity", "Reference", "Note", "User"
    ])

    qs = InventoryTransaction.objects.select_related("product", "created_by").order_by("-created_at")

    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        # include the entire end day by adding 1 day and using lt
        qs = qs.filter(created_at__lt=end.replace(hour=23, minute=59, second=59))

    for t in qs:
        writer.writerow([
            t.created_at.isoformat(),
            t.transaction_type,
            t.product.sku,
            t.product.name,
            t.quantity,
            t.reference,
            t.note,
            t.created_by.username if t.created_by else "",
        ])

    return response

@login_required
def export_transactions_pdf(request):
    start = _parse_date(request.GET.get("start", ""))
    end = _parse_date(request.GET.get("end", ""))

    qs = InventoryTransaction.objects.select_related("product", "created_by").order_by("-created_at")
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end.replace(hour=23, minute=59, second=59))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="transactions.pdf"'

    c = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Inventory Transactions Report")
    y -= 20

    c.setFont("Helvetica", 10)
    date_line = "All time"
    if start and end:
        date_line = f"From {start.date()} to {end.date()}"
    elif start:
        date_line = f"From {start.date()}"
    elif end:
        date_line = f"Up to {end.date()}"

    c.drawString(50, y, date_line)
    y -= 25

    # Column headers
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Type")
    c.drawString(200, y, "SKU")
    c.drawString(280, y, "Product")
    c.drawString(470, y, "Qty")
    y -= 15

    c.setFont("Helvetica", 9)

    for t in qs[:500]:  # cap to keep pdf sane
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, "Date")
            c.drawString(150, y, "Type")
            c.drawString(200, y, "SKU")
            c.drawString(280, y, "Product")
            c.drawString(470, y, "Qty")
            y -= 15
            c.setFont("Helvetica", 9)

        c.drawString(50, y, t.created_at.strftime("%Y-%m-%d"))
        c.drawString(150, y, t.transaction_type)
        c.drawString(200, y, t.product.sku[:12])
        c.drawString(280, y, t.product.name[:30])
        c.drawRightString(495, y, str(t.quantity))
        y -= 14

    c.showPage()
    c.save()
    return response

@require_group("Admin")
@login_required
def audit_list(request):
    logs = AuditLog.objects.select_related("actor").all()[:200]
    return render(request, "inventory/audit_list.html", {"logs": logs})

@login_required
def transaction_list(request):
    q = request.GET.get("q", "").strip()
    tx_type = request.GET.get("type", "").strip()  # IN / OUT / empty
    start = _parse_date(request.GET.get("start", ""))
    end = _parse_date(request.GET.get("end", ""))

    qs = InventoryTransaction.objects.select_related("product", "created_by").order_by("-created_at")

    if q:
        qs = qs.filter(
            Q(product__name__icontains=q) |
            Q(product__sku__icontains=q) |
            Q(reference__icontains=q)
        )

    if tx_type in ("IN", "OUT"):
        qs = qs.filter(transaction_type=tx_type)

    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end.replace(hour=23, minute=59, second=59))

    # Keep it simple for now (later: pagination)
    qs = qs[:200]

    return render(
        request,
        "inventory/transaction_list.html",
        {"transactions": qs, "q": q, "tx_type": tx_type, "start": request.GET.get("start",""), "end": request.GET.get("end","")},
    )
