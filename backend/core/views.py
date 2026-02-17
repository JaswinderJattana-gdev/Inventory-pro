from datetime import timedelta
from django.db import models
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from inventory.models import Product, InventoryTransaction


@login_required
def dashboard(request):
    # Low stock products
    low_stock = (
        Product.objects.select_related("category")
        .filter(is_active=True, quantity_on_hand__lte=models.F("reorder_level"))
        .order_by("quantity_on_hand", "name")[:10]
    )

    # Top movers last 30 days (sum of IN + OUT separately is fine; we’ll sum absolute moved qty)
    since = timezone.now() - timedelta(days=30)

    movers = (
        InventoryTransaction.objects.filter(created_at__gte=since)
        .values("product_id", "product__name", "product__sku")
        .annotate(moved_qty=Sum("quantity"))
        .order_by("-moved_qty")[:10]
    )

    return render(
        request,
        "core/dashboard.html",
        {
            "low_stock": low_stock,
            "movers": movers,
            "since": since.date(),
        },
    )
