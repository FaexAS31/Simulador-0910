
from django.db import models
from .base import TimeStampedModel
from .user import Consumidor

class Formulario(TimeStampedModel):
    
    consumidor = models.ForeignKey(
        Consumidor,
        on_delete=models.CASCADE,
        related_name='formularios',
        help_text="Consumer who submitted the form"
    )
    fecha_envio = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when form was submitted"
    )
    habito = models.JSONField(
        null=True,
        blank=True,
        help_text="Habit data as JSON (JSONB)"
    )
    emociones = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of emotion data (JSONB)"
    )
    motivos = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of motive data (JSONB)"
    )
    soluciones = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of solution data (JSONB)"
    )
    
    class Meta:
        db_table = 'formularios'
        verbose_name = 'Formulario'
        verbose_name_plural = 'Formularios'
        ordering = ['-fecha_envio']
        indexes = [
            models.Index(fields=['consumidor', 'fecha_envio']),
            models.Index(fields=['fecha_envio']),
        ]
    
    def __str__(self):
        habito_str = self.habito.get('nombre', 'Sin hábito') if self.habito else "Sin hábito"
        return f"Form {self.id} - {self.consumidor.nombre} - {habito_str}"
    
    @property
    def emotion_count(self):
        return len(self.emociones) if self.emociones else 0
    
    @property
    def motive_count(self):
        return len(self.motivos) if self.motivos else 0
    
    @property
    def solution_count(self):
        return len(self.soluciones) if self.soluciones else 0
    
    def get_emotion_ids(self):
        if not self.emociones:
            return []
        
        if isinstance(self.emociones, list):
            return [
                e.get('id') if isinstance(e, dict) else e
                for e in self.emociones
            ]
        return []
    
    def get_motive_ids(self):
        if not self.motivos:
            return []
        
        if isinstance(self.motivos, list):
            return [
                m.get('id') if isinstance(m, dict) else m
                for m in self.motivos
            ]
        return []
    
    def get_solution_ids(self):
        if not self.soluciones:
            return []
        
        if isinstance(self.soluciones, list):
            return [
                s.get('id') if isinstance(s, dict) else s
                for s in self.soluciones
            ]
        return []

class FormularioTemporal(TimeStampedModel):
    
    consumidor = models.ForeignKey(
        Consumidor,
        on_delete=models.CASCADE,
        related_name='formularios_temporales',
        help_text="Consumer who submitted the temporary form"
    )
    emociones = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of emotion data (JSONB)"
    )
    
    class Meta:
        db_table = 'formularios_temporales'
        verbose_name = 'Formulario Temporal'
        verbose_name_plural = 'Formularios Temporales'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consumidor', 'created_at']),
        ]
    
    def __str__(self):
        return f"Temp Form {self.id} - {self.consumidor.nombre}"
    
    @property
    def emotion_count(self):
        return len(self.emociones) if self.emociones else 0
    
    def get_emotion_ids(self):
        if not self.emociones:
            return []
        
        if isinstance(self.emociones, list):
            return [
                e.get('id') if isinstance(e, dict) else e
                for e in self.emociones
            ]
        return []

