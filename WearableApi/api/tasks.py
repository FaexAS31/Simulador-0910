from celery import shared_task
import logging
import numpy as np
import pandas as pd
from django.core.cache import cache
from django.utils import timezone
from api.models import Consumidor, Analisis, Ventana, Usuario, Notificacion, Deseo, Lectura

logger = logging.getLogger(__name__)


def calculate_features_from_readings(consumidor, time_window_minutes=30):
    """
    Calculate ML features from recent sensor readings
    
    Args:
        consumidor: Consumidor instance
        time_window_minutes: How many minutes back to look for readings
        
    Returns:
        dict with calculated features
    """
    # Get recent readings
    time_threshold = timezone.now() - timezone.timedelta(minutes=time_window_minutes)
    
    recent_ventanas = Ventana.objects.filter(
        consumidor=consumidor,
        window_start__gte=time_threshold
    ).order_by('-window_start')[:1]
    
    if not recent_ventanas.exists():
        logger.warning(f"No recent ventanas found for consumidor {consumidor.id}")
        return None
    
    ventana = recent_ventanas.first()
    lecturas = Lectura.objects.filter(ventana=ventana)
    
    if not lecturas.exists():
        logger.warning(f"No lecturas found in ventana {ventana.id}")
        return None
    
    # Convert to lists
    heart_rates = [l.heart_rate or 0 for l in lecturas]
    accel_x = [l.accel_x or 0 for l in lecturas]
    accel_y = [l.accel_y or 0 for l in lecturas]
    accel_z = [l.accel_z or 0 for l in lecturas]
    gyro_x = [l.gyro_x or 0 for l in lecturas]
    gyro_y = [l.gyro_y or 0 for l in lecturas]
    gyro_z = [l.gyro_z or 0 for l in lecturas]
    
    # Calculate features
    hr_array = np.array(heart_rates)
    
    accel_magnitude = np.sqrt(
        np.array(accel_x)**2 + 
        np.array(accel_y)**2 + 
        np.array(accel_z)**2
    )
    
    gyro_magnitude = np.sqrt(
        np.array(gyro_x)**2 + 
        np.array(gyro_y)**2 + 
        np.array(gyro_z)**2
    )
    
    features = {
        'hr_mean': float(np.mean(hr_array)),
        'hr_std': float(np.std(hr_array)),
        'hr_min': float(np.min(hr_array)),
        'hr_max': float(np.max(hr_array)),
        'hr_range': float(np.max(hr_array) - np.min(hr_array)),
        'accel_magnitude_mean': float(np.mean(accel_magnitude)),
        'accel_magnitude_std': float(np.std(accel_magnitude)),
        'gyro_magnitude_mean': float(np.mean(gyro_magnitude)),
        'gyro_magnitude_std': float(np.std(gyro_magnitude)),
        'accel_energy': float(np.sum(np.array(accel_x)**2 + np.array(accel_y)**2 + np.array(accel_z)**2)),
        'gyro_energy': float(np.sum(np.array(gyro_x)**2 + np.array(gyro_y)**2 + np.array(gyro_z)**2)),
    }
    
    return features, ventana


@shared_task(bind=True, max_retries=3)
def predict_smoking_craving(self, user_id, features_dict=None):
    """
    Async task to predict smoking craving
    
    Args:
        user_id: Usuario ID
        features_dict: Optional - if not provided, will calculate from recent readings
    """
    try:
        logger.info(f"Starting prediction for user {user_id}")
        
        # Get usuario
        try:
            usuario = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            error_msg = f"Usuario {user_id} does not exist"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # Get consumidor (with better error handling)
        try:
            consumidor = usuario.consumidor
        except Consumidor.DoesNotExist:
            error_msg = f"Usuario {user_id} has no linked Consumidor record"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user_id': user_id,
                'user_email': usuario.email,
                'suggestion': 'Create a Consumidor record for this Usuario'
            }
        
        # Calculate features from sensor readings if not provided
        logger.info(f"Received features_dict: {features_dict}")
        logger.info(f"features_dict is None: {features_dict is None}")
        logger.info(f"features_dict type: {type(features_dict)}")
        
        # Check if features_dict is None or empty
        if features_dict is None or len(features_dict) == 0 or 'hr_mean' not in features_dict:
            logger.info(f"Calculating features from sensor readings for consumidor {consumidor.id}")
            result = calculate_features_from_readings(consumidor)
            
            if result is None:
                error_msg = "No recent sensor readings found. Cannot make prediction."
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'suggestion': 'Ensure wearable is sending sensor data (Lectura records)'
                }
            
            features_dict, existing_ventana = result
            logger.info(f"Features calculated: {features_dict}")
        else:
            logger.info(f"Using provided manual features")
            existing_ventana = None
        
        # Check if ML model file exists
        try:
            import joblib
            
            # Load model package from cache or disk
            model_package = cache.get('ml_model_package')
            if model_package is None:
                model_package = joblib.load('models/smoking_craving_model.pkl')
                cache.set('ml_model_package', model_package, timeout=3600)
            
            # Extract components from the package
            model = model_package['model']
            scaler = model_package['scaler']
            feature_names = model_package['feature_names']
            
        except FileNotFoundError:
            error_msg = "ML model file not found at 'models/smoking_craving_model.pkl'"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'suggestion': 'Train and save your ML model first'
            }
        except KeyError as e:
            error_msg = f"Model package missing key: {e}. Retrain the model."
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return {
                'success': False,
                'error': f'Model loading failed: {str(e)}'
            }
        
        # Prepare features
        features_df = pd.DataFrame([features_dict])
        
        # Ensure features are in the correct order
        try:
            features_df = features_df[feature_names]
        except KeyError as e:
            error_msg = f"Missing required features: {e}. Required: {feature_names}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # Scale features
        features_scaled = scaler.transform(features_df)
        
        # Make prediction
        prediction = model.predict(features_scaled)[0]
        probability = model.predict_proba(features_scaled)[0][1]
        
        # Get model metrics from training (if available)
        model_metrics = model_package.get('metrics', {})
        accuracy = model_metrics.get('accuracy')
        precision = model_metrics.get('precision')
        recall = model_metrics.get('recall')
        f1 = model_metrics.get('f1_score')
        # roc_auc is not stored per-prediction, it's a global metric
        
        # Determine risk level
        if probability >= 0.7:
            risk_level = 'high'
            comentario = f'Alto riesgo de deseo detectado ({probability*100:.1f}%). Intervención inmediata recomendada.'
        elif probability >= 0.4:
            risk_level = 'medium'
            comentario = f'Riesgo moderado de deseo ({probability*100:.1f}%). Monitoreo continuo recomendado.'
        else:
            risk_level = 'low'
            comentario = f'Bajo riesgo de deseo ({probability*100:.1f}%). Estado estable.'
        
        logger.info(f"Prediction: probability={probability:.2%}, risk={risk_level}")
        
        # Use existing ventana or create new one
        if existing_ventana:
            ventana = existing_ventana
        else:
            ventana = Ventana.objects.create(
                consumidor=consumidor,
                window_start=timezone.now(),
                window_end=timezone.now() + timezone.timedelta(minutes=30)
            )
        
        # Guardar features calculadas en la ventana
        ventana.hr_mean = features_dict.get('hr_mean')
        ventana.hr_std = features_dict.get('hr_std')
        ventana.accel_energy = features_dict.get('accel_energy')
        ventana.gyro_energy = features_dict.get('gyro_energy')
        ventana.save()
        
        logger.info(f"Features saved to Ventana ID {ventana.id}")
        
        # Save to Analisis with metrics
        analisis = Analisis.objects.create(
            ventana=ventana,
            probabilidad_modelo=float(probability),
            urge_label=int(prediction),
            modelo_usado='LogisticRegression_v1',
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            roc_auc=None,  # ROC-AUC is a global metric, not per prediction
            comentario_modelo=comentario
        )
        
        logger.info(f"Prediction saved: Analisis ID {analisis.id}, risk={risk_level}, prob={probability:.2%}")
        
        # If high risk, create notification
        if risk_level == 'high':
            deseo = Deseo.objects.create(
                consumidor=consumidor,
                ventana=ventana,
                tipo='sustancia',
                resolved=False
            )
            
            Notificacion.objects.create(
                consumidor=consumidor,
                deseo=deseo,
                contenido=comentario,
                tipo='alerta',
                leida=False
            )
            
            logger.info(f"High risk notification created for consumidor {consumidor.id}")
        
        return {
            'success': True,
            'analisis_id': analisis.id,
            'probability': float(probability),
            'prediction': int(prediction),
            'risk_level': risk_level,
            'comentario': comentario,
            'model_metrics': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1
            },
            'user_id': user_id,
            'consumidor_id': consumidor.id
        }
        
    except Exception as exc:
        logger.error(f"Unexpected error in prediction: {exc}")
        # Don't retry if it's a data issue
        if isinstance(exc, (Usuario.DoesNotExist, Consumidor.DoesNotExist)):
            return {
                'success': False,
                'error': str(exc)
            }
        # Retry for other errors (network, temporary issues)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def simulate_wearable_cycle(self):
    """
    Tarea periódica que simula ciclo de wearable cada minuto:
    1. Genera ventana con lecturas de sensores
    2. Calcula features automáticamente
    3. Dispara predicción ML
    
    Esta tarea se ejecuta automáticamente cada 60 segundos vía Celery Beat.
    """
    import random
    from datetime import timedelta
    
    logger.info("=" * 70)
    logger.info("[CYCLE] Iniciando ciclo de simulación automático")
    
    try:
        # Obtener consumidores activos
        consumidores = list(Consumidor.objects.select_related('usuario').all())
        
        if not consumidores:
            logger.warning("[WARNING] No hay consumidores en la base de datos")
            return {
                'success': False,
                'error': 'No hay consumidores disponibles'
            }
        
        # Seleccionar consumidor aleatorio
        consumidor = random.choice(consumidores)
        usuario = consumidor.usuario
        
        logger.info(f"[USER] Consumidor seleccionado: {consumidor.nombre} (ID: {consumidor.id})")
        
        # === PASO 1: Crear Ventana ===
        now = timezone.now()
        window_start = now - timedelta(minutes=1)
        window_end = now
        
        ventana = Ventana.objects.create(
            consumidor=consumidor,
            window_start=window_start,
            window_end=window_end
        )
        
        logger.info(f"[WINDOW] Ventana creada: ID {ventana.id}")
        
        # === PASO 2: Generar Lecturas SIMPLES ===
        # Rangos realistas sin complicaciones
        base_hr = random.uniform(65, 95)  # Frecuencia cardíaca base
        
        lecturas_creadas = 0
        for i in range(60):
            # Heart rate: valor base + variación pequeña
            hr = base_hr + random.uniform(-5, 5)
            hr = max(50, min(150, hr))  # Limitar rango realista
            
            # Acelerómetro: valores simples entre -2 y 2 (g)
            accel_x = random.uniform(-1.5, 1.5)
            accel_y = random.uniform(-1.5, 1.5)
            accel_z = random.uniform(-1.5, 1.5)
            
            # Giroscopio: valores simples entre -1 y 1 (rad/s)
            gyro_x = random.uniform(-0.8, 0.8)
            gyro_y = random.uniform(-0.8, 0.8)
            gyro_z = random.uniform(-0.8, 0.8)
            
            # Django auto-asigna created_at con timezone.now()
            Lectura.objects.create(
                ventana=ventana,
                heart_rate=hr,
                accel_x=accel_x,
                accel_y=accel_y,
                accel_z=accel_z,
                gyro_x=gyro_x,
                gyro_y=gyro_y,
                gyro_z=gyro_z
            )
            lecturas_creadas += 1
        
        logger.info(f"[OK] {lecturas_creadas} lecturas generadas (HR base: {base_hr:.1f})")
        
        # === PASO 3: Disparar Predicción ===
        logger.info(f"[ML] Disparando predicción ML...")
        
        # Invocar tarea de predicción
        result = predict_smoking_craving.apply_async(
            kwargs={'user_id': usuario.id, 'features_dict': None},
            countdown=2  # Esperar 2 segundos
        )
        
        logger.info(f"[OK] Predicción encolada (Task ID: {result.id})")
        logger.info("=" * 70)
        
        return {
            'success': True,
            'consumidor_id': consumidor.id,
            'ventana_id': ventana.id,
            'lecturas_count': lecturas_creadas,
            'prediction_task_id': result.id,
            'base_hr': round(base_hr, 1)
        }
        
    except Exception as exc:
        logger.error(f"[ERROR] Error en ciclo de simulación: {exc}")
        logger.exception(exc)
        
        # Reintentar después de 30 segundos
        if self.request.retries < self.max_retries:
            logger.info(f"[RETRY] Reintentando en 30 segundos")
            raise self.retry(exc=exc, countdown=30)
        
        return {
            'success': False,
            'error': str(exc)
        }