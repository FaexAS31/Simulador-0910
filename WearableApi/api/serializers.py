
from rest_framework import serializers
from api.models import *

class UsuarioSerializer(serializers.ModelSerializer):
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre', 'telefono', 'email', 'password', 
            'rol', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password_hash': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class AdministradorSerializer(serializers.ModelSerializer):
    
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='usuario',
        write_only=True
    )
    
    class Meta:
        model = Administrador
        fields = ['id', 'usuario', 'usuario_id', 'area_responsable', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ConsumidorSerializer(serializers.ModelSerializer):
    
    usuario = UsuarioSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='usuario',
        write_only=True
    )
    bmi_category = serializers.ReadOnlyField()
    
    class Meta:
        model = Consumidor
        fields = [
            'id', 'usuario', 'usuario_id', 'edad', 'peso', 'altura', 
            'bmi', 'bmi_category', 'genero', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'bmi', 'bmi_category', 'created_at', 'updated_at']

class EmocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emocion
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class MotivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivo
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class SolucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solucion
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class HabitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habito
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class PermisoSerializer(serializers.ModelSerializer):
    is_readonly = serializers.ReadOnlyField()
    is_full_access = serializers.ReadOnlyField()
    
    class Meta:
        model = Permiso
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class FormularioSerializer(serializers.ModelSerializer):
    
    habito_nombre = serializers.SerializerMethodField()
    consumidor_nombre = serializers.CharField(source='consumidor.nombre', read_only=True)
    emotion_count = serializers.ReadOnlyField()
    motive_count = serializers.ReadOnlyField()
    solution_count = serializers.ReadOnlyField()
    
    def get_habito_nombre(self, obj):
        if obj.habito and isinstance(obj.habito, dict):
            return obj.habito.get('nombre', None)
        return None
    
    class Meta:
        model = Formulario
        fields = [
            'id', 'consumidor', 'consumidor_nombre', 'fecha_envio', 
            'habito', 'habito_nombre', 'emociones', 'motivos', 'soluciones',
            'emotion_count', 'motive_count', 'solution_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'fecha_envio', 'created_at', 'updated_at']

class FormularioTemporalSerializer(serializers.ModelSerializer):
    
    consumidor_nombre = serializers.CharField(source='consumidor.nombre', read_only=True)
    emotion_count = serializers.ReadOnlyField()
    
    class Meta:
        model = FormularioTemporal
        fields = [
            'id', 'consumidor', 'consumidor_nombre', 'emociones',
            'emotion_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class VentanaSerializer(serializers.ModelSerializer):
    
    consumidor_nombre = serializers.CharField(source='consumidor.nombre', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    has_sensor_data = serializers.ReadOnlyField()
    has_embeddings = serializers.ReadOnlyField()
    
    class Meta:
        model = Ventana
        fields = [
            'id', 'consumidor', 'consumidor_nombre', 'window_start', 'window_end',
            'hr_mean', 'hr_std', 'gyro_energy', 'accel_energy',
            'emotion_embedding', 'motive_embedding', 'solution_embedding',
            'duration_minutes', 'has_sensor_data', 'has_embeddings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class LecturaSerializer(serializers.ModelSerializer):
    
    has_heart_rate = serializers.ReadOnlyField()
    has_accelerometer = serializers.ReadOnlyField()
    has_gyroscope = serializers.ReadOnlyField()
    
    class Meta:
        model = Lectura
        fields = [
            'id', 'ventana', 'heart_rate', 
            'accel_x', 'accel_y', 'accel_z',
            'gyro_x', 'gyro_y', 'gyro_z',
            'has_heart_rate', 'has_accelerometer', 'has_gyroscope',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AnalisisSerializer(serializers.ModelSerializer):
    
    is_urge_predicted = serializers.ReadOnlyField()
    confidence_level = serializers.ReadOnlyField()
    consumidor_id = serializers.IntegerField(source='ventana.consumidor.id', read_only=True)
    
    class Meta:
        model = Analisis
        fields = [
            'id', 'ventana', 'consumidor_id', 'modelo_usado', 'probabilidad_modelo',
            'urge_label', 'recall', 'f1_score', 'accuracy', 'roc_auc',
            'comentario_modelo', 'feature_importance',
            'is_urge_predicted', 'confidence_level',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class DeseoSerializer(serializers.ModelSerializer):
    
    consumidor_nombre = serializers.CharField(source='consumidor.nombre', read_only=True)
    is_active = serializers.ReadOnlyField()
    time_to_resolution = serializers.ReadOnlyField()
    
    class Meta:
        model = Deseo
        fields = [
            'id', 'consumidor', 'consumidor_nombre', 'ventana', 'tipo',
            'resolved', 'is_active', 'time_to_resolution',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class NotificacionSerializer(serializers.ModelSerializer):
    
    consumidor_nombre = serializers.CharField(source='consumidor.nombre', read_only=True)
    is_unread = serializers.ReadOnlyField()
    age_hours = serializers.ReadOnlyField()
    is_recent = serializers.ReadOnlyField()
    
    class Meta:
        model = Notificacion
        fields = [
            'id', 'consumidor', 'consumidor_nombre', 'deseo', 'tipo',
            'contenido', 'fecha_envio', 'leida',
            'is_unread', 'age_hours', 'is_recent',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'fecha_envio', 'created_at', 'updated_at']

class VwHabitTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwHabitTracking
        fields = '__all__'

class VwHabitStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwHabitStats
        fields = '__all__'

class VwHeartRateTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwHeartRateTimeline
        fields = '__all__'

class VwHeartRateStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwHeartRateStats
        fields = '__all__'

class VwHeartRateTodaySerializer(serializers.ModelSerializer):
    class Meta:
        model = VwHeartRateToday
        fields = '__all__'

class VwPredictionTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwPredictionTimeline
        fields = '__all__'

class VwPredictionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VwPredictionSummary
        fields = '__all__'

class VwDesiresTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwDesiresTracking
        fields = '__all__'

class VwDesiresStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwDesiresStats
        fields = '__all__'

class VwDailySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VwDailySummary
        fields = '__all__'

class VwWeeklyComparisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = VwWeeklyComparison
        fields = '__all__'

class LoginSerializer(serializers.Serializer):
    
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email is required',
            'invalid': 'Enter a valid email address'
        }
    )
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Password is required'
        }
    )

class RegisterSerializer(serializers.Serializer):
    
    nombre = serializers.CharField(
        max_length=100,
        required=True,
        error_messages={'required': 'Name is required'}
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email is required',
            'invalid': 'Enter a valid email address'
        }
    )
    password = serializers.CharField(
        min_length=6,
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Password is required',
            'min_length': 'Password must be at least 6 characters long'
        }
    )
    telefono = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default=''
    )
    rol = serializers.ChoiceField(
        choices=RolChoices.choices,
        default=RolChoices.CONSUMIDOR,
        required=False
    )
    
    genero = serializers.ChoiceField(
        choices=GeneroChoices.choices,
        required=False,
        allow_null=True,
        default=None
    )
    
    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered")
        return value.lower()
    
    def validate_password(self, value):
        if not any(c.isalpha() for c in value):
            raise serializers.ValidationError("Password must contain at least one letter")
        return value

class UserProfileSerializer(serializers.Serializer):
    
    nombre = serializers.CharField(max_length=100, required=False)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(
        min_length=6,
        required=False,
        style={'input_type': 'password'}
    )
    
    edad = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=120)
    peso = serializers.FloatField(required=False, allow_null=True, min_value=1.0)
    altura = serializers.FloatField(required=False, allow_null=True, min_value=50.0)
    genero = serializers.ChoiceField(choices=GeneroChoices.choices, required=False)
    
    area_responsable = serializers.CharField(max_length=100, required=False, allow_blank=True)

