"""Seed basic business master data: units, conversions, currencies, sizes, colors."""

from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand

UNITS = [
    ("PCS", "Pieces", "count", True),
    ("DZN", "Dozen", "count", False),
    ("MTR", "Meter", "length", True),
    ("YDS", "Yard", "length", False),
    ("KG", "Kilogram", "weight", True),
    ("GM", "Gram", "weight", False),
    ("LTR", "Liter", "volume", True),
]

CONVERSIONS = [
    ("DZN", "PCS", "12"),
    ("YDS", "MTR", "0.9144"),
    ("GM", "KG", "0.001"),
]

CURRENCIES = [
    ("PKR", "Pakistani Rupee", "Rs", True),
    ("USD", "US Dollar", "$", False),
    ("EUR", "Euro", "€", False),
    ("GBP", "British Pound", "£", False),
    ("CNY", "Chinese Yuan", "¥", False),
    ("AED", "UAE Dirham", "د.إ", False),
]

SIZES = [
    ("XS", "Extra Small", 1),
    ("S", "Small", 2),
    ("M", "Medium", 3),
    ("L", "Large", 4),
    ("XL", "Extra Large", 5),
    ("XXL", "Double Extra Large", 6),
]

COLORS = [
    ("BLK", "Black", "#000000"),
    ("WHT", "White", "#FFFFFF"),
    ("NAV", "Navy", "#000080"),
    ("GRY", "Grey", "#808080"),
    ("RED", "Red", "#FF0000"),
    ("BLU", "Blue", "#0000FF"),
]


class Command(BaseCommand):
    help = "Seed basic master data: units of measure, conversions, currencies, sizes, colors (idempotent)."

    def handle(self, *args, **options):
        UnitOfMeasure = apps.get_model("masters", "UnitOfMeasure")
        UomConversion = apps.get_model("masters", "UomConversion")
        Currency = apps.get_model("masters", "Currency")
        Size = apps.get_model("masters", "Size")
        SizeGroup = apps.get_model("masters", "SizeGroup")
        SizeGroupSize = apps.get_model("masters", "SizeGroupSize")
        Color = apps.get_model("masters", "Color")

        units = {}
        for code, name, dimension, is_base in UNITS:
            unit, _ = UnitOfMeasure.objects.update_or_create(
                code=code, defaults={"name": name, "dimension": dimension, "is_base": is_base}
            )
            units[code] = unit

        for from_code, to_code, factor in CONVERSIONS:
            UomConversion.objects.update_or_create(
                from_uom=units[from_code],
                to_uom=units[to_code],
                defaults={"factor": Decimal(factor)},
            )

        for code, name, symbol, is_base in CURRENCIES:
            Currency.objects.update_or_create(code=code, defaults={"name": name, "symbol": symbol, "is_base": is_base})

        size_obj = {}
        for code, name, order in SIZES:
            size, _ = Size.objects.update_or_create(code=code, defaults={"name": name, "sort_order": order})
            size_obj[code] = size

        if not SizeGroup.objects.filter(name="Standard").exists():
            group = SizeGroup.objects.create(name="Standard")
            for i, code in enumerate([s for s, _, _ in SIZES]):
                SizeGroupSize.objects.create(size_group=group, size=size_obj[code], sort_order=i)

        for code, name, hex_value in COLORS:
            Color.objects.update_or_create(code=code, defaults={"name": name, "hex": hex_value})

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(UNITS)} uom, {len(CONVERSIONS)} conversions, {len(CURRENCIES)} currencies, {len(SIZES)} sizes, {len(COLORS)} colors."
            )
        )