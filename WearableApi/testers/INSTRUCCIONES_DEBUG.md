# 🐛 Instrucciones para Debuggear el Error

## Problema Actual
El error indica que las features calculadas no coinciden con las esperadas por el modelo.

## ✅ Pasos para Resolver:

### 1. **Reiniciar Celery** (CRÍTICO)
El código actualizado tiene nuevos logs de debug que te dirán exactamente qué está pasando.

En la terminal donde corre Celery:
1. Presiona `Ctrl+C` para detenerlo
2. Ejecuta nuevamente:
   ```powershell
   celery -A WearableApi worker --loglevel=info --pool=solo
   ```

### 2. **Hacer una petición POST al endpoint**

Opción A - Body vacío (automático):
```bash
POST http://localhost:8000/api/predict/
Headers: Authorization: Bearer <tu_token>
Body: {}
```

Opción B - Con features manuales:
```bash
POST http://localhost:8000/api/predict/
Headers: Authorization: Bearer <tu_token>
Body: {
  "manual_features": {
    "hr_mean": 85.5,
    "hr_std": 10.2,
    "hr_min": 70,
    "hr_max": 100,
    "hr_range": 30,
    "accel_magnitude_mean": 1.2,
    "accel_magnitude_std": 0.5,
    "gyro_magnitude_mean": 0.8,
    "gyro_magnitude_std": 0.3,
    "accel_energy": 150.0,
    "gyro_energy": 80.0
  }
}
```

### 3. **Ver los logs de debug**

Después de reiniciar Celery y hacer la petición, deberías ver algo como:

```
[INFO] Starting prediction for user 2
[INFO] Received features_dict: None
[INFO] features_dict is None: True
[INFO] features_dict type: <class 'NoneType'>
[INFO] Calculating features from sensor readings for consumidor X
```

O si hay un problema:

```
[INFO] Received features_dict: {}
[INFO] features_dict is None: False
[INFO] features_dict type: <class 'dict'>
[INFO] Calculating features from sensor readings for consumidor X
```

### 4. **Posibles Escenarios**

#### Escenario A: No hay lecturas recientes
```
[ERROR] No recent sensor readings found. Cannot make prediction.
```
**Solución:** Inserta datos de prueba con `python train_model.py`

#### Escenario B: El modelo no existe
```
[ERROR] ML model file not found at 'models/smoking_craving_model.pkl'
```
**Solución:** Entrena el modelo con `python train_model.py`

#### Escenario C: Features incorrectas
```
[ERROR] Missing required features: ...
```
**Solución:** Asegúrate de usar el formato correcto de `manual_features`

---

## 📋 Checklist de Verificación

- [ ] Celery reiniciado con el código actualizado
- [ ] Usuario con id=2 existe y tiene Consumidor asociado
- [ ] Hay Ventanas recientes (últimos 30 minutos) para ese Consumidor
- [ ] Hay Lecturas en esas Ventanas
- [ ] El modelo existe en `models/smoking_craving_model.pkl`
- [ ] El body del POST es `{}` o tiene `manual_features` correcto

---

## 🔍 Comando para verificar datos

Si tienes acceso a Django shell:

```python
python manage.py shell

from api.models import Usuario, Consumidor, Ventana, Lectura
from django.utils import timezone
from datetime import timedelta

# Verificar usuario
u = Usuario.objects.get(id=2)
print(f"Usuario: {u.email}")
print(f"Tiene consumidor: {hasattr(u, 'consumidor')}")

# Verificar ventanas recientes
c = u.consumidor
ventanas = Ventana.objects.filter(
    consumidor=c,
    window_start__gte=timezone.now() - timedelta(minutes=30)
)
print(f"Ventanas recientes: {ventanas.count()}")

if ventanas.exists():
    v = ventanas.first()
    lecturas = Lectura.objects.filter(ventana=v)
    print(f"Lecturas en ventana {v.id}: {lecturas.count()}")
```

---

## 💡 Si todo falla

Envía una petición con `manual_features` para probar que el flujo funciona:

```bash
POST /api/predict/
{
  "manual_features": {
    "hr_mean": 85.0,
    "hr_std": 10.0,
    "hr_min": 70.0,
    "hr_max": 100.0,
    "hr_range": 30.0,
    "accel_magnitude_mean": 1.2,
    "accel_magnitude_std": 0.5,
    "gyro_magnitude_mean": 0.8,
    "gyro_magnitude_std": 0.3,
    "accel_energy": 150.0,
    "gyro_energy": 80.0
  }
}
```

Esto debería funcionar independientemente de si tienes lecturas o no.
