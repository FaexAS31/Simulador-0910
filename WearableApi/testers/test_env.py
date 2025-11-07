from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'

print("="*60)
print("🔍 Testing .env file loading")
print("="*60)
print(f"BASE_DIR: {BASE_DIR}")
print(f".env path: {env_path}")
print(f".env exists: {env_path.exists()}")
print()

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("✅ .env loaded successfully")
else:
    print("❌ .env file not found")

print()
print("="*60)
print("📋 Environment Variables")
print("="*60)

vars_to_check = [
    'DEBUG',
    'SECRET_KEY',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
    'POSTGRES_HOST',
    'POSTGRES_PORT',
    'SENDGRID_API_KEY',
    'SENTRY_DSN',
    'CELERY_BROKER_URL'
]

for var in vars_to_check:
    value = os.environ.get(var)
    if value:
        if 'KEY' in var or 'PASSWORD' in var or 'DSN' in var:
            display_value = value[:10] + '...' if len(value) > 10 else '***'
        else:
            display_value = value
        print(f"✅ {var}: {display_value}")
    else:
        print(f"❌ {var}: NOT SET")

print("="*60)

