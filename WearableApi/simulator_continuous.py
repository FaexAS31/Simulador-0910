"""
Simulador Continuo de Wearable
================================
Genera datos de sensores cada minuto e invoca el pipeline de predicción.

Flujo:
1. Cada minuto: Crea Ventana nueva
2. Genera 60 Lecturas (1 por segundo simulado)
3. Calcula features y guarda en Ventana
4. Invoca predicción ML -> guarda en Analisis
5. Crea notificación si hay alto riesgo

Ejecutar: python simulator_continuous.py
"""
import os
import django
import time
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
django.setup()

from django.utils import timezone
from api.models import Usuario, Consumidor, Ventana, Lectura, Analisis, Notificacion
from api.tasks import predict_smoking_craving
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class WearableSimulator:
    """
    Simulador de datos de wearable con patrones realistas
    """
    
    def __init__(self, consumidor_id=None):
        """
        Inicializar simulador
        
        Args:
            consumidor_id: ID del consumidor (si no se proporciona, usa el primero)
        """
        if consumidor_id:
            self.consumidor = Consumidor.objects.get(id=consumidor_id)
        else:
            # Obtener el primer consumidor disponible
            self.consumidor = Consumidor.objects.first()
            if not self.consumidor:
                raise Exception("No hay consumidores en la base de datos")
        
        logger.info(f"✅ Simulador inicializado para: {self.consumidor.nombre}")
        
    def generate_heart_rate(self):
        """
        Genera frecuencia cardíaca realista y variable
        
        Returns:
            float: Heart rate en BPM
        """
        # Rango normal: 60-100 BPM con variación
        hr = random.uniform(65, 95) + random.uniform(-5, 5)
        return max(50, min(150, hr))
    
    def generate_accelerometer(self):
        """
        Genera datos de acelerómetro simples
        
        Returns:
            tuple: (accel_x, accel_y, accel_z) en g
        """
        # Valores simples entre -1.5 y 1.5 g
        x = random.uniform(-1.5, 1.5)
        y = random.uniform(-1.5, 1.5)
        z = random.uniform(-1.5, 1.5)
        return (x, y, z)
    
    def generate_gyroscope(self):
        """
        Genera datos de giroscopio simples
        
        Returns:
            tuple: (gyro_x, gyro_y, gyro_z) en rad/s
        """
        # Valores simples entre -0.8 y 0.8 rad/s
        x = random.uniform(-0.8, 0.8)
        y = random.uniform(-0.8, 0.8)
        z = random.uniform(-0.8, 0.8)
        return (x, y, z)
    
    def create_window_with_readings(self):
        """
        Crea una ventana de tiempo con lecturas de sensores
        
        Returns:
            Ventana: Ventana creada
        """
        now = timezone.now()
        window_start = now - timedelta(minutes=1)
        window_end = now
        
        # Crear ventana
        ventana = Ventana.objects.create(
            consumidor=self.consumidor,
            window_start=window_start,
            window_end=window_end
        )
        
        logger.info(f"📦 Ventana creada: ID {ventana.id}")
        
        # Generar 60 lecturas (1 por segundo)
        lecturas_creadas = 0
        for i in range(60):
            hr = self.generate_heart_rate()
            accel = self.generate_accelerometer()
            gyro = self.generate_gyroscope()
            
            # Django auto-asigna created_at con timezone.now()
            Lectura.objects.create(
                ventana=ventana,
                heart_rate=hr,
                accel_x=accel[0],
                accel_y=accel[1],
                accel_z=accel[2],
                gyro_x=gyro[0],
                gyro_y=gyro[1],
                gyro_z=gyro[2]
            )
            lecturas_creadas += 1
        
        logger.info(f"✅ {lecturas_creadas} lecturas generadas")
        
        return ventana
    
    def trigger_prediction(self, ventana):
        """
        Dispara predicción ML de forma asíncrona con Celery
        
        Args:
            ventana: Ventana sobre la cual predecir
        """
        try:
            # Obtener usuario del consumidor
            usuario = self.consumidor.usuario
            
            # Invocar tarea Celery (asíncrono)
            result = predict_smoking_craving.delay(user_id=usuario.id, features_dict=None)
            
            logger.info(f"🤖 Predicción enviada a Celery (Task ID: {result.id})")
            
            # Esperar resultado (opcional, con timeout)
            try:
                output = result.get(timeout=10)
                
                if output.get('success'):
                    prob = output.get('probability', 0)
                    risk = output.get('risk_level', 'unknown')
                    analisis_id = output.get('analisis_id')
                    
                    logger.info(f"✅ Predicción completada:")
                    logger.info(f"   - Análisis ID: {analisis_id}")
                    logger.info(f"   - Probabilidad: {prob:.2%}")
                    logger.info(f"   - Riesgo: {risk.upper()}")
                    
                    # Verificar si se creó notificación
                    if output.get('notification_sent'):
                        logger.warning(f"🔔 Notificación de alto riesgo enviada!")
                    
                    return output
                else:
                    logger.error(f"❌ Predicción falló: {output.get('error')}")
                    return None
                    
            except Exception as e:
                logger.error(f"⏱️  Timeout esperando resultado: {e}")
                logger.info("   (La predicción continúa en background)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error al disparar predicción: {e}")
            return None
    
    def run_cycle(self):
        """
        Ejecuta un ciclo completo de simulación:
        1. Crear ventana con lecturas
        2. Disparar predicción ML
        """
        logger.info("=" * 70)
        logger.info(f"🔄 INICIANDO CICLO DE SIMULACIÓN")
        logger.info(f"   Consumidor: {self.consumidor.nombre}")
        logger.info(f"   Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        # Crear ventana con lecturas
        ventana = self.create_window_with_readings()
        
        # Disparar predicción
        self.trigger_prediction(ventana)
        
        logger.info("=" * 70)
        logger.info("✅ Ciclo completado")
        logger.info("=" * 70)
        logger.info("")


def main():
    """
    Función principal del simulador continuo
    """
    print("=" * 70)
    print("🚀 SIMULADOR CONTINUO DE WEARABLE")
    print("=" * 70)
    print()
    print("Este script genera datos de sensores cada minuto y ejecuta")
    print("predicciones ML automáticamente.")
    print()
    print("Presiona Ctrl+C para detener el simulador.")
    print("=" * 70)
    print()
    
    # Permitir elegir consumidor
    consumidores = Consumidor.objects.all()
    
    if not consumidores.exists():
        print("❌ No hay consumidores en la base de datos")
        print("💡 Crea un usuario y consumidor primero")
        return
    
    print("Consumidores disponibles:")
    for i, c in enumerate(consumidores, 1):
        usuario = c.usuario
        print(f"  {i}. {c.nombre} (Usuario: {usuario.email})")
    
    print()
    choice = input("Selecciona consumidor (número) o Enter para el primero: ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(consumidores):
        consumidor_id = list(consumidores)[int(choice) - 1].id
    else:
        consumidor_id = consumidores.first().id
    
    # Inicializar simulador
    simulator = WearableSimulator(consumidor_id=consumidor_id)
    
    print()
    print("🟢 Simulador iniciado")
    print()
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            
            # Ejecutar ciclo
            simulator.run_cycle()
            
            # Mostrar estadísticas cada 5 ciclos
            if cycle_count % 5 == 0:
                total_ventanas = Ventana.objects.filter(consumidor=simulator.consumidor).count()
                total_analisis = Analisis.objects.filter(
                    ventana__consumidor=simulator.consumidor
                ).count()
                
                logger.info(f"📈 Estadísticas después de {cycle_count} ciclos:")
                logger.info(f"   - Total ventanas: {total_ventanas}")
                logger.info(f"   - Total análisis: {total_analisis}")
                logger.info("")
            
            # Esperar 60 segundos hasta el siguiente ciclo
            logger.info("😴 Esperando 60 segundos hasta el próximo ciclo...")
            logger.info("")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("🛑 Simulador detenido por el usuario")
        print(f"📊 Total de ciclos ejecutados: {cycle_count}")
        print("=" * 70)


if __name__ == "__main__":
    main()
