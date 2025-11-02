import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

from api.models import Ventana, Lectura, Analisis

print("\n" + "=" * 70)
print("🔍 VERIFICACIÓN RÁPIDA")
print("=" * 70)

# Última ventana
v = Ventana.objects.order_by('-id').first()
print(f"\n🆔 Última ventana ID: {v.id}")
print(f"📅 Creada: {v.created_at}")
print(f"👤 Consumidor: {v.consumidor.nombre}")

# Lecturas
lecturas_count = Lectura.objects.filter(ventana=v).count()
print(f"\n📊 Lecturas en esta ventana: {lecturas_count}")

if lecturas_count > 0:
    lecturas = Lectura.objects.filter(ventana=v)[:5]
    print("\n❤️  Primeras 5 Heart Rates:")
    for i, l in enumerate(lecturas, 1):
        print(f"  {i}. {l.heart_rate:.2f} BPM")

# Features
print(f"\n🧮 Features calculadas:")
print(f"  HR Mean:       {v.hr_mean}")
print(f"  HR Std:        {v.hr_std}")
print(f"  Accel Energy:  {v.accel_energy}")
print(f"  Gyro Energy:   {v.gyro_energy}")

# Análisis
analisis = Analisis.objects.filter(ventana=v).first()
if analisis:
    print(f"\n🤖 Análisis ML:")
    print(f"  ID: {analisis.id}")
    print(f"  Probabilidad: {analisis.probabilidad_modelo:.2%}")
    print(f"  Predicción: {analisis.urge_label} ({'Urge' if analisis.urge_label == 1 else 'No Urge'})")
else:
    print("\n⚠️  No hay análisis para esta ventana todavía")

print("\n" + "=" * 70)
