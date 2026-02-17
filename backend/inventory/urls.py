from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_update, name="product_update"),
    path("products/<int:pk>/stock/", views.stock_transaction, name="stock_transaction"),
    path("reports/", views.reports_home, name="reports_home"),
    path("reports/products.csv", views.export_products_csv, name="export_products_csv"),
    path("reports/transactions.csv", views.export_transactions_csv, name="export_transactions_csv"),
    path("reports/transactions.pdf", views.export_transactions_pdf, name="export_transactions_pdf"),
    path("audit/", views.audit_list, name="audit_list"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
]
