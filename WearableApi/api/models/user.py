"""
User Models
===========
Models for user management: Usuario, Administrador, Consumidor

Design Pattern: Class Table Inheritance
Usuario is the base, with Administrador and Consumidor extending it.
"""

from django.db import models # type: ignore
from django.contrib.auth.hashers import make_password, check_password # type: ignore
from .base import TimeStampedModel


class RolChoices(models.TextChoices):
    """Enum for user roles"""
    CONSUMIDOR = 'consumidor', 'Consumidor'
    ADMINISTRADOR = 'administrador', 'Administrador'


class Usuario(TimeStampedModel):
    """
    Base user model for all users in the system.
    
    Handles authentication via email and password hash.
    No Django User model integration for simplicity.
    """
    
    nombre = models.CharField(
        max_length=100,
        help_text="Full name of the user"
    )
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Phone number (optional)"
    )
    email = models.EmailField(
        max_length=120,
        unique=True,
        help_text="Email address (used for login)"
    )
    password_hash = models.TextField(
        help_text="Hashed password (never store plain text)"
    )
    rol = models.CharField(
        max_length=50,
        choices=RolChoices.choices,
        default=RolChoices.CONSUMIDOR,
        help_text="User role (consumidor or administrador)"
    )
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['rol']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.email})"
    
    def set_password(self, raw_password):
        """
        Hash and set the password
        
        Args:
            raw_password: Plain text password
        """
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """
        Verify password against stored hash
        
        Args:
            raw_password: Plain text password to check
        
        Returns:
            bool: True if password matches
        """
        return check_password(raw_password, self.password_hash)
    
    @property
    def is_administrador(self):
        """Check if user is an administrator"""
        return self.rol == RolChoices.ADMINISTRADOR
    
    @property
    def is_consumidor(self):
        """Check if user is a consumer"""
        return self.rol == RolChoices.CONSUMIDOR


class Administrador(TimeStampedModel):
    """
    Administrator model with one-to-one relationship to Usuario.
    
    Extends Usuario with admin-specific fields.
    """
    
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='administrador',
        help_text="Reference to base Usuario"
    )
    area_responsable = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Responsible area (e.g., 'IT', 'Health Services')"
    )
    
    class Meta:
        db_table = 'administradores'
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'
        indexes = [
            models.Index(fields=['usuario']),
        ]
    
    def __str__(self):
        return f"Admin: {self.usuario.nombre}"
    
    @property
    def nombre(self):
        """Get name from related usuario"""
        return self.usuario.nombre
    
    @property
    def email(self):
        """Get email from related usuario"""
        return self.usuario.email


class GeneroChoices(models.TextChoices):
    """Enum for gender choices"""
    MASCULINO = 'masculino', 'Masculino'
    FEMENINO = 'femenino', 'Femenino'


class Consumidor(TimeStampedModel):
    """
    Consumer model with health tracking data.
    
    One-to-one relationship with Usuario.
    Includes health metrics and BMI calculation.
    """
    
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='consumidor',
        help_text="Reference to base Usuario"
    )
    edad = models.IntegerField(
        null=True,
        blank=True,
        help_text="Age in years"
    )
    peso = models.FloatField(
        null=True,
        blank=True,
        help_text="Weight in kilograms"
    )
    altura = models.FloatField(
        null=True,
        blank=True,
        help_text="Height in centimeters"
    )
    bmi = models.FloatField(
        null=True,
        blank=True,
        editable=False,
        help_text="Body Mass Index (calculated by database)"
    )
    genero = models.CharField(
        max_length=30,
        choices=GeneroChoices.choices,
        help_text="Gender"
    )
    
    class Meta:
        db_table = 'consumidores'
        verbose_name = 'Consumidor'
        verbose_name_plural = 'Consumidores'
        indexes = [
            models.Index(fields=['usuario']),
        ]
    
    def __str__(self):
        return f"Consumer: {self.usuario.nombre}"
    
    @property
    def nombre(self):
        """Get name from related usuario"""
        return self.usuario.nombre
    
    @property
    def email(self):
        """Get email from related usuario"""
        return self.usuario.email
    
    def calculate_bmi(self):
        """
        Calculate BMI manually (database also calculates)
        
        Returns:
            float: BMI value or None
        """
        if self.peso and self.altura and self.altura > 0:
            altura_metros = self.altura / 100
            return round(self.peso / (altura_metros ** 2), 2)
        return None
    
    @property
    def bmi_category(self):
        """
        Get BMI category
        
        Returns:
            str: BMI category (Underweight, Normal, Overweight, Obese)
        """
        if not self.bmi:
            return "Unknown"
        
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal"
        elif self.bmi < 30:
            return "Overweight"
        else:
            return "Obese"