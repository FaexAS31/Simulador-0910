"""
Script completo para probar Celery con predicciones ML
Ejecutar: py manage.py shell < test_celery_full.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

import time
from api.tasks import predict_smoking_craving
from api.models import Usuario, Ventana, Lectura
from django.utils import timezone
from datetime import timedelta

print("=" * 70)
print("🧪 PRUEBA COMPLETA DE CELERY + MODELO ML")
print("=" * 70)

# Verificar pre-requisitos
print("\n📋 Verificando pre-requisitos...")

# 1. Usuario
try:
    usuario = Usuario.objects.get(id=2)
    print(f"✅ Usuario: {usuario.email} (ID: {usuario.id})")
except Usuario.DoesNotExist:
    print("❌ Usuario con ID=2 no existe")
    print("💡 Cambia el ID o crea el usuario")
    exit(1)

# 2. Consumidor
try:
    consumidor = usuario.consumidor
    print(f"✅ Consumidor: ID {consumidor.id}")
except:
    print("❌ Usuario no tiene Consumidor asociado")
    exit(1)

# 3. Ventanas recientes
ventanas_recientes = Ventana.objects.filter(
    consumidor=consumidor,
    window_start__gte=timezone.now() - timedelta(minutes=30)
)

if ventanas_recientes.count() == 0:
    print("⚠️  No hay ventanas recientes (últimos 30 min)")
    print("💡 Ejecuta: py insert_test_data.py")
    print("\n⏭️  Continuando con test manual solamente...")
    has_recent_data = False
else:
    ventana = ventanas_recientes.first()
    lecturas_count = Lectura.objects.filter(ventana=ventana).count()
    print(f"✅ Ventanas recientes: {ventanas_recientes.count()}")
    print(f"✅ Lecturas en ventana más reciente: {lecturas_count}")
    has_recent_data = True

# 4. Modelo ML
import os
if os.path.exists('models/smoking_craving_model.pkl'):
    print("✅ Modelo ML encontrado: models/smoking_craving_model.pkl")
else:
    print("❌ Modelo ML no encontrado")
    print("💡 Ejecuta: py train_model.py --auto")
    exit(1)

print("\n" + "=" * 70)

# TEST 1: Predicción Automática (desde lecturas)
if has_recent_data:
    print("\n🔬 TEST 1: Predicción Automática (desde lecturas del wearable)")
    print("-" * 70)
    
    try:
        result1 = predict_smoking_craving.delay(user_id=usuario.id, features_dict=None)
        print(f"   📤 Tarea enviada a Celery")
        print(f"   🆔 Task ID: {result1.id}")
        print(f"   ⏳ Esperando resultado...")
        
        # Esperar con timeout
        output1 = result1.get(timeout=15)
        
        if output1.get('success'):
            print(f"\n   ✅ ÉXITO!")
            print(f"   📊 Resultados:")
            print(f"      - Analisis ID: {output1.get('analisis_id')}")
            print(f"      - Probabilidad: {output1.get('probability', 0):.2%}")
            print(f"      - Predicción: {output1.get('prediction')} (0=No urge, 1=Urge)")
            print(f"      - Nivel de Riesgo: {output1.get('risk_level').upper()}")
            print(f"      - Comentario: {output1.get('comentario')}")
            
            metrics = output1.get('model_metrics', {})
            if any(metrics.values()):
                print(f"\n   📈 Métricas del Modelo:")
                print(f"      - Accuracy:  {metrics.get('accuracy', 'N/A')}")
                print(f"      - Precision: {metrics.get('precision', 'N/A')}")
                print(f"      - Recall:    {metrics.get('recall', 'N/A')}")
                print(f"      - F1-Score:  {metrics.get('f1_score', 'N/A')}")
        else:
            print(f"\n   ❌ FALLÓ")
            print(f"   Error: {output1.get('error')}")
            print(f"   Sugerencia: {output1.get('suggestion', 'N/A')}")
            
    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        print(f"   💡 Asegúrate de que Celery worker esté corriendo")
else:
    print("\n⏭️  TEST 1 omitido (no hay datos recientes)")

# TEST 2: Predicción Manual (con features)
print("\n" + "=" * 70)
print("\n🔬 TEST 2: Predicción Manual (con features proporcionadas)")
print("-" * 70)

# Features que simulan alto riesgo
features_alto_riesgo = {
    'hr_mean': 98.5,
    'hr_std': 14.2,
    'hr_min': 80.0,
    'hr_max': 120.0,
    'hr_range': 40.0,
    'accel_magnitude_mean': 2.1,
    'accel_magnitude_std': 0.9,
    'gyro_magnitude_mean': 1.2,
    'gyro_magnitude_std': 0.5,
    'accel_energy': 250.0,
    'gyro_energy': 120.0
}

try:
    result2 = predict_smoking_craving.delay(
        user_id=usuario.id, 
        features_dict=features_alto_riesgo
    )
    print(f"   📤 Tarea enviada a Celery")
    print(f"   🆔 Task ID: {result2.id}")
    print(f"   📊 Features enviadas: Alto Riesgo simulado")
    print(f"   ⏳ Esperando resultado...")
    
    output2 = result2.get(timeout=15)
    
    if output2.get('success'):
        print(f"\n   ✅ ÉXITO!")
        print(f"   📊 Resultados:")
        print(f"      - Analisis ID: {output2.get('analisis_id')}")
        print(f"      - Probabilidad: {output2.get('probability', 0):.2%}")
        print(f"      - Predicción: {output2.get('prediction')} (0=No urge, 1=Urge)")
        print(f"      - Nivel de Riesgo: {output2.get('risk_level').upper()}")
        print(f"      - Comentario: {output2.get('comentario')}")
    else:
        print(f"\n   ❌ FALLÓ")
        print(f"   Error: {output2.get('error')}")
        
except Exception as e:
    print(f"\n   ❌ ERROR: {e}")
    print(f"   💡 Asegúrate de que Celery worker esté corriendo")

# TEST 3: Predicción con Bajo Riesgo
print("\n" + "=" * 70)
print("\n🔬 TEST 3: Predicción Manual (bajo riesgo simulado)")
print("-" * 70)

features_bajo_riesgo = {
    'hr_mean': 68.5,
    'hr_std': 6.2,
    'hr_min': 60.0,
    'hr_max': 78.0,
    'hr_range': 18.0,
    'accel_magnitude_mean': 0.5,
    'accel_magnitude_std': 0.2,
    'gyro_magnitude_mean': 0.2,
    'gyro_magnitude_std': 0.1,
    'accel_energy': 80.0,
    'gyro_energy': 30.0
}

try:
    result3 = predict_smoking_craving.delay(
        user_id=usuario.id, 
        features_dict=features_bajo_riesgo
    )
    print(f"   📤 Tarea enviada a Celery")
    print(f"   🆔 Task ID: {result3.id}")
    print(f"   📊 Features enviadas: Bajo Riesgo simulado")
    print(f"   ⏳ Esperando resultado...")
    
    output3 = result3.get(timeout=15)
    
    if output3.get('success'):
        print(f"\n   ✅ ÉXITO!")
        print(f"   📊 Resultados:")
        print(f"      - Probabilidad: {output3.get('probability', 0):.2%}")
        print(f"      - Nivel de Riesgo: {output3.get('risk_level').upper()}")
        print(f"      - Comentario: {output3.get('comentario')}")
    else:
        print(f"\n   ❌ FALLÓ")
        print(f"   Error: {output3.get('error')}")
        
except Exception as e:
    print(f"\n   ❌ ERROR: {e}")

# Resumen Final
print("\n" + "=" * 70)
print("✅ PRUEBAS COMPLETADAS")
print("=" * 70)

print("\n📊 Resumen:")
print(f"   - Usuario probado: {usuario.email}")
print(f"   - Tests ejecutados: 3")
print(f"   - Modelo: LogisticRegression_v1")

print("\n💡 Próximos pasos:")
print("   1. Verifica los registros en la tabla 'analisis' de la BD")
print("   2. Revisa los logs de Celery en la otra terminal")
print("   3. Si hay notificaciones, revisa la tabla 'notificacion'")
print("   4. Prueba el endpoint REST: POST /api/predict/")

print("\n" + "=" * 70)
