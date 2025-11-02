"""
Analysis Models
===============
Models for ML analysis and user interactions: Analisis, Deseos, Notificaciones

These models handle ML predictions, desire tracking, and notifications.
"""

from django.db import models # type: ignore
from .base import TimeStampedModel
from .user import Consumidor
from .sensor import Ventana


class Analisis(TimeStampedModel):
    """
    ML model analysis/prediction results.
    
    Stores output from machine learning models:
    - Model metadata (name, version)
    - Prediction results (urge_label, probability)
    - Performance metrics (recall, f1, accuracy, roc_auc)
    - Feature importance for interpretability
    """
    
    ventana = models.ForeignKey(
        Ventana,
        on_delete=models.CASCADE,
        related_name='analisis',
        help_text="Time window this analysis is based on"
    )
    modelo_usado = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Name/version of ML model used"
    )
    probabilidad_modelo = models.FloatField(
        null=True,
        blank=True,
        help_text="Model prediction probability (0-1)"
    )
    urge_label = models.IntegerField(
        null=True,
        blank=True,
        help_text="Binary label: 1=urge detected, 0=no urge"
    )
    recall = models.FloatField(
        null=True,
        blank=True,
        help_text="Model recall metric (0-1)"
    )
    f1_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Model F1 score (0-1)"
    )
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="Model accuracy (0-1)"
    )
    roc_auc = models.FloatField(
        null=True,
        blank=True,
        help_text="ROC AUC score (0-1)"
    )
    comentario_modelo = models.TextField(
        null=True,
        blank=True,
        help_text="Optional notes about the prediction"
    )
    feature_importance = models.JSONField(
        null=True,
        blank=True,
        help_text="Feature importance scores (JSONB)"
    )
    
    class Meta:
        db_table = 'analisis'
        verbose_name = 'Análisis'
        verbose_name_plural = 'Análisis'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ventana']),
            models.Index(fields=['probabilidad_modelo']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(urge_label__in=[0, 1]),
                name='check_urge_label'
            ),
            models.CheckConstraint(
                check=models.Q(probabilidad_modelo__gte=0, probabilidad_modelo__lte=1),
                name='check_probabilidad_range'
            ),
        ]
    
    def __str__(self):
        urge_str = "Urge" if self.urge_label == 1 else "No Urge"
        return f"Analysis {self.id} - {urge_str} (p={self.probabilidad_modelo})"
    
    @property
    def is_urge_predicted(self):
        """Check if urge was predicted"""
        return self.urge_label == 1
    
    @property
    def confidence_level(self):
        """
        Get confidence level of prediction
        
        Returns:
            str: Low, Medium, or High
        """
        if self.probabilidad_modelo is None:
            return "Unknown"
        
        if self.probabilidad_modelo < 0.6:
            return "Low"
        elif self.probabilidad_modelo < 0.8:
            return "Medium"
        else:
            return "High"
    
    @property
    def consumidor(self):
        """Get related consumer through ventana"""
        return self.ventana.consumidor if self.ventana else None


class DeseoTipoChoices(models.TextChoices):
    """Enum for desire/urge types"""
    COMIDA = 'comida', 'Comida'
    BEBIDA = 'bebida', 'Bebida'
    COMPRA = 'compra', 'Compra'
    SUSTANCIA = 'sustancia', 'Sustancia'
    OTRO = 'otro', 'Otro'


class Deseo(TimeStampedModel):
    """
    Desire/urge tracking model.
    
    Records when a consumer experiences an urge and tracks:
    - Type of desire
    - Associated time window (if from sensor data)
    - Resolution status
    """
    
    consumidor = models.ForeignKey(
        Consumidor,
        on_delete=models.CASCADE,
        related_name='deseos',
        help_text="Consumer experiencing the desire"
    )
    ventana = models.ForeignKey(
        Ventana,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deseos',
        help_text="Associated time window (optional)"
    )
    tipo = models.CharField(
        max_length=50,
        choices=DeseoTipoChoices.choices,
        help_text="Type of desire/urge"
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether the desire was resolved/overcome"
    )
    
    class Meta:
        db_table = 'deseos'
        verbose_name = 'Deseo'
        verbose_name_plural = 'Deseos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consumidor', 'created_at']),
            models.Index(fields=['consumidor', 'resolved']),
            models.Index(fields=['ventana']),
        ]
    
    def __str__(self):
        status = "Resuelto" if self.resolved else "Activo"
        return f"Desire {self.id} - {self.tipo} ({status})"
    
    @property
    def is_active(self):
        """Check if desire is still active (not resolved)"""
        return not self.resolved
    
    @property
    def time_to_resolution(self):
        """
        Calculate time to resolution in hours
        
        Returns:
            float: Hours to resolution or None if not resolved
        """
        if self.resolved and self.created_at and self.updated_at:
            delta = self.updated_at - self.created_at
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    def mark_resolved(self):
        """Mark desire as resolved"""
        self.resolved = True
        self.save()


class NotificacionTipoChoices(models.TextChoices):
    """Enum for notification types"""
    RECOMENDACION = 'recomendacion', 'Recomendación'
    ALERTA = 'alerta', 'Alerta'
    RECORDATORIO = 'recordatorio', 'Recordatorio'
    LOGRO = 'logro', 'Logro'


class Notificacion(TimeStampedModel):
    """
    Notification model for sending messages to consumers.
    
    Handles:
    - Recommendations (coping strategies)
    - Alerts (potential urges detected)
    - Reminders (check-ins, logging)
    - Achievements (milestones reached)
    """
    
    consumidor = models.ForeignKey(
        Consumidor,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        help_text="Consumer receiving the notification"
    )
    deseo = models.ForeignKey(
        Deseo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones',
        help_text="Related desire (optional)"
    )
    tipo = models.CharField(
        max_length=50,
        choices=NotificacionTipoChoices.choices,
        help_text="Type of notification"
    )
    contenido = models.TextField(
        help_text="Notification content/message"
    )
    fecha_envio = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when notification was sent"
    )
    leida = models.BooleanField(
        default=False,
        help_text="Whether notification has been read"
    )
    
    class Meta:
        db_table = 'notificaciones'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']
        indexes = [
            models.Index(fields=['consumidor', 'fecha_envio']),
            models.Index(fields=['consumidor', 'leida']),
            models.Index(fields=['deseo']),
            models.Index(fields=['fecha_envio']),
        ]
    
    def __str__(self):
        status = "Leída" if self.leida else "No leída"
        return f"Notification {self.id} - {self.tipo} ({status})"
    
    @property
    def is_unread(self):
        """Check if notification is unread"""
        return not self.leida
    
    def mark_read(self):
        """Mark notification as read"""
        self.leida = True
        self.save()
    
    def mark_unread(self):
        """Mark notification as unread"""
        self.leida = False
        self.save()
    
    @property
    def age_hours(self):
        """
        Get age of notification in hours
        
        Returns:
            float: Hours since notification was sent
        """
        from django.utils import timezone # type: ignore
        if self.fecha_envio:
            delta = timezone.now() - self.fecha_envio
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    @property
    def is_recent(self):
        """Check if notification is recent (less than 24 hours old)"""
        age = self.age_hours
        return age is not None and age < 24