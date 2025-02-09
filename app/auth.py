import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import g, request
from flask_restx import abort
import os

# Configuración JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'tu_clave_secreta_desarrollo')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_jwt_token(user_data):
    """Genera un token JWT con la información del usuario."""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'email': user_data.get('email'),  # Añadimos el email
        'full_name': user_data.get('full_name'),  # También el nombre completo por si lo necesitamos
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token):
    """Decodifica y valida un token JWT."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        abort(401, "Token has expired")
    except jwt.InvalidTokenError:
        abort(401, "Invalid token")


def jwt_required(f):
    """Decorator para proteger rutas con JWT."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            abort(401, "Authorization header missing or invalid")

        token = auth_header.split(' ')[1]

        try:
            payload = decode_jwt_token(token)
            g.user = {
                'id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role'],
                'email': payload.get('email'),  # Añadimos el email
                'full_name': payload.get('full_name')  # Y el nombre completo
            }
            return f(*args, **kwargs)
        except Exception as e:
            abort(401, str(e))

    return decorated