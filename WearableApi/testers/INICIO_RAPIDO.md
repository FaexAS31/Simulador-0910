# 🚀 Inicio Rápido - Simulación Continua

## ⚡ Opción 1: Script Todo-en-Uno (RECOMENDADO)

```powershell
.\start_simulation.ps1
```

Elige opción 1 o 2 cuando te pregunte.

---

## ⚡ Opción 2: Manual

### A) Simulador Interactivo
```powershell
python simulator_continuous.py
```
- Control manual con Ctrl+C
- Ideal para testing

### B) Celery Beat (Automático)

**Terminal 1** - Worker:
```powershell
celery -A WearableApi worker --loglevel=info --pool=solo
```

**Terminal 2** - Beat:
```powershell
celery -A WearableApi beat --loglevel=info
```

---

## 📊 Monitor en Tiempo Real

```powershell
python monitor.py
```

Muestra estadísticas actualizadas cada 10 segundos.

---

## 🔍 Verificar Datos

```powershell
python verify_features.py
```

---

## ✅ Pre-requisitos

1. ✅ PostgreSQL corriendo
2. ✅ Modelo ML entrenado: `python train_model.py --auto`
3. ✅ Usuario y Consumidor creados
4. ✅ Celery Worker reiniciado (para cargar código nuevo)

---

## 📝 Notas

- Genera **1 ventana cada minuto**
- **60 lecturas por ventana** (1 por segundo)
- **Features calculadas automáticamente**
- **Predicción ML guardada en `analisis`**
- **Notificaciones si riesgo > 70%**

---

## 📖 Documentación Completa

Ver: `SIMULACION_CONTINUA.md`
