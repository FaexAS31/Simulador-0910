"""
Sensor Data Models
==================
Models for wearable sensor data: Ventanas, Lecturas

Ventanas (Windows) aggregate sensor readings over time periods.
Lecturas (Readings) are individual sensor data points.
"""

from django.db import models # type: ignore
from .base import TimeStampedModel
from .user import Consumidor


class Ventana(TimeStampedModel):
    """
    Time window model for aggregated sensor data.
    
    Represents a time period (window) with aggregated sensor metrics:
    - Heart rate statistics (mean, std)
    - Motion energy (gyroscope, accelerometer)
    - ML model embeddings for emotions, motives, solutions
    
    Used for ML model input and analysis.
    """
    
    consumidor = models.ForeignKey(
        Consumidor,
        on_delete=models.CASCADE,
        related_name='ventanas',
        help_text="Consumer this window belongs to"
    )
    window_start = models.DateTimeField(
        help_text="Start timestamp of the time window"
    )
    window_end = models.DateTimeField(
        help_text="End timestamp of the time window"
    )
    hr_mean = models.FloatField(
        null=True,
        blank=True,
        help_text="Mean heart rate in the window (BPM)"
    )
    hr_std = models.FloatField(
        null=True,
        blank=True,
        help_text="Standard deviation of heart rate"
    )
    gyro_energy = models.FloatField(
        null=True,
        blank=True,
        help_text="Gyroscope energy (motion intensity)"
    )
    accel_energy = models.FloatField(
        null=True,
        blank=True,
        help_text="Accelerometer energy (movement intensity)"
    )
    emotion_embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding of emotions (for ML)"
    )
    motive_embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding of motives (for ML)"
    )
    solution_embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding of solutions (for ML)"
    )
    
    class Meta:
        db_table = 'ventanas'
        verbose_name = 'Ventana'
        verbose_name_plural = 'Ventanas'
        ordering = ['-window_start']
        indexes = [
            models.Index(fields=['consumidor', 'window_start']),
            models.Index(fields=['window_start']),
            models.Index(fields=['window_end']),
        ]
        # Constraint: window_end must be after window_start
        constraints = [
            models.CheckConstraint(
                check=models.Q(window_end__gt=models.F('window_start')),
                name='check_window_order'
            )
        ]
    
    def __str__(self):
        return (
            f"Window {self.id} - {self.consumidor.nombre} "
            f"({self.window_start.strftime('%Y-%m-%d %H:%M')})"
        )
    
    @property
    def duration_minutes(self):
        """
        Calculate window duration in minutes
        
        Returns:
            float: Duration in minutes
        """
        if self.window_start and self.window_end:
            delta = self.window_end - self.window_start
            return delta.total_seconds() / 60
        return None
    
    @property
    def has_sensor_data(self):
        """Check if window has any sensor data"""
        return any([
            self.hr_mean is not None,
            self.gyro_energy is not None,
            self.accel_energy is not None
        ])
    
    @property
    def has_embeddings(self):
        """Check if window has ML embeddings"""
        return any([
            self.emotion_embedding,
            self.motive_embedding,
            self.solution_embedding
        ])
    
    def get_heart_rate_range(self):
        """
        Estimate heart rate range from mean and std
        
        Returns:
            tuple: (min_estimate, max_estimate) or None
        """
        if self.hr_mean is not None and self.hr_std is not None:
            return (
                round(self.hr_mean - self.hr_std, 2),
                round(self.hr_mean + self.hr_std, 2)
            )
        return None


class Lectura(TimeStampedModel):
    """
    Individual sensor reading model.
    
    Stores raw sensor data points:
    - Heart rate
    - 3-axis accelerometer (x, y, z)
    - 3-axis gyroscope (x, y, z)
    
    Multiple readings aggregate into a Ventana.
    """
    
    ventana = models.ForeignKey(
        Ventana,
        on_delete=models.CASCADE,
        related_name='lecturas',
        help_text="Time window this reading belongs to"
    )
    heart_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="Heart rate in beats per minute (BPM)"
    )
    accel_x = models.FloatField(
        null=True,
        blank=True,
        help_text="Accelerometer X-axis value"
    )
    accel_y = models.FloatField(
        null=True,
        blank=True,
        help_text="Accelerometer Y-axis value"
    )
    accel_z = models.FloatField(
        null=True,
        blank=True,
        help_text="Accelerometer Z-axis value"
    )
    gyro_x = models.FloatField(
        null=True,
        blank=True,
        help_text="Gyroscope X-axis value"
    )
    gyro_y = models.FloatField(
        null=True,
        blank=True,
        help_text="Gyroscope Y-axis value"
    )
    gyro_z = models.FloatField(
        null=True,
        blank=True,
        help_text="Gyroscope Z-axis value"
    )
    
    class Meta:
        db_table = 'lecturas'
        verbose_name = 'Lectura'
        verbose_name_plural = 'Lecturas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ventana', 'created_at']),
        ]
    
    def __str__(self):
        return f"Reading {self.id} - Window {self.ventana_id}"
    
    @property
    def has_heart_rate(self):
        """Check if reading has heart rate data"""
        return self.heart_rate is not None
    
    @property
    def has_accelerometer(self):
        """Check if reading has accelerometer data"""
        return any([
            self.accel_x is not None,
            self.accel_y is not None,
            self.accel_z is not None
        ])
    
    @property
    def has_gyroscope(self):
        """Check if reading has gyroscope data"""
        return any([
            self.gyro_x is not None,
            self.gyro_y is not None,
            self.gyro_z is not None
        ])
    
    def get_accelerometer_magnitude(self):
        """
        Calculate accelerometer vector magnitude
        
        Returns:
            float: Magnitude or None
        """
        if self.has_accelerometer:
            import math
            x = self.accel_x or 0
            y = self.accel_y or 0
            z = self.accel_z or 0
            return math.sqrt(x**2 + y**2 + z**2)
        return None
    
    def get_gyroscope_magnitude(self):
        """
        Calculate gyroscope vector magnitude
        
        Returns:
            float: Magnitude or None
        """
        if self.has_gyroscope:
            import math
            x = self.gyro_x or 0
            y = self.gyro_y or 0
            z = self.gyro_z or 0
            return math.sqrt(x**2 + y**2 + z**2)
        return None