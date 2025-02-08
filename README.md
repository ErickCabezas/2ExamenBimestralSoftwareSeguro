# Configuración del Entorno Local

Esta guía te ayudará a configurar y ejecutar el proyecto localmente.

## Requisitos Previos

- Python 3.x
- PostgreSQL

## Pasos de Instalación

### 1. Crear y Activar el Entorno Virtual

Primero, crea un entorno virtual de Python:

```bash
python -m venv venv
```

Luego actívalo:

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 2. Dependencias

El proyecto requiere las siguientes dependencias:
- Flask v2.0.3
- psycopg2-binary v2.9.6
- gunicorn v20.1.0
- python-dotenv
- Flask-RESTX v0.5.1
- Werkzeug v2.0.3
- PyJWT v2.8.0

Instala todas las dependencias usando:

```bash
pip install -r requirements.txt
```

### 3. Configuración del Entorno

Crea un archivo `.env` en la raíz del proyecto con la siguiente configuración:

```plaintext
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=corebank
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
JWT_SECRET_KEY=tu_clave_secreta_desarrollo
```

Asegúrate de reemplazar los valores con tu configuración real, especialmente la `JWT_SECRET_KEY` para propósitos de desarrollo.
### 4. Ejecutar proyecto
Mantener el entorno virtual (venv) activado, pero ejecutar desde la raíz del proyecto. Es decir:
Mantén el venv activado:
Deberías ver (venv) al inicio de tu línea de comandos
```bash
(venv) PS C:\Users\USUARIO\source\repos\Examen2BSoftwareSeguro\core-bankec-python>
```
Asegúrate que estás en la raíz del proyecto (donde está el run.py), NO dentro de la carpeta app:

CORRECTO - Estar aquí:
```bash
C:\Users\USUARIO\source\repos\Examen2BSoftwareSeguro\core-bankec-python>
```
#### NO estar aquí:
```bash
C:\Users\USUARIO\source\repos\Examen2BSoftwareSeguro\core-bankec-python\app>
```
### Ejecuta el programa:
```bash
python run.py
```

# Implementación de JWT en Core Banking API

## Descripción
Este documento detalla la implementación de JSON Web Tokens (JWT) para la autenticación y autorización en el Core Banking API. La implementación permite asegurar los endpoints y manejar la autenticación de usuarios de manera stateless.

## Estructura de Archivos
```
core-bankec-python/
├── app/
│   ├── __init__.py
│   ├── auth.py        # Manejo de JWT
│   ├── db.py          # Conexión a base de datos
│   └── main.py        # Endpoints principales
├── run.py             # Archivo de ejecución
└── requirements.txt   # Dependencias
```

## Dependencias
```
Flask==2.0.3
Flask-RESTX==0.5.1
PyJWT==2.8.0
```

## Implementación

### 1. Configuración JWT (auth.py)
```python
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import g, request
from flask_restx import abort
import os

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'tu_clave_secreta_desarrollo')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

def generate_jwt_token(user_data):
    """Genera un token JWT."""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
```

### 2. Protección de Rutas
```python
def jwt_required(f):
    """Decorator para proteger endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            abort(401, "Authorization header missing or invalid")
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            g.user = {
                'id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            abort(401, "Token has expired")
        except jwt.InvalidTokenError:
            abort(401, "Invalid token")
    return decorated
```

### 3. Implementación en Endpoints (main.py)
```python
@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model, validate=True)
    def post(self):
        """Login endpoint que genera token JWT."""
        data = api.payload
        # Validación de credenciales
        if user_valid:
            token = generate_jwt_token(user_data)
            return {"token": token}, 200
        return {"message": "Invalid credentials"}, 401

@bank_ns.route('/deposit')
class Deposit(Resource):
    @jwt_required
    def post(self):
        """Endpoint protegido con JWT."""
        # Acceso a datos del usuario
        user_id = g.user['id']
        # Lógica del endpoint...
```

## Uso

### 1. Login y Obtención del Token
```bash
curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"user1","password":"pass1"}'
```

### 2. Uso del Token en Requests
```bash
curl -X POST http://localhost:8000/bank/deposit \
     -H "Authorization: Bearer <tu_token_jwt>" \
     -H "Content-Type: application/json" \
     -d '{"amount":100}'
```

## Variables de Entorno
```
JWT_SECRET_KEY=tu_clave_secreta  # Requerido en producción
```

## Seguridad
- Los tokens expiran después de 24 horas
- Cada token contiene el ID, username y rol del usuario
- Las contraseñas nunca se incluyen en el token
- Se recomienda usar HTTPS en producción
