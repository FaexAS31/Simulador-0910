# Sistema de Simulación Continua - Wearable API

## 📋 Descripción

Este sistema simula datos de sensores de wearable de forma continua y automática:

1. **Cada minuto** → Genera nueva ventana temporal
2. **60 lecturas/ventana** → Simula 1 lectura por segundo
3. **Cálculo automático** → Features calculadas desde lecturas
4. **Predicción ML** → Análisis de riesgo guardado en DB
5. **Notificaciones** → Alertas cuando hay alto riesgo

## 🚀 Opciones de Ejecución

### Opción 1: Script Manual (simulator_continuous.py)

Ejecutar simulador manualmente con control interactivo:

```powershell
python simulator_continuous.py
```

**Características:**
- ✅ Control manual (Start/Stop con Ctrl+C)
- ✅ Selección de consumidor específico
- ✅ Logs detallados en tiempo real
- ✅ Estadísticas cada 5 ciclos
- ⚠️ Requiere terminal abierta

**Cuándo usar:**
- Testing y desarrollo
- Debugging de issues
- Demostración interactiva
- Necesitas ver logs en vivo

---

### Opción 2: Celery Beat (RECOMENDADO para producción)

Sistema automático con Celery Beat:

#### Paso 1: Iniciar Celery Worker

```powershell
celery -A WearableApi worker --loglevel=info --pool=solo
```

#### Paso 2: Iniciar Celery Beat (en otra terminal)

```powershell
celery -A WearableApi beat --loglevel=info
```

**Características:**
- ✅ Totalmente automático
- ✅ Reinicio automático si falla
- ✅ Funciona en background
- ✅ Escalable (múltiples workers)
- ✅ Persistencia entre reinicios
- ✅ Puede ejecutarse como servicio Windows

**Cuándo usar:**
- Producción
- Simulaciones largas (días/semanas)
- Ambiente sin supervisión
- Necesitas alta disponibilidad

---

## 📊 Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    CELERY BEAT (cada 60s)                   │
│                  Dispara: simulate_wearable_cycle()         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Crear Ventana                                      │
│  - window_start = ahora - 1 min                             │
│  - window_end = ahora                                       │
│  - consumidor = aleatorio (o específico)                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Generar 60 Lecturas                                │
│  Para cada segundo (0-59):                                  │
│    - heart_rate (basado en estrés + actividad)             │
│    - accel_x, accel_y, accel_z (movimiento 3D)             │
│    - gyro_x, gyro_y, gyro_z (rotación 3D)                  │
│  → Guardar en tabla: lecturas                               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Calcular Features (automático)                    │
│  Función: calculate_features_from_readings()                │
│    - hr_mean, hr_std, hr_min, hr_max, hr_range             │
│    - accel_magnitude_mean, accel_magnitude_std              │
│    - gyro_magnitude_mean, gyro_magnitude_std                │
│    - accel_energy, gyro_energy                              │
│  → Guardar en tabla: ventanas (campos de features)         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 4: Predicción ML                                      │
│  Tarea: predict_smoking_craving()                           │
│    - Cargar modelo: smoking_craving_model.pkl               │
│    - Predecir: probability, risk_level                      │
│  → Guardar en tabla: analisis                               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 5: Notificación (si riesgo alto)                     │
│  Si probability > 0.7:                                      │
│    - Crear registro en tabla: notificaciones                │
│    - tipo = 'alerta'                                        │
│    - contenido = mensaje de recomendación                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Configuración de Parámetros

### Modificar Frecuencia de Simulación

Editar `WearableApi/celery.py`:

```python
app.conf.beat_schedule = {
    'simulate-wearable-data-every-minute': {
        'task': 'api.tasks.simulate_wearable_cycle',
        'schedule': 60.0,  # ← Cambiar aquí (segundos)
    },
}
```

Ejemplos:
- **30 segundos**: `'schedule': 30.0`
- **2 minutos**: `'schedule': 120.0`
- **5 minutos**: `'schedule': 300.0`

### Simular Múltiples Consumidores

Editar `api/tasks.py`, función `simulate_wearable_cycle()`:

```python
# Línea ~325 - Cambiar de:
consumidor = random.choice(consumidores)

# A (para simular TODOS los consumidores):
for consumidor in consumidores:
    # ... resto del código
```

### Ajustar Patrones de Datos

Editar `api/tasks.py` líneas ~350-370:

```python
# Nivel de estrés (0.0 - 1.0)
stress_level = random.uniform(0.2, 0.8)  # ← Cambiar rango

# Actividad
activity = random.choice(['rest', 'walking', 'active'])  # ← Cambiar opciones

# Frecuencia cardíaca base
if activity == 'rest':
    base_hr = random.uniform(60, 75)  # ← Ajustar rango
```

---

## 🔍 Verificar que Funciona

### 1. Verificar Celery Beat está corriendo

```powershell
# Buscar proceso
Get-Process | Where-Object {$_.ProcessName -like "*celery*"}
```

### 2. Ver últimas ventanas creadas

```powershell
python verify_features.py
```

### 3. Consultar base de datos

```sql
-- Últimas 10 ventanas con features
SELECT 
    id, 
    consumidor_id,
    window_start,
    hr_mean, 
    hr_std, 
    accel_energy, 
    gyro_energy 
FROM ventanas 
ORDER BY id DESC 
LIMIT 10;

-- Últimos 10 análisis
SELECT 
    id,
    ventana_id,
    modelo_usado,
    probabilidad_modelo,
    urge_label,
    comentario_modelo,
    created_at
FROM analisis
ORDER BY id DESC
LIMIT 10;

-- Notificaciones de alto riesgo
SELECT 
    id,
    consumidor_id,
    tipo,
    contenido,
    fecha_envio,
    leida
FROM notificaciones
WHERE tipo = 'alerta'
ORDER BY fecha_envio DESC
LIMIT 10;
```

---

## 🛑 Detener Simulación

### Script Manual
- Presionar **Ctrl+C** en la terminal

### Celery Beat
```powershell
# Detener Beat (terminal 2)
Ctrl+C

# Detener Worker (terminal 1)
Ctrl+C
```

---

## 📈 Monitoreo

### Ver logs de Celery Worker

Los logs muestran:
- ✅ Ventanas creadas
- ✅ Lecturas generadas
- ✅ Predictions ejecutadas
- ✅ Notificaciones enviadas
- ❌ Errores si ocurren

### Estadísticas en tiempo real

Ejecutar en otra terminal:

```powershell
python -c "
from api.models import Ventana, Analisis, Notificacion
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

print('📊 ESTADÍSTICAS')
print(f'Ventanas totales: {Ventana.objects.count()}')
print(f'Análisis totales: {Analisis.objects.count()}')
print(f'Notificaciones: {Notificacion.objects.count()}')
"
```

---

## ⚠️ Troubleshooting

### Problema: Celery Beat no dispara tareas

**Solución:**
1. Verificar que ambos procesos estén corriendo (worker + beat)
2. Revisar `WearableApi/celery.py` configuración
3. Borrar archivo `celerybeat-schedule.db` y reiniciar

```powershell
rm celerybeat-schedule.db
celery -A WearableApi beat --loglevel=info
```

### Problema: Features siguen en NULL

**Solución:**
1. Reiniciar Celery Worker (tiene código viejo cacheado)
2. Verificar modelo ML existe: `models/smoking_craving_model.pkl`
3. Revisar logs de Celery para errores

### Problema: No se crean notificaciones

**Verificar:**
- Probabilidad del modelo > 0.7 (umbral de alto riesgo)
- Función `send_notification()` habilitada en `tasks.py`
- Logs de Celery para confirmar envío

---

## 🔧 Comandos Útiles

```powershell
# Ver última tarea ejecutada
celery -A WearableApi inspect active

# Ver tareas programadas
celery -A WearableApi inspect scheduled

# Ver estado de workers
celery -A WearableApi inspect stats

# Borrar todas las tareas pendientes
celery -A WearableApi purge

# Reiniciar worker con código actualizado
# Ctrl+C y volver a ejecutar:
celery -A WearableApi worker --loglevel=info --pool=solo
```

---

## 📝 Notas Importantes

1. **PostgreSQL debe estar corriendo** antes de iniciar simulación
2. **Modelo ML debe existir**: ejecutar `python train_model.py --auto` si no existe
3. **Consumidor debe existir**: crear usuario y consumidor primero
4. **En Windows usar `--pool=solo`** para Celery Worker
5. **Features calculadas automáticamente** desde lecturas (no manual)
6. **Ventanas antiguas permanecen NULL** (solo nuevas tienen features)

---

## 🎉 Resumen

| Método | Automático | Background | Producción | Debugging |
|--------|-----------|-----------|-----------|-----------|
| **Script Manual** | ❌ | ❌ | ❌ | ✅ |
| **Celery Beat** | ✅ | ✅ | ✅ | ⚠️ |

**Recomendación:**
- **Desarrollo/Testing**: Usar script manual
- **Producción/Demo**: Usar Celery Beat
