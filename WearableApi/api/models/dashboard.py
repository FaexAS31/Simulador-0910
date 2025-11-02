"""
Dashboard View Models
=====================
Read-only models mapping to PostgreSQL views for dashboard data.

Design Pattern: Data Mapper Pattern
These models map to database views (not tables) and are read-only.

Important: managed = False means Django won't create/modify these in migrations.
The PostgreSQL views must be created separately.
"""

from django.db import models # type: ignore


class VwHabitTracking(models.Model):
    """
    Maps to vw_habit_tracking view.
    Provides cigarette/habit tracking data over time.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    habito_nombre = models.CharField(max_length=50)
    fecha = models.DateField()
    total_cigarrillos = models.IntegerField()
    cigarrillos_hoy = models.IntegerField()
    cigarrillos_semana = models.IntegerField()
    cigarrillos_mes = models.IntegerField()
    
    class Meta:
        managed = False  # Don't create table, it's a view
        db_table = 'vw_habit_tracking'
        verbose_name = 'Habit Tracking'
        verbose_name_plural = 'Habit Tracking'


class VwHabitStats(models.Model):
    """
    Maps to vw_habit_stats view.
    Aggregated habit statistics.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    habito_nombre = models.CharField(max_length=50)
    total_eventos = models.IntegerField()
    primer_registro = models.DateTimeField()
    ultimo_registro = models.DateTimeField()
    promedio_diario = models.DecimalField(max_digits=10, decimal_places=2)
    eventos_mes_actual = models.IntegerField()
    eventos_mes_anterior = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_habit_stats'
        verbose_name = 'Habit Statistics'
        verbose_name_plural = 'Habit Statistics'


class VwHeartRateTimeline(models.Model):
    """
    Maps to vw_heart_rate_timeline view.
    Heart rate data over time for charts.
    """
    
    id = models.IntegerField(primary_key=True)
    consumidor_id = models.IntegerField()
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    heart_rate_mean = models.FloatField()
    heart_rate_std = models.FloatField()
    heart_rate_min_estimate = models.DecimalField(max_digits=10, decimal_places=2)
    heart_rate_max_estimate = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    hora = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_heart_rate_timeline'
        verbose_name = 'Heart Rate Timeline'
        verbose_name_plural = 'Heart Rate Timeline'


class VwHeartRateStats(models.Model):
    """
    Maps to vw_heart_rate_stats view.
    Aggregated heart rate statistics.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    total_mediciones = models.IntegerField()
    hr_promedio_general = models.DecimalField(max_digits=10, decimal_places=2)
    hr_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    hr_maximo = models.DecimalField(max_digits=10, decimal_places=2)
    hr_desviacion = models.DecimalField(max_digits=10, decimal_places=2)
    hr_promedio_hoy = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    hr_promedio_semana = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    class Meta:
        managed = False
        db_table = 'vw_heart_rate_stats'
        verbose_name = 'Heart Rate Statistics'
        verbose_name_plural = 'Heart Rate Statistics'


class VwPredictionTimeline(models.Model):
    """
    Maps to vw_prediction_timeline view.
    Individual predictions over time.
    """
    
    analisis_id = models.IntegerField(primary_key=True)
    consumidor_id = models.IntegerField()
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    modelo_usado = models.CharField(max_length=100)
    urge_label = models.IntegerField()
    probabilidad_modelo = models.FloatField()
    accuracy = models.FloatField()
    fecha = models.DateField()
    hora = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_prediction_timeline'
        verbose_name = 'Prediction Timeline'
        verbose_name_plural = 'Prediction Timeline'


class VwPredictionSummary(models.Model):
    """
    Maps to vw_prediction_summary view.
    Simple prediction statistics.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    total_predicciones = models.IntegerField()
    predicciones_urge = models.IntegerField()
    predicciones_no_urge = models.IntegerField()
    porcentaje_urge = models.DecimalField(max_digits=5, decimal_places=2)
    predicciones_hoy = models.IntegerField()
    predicciones_semana = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_prediction_summary'
        verbose_name = 'Prediction Summary'
        verbose_name_plural = 'Prediction Summary'


class VwDesiresTracking(models.Model):
    """
    Maps to vw_desires_tracking view.
    Individual desire records with details.
    """
    
    deseo_id = models.IntegerField(primary_key=True)
    consumidor_id = models.IntegerField()
    deseo_tipo = models.CharField(max_length=50)
    resolved = models.BooleanField()
    fecha_creacion = models.DateTimeField()
    ventana_inicio = models.DateTimeField(null=True)
    heart_rate_durante = models.FloatField(null=True)
    urge_label = models.IntegerField(null=True)
    probabilidad_modelo = models.FloatField(null=True)
    horas_hasta_resolucion = models.FloatField(null=True)
    
    class Meta:
        managed = False
        db_table = 'vw_desires_tracking'
        verbose_name = 'Desires Tracking'
        verbose_name_plural = 'Desires Tracking'


class VwDesiresStats(models.Model):
    """
    Maps to vw_desires_stats view.
    Aggregated desire statistics by type.
    """
    
    consumidor_id = models.IntegerField()
    deseo_tipo = models.CharField(max_length=50, primary_key=True)
    total_deseos = models.IntegerField()
    deseos_resueltos = models.IntegerField()
    deseos_activos = models.IntegerField()
    porcentaje_resolucion = models.DecimalField(max_digits=5, decimal_places=2)
    promedio_horas_resolucion = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    deseos_hoy = models.IntegerField()
    deseos_resueltos_hoy = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_desires_stats'
        verbose_name = 'Desires Statistics'
        verbose_name_plural = 'Desires Statistics'


class VwDailySummary(models.Model):
    """
    Maps to vw_daily_summary view.
    Daily summary with all key metrics for dashboard KPI cards.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    fecha = models.DateField()
    cigarrillos_hoy = models.IntegerField()
    cigarrillos_semana = models.IntegerField()
    cigarrillos_mes = models.IntegerField()
    hr_promedio_hoy = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    deseos_hoy = models.IntegerField()
    deseos_resueltos_hoy = models.IntegerField()
    deseos_activos = models.IntegerField()
    predicciones_hoy = models.IntegerField()
    total_predicciones_correctas = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_daily_summary'
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summary'


class VwWeeklyComparison(models.Model):
    """
    Maps to vw_weekly_comparison view.
    Week-over-week comparison for progress tracking.
    """
    
    consumidor_id = models.IntegerField(primary_key=True)
    cigarrillos_semana_actual = models.IntegerField()
    cigarrillos_semana_anterior = models.IntegerField()
    porcentaje_cambio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    deseos_semana_actual = models.IntegerField()
    deseos_semana_anterior = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'vw_weekly_comparison'
        verbose_name = 'Weekly Comparison'
        verbose_name_plural = 'Weekly Comparison'