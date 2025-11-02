"""
API URL Configuration
=====================
Automatic URL routing using Django REST Framework routers.

All endpoints follow REST conventions:
    GET    /api/resource/          - List
    POST   /api/resource/          - Create
    GET    /api/resource/{id}/     - Retrieve
    PUT    /api/resource/{id}/     - Update
    PATCH  /api/resource/{id}/     - Partial Update
    DELETE /api/resource/{id}/     - Delete
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

# Initialize router
router = DefaultRouter()

# ============================================
# USER ROUTES
# ============================================
router.register(r'usuarios', views.UsuarioViewSet, basename='usuario')
router.register(r'administradores', views.AdministradorViewSet, basename='administrador')
router.register(r'consumidores', views.ConsumidorViewSet, basename='consumidor')

# ============================================
# LOOKUP ROUTES
# ============================================
router.register(r'emociones', views.EmocionViewSet, basename='emocion')
router.register(r'motivos', views.MotivoViewSet, basename='motivo')
router.register(r'soluciones', views.SolucionViewSet, basename='solucion')
router.register(r'habitos', views.HabitoViewSet, basename='habito')
router.register(r'permisos', views.PermisoViewSet, basename='permiso')

# ============================================
# FORM ROUTES
# ============================================
router.register(r'formularios', views.FormularioViewSet, basename='formulario')
router.register(r'formularios-temporales', views.FormularioTemporalViewSet, basename='formulario-temporal')

# ============================================
# SENSOR ROUTES
# ============================================
router.register(r'ventanas', views.VentanaViewSet, basename='ventana')
router.register(r'lecturas', views.LecturaViewSet, basename='lectura')

# ============================================
# ANALYSIS ROUTES
# ============================================
router.register(r'analisis', views.AnalisisViewSet, basename='analisis')
router.register(r'deseos', views.DeseoViewSet, basename='deseo')
router.register(r'notificaciones', views.NotificacionViewSet, basename='notificacion')

# ============================================
# DASHBOARD ROUTES (Read-Only)
# ============================================
router.register(r'dashboard/habit-tracking', views.VwHabitTrackingViewSet, basename='dashboard-habit-tracking')
router.register(r'dashboard/habit-stats', views.VwHabitStatsViewSet, basename='dashboard-habit-stats')
router.register(r'dashboard/heart-rate', views.VwHeartRateTimelineViewSet, basename='dashboard-heart-rate')
router.register(r'dashboard/heart-rate-stats', views.VwHeartRateStatsViewSet, basename='dashboard-heart-rate-stats')
router.register(r'dashboard/predictions', views.VwPredictionTimelineViewSet, basename='dashboard-predictions')
router.register(r'dashboard/prediction-summary', views.VwPredictionSummaryViewSet, basename='dashboard-prediction-summary')
router.register(r'dashboard/desires', views.VwDesiresTrackingViewSet, basename='dashboard-desires')
router.register(r'dashboard/desires-stats', views.VwDesiresStatsViewSet, basename='dashboard-desires-stats')
router.register(r'dashboard/daily-summary', views.VwDailySummaryViewSet, basename='dashboard-daily-summary')
router.register(r'dashboard/weekly-comparison', views.VwWeeklyComparisonViewSet, basename='dashboard-weekly-comparison')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('predict/', views.predict_craving),
    path('task-status/<str:task_id>/', views.check_task_status),
]

"""
AVAILABLE ENDPOINTS
===================

USER MANAGEMENT
---------------
POST   /api/usuarios/register/              # Register new user
POST   /api/usuarios/login/                 # Login
GET    /api/usuarios/                       # List users
POST   /api/usuarios/                       # Create user
GET    /api/usuarios/{id}/                  # Get user
PUT    /api/usuarios/{id}/                  # Update user
DELETE /api/usuarios/{id}/                  # Delete user
GET    /api/administradores/                # List admins
GET    /api/consumidores/                   # List consumers

LOOKUP TABLES
-------------
GET    /api/emociones/                      # List emotions
POST   /api/emociones/                      # Create emotion
GET    /api/motivos/                        # List motives
GET    /api/soluciones/                     # List solutions
GET    /api/habitos/                        # List habits
GET    /api/permisos/                       # List permissions

FORMS
-----
GET    /api/formularios/                    # List forms
POST   /api/formularios/                    # Create form
GET    /api/formularios/{id}/               # Get form
PUT    /api/formularios/{id}/               # Update form
DELETE /api/formularios/{id}/               # Delete form

GET    /api/formularios-temporales/         # List temporary forms
POST   /api/formularios-temporales/         # Create temporary form

SENSOR DATA
-----------
GET    /api/ventanas/                       # List windows
POST   /api/ventanas/                       # Create window
GET    /api/lecturas/                       # List readings
POST   /api/lecturas/                       # Create reading

ANALYSIS
--------
GET    /api/analisis/                       # List analyses
POST   /api/analisis/                       # Create analysis

GET    /api/deseos/                         # List desires
POST   /api/deseos/                         # Create desire
POST   /api/deseos/{id}/resolve/            # Mark resolved

GET    /api/notificaciones/                 # List notifications
POST   /api/notificaciones/                 # Create notification
POST   /api/notificaciones/{id}/mark-read/  # Mark as read
POST   /api/notificaciones/{id}/mark-unread/ # Mark as unread

DASHBOARD (Read-Only)
---------------------
GET    /api/dashboard/habit-tracking/       # Cigarette tracking
GET    /api/dashboard/habit-stats/          # Habit statistics
GET    /api/dashboard/heart-rate/           # HR timeline
GET    /api/dashboard/heart-rate-stats/     # HR statistics
GET    /api/dashboard/predictions/          # Prediction timeline
GET    /api/dashboard/prediction-summary/   # Prediction summary
GET    /api/dashboard/desires/              # Desires tracking
GET    /api/dashboard/desires-stats/        # Desires statistics
GET    /api/dashboard/daily-summary/        # Daily KPIs
GET    /api/dashboard/weekly-comparison/    # Week comparison

FILTERING
---------
Consumer-specific data can be filtered using query parameters:
    ?consumidor_id=123

Example: /api/formularios/?consumidor_id=123
"""