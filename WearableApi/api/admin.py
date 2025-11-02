"""
Django Admin Configuration
==========================
Custom admin interfaces for all models with search, filters, and inline editing.

Access at: http://localhost:8000/admin/
"""

from django.contrib import admin # type: ignore
from django.utils.html import format_html # type: ignore
from api.models import *


# ============================================
# USER ADMIN
# ============================================

class ConsumidorInline(admin.StackedInline):
    """Inline for Consumidor in Usuario admin"""
    model = Consumidor
    extra = 0
    readonly_fields = ('bmi',)


class AdministradorInline(admin.StackedInline):
    """Inline for Administrador in Usuario admin"""
    model = Administrador
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """Usuario admin with inline role details"""
    
    list_display = ['id', 'nombre', 'email', 'rol', 'created_at']
    list_filter = ['rol', 'created_at']
    search_fields = ['nombre', 'email']
    readonly_fields = ['password_hash', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('nombre', 'email', 'telefono', 'rol')
        }),
        ('Security', {
            'fields': ('password_hash',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ConsumidorInline, AdministradorInline]


@admin.register(Consumidor)
class ConsumidorAdmin(admin.ModelAdmin):
    """Consumidor admin with health metrics"""
    
    list_display = ['id', 'get_nombre', 'genero', 'edad', 'bmi_colored', 'created_at']
    list_filter = ['genero', 'created_at']
    search_fields = ['usuario__nombre', 'usuario__email']
    readonly_fields = ['bmi', 'bmi_category', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Health Metrics', {
            'fields': ('edad', 'peso', 'altura', 'bmi', 'bmi_category', 'genero')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_nombre(self, obj):
        return obj.usuario.nombre
    get_nombre.short_description = 'Nombre'
    get_nombre.admin_order_field = 'usuario__nombre'
    
    def bmi_colored(self, obj):
        """Display BMI with color based on category"""
        if not obj.bmi:
            return '-'
        
        color = '#28a745'  # Green (Normal)
        if obj.bmi < 18.5:
            color = '#ffc107'  # Yellow (Underweight)
        elif obj.bmi >= 30:
            color = '#dc3545'  # Red (Obese)
        elif obj.bmi >= 25:
            color = '#fd7e14'  # Orange (Overweight)
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}</span>',
            color, obj.bmi
        )
    bmi_colored.short_description = 'BMI'


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    """Administrador admin"""
    
    list_display = ['id', 'get_nombre', 'area_responsable', 'created_at']
    search_fields = ['usuario__nombre', 'usuario__email', 'area_responsable']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_nombre(self, obj):
        return obj.usuario.nombre
    get_nombre.short_description = 'Nombre'


# ============================================
# LOOKUP ADMIN
# ============================================

@admin.register(Emocion)
class EmocionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at']
    search_fields = ['nombre', 'descripcion']


@admin.register(Motivo)
class MotivoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at']
    search_fields = ['nombre', 'descripcion']


@admin.register(Solucion)
class SolucionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at']
    search_fields = ['nombre', 'descripcion']


@admin.register(Habito)
class HabitoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'descripcion', 'created_at']
    search_fields = ['nombre', 'descripcion']


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ['id', 'lectura', 'creacion', 'edicion', 'eliminacion', 'is_full_access']
    list_filter = ['lectura', 'creacion', 'edicion', 'eliminacion']


# ============================================
# FORM ADMIN
# ============================================

@admin.register(Formulario)
class FormularioAdmin(admin.ModelAdmin):
    """Formulario admin with JSON preview"""
    
    list_display = ['id', 'get_consumidor', 'get_habito', 'fecha_envio', 'emotion_count']
    list_filter = ['fecha_envio', 'habito', 'created_at']
    search_fields = ['consumidor__usuario__nombre', 'habito__nombre']
    readonly_fields = ['fecha_envio', 'emotion_count', 'motive_count', 'solution_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('consumidor', 'habito', 'fecha_envio')
        }),
        ('JSONB Data', {
            'fields': ('emociones', 'motivos', 'soluciones')
        }),
        ('Counts', {
            'fields': ('emotion_count', 'motive_count', 'solution_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre
    get_consumidor.short_description = 'Consumidor'
    get_consumidor.admin_order_field = 'consumidor__usuario__nombre'
    
    def get_habito(self, obj):
        return obj.habito.nombre if obj.habito else '-'
    get_habito.short_description = 'Hábito'


@admin.register(FormularioTemporal)
class FormularioTemporalAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_consumidor', 'emotion_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['consumidor__usuario__nombre']
    readonly_fields = ['emotion_count', 'created_at', 'updated_at']
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre
    get_consumidor.short_description = 'Consumidor'


# ============================================
# SENSOR ADMIN
# ============================================

class LecturaInline(admin.TabularInline):
    """Inline for Lecturas in Ventana admin"""
    model = Lectura
    extra = 0
    fields = ['heart_rate', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']


@admin.register(Ventana)
class VentanaAdmin(admin.ModelAdmin):
    """Ventana admin with sensor data inline"""
    
    list_display = ['id', 'get_consumidor', 'window_start', 'window_end', 'hr_mean', 'duration_minutes']
    list_filter = ['window_start', 'created_at']
    search_fields = ['consumidor__usuario__nombre']
    readonly_fields = ['duration_minutes', 'has_sensor_data', 'has_embeddings', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('consumidor', 'window_start', 'window_end', 'duration_minutes')
        }),
        ('Sensor Data', {
            'fields': ('hr_mean', 'hr_std', 'gyro_energy', 'accel_energy', 'has_sensor_data')
        }),
        ('Embeddings', {
            'fields': ('emotion_embedding', 'motive_embedding', 'solution_embedding', 'has_embeddings'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LecturaInline]
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre
    get_consumidor.short_description = 'Consumidor'


@admin.register(Lectura)
class LecturaAdmin(admin.ModelAdmin):
    list_display = ['id', 'ventana_id', 'heart_rate', 'has_accelerometer', 'has_gyroscope', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['has_heart_rate', 'has_accelerometer', 'has_gyroscope', 'created_at', 'updated_at']


# ============================================
# ANALYSIS ADMIN
# ============================================

@admin.register(Analisis)
class AnalisisAdmin(admin.ModelAdmin):
    """Analisis admin with prediction details"""
    
    list_display = ['id', 'get_consumidor', 'modelo_usado', 'urge_label_display', 'probabilidad_modelo', 'confidence_level']
    list_filter = ['urge_label', 'modelo_usado', 'created_at']
    search_fields = ['ventana__consumidor__usuario__nombre', 'modelo_usado']
    readonly_fields = ['is_urge_predicted', 'confidence_level', 'created_at', 'updated_at']
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre if obj.consumidor else '-'
    get_consumidor.short_description = 'Consumidor'
    
    def urge_label_display(self, obj):
        """Display urge label with color"""
        if obj.urge_label == 1:
            return format_html('<span style="color: #dc3545; font-weight: bold;">Urge</span>')
        elif obj.urge_label == 0:
            return format_html('<span style="color: #28a745;">No Urge</span>')
        return '-'
    urge_label_display.short_description = 'Prediction'


@admin.register(Deseo)
class DeseoAdmin(admin.ModelAdmin):
    """Deseo admin with resolution tracking"""
    
    list_display = ['id', 'get_consumidor', 'tipo', 'resolved_display', 'time_to_resolution', 'created_at']
    list_filter = ['tipo', 'resolved', 'created_at']
    search_fields = ['consumidor__usuario__nombre']
    readonly_fields = ['is_active', 'time_to_resolution', 'created_at', 'updated_at']
    
    actions = ['mark_as_resolved']
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre
    get_consumidor.short_description = 'Consumidor'
    
    def resolved_display(self, obj):
        """Display resolved status with color"""
        if obj.resolved:
            return format_html('<span style="color: #28a745;">✓ Resuelto</span>')
        return format_html('<span style="color: #ffc107;">⏳ Activo</span>')
    resolved_display.short_description = 'Estado'
    
    def mark_as_resolved(self, request, queryset):
        """Bulk action to mark desires as resolved"""
        count = queryset.update(resolved=True)
        self.message_user(request, f'{count} desires marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected as resolved'


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    """Notificacion admin with read status"""
    
    list_display = ['id', 'get_consumidor', 'tipo', 'leida_display', 'fecha_envio', 'is_recent']
    list_filter = ['tipo', 'leida', 'fecha_envio']
    search_fields = ['consumidor__usuario__nombre', 'contenido']
    readonly_fields = ['fecha_envio', 'is_unread', 'age_hours', 'is_recent', 'created_at', 'updated_at']
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def get_consumidor(self, obj):
        return obj.consumidor.nombre
    get_consumidor.short_description = 'Consumidor'
    
    def leida_display(self, obj):
        """Display read status with color"""
        if obj.leida:
            return format_html('<span style="color: #6c757d;">✓ Leída</span>')
        return format_html('<span style="color: #007bff; font-weight: bold;">✉ No leída</span>')
    leida_display.short_description = 'Estado'
    
    def mark_as_read(self, request, queryset):
        """Bulk action to mark as read"""
        count = queryset.update(leida=True)
        self.message_user(request, f'{count} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        """Bulk action to mark as unread"""
        count = queryset.update(leida=False)
        self.message_user(request, f'{count} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected as unread'


# ============================================
# ADMIN SITE CUSTOMIZATION
# ============================================

admin.site.site_header = "Health Tracker Administration"
admin.site.site_title = "Health Tracker Admin"
admin.site.index_title = "Welcome to Health Tracker Admin Portal"