from decimal import Decimal
from core.models import ScooterLevel

levels = [
    (1, Decimal('275.00'), Decimal('3.50')),
    (2, Decimal('650.00'), Decimal('13.00')),
    (3, Decimal('1500.00'), Decimal('30.00')),
    (4, Decimal('3000.00'), Decimal('60.00')),
    (5, Decimal('5000.00'), Decimal('75.00')),
    (6, Decimal('10000.00'), Decimal('150.00')),
    (7, Decimal('25000.00'), Decimal('375.00')),
    (8, Decimal('50000.00'), Decimal('750.00')),
    (9, Decimal('100000.00'), Decimal('1500.00')),
]

for number, price, income in levels:
    ScooterLevel.objects.update_or_create(
        number=number,
        defaults={
            'price': price,
            'income': income,
            'expected_scooter_count': 1,
        }
    )

print("✅ Уровни успешно добавлены или обновлены.")
