# 🧪 Guía de Pruebas con Celery

## 📋 Pre-requisitos

- ✅ Modelo entrenado (`models/smoking_craving_model.pkl`)
- ✅ Datos de prueba en la BD (Ventanas + Lecturas recientes)
- ✅ Redis corriendo (si usas Redis como broker)
- ✅ Usuario con Consumidor asociado

---

## 🚀 Paso 1: Preparar el entorno

### 1.1 Verificar que el modelo existe
```powershell
ls models/smoking_craving_model.pkl
```

### 1.2 Verificar datos de prueba
```powershell
py manage.py shell
```
```python
from api.models import Ventana, Lectura
from django.utils import timezone
from datetime import timedelta

# Verificar ventanas recientes
ventanas = Ventana.objects.filter(
    window_start__gte=timezone.now() - timedelta(minutes=30)
)
print(f"Ventanas recientes: {ventanas.count()}")

if ventanas.count() == 0:
    print("⚠️ No hay ventanas recientes. Ejecuta: py insert_test_data.py")
else:
    v = ventanas.first()
    lecturas = Lectura.objects.filter(ventana=v).count()
    print(f"Lecturas en ventana {v.id}: {lecturas}")
```

---

## 🔥 Paso 2: Iniciar Celery Worker

### Terminal 1 - Celery Worker
```powershell
# En la carpeta del proyecto
cd "C:\Users\MSI\Desktop\9B\Proyecto 9B\API_wearable\Simulador-0910\WearableApi"

# Iniciar worker
celery -A WearableApi worker --loglevel=info --pool=solo
```

**Qué esperar:**
```
 -------------- celery@HOSTNAME v5.x.x (...)
---- **** ----- 
--- * ***  * -- Windows-10.0.xxxxx-...
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         WearableApi:...
- ** ---------- .> transport:   redis://localhost:6379//
- ** ---------- .> results:     disabled://
- *** --- * --- .> concurrency: 1 (solo)
-- ******* ---- .> task events: OFF

[tasks]
  . api.tasks.predict_smoking_craving

[2025-11-01 22:xx:xx,xxx: INFO/MainProcess] Connected to redis://localhost:6379//
[2025-11-01 22:xx:xx,xxx: INFO/MainProcess] mingle: searching for neighbors
[2025-11-01 22:xx:xx,xxx: INFO/MainProcess] mingle: all alone
[2025-11-01 22:xx:xx,xxx: INFO/MainProcess] celery@HOSTNAME ready.
```

✅ **Si ves "celery@HOSTNAME ready" - ¡Está funcionando!**

❌ **Si hay error de conexión a Redis:**
- Verifica que Redis esté corriendo
- O cambia el broker en `settings.py` a `CELERY_BROKER_URL = 'filesystem://'`

---

## 📡 Paso 3: Probar desde Django Shell

### Terminal 2 - Django Shell
```powershell
py manage.py shell
```

### Prueba 1: Predicción Automática (desde lecturas)
```python
from api.tasks import predict_smoking_craving

# Ejecutar tarea asíncrona
result = predict_smoking_craving.delay(user_id=2, features_dict=None)

# Ver estado
print(f"Task ID: {result.id}")
print(f"Estado: {result.state}")

# Esperar resultado (blocking)
import time
time.sleep(5)

# Obtener resultado
output = result.get(timeout=10)
print(f"\n🎯 Resultado:")
print(output)
```

### Prueba 2: Predicción con Features Manuales
```python
from api.tasks import predict_smoking_craving

# Features manuales para testing
manual_features = {
    'hr_mean': 95.5,
    'hr_std': 12.2,
    'hr_min': 75.0,
    'hr_max': 110.0,
    'hr_range': 35.0,
    'accel_magnitude_mean': 1.8,
    'accel_magnitude_std': 0.7,
    'gyro_magnitude_mean': 0.9,
    'gyro_magnitude_std': 0.4,
    'accel_energy': 200.0,
    'gyro_energy': 100.0
}

result = predict_smoking_craving.delay(
    user_id=2, 
    features_dict=manual_features
)

print(f"Task ID: {result.id}")
time.sleep(3)
print(result.get(timeout=10))
```

---

## 🌐 Paso 4: Probar desde API REST

### Herramienta: Postman, Insomnia, o Thunder Client (VS Code)

### 4.1 Login (obtener token)
```http
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
  "email": "juan.perez@email.com",
  "password": "tu_password"
}
```

**Respuesta:**
```json
{
  "token": "abc123xyz...",
  "user_id": 2
}
```

### 4.2 Predicción Automática
```http
POST http://localhost:8000/api/predict/
Authorization: Bearer abc123xyz...
Content-Type: application/json

{}
```

**Respuesta Esperada:**
```json
{
  "task_id": "d7e2e62b-02b2-4ee8-ab39-97db6226e6c9",
  "status": "processing",
  "message": "Prediction task started. Will calculate from sensor readings."
}
```

### 4.3 Verificar Estado de la Tarea
```http
GET http://localhost:8000/api/task-status/{task_id}/
Authorization: Bearer abc123xyz...
```

**Respuesta cuando está listo:**
```json
{
  "status": "completed",
  "result": {
    "success": true,
    "analisis_id": 15,
    "probability": 0.85,
    "prediction": 1,
    "risk_level": "high",
    "comentario": "Alto riesgo de deseo detectado (85.0%). Intervención inmediata recomendada.",
    "model_metrics": {
      "accuracy": 1.0,
      "precision": 1.0,
      "recall": 1.0,
      "f1_score": 1.0
    },
    "user_id": 2,
    "consumidor_id": 1
  }
}
```

### 4.4 Predicción con Features Manuales
```http
POST http://localhost:8000/api/predict/
Authorization: Bearer abc123xyz...
Content-Type: application/json

{
  "manual_features": {
    "hr_mean": 95.5,
    "hr_std": 12.2,
    "hr_min": 75.0,
    "hr_max": 110.0,
    "hr_range": 35.0,
    "accel_magnitude_mean": 1.8,
    "accel_magnitude_std": 0.7,
    "gyro_magnitude_mean": 0.9,
    "gyro_magnitude_std": 0.4,
    "accel_energy": 200.0,
    "gyro_energy": 100.0
  }
}
```

---

## 📊 Paso 5: Monitorear en Terminal de Celery

En la **Terminal 1** (donde corre Celery), deberías ver:

```
[2025-11-01 22:xx:xx] [INFO] Starting prediction for user 2
[2025-11-01 22:xx:xx] [INFO] Received features_dict: None
[2025-11-01 22:xx:xx] [INFO] features_dict is None: True
[2025-11-01 22:xx:xx] [INFO] Calculating features from sensor readings for consumidor 1
[2025-11-01 22:xx:xx] [INFO] Features calculated: {'hr_mean': 85.5, ...}
[2025-11-01 22:xx:xx] [INFO] Prediction: probability=85.00%, risk=high
[2025-11-01 22:xx:xx] [INFO] Prediction saved: Analisis ID 15, risk=high, prob=85.00%
[2025-11-01 22:xx:xx] [INFO] High risk notification created for consumidor 1
[2025-11-01 22:xx:xx,xxx: INFO/MainProcess] Task api.tasks.predict_smoking_craving[xxx-xxx-xxx] succeeded in 2.5s
```

---

## ✅ Checklist de Validación

- [ ] Celery worker arranca sin errores
- [ ] Task aparece en la lista de tasks disponibles
- [ ] Predicción desde shell funciona
- [ ] Predicción automática (sin features) funciona
- [ ] Predicción manual (con features) funciona
- [ ] API REST responde con task_id
- [ ] task-status endpoint devuelve el resultado
- [ ] Logs de Celery muestran el flujo completo
- [ ] Analisis se guarda en BD con métricas
- [ ] Notificación se crea para alto riesgo
- [ ] Features se calculan correctamente desde lecturas

---

## 🐛 Troubleshooting

### Error: "No recent sensor readings found"
**Solución:**
```powershell
py insert_test_data.py
# Responde 'n' a limpiar datos antiguos
```

### Error: "Connection to Redis failed"
**Solución:**
- Verifica Redis: `redis-cli ping` (debe responder PONG)
- O cambia a broker de memoria en development

### Error: "'dict' object has no attribute 'predict'"
**Solución:**
- Reinicia Celery worker (Ctrl+C y vuelve a ejecutar)
- Limpia caché: `py manage.py shell` → `from django.core.cache import cache; cache.clear()`

### Error: "Missing required features"
**Solución:**
- Asegúrate de enviar body vacío `{}` o con todas las 11 features
- Verifica que las lecturas existen y son recientes

---

## 📝 Script de Prueba Completo

Guarda esto como `test_celery_full.py`:

```python
import time
from api.tasks import predict_smoking_craving

print("=" * 60)
print("🧪 PRUEBA COMPLETA DE CELERY")
print("=" * 60)

# Test 1: Predicción automática
print("\n🔬 Test 1: Predicción Automática")
result1 = predict_smoking_craving.delay(user_id=2, features_dict=None)
print(f"   Task ID: {result1.id}")
time.sleep(3)

try:
    output1 = result1.get(timeout=10)
    print(f"   ✅ Success: {output1.get('success')}")
    print(f"   Probability: {output1.get('probability', 0):.2%}")
    print(f"   Risk: {output1.get('risk_level')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Predicción manual
print("\n🔬 Test 2: Predicción Manual")
features = {
    'hr_mean': 95.5, 'hr_std': 12.2, 'hr_min': 75.0, 'hr_max': 110.0,
    'hr_range': 35.0, 'accel_magnitude_mean': 1.8, 'accel_magnitude_std': 0.7,
    'gyro_magnitude_mean': 0.9, 'gyro_magnitude_std': 0.4,
    'accel_energy': 200.0, 'gyro_energy': 100.0
}

result2 = predict_smoking_craving.delay(user_id=2, features_dict=features)
print(f"   Task ID: {result2.id}")
time.sleep(3)

try:
    output2 = result2.get(timeout=10)
    print(f"   ✅ Success: {output2.get('success')}")
    print(f"   Probability: {output2.get('probability', 0):.2%}")
    print(f"   Risk: {output2.get('risk_level')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Pruebas completadas")
print("=" * 60)
```

**Ejecutar:**
```powershell
py manage.py shell < test_celery_full.py
```

---

## 🎯 Resultado Esperado

Si todo funciona correctamente:
- ✅ Worker procesa tareas sin errores
- ✅ Predicciones se completan en ~2-5 segundos
- ✅ Análisis se guardan en BD
- ✅ Notificaciones se crean para alto riesgo
- ✅ API devuelve resultados completos
