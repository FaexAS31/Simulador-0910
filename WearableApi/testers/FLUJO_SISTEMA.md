# 🔄 FLUJO COMPLETO DEL SISTEMA DE SIMULACIÓN

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ⏰ CELERY BEAT (cada 60 segundos)                                     │
│     Tarea programada: simulate_wearable_cycle()                        │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  📦 PASO 1: Crear Ventana                                               │
│                                                                         │
│  Ventana.objects.create(                                                │
│      consumidor = random.choice(consumidores),                          │
│      window_start = now - 1 minuto,                                     │
│      window_end = now                                                   │
│  )                                                                      │
│                                                                         │
│  ✅ Guardado en PostgreSQL → tabla: ventanas                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 PASO 2: Generar 60 Lecturas (1 por segundo simulado)               │
│                                                                         │
│  Parámetros realistas:                                                 │
│    - stress_level = 0.0 - 1.0 (aleatorio)                              │
│    - activity = "rest" | "walking" | "active"                          │
│                                                                         │
│  Para cada segundo (0-59):                                             │
│    Lectura.objects.create(                                              │
│        ventana = ventana,                                               │
│        heart_rate = f(stress, activity) + ruido,                       │
│        accel_x, accel_y, accel_z = magnitud_3d(activity),              │
│        gyro_x, gyro_y, gyro_z = magnitud_3d(activity),                 │
│        created_at = timestamp                                           │
│    )                                                                    │
│                                                                         │
│  ✅ 60 lecturas guardadas en PostgreSQL → tabla: lecturas              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🧮 PASO 3: Invocar Predicción ML (asíncrono)                          │
│                                                                         │
│  predict_smoking_craving.apply_async(                                   │
│      user_id = usuario.id,                                              │
│      features_dict = None  ← Calcula automáticamente                   │
│  )                                                                      │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🔬 TAREA: predict_smoking_craving()                                    │
│                                                                         │
│  3.1) Calcular features desde lecturas:                                │
│       - Obtener últimas lecturas de la ventana                         │
│       - Calcular 11 features:                                          │
│         * hr_mean, hr_std, hr_min, hr_max, hr_range                    │
│         * accel_magnitude_mean, accel_magnitude_std                    │
│         * gyro_magnitude_mean, gyro_magnitude_std                      │
│         * accel_energy, gyro_energy                                    │
│                                                                         │
│  3.2) Guardar features en Ventana:                                     │
│       ventana.hr_mean = features['hr_mean']                            │
│       ventana.hr_std = features['hr_std']                              │
│       ventana.accel_energy = features['accel_energy']                  │
│       ventana.gyro_energy = features['gyro_energy']                    │
│       ventana.save()                                                   │
│                                                                         │
│  ✅ Features guardadas en PostgreSQL → tabla: ventanas (UPDATE)        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🤖 PASO 4: Predicción con Modelo ML                                   │
│                                                                         │
│  4.1) Cargar modelo:                                                   │
│       model_package = joblib.load('models/smoking_craving_model.pkl')  │
│       model = model_package['model']                                   │
│       scaler = model_package['scaler']                                 │
│                                                                         │
│  4.2) Preparar datos:                                                  │
│       X = [features en orden correcto]                                 │
│       X_scaled = scaler.transform(X)                                   │
│                                                                         │
│  4.3) Predecir:                                                        │
│       probability = model.predict_proba(X_scaled)[0][1]                │
│       prediction = 1 if probability > 0.5 else 0                       │
│                                                                         │
│  4.4) Determinar nivel de riesgo:                                      │
│       risk_level = "high" if prob > 0.7                                │
│                  else "medium" if prob > 0.4                           │
│                  else "low"                                            │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  💾 PASO 5: Guardar Análisis                                           │
│                                                                         │
│  Analisis.objects.create(                                               │
│      ventana = ventana,                                                 │
│      modelo_usado = "LogisticRegression_v1",                           │
│      probabilidad_modelo = probability,                                │
│      urge_label = prediction,                                          │
│      accuracy = model_package['metrics']['accuracy'],                  │
│      precision = model_package['metrics']['precision'],                │
│      recall = model_package['metrics']['recall'],                      │
│      f1_score = model_package['metrics']['f1_score'],                  │
│      comentario_modelo = f"Riesgo {risk_level}"                        │
│  )                                                                      │
│                                                                         │
│  ✅ Análisis guardado en PostgreSQL → tabla: analisis                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  🔔 PASO 6: Notificación (si riesgo alto)                              │
│                                                                         │
│  if probability > 0.7:                                                 │
│      Notificacion.objects.create(                                       │
│          consumidor = consumidor,                                       │
│          tipo = 'alerta',                                               │
│          contenido = "⚠️ Alto riesgo detectado...",                    │
│          leida = False                                                  │
│      )                                                                  │
│                                                                         │
│  ✅ Notificación guardada en PostgreSQL → tabla: notificaciones        │
└─────────────────────────────────────────────────────────────────────────┘

                                 │
                                 ▼
                        ⏰ Esperar 60 segundos
                                 │
                                 ▼
                       🔄 Repetir desde PASO 1
```

---

## 📊 Resumen de Tablas Afectadas

| Tabla | Acción | Frecuencia |
|-------|--------|-----------|
| **ventanas** | INSERT + UPDATE | Cada 60s |
| **lecturas** | INSERT (60 registros) | Cada 60s |
| **analisis** | INSERT | Cada 60s |
| **notificaciones** | INSERT (condicional) | Si prob > 0.7 |

---

## 🎯 Datos Generados por Minuto

- **1 Ventana** nueva
- **60 Lecturas** (1 por segundo simulado)
- **1 Análisis** ML
- **0-1 Notificación** (solo si alto riesgo)

---

## 📈 Ejemplo de Volumen de Datos

| Tiempo | Ventanas | Lecturas | Análisis |
|--------|----------|----------|----------|
| 1 hora | 60 | 3,600 | 60 |
| 8 horas | 480 | 28,800 | 480 |
| 24 horas | 1,440 | 86,400 | 1,440 |
| 7 días | 10,080 | 604,800 | 10,080 |

---

## 🔧 Personalización

### Cambiar frecuencia (cada 30 segundos)
```python
# WearableApi/celery.py
'schedule': 30.0  # ← Cambiar aquí
```

### Simular múltiples consumidores
```python
# api/tasks.py - línea ~325
for consumidor in consumidores:  # ← Cambiar de random.choice() a for
    # ... generar datos
```

### Ajustar patrones de estrés
```python
# api/tasks.py - línea ~345
stress_level = random.uniform(0.5, 0.9)  # ← Mayor estrés
```

---

## ✅ Verificación Rápida

```sql
-- Verificar última ventana creada
SELECT id, consumidor_id, window_start, hr_mean, accel_energy
FROM ventanas 
ORDER BY id DESC 
LIMIT 1;

-- Verificar últimas 5 lecturas
SELECT id, ventana_id, heart_rate, accel_x, gyro_x, created_at
FROM lecturas
ORDER BY id DESC
LIMIT 5;

-- Verificar último análisis
SELECT id, ventana_id, probabilidad_modelo, urge_label, comentario_modelo
FROM analisis
ORDER BY id DESC
LIMIT 1;
```

---

## 🚀 Inicio Rápido

```powershell
# Opción más simple:
.\start_simulation.ps1

# O manual:
# Terminal 1
celery -A WearableApi worker --loglevel=info --pool=solo

# Terminal 2
celery -A WearableApi beat --loglevel=info

# Terminal 3 (opcional - monitoreo)
python monitor.py
```
