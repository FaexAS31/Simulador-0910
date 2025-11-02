# Script de Inicio Rápido - Simulación Continua
# Ejecutar: .\start_simulation.ps1

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  🚀 INICIO DE SIMULACIÓN CONTINUA - WEARABLE API" -ForegroundColor Green
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Función para verificar proceso en ejecución
function Test-ProcessRunning {
    param($ProcessName)
    return (Get-Process | Where-Object {$_.ProcessName -like "*$ProcessName*"}).Count -gt 0
}

# Verificar si Celery ya está corriendo
if (Test-ProcessRunning "celery") {
    Write-Host "⚠️  Celery ya está en ejecución" -ForegroundColor Yellow
    Write-Host ""
    $respuesta = Read-Host "¿Deseas detener los procesos existentes? (s/n)"
    
    if ($respuesta -eq "s" -or $respuesta -eq "S") {
        Write-Host "🛑 Deteniendo procesos Celery..." -ForegroundColor Yellow
        Get-Process | Where-Object {$_.ProcessName -like "*celery*"} | Stop-Process -Force
        Start-Sleep -Seconds 2
        Write-Host "✅ Procesos detenidos" -ForegroundColor Green
    } else {
        Write-Host "❌ Cancelando inicio..." -ForegroundColor Red
        exit
    }
}

Write-Host ""
Write-Host "📋 Selecciona el modo de simulación:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. 🔧 Script Manual (simulator_continuous.py)" -ForegroundColor White
Write-Host "     - Control interactivo" -ForegroundColor Gray
Write-Host "     - Ideal para testing y debugging" -ForegroundColor Gray
Write-Host "     - Requiere terminal abierta" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. ⚙️  Celery Beat Automático (RECOMENDADO)" -ForegroundColor White
Write-Host "     - Totalmente automático" -ForegroundColor Gray
Write-Host "     - Funciona en background" -ForegroundColor Gray
Write-Host "     - Ideal para producción" -ForegroundColor Gray
Write-Host ""

$opcion = Read-Host "Ingresa opción (1 o 2)"

if ($opcion -eq "1") {
    # OPCIÓN 1: Script Manual
    Write-Host ""
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
    Write-Host "  🔧 MODO: Script Manual" -ForegroundColor Yellow
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "▶️  Iniciando simulator_continuous.py..." -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Presiona Ctrl+C para detener la simulación" -ForegroundColor Yellow
    Write-Host ""
    
    python simulator_continuous.py
    
} elseif ($opcion -eq "2") {
    # OPCIÓN 2: Celery Beat
    Write-Host ""
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
    Write-Host "  ⚙️  MODO: Celery Beat Automático" -ForegroundColor Yellow
    Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 69) -ForegroundColor Cyan
    Write-Host ""
    
    # Verificar que Redis esté disponible (opcional)
    Write-Host "🔍 Verificando pre-requisitos..." -ForegroundColor Cyan
    
    # Verificar modelo ML
    if (Test-Path "models\smoking_craving_model.pkl") {
        Write-Host "✅ Modelo ML encontrado" -ForegroundColor Green
    } else {
        Write-Host "❌ Modelo ML no encontrado" -ForegroundColor Red
        Write-Host "💡 Ejecuta: python train_model.py --auto" -ForegroundColor Yellow
        exit
    }
    
    # Verificar que hay consumidores
    $checkConsumers = python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings'); django.setup(); from api.models import Consumidor; print(Consumidor.objects.count())"
    
    if ([int]$checkConsumers -eq 0) {
        Write-Host "❌ No hay consumidores en la base de datos" -ForegroundColor Red
        Write-Host "💡 Crea un usuario y consumidor primero" -ForegroundColor Yellow
        exit
    } else {
        Write-Host "✅ Consumidores disponibles: $checkConsumers" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "🚀 Iniciando sistema Celery..." -ForegroundColor Green
    Write-Host ""
    
    # Borrar archivo de estado viejo si existe
    if (Test-Path "celerybeat-schedule.db") {
        Write-Host "🗑️  Eliminando archivo de estado viejo..." -ForegroundColor Gray
        Remove-Item "celerybeat-schedule.db" -Force
    }
    
    Write-Host "📝 NOTA: Se abrirán 2 ventanas de terminal:" -ForegroundColor Yellow
    Write-Host "   - Terminal 1: Celery Worker (ejecuta tareas)" -ForegroundColor Gray
    Write-Host "   - Terminal 2: Celery Beat (programa tareas cada minuto)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 Para detener: cierra ambas ventanas o presiona Ctrl+C en cada una" -ForegroundColor Yellow
    Write-Host ""
    
    $continuar = Read-Host "¿Continuar? (Enter para sí, n para cancelar)"
    
    if ($continuar -eq "n" -or $continuar -eq "N") {
        Write-Host "❌ Cancelado" -ForegroundColor Red
        exit
    }
    
    Write-Host ""
    Write-Host "▶️  Iniciando Celery Worker..." -ForegroundColor Green
    
    # Iniciar Celery Worker en nueva ventana
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '🔧 CELERY WORKER' -ForegroundColor Green; Write-Host ''; celery -A WearableApi worker --loglevel=info --pool=solo"
    
    Start-Sleep -Seconds 3
    
    Write-Host "▶️  Iniciando Celery Beat..." -ForegroundColor Green
    
    # Iniciar Celery Beat en nueva ventana
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '⏰ CELERY BEAT' -ForegroundColor Cyan; Write-Host ''; celery -A WearableApi beat --loglevel=info"
    
    Write-Host ""
    Write-Host "=" -ForegroundColor Green -NoNewline; Write-Host ("=" * 69) -ForegroundColor Green
    Write-Host "  ✅ SISTEMA INICIADO" -ForegroundColor Green
    Write-Host "=" -ForegroundColor Green -NoNewline; Write-Host ("=" * 69) -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 El sistema generará datos automáticamente cada 60 segundos" -ForegroundColor White
    Write-Host ""
    Write-Host "🔍 Verificar funcionamiento:" -ForegroundColor Cyan
    Write-Host "   python verify_features.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📈 Ver estadísticas:" -ForegroundColor Cyan
    Write-Host "   Consulta la base de datos (tabla: ventanas, analisis, notificaciones)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🛑 Para detener:" -ForegroundColor Cyan
    Write-Host "   Cierra las 2 ventanas de Celery que se abrieron" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host ""
    Write-Host "❌ Opción inválida" -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Presiona Enter para cerrar este script..." -ForegroundColor Gray
Read-Host
