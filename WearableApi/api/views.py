"""
API Views
=========
ViewSets for all models with automatic CRUD operations and logging.

Design Pattern: ViewSet Pattern (Django REST Framework)
Each ViewSet handles CRUD operations for a model.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password


from api.models import *
from api.serializers import *
from utils.mixins import LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin
from utils.decorators import log_endpoint
from .tasks import predict_smoking_craving
from celery.result import AsyncResult





# ============================================
# USER VIEWSETS
# ============================================

class UsuarioViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet for Usuario CRUD operations.
    
    Endpoints:
        GET    /api/usuarios/          - List all users
        POST   /api/usuarios/          - Create user
        GET    /api/usuarios/{id}/     - Get user detail
        PUT    /api/usuarios/{id}/     - Update user
        DELETE /api/usuarios/{id}/     - Delete user
    """
    
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new user (consumidor or administrador).
        
        POST /api/usuarios/register/
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        rol = data.pop('rol', 'consumidor')
        
        # Create Usuario
        usuario = Usuario(
            nombre=data['nombre'],
            email=data['email'],
            telefono=data.get('telefono', ''),
            rol=rol
        )
        usuario.set_password(data['password'])
        usuario.save()
        
        # Create role-specific record
        if rol == 'consumidor':
            Consumidor.objects.create(
                usuario=usuario,
                edad=data.get('edad'),
                peso=data.get('peso'),
                altura=data.get('altura'),
                genero=data.get('genero', 'masculino')
            )
        elif rol == 'administrador':
            Administrador.objects.create(
                usuario=usuario,
                area_responsable=data.get('area_responsable', '')
            )
        
        self.logger.info(f"New user registered: {usuario.email} ({rol})")
        
        return Response({
            'message': 'User registered successfully',
            'user_id': usuario.id,
            'email': usuario.email,
            'rol': usuario.rol
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login endpoint (simple password check).
        
        POST /api/usuarios/login/
        Body: {"email": "...", "password": "..."}
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            usuario = Usuario.objects.get(email=email)
            
            if usuario.check_password(password):
                self.logger.info(f"User logged in: {email}")
                
                response_data = {
                    'user_id': usuario.id,
                    'nombre': usuario.nombre,
                    'email': usuario.email,
                    'rol': usuario.rol
                }
                
                # Add consumidor_id if user is consumidor
                if usuario.rol == 'consumidor':
                    try:
                        consumidor = usuario.consumidor
                        response_data['consumidor_id'] = consumidor.id
                    except Consumidor.DoesNotExist:
                        pass
                
                return Response(response_data)
            else:
                self.logger.warning(f"Failed login attempt: {email} (wrong password)")
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        except Usuario.DoesNotExist:
            self.logger.warning(f"Failed login attempt: {email} (user not found)")
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class AdministradorViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Administrador"""
    
    queryset = Administrador.objects.select_related('usuario').all()
    serializer_class = AdministradorSerializer


class ConsumidorViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Consumidor"""
    
    queryset = Consumidor.objects.select_related('usuario').all()
    serializer_class = ConsumidorSerializer


# ============================================
# LOOKUP VIEWSETS
# ============================================

class EmocionViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Emociones"""
    queryset = Emocion.objects.all()
    serializer_class = EmocionSerializer


class MotivoViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Motivos"""
    queryset = Motivo.objects.all()
    serializer_class = MotivoSerializer


class SolucionViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Soluciones"""
    queryset = Solucion.objects.all()
    serializer_class = SolucionSerializer


class HabitoViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Habitos"""
    queryset = Habito.objects.all()
    serializer_class = HabitoSerializer


class PermisoViewSet(LoggingMixin, viewsets.ModelViewSet):
    """ViewSet for Permisos"""
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer


# ============================================
# FORM VIEWSETS
# ============================================

class FormularioViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Formularios with consumer filtering.
    
    Filter by consumer: /api/formularios/?consumidor_id=123
    """
    
    queryset = Formulario.objects.select_related(
        'consumidor__usuario', 'habito'
    ).all()
    serializer_class = FormularioSerializer


class FormularioTemporalViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    """ViewSet for FormulariosTemporales"""
    
    queryset = FormularioTemporal.objects.select_related(
        'consumidor__usuario'
    ).all()
    serializer_class = FormularioTemporalSerializer


# ============================================
# SENSOR VIEWSETS
# ============================================

class VentanaViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    """ViewSet for Ventanas (time windows)"""
    
    queryset = Ventana.objects.select_related('consumidor__usuario').all()
    serializer_class = VentanaSerializer


class LecturaViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet for Lecturas (sensor readings).
    
    Filter by window: /api/lecturas/?ventana_id=123
    """
    
    queryset = Lectura.objects.select_related('ventana').all()
    serializer_class = LecturaSerializer
    
    def get_queryset(self):
        """Filter by ventana_id if provided"""
        queryset = super().get_queryset()
        ventana_id = self.request.query_params.get('ventana_id')
        
        if ventana_id:
            queryset = queryset.filter(ventana_id=ventana_id)
        
        return queryset


# ============================================
# ANALYSIS VIEWSETS
# ============================================

class AnalisisViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet for Analisis (ML predictions).
    
    Filter by consumer: /api/analisis/?consumidor_id=123
    """
    
    queryset = Analisis.objects.select_related('ventana__consumidor').all()
    serializer_class = AnalisisSerializer
    
    def get_queryset(self):
        """Filter by consumidor_id if provided"""
        queryset = super().get_queryset()
        consumidor_id = self.request.query_params.get('consumidor_id')
        
        if consumidor_id:
            queryset = queryset.filter(ventana__consumidor_id=consumidor_id)
        
        return queryset


class DeseoViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Deseos (urges/desires).
    
    Custom actions:
        POST /api/deseos/{id}/resolve/ - Mark desire as resolved
    """
    
    queryset = Deseo.objects.select_related('consumidor__usuario', 'ventana').all()
    serializer_class = DeseoSerializer
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark desire as resolved"""
        deseo = self.get_object()
        deseo.mark_resolved()
        
        self.logger.info(f"Desire {pk} marked as resolved")
        
        return Response({
            'message': 'Desire marked as resolved',
            'id': deseo.id,
            'resolved': deseo.resolved,
            'time_to_resolution': deseo.time_to_resolution
        })


class NotificacionViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Notificaciones.
    
    Custom actions:
        POST /api/notificaciones/{id}/mark-read/ - Mark as read
        POST /api/notificaciones/{id}/mark-unread/ - Mark as unread
    """
    
    queryset = Notificacion.objects.select_related(
        'consumidor__usuario', 'deseo'
    ).all()
    serializer_class = NotificacionSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notificacion = self.get_object()
        notificacion.mark_read()
        
        self.logger.info(f"Notification {pk} marked as read")
        
        return Response({
            'message': 'Notification marked as read',
            'id': notificacion.id,
            'leida': notificacion.leida
        })
    
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark notification as unread"""
        notificacion = self.get_object()
        notificacion.mark_unread()
        
        self.logger.info(f"Notification {pk} marked as unread")
        
        return Response({
            'message': 'Notification marked as unread',
            'id': notificacion.id,
            'leida': notificacion.leida
        })


# ============================================
# DASHBOARD VIEWSETS (Read-Only)
# ============================================

class VwHabitTrackingViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for habit tracking dashboard view"""
    queryset = VwHabitTracking.objects.all()
    serializer_class = VwHabitTrackingSerializer


class VwHabitStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for habit statistics dashboard view"""
    queryset = VwHabitStats.objects.all()
    serializer_class = VwHabitStatsSerializer


class VwHeartRateTimelineViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for heart rate timeline dashboard view"""
    queryset = VwHeartRateTimeline.objects.all()
    serializer_class = VwHeartRateTimelineSerializer


class VwHeartRateStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for heart rate statistics dashboard view"""
    queryset = VwHeartRateStats.objects.all()
    serializer_class = VwHeartRateStatsSerializer


class VwPredictionTimelineViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for prediction timeline dashboard view"""
    queryset = VwPredictionTimeline.objects.all()
    serializer_class = VwPredictionTimelineSerializer


class VwPredictionSummaryViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for prediction summary dashboard view"""
    queryset = VwPredictionSummary.objects.all()
    serializer_class = VwPredictionSummarySerializer


class VwDesiresTrackingViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for desires tracking dashboard view"""
    queryset = VwDesiresTracking.objects.all()
    serializer_class = VwDesiresTrackingSerializer


class VwDesiresStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for desires statistics dashboard view"""
    queryset = VwDesiresStats.objects.all()
    serializer_class = VwDesiresStatsSerializer


class VwDailySummaryViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for daily summary dashboard view"""
    queryset = VwDailySummary.objects.all()
    serializer_class = VwDailySummarySerializer


class VwWeeklyComparisonViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    """Read-only ViewSet for weekly comparison dashboard view"""
    queryset = VwWeeklyComparison.objects.all()
    serializer_class = VwWeeklyComparisonSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_craving(request):
    """
    Trigger async prediction
    
    POST /api/predict/
    
    OPTION 1: Let the system calculate features from sensor readings (RECOMMENDED)
    {
        // Empty body - will use recent Lectura data
    }
    
    OPTION 2: Provide manual features (for testing)
    {
        "manual_features": {
            "hr_mean": 85.5,
            "hr_std": 10.2,
            "hr_min": 70,
            "hr_max": 100,
            "hr_range": 30,
            "accel_magnitude_mean": 1.2,
            "accel_magnitude_std": 0.5,
            "gyro_magnitude_mean": 0.8,
            "gyro_magnitude_std": 0.3,
            "accel_energy": 150.0,
            "gyro_energy": 80.0
        }
    }
    """
    # Check if manual features provided (for testing)
    manual_features = request.data.get('manual_features', None)
    
    # Trigger async task - will auto-calculate from readings if manual_features is None
    task = predict_smoking_craving.delay(request.user.id, manual_features)
    
    return Response({
        'task_id': task.id,
        'status': 'processing',
        'message': 'Prediction task started. Will calculate from sensor readings.' if manual_features is None else 'Using provided manual features.'
    }, status=202)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_task_status(request, task_id):
    """Check status of async task"""
    task = AsyncResult(task_id)
    
    if task.ready():
        return Response({
            'status': 'completed',
            'result': task.result
        })
    else:
        return Response({'status': 'processing'})