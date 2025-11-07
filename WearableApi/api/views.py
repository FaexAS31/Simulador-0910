
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
from .tasks import predict_smoking_craving
from celery.result import AsyncResult

class UsuarioViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['register', 'login']:
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
        
        return Response(auth_data, status=status.HTTP_200_OK)
    
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

class LecturaViewSet(LoggingMixin, viewsets.ModelViewSet):
    
    queryset = Lectura.objects.select_related('ventana').all()
    serializer_class = LecturaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ventana_id = self.request.query_params.get('ventana_id')
        
        if ventana_id:
            queryset = queryset.filter(ventana_id=ventana_id)
        
        return queryset

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

