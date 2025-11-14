
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password

from api.models import *
from api.serializers import *
from api.services import AuthenticationService, UserFactory
from utils.mixins import LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin
from utils.decorators import log_endpoint
from django.utils import timezone
from django.core.cache import cache
from .tasks import predict_smoking_craving
from celery.result import AsyncResult

# Import the new Celery tasks
from api.tasks import (
    check_and_calculate_ventana_stats,
    calculate_ventana_statistics,
    trigger_prediction_if_ready
)

class UsuarioViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['register', 'login', 'logout']:
            return [AllowAny()]
        return [permission() for permission in self.permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        usuario, success, message = UserFactory.create_user(serializer.validated_data)
        
        if not success:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from api.services.auth_service import AuthenticationService
        tokens = AuthenticationService.generate_tokens(usuario)
        
        user_data = {
            'id': usuario.id,
            'user_id': usuario.id,
            'nombre': usuario.nombre,
            'email': usuario.email,
            'telefono': usuario.telefono,
            'rol': usuario.rol,
        }
        
        if usuario.is_consumidor and hasattr(usuario, 'consumidor'):
            consumidor = usuario.consumidor
            user_data['consumidor_id'] = consumidor.id
            user_data['edad'] = consumidor.edad
            user_data['peso'] = consumidor.peso
            user_data['altura'] = consumidor.altura
            user_data['genero'] = consumidor.genero
            user_data['bmi'] = consumidor.bmi
        elif usuario.is_administrador and hasattr(usuario, 'administrador'):
            admin = usuario.administrador
            user_data['administrador_id'] = admin.id
        
        self.logger.info(f"New user registered: {usuario.email} (rol: {usuario.rol})")
        
        return Response({
            'token': tokens['access'],
            'refresh_token': tokens['refresh'],
            'expires_in': 3600,
            'user': user_data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        success, auth_data, error = AuthenticationService.authenticate(email, password)
        
        if not success:
            return Response(
                {'error': error},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # ============================================
        # AUTO-START MONITORING SESSION FOR CONSUMERS
        # ============================================
        usuario = Usuario.objects.get(email=email)
        
        if hasattr(usuario, 'consumidor'):
            consumidor = usuario.consumidor
            device_id = 'default'  # Can be customized if multiple devices
            
            # Create new ventana for this session
            ventana = Ventana.objects.create(
                consumidor=consumidor,
                window_start=timezone.now(),
                window_end=timezone.now() + timezone.timedelta(hours=8)  # 8-hour session
            )
            
            # Generate session ID
            import secrets
            session_id = f"sess_{secrets.token_hex(8)}"
            
            # Store active session in cache
            session_data = {
                'session_id': session_id,
                'consumidor_id': consumidor.id,
                'ventana_id': ventana.id,
                'device_id': device_id,
                'usuario_id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.email,
                'edad': consumidor.edad,
                'genero': consumidor.genero,
                'started_at': timezone.now().isoformat(),
            }
            
            # Store in cache with 8-hour expiration
            session_key = f'active_session:{consumidor.id}'
            cache.set(session_key, session_data, timeout=28800)  # 8 hours
            
            # Also store by device_id for ESP32 polling
            device_key = f'device_session:{device_id}'
            cache.set(device_key, session_data, timeout=28800)
            
            # Add session info to auth response
            auth_data['monitoring_session'] = {
                'session_id': session_id,
                'ventana_id': ventana.id,
                'is_active': True,
                'started_at': session_data['started_at']
            }
            
            self.logger.info(
                f"Auto-started monitoring session for consumer {consumidor.id} "
                f"(Ventana {ventana.id})"
            )
        
        return Response(auth_data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user and automatically stop monitoring session
        
        POST /api/usuarios/logout/
        
        Response:
        {
            "message": "Logged out successfully",
            "session_stopped": true
        }
        """
        try:
            usuario = request.user
            session_stopped = False
            
            # If user is a consumer, stop their monitoring session
            if hasattr(usuario, 'consumidor'):
                consumidor = usuario.consumidor
                
                # Get active session
                session_key = f'active_session:{consumidor.id}'
                session_data = cache.get(session_key)
                
                if session_data:
                    # Remove session from cache
                    cache.delete(session_key)
                    
                    # Also remove device session
                    device_id = session_data.get('device_id', 'default')
                    device_key = f'device_session:{device_id}'
                    cache.delete(device_key)
                    
                    # Close the ventana window
                    ventana_id = session_data['ventana_id']
                    try:
                        ventana = Ventana.objects.get(id=ventana_id)
                        ventana.window_end = timezone.now()
                        ventana.save()
                        session_stopped = True
                    except Ventana.DoesNotExist:
                        pass
                    
                    self.logger.info(
                        f"Monitoring session stopped on logout: Consumer {consumidor.id}"
                    )
            
            # Blacklist the token (if using token blacklist)
            # This depends on your JWT implementation
            
            self.logger.info(f"User logged out: {usuario.email}")
            
            return Response({
                'message': 'Logged out successfully',
                'session_stopped': session_stopped
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error during logout: {str(e)}")
            return Response({
                'error': 'Logout failed',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def profile(self, request, pk=None):
        usuario = self.get_object()
        serializer = UserProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        success, message = UserFactory.update_user(usuario, serializer.validated_data)
        
        if not success:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_serializer = UsuarioSerializer(usuario)
        return Response({
            'message': message,
            'user': updated_serializer.data
        }, status=status.HTTP_200_OK)


class DeviceSessionViewSet(LoggingMixin, viewsets.ViewSet):
    """
    ViewSet for ESP32 device session management
    Sessions are automatically created on consumer login
    
    Endpoints:
    - POST /device-session/check-session/ - Check for active session (ESP32, no auth)
    - GET /device-session/active/ - Get active session info (website, requires auth)
    - POST /device-session/extend-window/ - Extend ventana window (ESP32, no auth)
    """
    
    def get_permissions(self):
        """
        Allow unauthenticated access for ESP32 endpoints
        """
        if self.action in ['check_session', 'extend_window']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def check_session(self, request):
        """
        ESP32 checks if there's an active session for this device
        Called every 10 seconds by ESP32
        
        POST /api/device-session/check-session/
        Body: {
            "device_id": "ESP32_ABC123"
        }
        
        Response (if session active):
        {
            "is_active": true,
            "session_id": "sess_xyz789",
            "consumidor_id": 1,
            "ventana_id": 42,
            "usuario_nombre": "John Doe",
            "started_at": "2025-11-10T12:30:00Z"
        }
        
        Response (if no session):
        {
            "is_active": false,
            "message": "No active session"
        }
        """
        try:
            device_id = request.data.get('device_id', 'default')
            
            # Check if there's an active session for this device
            device_key = f'device_session:{device_id}'
            session_data = cache.get(device_key)
            
            if session_data:
                return Response({
                    'is_active': True,
                    'session_id': session_data['session_id'],
                    'consumidor_id': session_data['consumidor_id'],
                    'ventana_id': session_data['ventana_id'],
                    'usuario_nombre': session_data['nombre'],
                    'usuario_email': session_data['email'],
                    'edad': session_data.get('edad'),
                    'genero': session_data.get('genero'),
                    'started_at': session_data['started_at'],
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'is_active': False,
                    'message': 'No active session for this device'
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error checking session: {str(e)}")
            return Response({
                'error': 'Failed to check session',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def active(self, request):
        """
        Get current active session info for logged-in user
        Used by website to show session status
        
        GET /api/device-session/active/
        
        Response:
        {
            "is_active": true,
            "session_id": "sess_xyz789",
            "ventana_id": 42,
            "device_id": "default",
            "started_at": "2025-11-10T12:30:00Z"
        }
        """
        try:
            usuario = request.user
            
            if not hasattr(usuario, 'consumidor'):
                return Response({
                    'error': 'Only consumers can check session status'
                }, status=status.HTTP_403_FORBIDDEN)
            
            consumidor = usuario.consumidor
            
            # Get active session
            session_key = f'active_session:{consumidor.id}'
            session_data = cache.get(session_key)
            
            if session_data:
                return Response({
                    'is_active': True,
                    'session_id': session_data['session_id'],
                    'ventana_id': session_data['ventana_id'],
                    'device_id': session_data['device_id'],
                    'started_at': session_data['started_at'],
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'is_active': False,
                    'message': 'No active monitoring session'
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error getting active session: {str(e)}")
            return Response({
                'error': 'Failed to get session status',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def extend_window(self, request):
        """
        Extend the current ventana window
        Called by ESP32 to keep session alive
        
        POST /api/device-session/extend-window/
        Body: {"ventana_id": 42}
        """
        try:
            ventana_id = request.data.get('ventana_id')
            
            if not ventana_id:
                return Response({
                    'error': 'ventana_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                ventana = Ventana.objects.get(id=ventana_id)
            except Ventana.DoesNotExist:
                return Response({
                    'error': 'Ventana not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Extend window by 1 hour
            ventana.window_end = timezone.now() + timezone.timedelta(hours=1)
            ventana.save()
            
            self.logger.info(f"Ventana {ventana_id} window extended")
            
            return Response({
                'status': 'success',
                'new_window_end': ventana.window_end.isoformat(),
                'message': 'Window extended by 1 hour'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            self.logger.error(f"Error extending window: {str(e)}")
            return Response({
                'error': 'Failed to extend window',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class AdministradorViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Administrador.objects.select_related('usuario').all()
    serializer_class = AdministradorSerializer

class ConsumidorViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Consumidor.objects.select_related('usuario').all()
    serializer_class = ConsumidorSerializer

class EmocionViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Emocion.objects.all()
    serializer_class = EmocionSerializer

class MotivoViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Motivo.objects.all()
    serializer_class = MotivoSerializer

class SolucionViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Solucion.objects.all()
    serializer_class = SolucionSerializer

class HabitoViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Habito.objects.all()
    serializer_class = HabitoSerializer

class PermisoViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer

class FormularioViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    
    queryset = Formulario.objects.select_related(
        'consumidor__usuario'
    ).all()
    serializer_class = FormularioSerializer

class FormularioTemporalViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    
    queryset = FormularioTemporal.objects.select_related(
        'consumidor__usuario'
    ).all()
    serializer_class = FormularioTemporalSerializer

class VentanaViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    
    queryset = Ventana.objects.select_related('consumidor__usuario').all()
    serializer_class = VentanaSerializer


class AnalisisViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Analisis.objects.select_related('ventana__consumidor').all()
    serializer_class = AnalisisSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        consumidor_id = self.request.query_params.get('consumidor_id')
        
        if consumidor_id:
            queryset = queryset.filter(ventana__consumidor_id=consumidor_id)
        
        return queryset

class DeseoViewSet(LoggingMixin, ConsumerFilterMixin, viewsets.ModelViewSet):
    
    queryset = Deseo.objects.select_related('consumidor__usuario', 'ventana').all()
    serializer_class = DeseoSerializer
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
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
    
    queryset = Notificacion.objects.select_related(
        'consumidor__usuario', 'deseo'
    ).all()
    serializer_class = NotificacionSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
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
        notificacion = self.get_object()
        notificacion.mark_unread()
        
        self.logger.info(f"Notification {pk} marked as unread")
        
        return Response({
            'message': 'Notification marked as unread',
            'id': notificacion.id,
            'leida': notificacion.leida
        })

class VwHabitTrackingViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwHabitTracking.objects.all()
    serializer_class = VwHabitTrackingSerializer

class VwHabitStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwHabitStats.objects.all()
    serializer_class = VwHabitStatsSerializer

class VwHeartRateTimelineViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwHeartRateTimeline.objects.all()
    serializer_class = VwHeartRateTimelineSerializer

class VwHeartRateStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwHeartRateStats.objects.all()
    serializer_class = VwHeartRateStatsSerializer

class VwHeartRateTodayViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwHeartRateToday.objects.all()
    serializer_class = VwHeartRateTodaySerializer

class VwPredictionTimelineViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwPredictionTimeline.objects.all()
    serializer_class = VwPredictionTimelineSerializer

class VwPredictionSummaryViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwPredictionSummary.objects.all()
    serializer_class = VwPredictionSummarySerializer

class VwDesiresTrackingViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwDesiresTracking.objects.all()
    serializer_class = VwDesiresTrackingSerializer

class VwDesiresStatsViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwDesiresStats.objects.all()
    serializer_class = VwDesiresStatsSerializer

class VwDailySummaryViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwDailySummary.objects.all()
    serializer_class = VwDailySummarySerializer

class VwWeeklyComparisonViewSet(LoggingMixin, ConsumerFilterMixin, ReadOnlyMixin, viewsets.ModelViewSet):
    queryset = VwWeeklyComparison.objects.all()
    serializer_class = VwWeeklyComparisonSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_craving(request):
    manual_features = request.data.get('manual_features', None)
    
    task = predict_smoking_craving.delay(request.user.id, manual_features)
    
    return Response({
        'task_id': task.id,
        'status': 'processing',
        'message': 'Prediction task started. Will calculate from sensor readings.' if manual_features is None else 'Using provided manual features.'
    }, status=202)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_task_status(request, task_id):
    task = AsyncResult(task_id)
    
    if task.ready():
        return Response({
            'status': 'completed',
            'result': task.result
        })
    else:
        return Response({'status': 'processing'})


class LecturaViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing sensor readings (Lecturas) from ESP32
    
    Automatically triggers Celery tasks to:
    1. Calculate ventana statistics (hr_mean, hr_std, accel_energy, gyro_energy)
    2. Trigger ML predictions when ready
    
    Endpoints:
    - GET /api/lecturas/ - List all readings (with filters)
    - GET /api/lecturas/:id/ - Get specific reading
    - POST /api/lecturas/ - Create new reading (ESP32, no auth required)
    - GET /api/lecturas/recent/ - Get recent readings for a consumer
    """
    
    queryset = Lectura.objects.select_related('ventana', 'ventana__consumidor').all()
    serializer_class = LecturaSerializer
    
    def get_queryset(self):
        """
        Filter queryset based on query parameters
        Supports: ventana_id, consumidor_id, limit, ordering
        """
        queryset = super().get_queryset()
        
        # Filter by ventana_id
        ventana_id = self.request.query_params.get('ventana_id')
        if ventana_id:
            queryset = queryset.filter(ventana_id=ventana_id)
        
        # Filter by consumidor_id (through ventana relationship)
        consumidor_id = self.request.query_params.get('consumidor_id')
        if consumidor_id:
            queryset = queryset.filter(ventana__consumidor_id=consumidor_id)
        
        # Apply ordering (default: most recent first)
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        # Apply limit if specified
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit_int = int(limit)
                queryset = queryset[:limit_int]
            except ValueError:
                pass
        
        return queryset
    
    def get_permissions(self):
        """
        Allow unauthenticated POST requests for ESP32 sensor data
        All other actions require authentication
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """
        Create a new lectura from ESP32 sensor data
        
        This method:
        1. Validates and saves the sensor reading
        2. Checks if ventana has enough readings (default: 5)
        3. Triggers Celery task to calculate ventana statistics if ready
        4. Triggers ML prediction if statistics are complete
        
        Expected payload:
        {
            "ventana": 1,  # or "ventana_id": 1
            "heart_rate": 75.5,
            "accel_x": 0.12,
            "accel_y": -0.05,
            "accel_z": 0.98,
            "gyro_x": 1.5,
            "gyro_y": -0.3,
            "gyro_z": 0.8
        }
        """
        try:
            # Support both 'ventana' and 'ventana_id' in request
            ventana_id = request.data.get('ventana') or request.data.get('ventana_id')
            
            if not ventana_id:
                return Response({
                    'error': 'ventana_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate ventana exists
            try:
                ventana = Ventana.objects.get(id=ventana_id)
            except Ventana.DoesNotExist:
                return Response({
                    'error': f'Ventana with id {ventana_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Create the lectura
            data = request.data.copy()
            data['ventana'] = ventana_id  # Ensure 'ventana' key is used
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            lectura = self.perform_create(serializer)
            
            self.logger.info(
                f"✓ Lectura created: ID={lectura.id}, Ventana={ventana_id}, "
                f"HR={data.get('heart_rate')}, "
                f"Accel=({data.get('accel_x')}, {data.get('accel_y')}, {data.get('accel_z')}), "
                f"Gyro=({data.get('gyro_x')}, {data.get('gyro_y')}, {data.get('gyro_z')})"
            )
            
            # TRIGGER CELERY TASKS
            # Check if we have enough readings to calculate statistics
            lectura_count = Lectura.objects.filter(ventana_id=ventana_id).count()
            
            # Trigger check and calculation every 5 readings
            # This prevents overwhelming the task queue
            if lectura_count % 5 == 0:
                self.logger.info(
                    f"📊 Triggering ventana calculation check (count: {lectura_count})"
                )
                check_and_calculate_ventana_stats.delay(ventana_id, min_readings=5)
            
            # If ventana is ending soon, force calculation
            if ventana.window_end and timezone.now() >= ventana.window_end:
                self.logger.info(f"⏰ Ventana {ventana_id} window ended, forcing calculation")
                calculate_ventana_statistics.delay(ventana_id)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                {
                    'status': 'success',
                    'id': lectura.id,
                    'ventana_id': ventana_id,
                    'message': 'Sensor data saved successfully',
                    'lectura_count': lectura_count,
                    'calculation_pending': lectura_count % 5 == 0,
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except Exception as e:
            self.logger.error(f"Error creating lectura: {str(e)}")
            return Response({
                'error': 'Failed to create lectura',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """Save the lectura and return the instance"""
        return serializer.save()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def recent(self, request):
        """
        Get recent sensor readings for a consumer
        
        Query params:
        - consumidor_id (required): Consumer ID
        - limit (optional): Number of readings to return (default: 10)
        - hours (optional): Only readings from last N hours
        
        GET /api/lecturas/recent/?consumidor_id=1&limit=20&hours=1
        """
        consumidor_id = request.query_params.get('consumidor_id')
        if not consumidor_id:
            return Response({
                'error': 'consumidor_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get limit parameter
        limit = int(request.query_params.get('limit', 10))
        
        # Base queryset
        queryset = self.get_queryset().filter(
            ventana__consumidor_id=consumidor_id
        )
        
        # Filter by hours if specified
        hours = request.query_params.get('hours')
        if hours:
            from datetime import timedelta
            time_threshold = timezone.now() - timedelta(hours=int(hours))
            queryset = queryset.filter(created_at__gte=time_threshold)
        
        # Apply limit and get results
        lecturas = queryset[:limit]
        serializer = self.get_serializer(lecturas, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def force_calculation(self, request):
        """
        Force calculation of ventana statistics
        Useful for manual triggering or testing
        
        POST /api/lecturas/force-calculation/
        Body: { "ventana_id": 1 }
        """
        ventana_id = request.data.get('ventana_id')
        
        if not ventana_id:
            return Response({
                'error': 'ventana_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ventana = Ventana.objects.get(id=ventana_id)
        except Ventana.DoesNotExist:
            return Response({
                'error': f'Ventana {ventana_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if there are readings
        lectura_count = Lectura.objects.filter(ventana_id=ventana_id).count()
        
        if lectura_count == 0:
            return Response({
                'error': 'No readings available for this ventana'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger calculation
        task = calculate_ventana_statistics.delay(ventana_id)
        
        self.logger.info(
            f"🔧 Manual calculation triggered for Ventana {ventana_id} "
            f"(Task ID: {task.id})"
        )
        
        return Response({
            'status': 'calculation_triggered',
            'ventana_id': ventana_id,
            'lectura_count': lectura_count,
            'task_id': task.id,
            'message': 'Ventana calculation task started'
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """
        Get statistics about lecturas and ventanas
        
        GET /api/lecturas/stats/?consumidor_id=1
        """
        consumidor_id = request.query_params.get('consumidor_id')
        
        if consumidor_id:
            # Stats for specific consumer
            total_lecturas = Lectura.objects.filter(
                ventana__consumidor_id=consumidor_id
            ).count()
            
            ventanas_with_stats = Ventana.objects.filter(
                consumidor_id=consumidor_id,
                hr_mean__isnull=False
            ).count()
            
            ventanas_pending = Ventana.objects.filter(
                consumidor_id=consumidor_id,
                hr_mean__isnull=True
            ).count()
            
            return Response({
                'consumidor_id': consumidor_id,
                'total_lecturas': total_lecturas,
                'ventanas_calculated': ventanas_with_stats,
                'ventanas_pending': ventanas_pending
            })
        else:
            # Global stats
            total_lecturas = Lectura.objects.count()
            total_ventanas = Ventana.objects.count()
            ventanas_calculated = Ventana.objects.filter(hr_mean__isnull=False).count()
            ventanas_pending = Ventana.objects.filter(hr_mean__isnull=True).count()
            
            return Response({
                'total_lecturas': total_lecturas,
                'total_ventanas': total_ventanas,
                'ventanas_calculated': ventanas_calculated,
                'ventanas_pending': ventanas_pending,
                'calculation_rate': f"{(ventanas_calculated/total_ventanas*100):.1f}%" if total_ventanas > 0 else "0%"
            })
