"""
Script simple para verificar que las features se guardan en Ventana
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

from api.models import Ventana
from django.db.models import Q

print("=" * 60)
print("🔍 VERIFICANDO FEATURES EN VENTANA")
print("=" * 60)

# Obtener últimas 10 ventanas
ventanas = Ventana.objects.all().order_by('-id')[:10]

print(f"\n📊 Últimas 10 ventanas:")
print("-" * 60)

for v in ventanas:
    print(f"\nVentana ID: {v.id}")
    print(f"  Consumidor: {v.consumidor_id}")
    print(f"  Created: {v.window_start}")
    print(f"  hr_mean: {v.hr_mean}")
    print(f"  hr_std: {v.hr_std}")
    print(f"  accel_energy: {v.accel_energy}")
    print(f"  gyro_energy: {v.gyro_energy}")

# Contar cuántas tienen features
ventanas_con_features = Ventana.objects.filter(
    Q(hr_mean__isnull=False) | 
    Q(hr_std__isnull=False) | 
    Q(accel_energy__isnull=False) | 
    Q(gyro_energy__isnull=False)
).count()

total_ventanas = Ventana.objects.count()

print("\n" + "=" * 60)
print(f"📊 Resumen:")
print(f"   Total ventanas: {total_ventanas}")
print(f"   Con features guardadas: {ventanas_con_features}")
print(f"   Sin features: {total_ventanas - ventanas_con_features}")
print("=" * 60)
