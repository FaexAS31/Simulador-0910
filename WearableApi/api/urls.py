
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter()

router.register(r'usuarios', views.UsuarioViewSet, basename='usuario')
router.register(r'administradores', views.AdministradorViewSet, basename='administrador')
router.register(r'consumidores', views.ConsumidorViewSet, basename='consumidor')

router.register(r'emociones', views.EmocionViewSet, basename='emocion')
router.register(r'motivos', views.MotivoViewSet, basename='motivo')
router.register(r'soluciones', views.SolucionViewSet, basename='solucion')
router.register(r'habitos', views.HabitoViewSet, basename='habito')
router.register(r'permisos', views.PermisoViewSet, basename='permiso')

router.register(r'formularios', views.FormularioViewSet, basename='formulario')
router.register(r'formularios-temporales', views.FormularioTemporalViewSet, basename='formulario-temporal')

router.register(r'ventanas', views.VentanaViewSet, basename='ventana')
router.register(r'lecturas', views.LecturaViewSet, basename='lectura')

router.register(r'analisis', views.AnalisisViewSet, basename='analisis')
router.register(r'deseos', views.DeseoViewSet, basename='deseo')
router.register(r'notificaciones', views.NotificacionViewSet, basename='notificacion')

router.register(r'dashboard/habit-tracking', views.VwHabitTrackingViewSet, basename='dashboard-habit-tracking')
router.register(r'dashboard/habit-stats', views.VwHabitStatsViewSet, basename='dashboard-habit-stats')
router.register(r'dashboard/heart-rate', views.VwHeartRateTimelineViewSet, basename='dashboard-heart-rate')
router.register(r'dashboard/heart-rate-stats', views.VwHeartRateStatsViewSet, basename='dashboard-heart-rate-stats')
router.register(r'dashboard/predictions', views.VwPredictionTimelineViewSet, basename='dashboard-predictions')
router.register(r'dashboard/prediction-summary', views.VwPredictionSummaryViewSet, basename='dashboard-prediction-summary')
router.register(r'dashboard/desires-tracking', views.VwDesiresTrackingViewSet, basename='dashboard-desires-tracking')
router.register(r'dashboard/desires', views.VwDesiresTrackingViewSet, basename='dashboard-desires')
router.register(r'dashboard/desires-stats', views.VwDesiresStatsViewSet, basename='dashboard-desires-stats')
router.register(r'dashboard/daily-summary', views.VwDailySummaryViewSet, basename='dashboard-daily-summary')
router.register(r'dashboard/weekly-comparison', views.VwWeeklyComparisonViewSet, basename='dashboard-weekly-comparison')
router.register(r'dashboard/heart-rate-today', views.VwHeartRateTodayViewSet, basename='dashboard-heart-rate-today')

urlpatterns = [
    path('', include(router.urls)),
    path('predict/', views.predict_craving),
    path('task-status/<str:task_id>/', views.check_task_status),
]

