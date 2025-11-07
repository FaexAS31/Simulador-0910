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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class WearableSimulator:
    
    def __init__(self, consumidor_id=None):
        if consumidor_id:
            self.consumidor = Consumidor.objects.get(id=consumidor_id)
        else:
            self.consumidor = Consumidor.objects.first()
            if not self.consumidor:
                raise Exception("No hay consumidores en la base de datos")
        
        logger.info(f"✅ Simulador inicializado para: {self.consumidor.nombre}")
        
    def generate_heart_rate(self):
        hr = random.uniform(65, 95) + random.uniform(-5, 5)
        return max(50, min(150, hr))
    
    def generate_accelerometer(self):
        x = random.uniform(-1.5, 1.5)
        y = random.uniform(-1.5, 1.5)
        z = random.uniform(-1.5, 1.5)
        return (x, y, z)
    
    def generate_gyroscope(self):
        x = random.uniform(-0.8, 0.8)
        y = random.uniform(-0.8, 0.8)
        z = random.uniform(-0.8, 0.8)
        return (x, y, z)
    
    def create_window_with_readings(self):
        now = timezone.now()
        window_start = now - timedelta(minutes=1)
        window_end = now
        
        ventana = Ventana.objects.create(
            consumidor=self.consumidor,
            window_start=window_start,
            window_end=window_end
        )
        
        logger.info(f"📦 Ventana creada: ID {ventana.id}")
        
        lecturas_creadas = 0
        for i in range(60):
            hr = self.generate_heart_rate()
            accel = self.generate_accelerometer()
            gyro = self.generate_gyroscope()
            
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
        try:
            usuario = self.consumidor.usuario
            
            result = predict_smoking_craving.delay(user_id=usuario.id, features_dict=None)
            
            logger.info(f"🤖 Predicción enviada a Celery (Task ID: {result.id})")
            
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
        logger.info("=" * 70)
        logger.info(f"🔄 INICIANDO CICLO DE SIMULACIÓN")
        logger.info(f"   Consumidor: {self.consumidor.nombre}")
        logger.info(f"   Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        ventana = self.create_window_with_readings()
        
        self.trigger_prediction(ventana)
        
        logger.info("=" * 70)
        logger.info("✅ Ciclo completado")
        logger.info("=" * 70)
        logger.info("")

def main():
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
    
    simulator = WearableSimulator(consumidor_id=consumidor_id)
    
    print()
    print("🟢 Simulador iniciado")
    print()
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            
            simulator.run_cycle()
            
            if cycle_count % 5 == 0:
                total_ventanas = Ventana.objects.filter(consumidor=simulator.consumidor).count()
                total_analisis = Analisis.objects.filter(
                    ventana__consumidor=simulator.consumidor
                ).count()
                
                logger.info(f"📈 Estadísticas después de {cycle_count} ciclos:")
                logger.info(f"   - Total ventanas: {total_ventanas}")
                logger.info(f"   - Total análisis: {total_analisis}")
                logger.info("")
            
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

