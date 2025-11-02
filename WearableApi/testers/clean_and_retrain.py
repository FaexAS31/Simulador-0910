"""
Script para limpiar datos antiguos y entrenar con datos realistas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

from api.models import Ventana, Lectura, Analisis

print("=" * 60)
print("🗑️  LIMPIEZA DE DATOS ANTIGUOS")
print("=" * 60)

# Contar datos actuales
ventanas_count = Ventana.objects.count()
lecturas_count = Lectura.objects.count()
analisis_count = Analisis.objects.count()

print(f"\n📊 Datos actuales:")
print(f"   - Ventanas: {ventanas_count}")
print(f"   - Lecturas: {lecturas_count}")
print(f"   - Análisis: {analisis_count}")

if ventanas_count > 0:
    print(f"\n⚠️  ¿Quieres eliminar TODOS los datos para reentrenar? (y/n): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        # Eliminar en orden correcto (respetando foreign keys)
        Analisis.objects.all().delete()
        Lectura.objects.all().delete()
        Ventana.objects.all().delete()
        
        print("✅ Todos los datos eliminados")
        print("\n💡 Ahora ejecuta: py train_model.py")
        print("   Y responde 'y' cuando pregunte si insertar datos de muestra")
    else:
        print("❌ Operación cancelada")
else:
    print("\n✅ No hay datos para eliminar")
    print("💡 Ejecuta: py train_model.py")

print("\n" + "=" * 60)
