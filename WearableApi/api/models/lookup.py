"""
Lookup Tables
=============
Models for controlled vocabularies: Emociones, Motivos, Soluciones, Habitos, Permisos

Design Pattern: Flyweight Pattern
Shared reference data used across multiple entities.
"""

from django.db import models # type: ignore
from .base import TimeStampedModel


class BaseLookupModel(TimeStampedModel):
    """
    Abstract base model for all lookup tables.
    
    Provides common structure for controlled vocabularies.
    """
    
    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique name identifier"
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text="Optional description"
    )
    
    class Meta:
        abstract = True
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Emocion(BaseLookupModel):
    """
    Emotion lookup table.
    
    Examples: "ansiedad", "felicidad", "tristeza", "enojo"
    """
    
    class Meta:
        db_table = 'emociones'
        verbose_name = 'Emoción'
        verbose_name_plural = 'Emociones'


class Motivo(BaseLookupModel):
    """
    Motive/reason lookup table.
    
    Examples: "estrés", "aburrimiento", "social", "habitual"
    """
    
    class Meta:
        db_table = 'motivos'
        verbose_name = 'Motivo'
        verbose_name_plural = 'Motivos'


class Solucion(BaseLookupModel):
    """
    Solution/coping strategy lookup table.
    
    Examples: "respiración", "ejercicio", "meditación", "llamar amigo"
    """
    
    class Meta:
        db_table = 'soluciones'
        verbose_name = 'Solución'
        verbose_name_plural = 'Soluciones'


class Habito(BaseLookupModel):
    """
    Habit lookup table.
    
    Examples: "fumar", "beber", "comer en exceso"
    """
    
    class Meta:
        db_table = 'habitos'
        verbose_name = 'Hábito'
        verbose_name_plural = 'Hábitos'


class Permiso(TimeStampedModel):
    """
    Permission model for future role-based access control.
    
    Currently not linked to any model but prepared for future use.
    
    Fields define CRUD permissions:
    - lectura: Can read/view data
    - creacion: Can create new records
    - edicion: Can modify existing records
    - eliminacion: Can delete records
    """
    
    lectura = models.BooleanField(
        default=True,
        help_text="Permission to read/view"
    )
    creacion = models.BooleanField(
        default=False,
        help_text="Permission to create"
    )
    edicion = models.BooleanField(
        default=False,
        help_text="Permission to edit"
    )
    eliminacion = models.BooleanField(
        default=False,
        help_text="Permission to delete"
    )
    
    class Meta:
        db_table = 'permisos'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
    
    def __str__(self):
        perms = []
        if self.lectura:
            perms.append('Lectura')
        if self.creacion:
            perms.append('Creación')
        if self.edicion:
            perms.append('Edición')
        if self.eliminacion:
            perms.append('Eliminación')
        return f"Permisos: {', '.join(perms) if perms else 'Ninguno'}"
    
    @property
    def is_readonly(self):
        """Check if permission is read-only"""
        return self.lectura and not (
            self.creacion or self.edicion or self.eliminacion
        )
    
    @property
    def is_full_access(self):
        """Check if permission has full CRUD access"""
        return all([
            self.lectura,
            self.creacion,
            self.edicion,
            self.eliminacion
        ])