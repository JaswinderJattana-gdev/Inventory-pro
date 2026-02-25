import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Category, Product, InventoryTransaction

class Command(BaseCommand):
    help = "Seed demo data for portfolio"

    def handle(self, *args, **options):
        # Categories
        cat_names = ["Beverages", "Snacks", "Office Supplies", "Electronics", "Cleaning"]
        categories = []
        for name in cat_names:
            c, _ = Category.objects.get_or_create(name=name)
            categories.append(c)

        # Products
        products_data = [
            ("COF-001", "Coffee Beans 1kg"),
            ("TEA-010", "Green Tea Pack"),
            ("SNK-100", "Protein Bar Box"),
            ("PEN-200", "Ballpoint Pens (10)"),
            ("PAP-250", "A4 Paper Ream"),
            ("CLN-300", "Surface Cleaner"),
            ("USB-400", "USB-C Cable"),
            ("KB-450", "Wireless Keyboard"),
        ]

        created_products = []
        for sku, name in products_data:
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": random.choice(categories),
                    "cost": random.randint(5, 50),
                    "price": random.randint(10, 90),
                    "quantity_on_hand": 0,
                    "reorder_level": random.randint(5, 20),
                    "is_active": True,
                },
            )
            created_products.append(p)

        # Transactions
        User = get_user_model()
        actor = User.objects.order_by("id").first()

        for p in created_products:
            # stock in
            qty_in = random.randint(10, 60)
            InventoryTransaction.objects.create(
                product=p,
                transaction_type="IN",
                quantity=qty_in,
                reference="seed_demo",
                note="Initial stock",
                created_by=actor,
            )
            p.quantity_on_hand += qty_in

            # some stock out
            qty_out = random.randint(0, min(20, p.quantity_on_hand))
            if qty_out > 0:
                InventoryTransaction.objects.create(
                    product=p,
                    transaction_type="OUT",
                    quantity=qty_out,
                    reference="seed_demo",
                    note="Sample sales",
                    created_by=actor,
                )
                p.quantity_on_hand -= qty_out

            p.save()

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))