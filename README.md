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
## Variables de Entorno
```
JWT_SECRET_KEY=tu_clave_secreta  # Requerido en producción
```

## Seguridad
- Los tokens expiran después de 24 horas
- Cada token contiene el ID, username y rol del usuario
- Las contraseñas nunca se incluyen en el token
- Se recomienda usar HTTPS en producción
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

# LOGS


### 4. Logger y LogType
La clase Logger se encarga de gestionar los logs en la base de datos. El tipo de log se define mediante la enumeración LogType, que incluye los siguientes niveles de log:
- Info
- Warning
- Error
- Debug
- Critical

```python
class Logger:
    def __init__(self, get_connection_func):
        self.get_connection = get_connection_func
        print("Iniciando sistema de logs en base de datos...")

    @contextmanager
    def get_db_connection(self):
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception as e:
            print(f"Error de conexión: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def log(self, log_type, remote_ip, username, action, http_code, additional_info=None):
        print("Intentando escribir log...")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(""" 
                        INSERT INTO bank.logs 
                        (timestamp, log_type, remote_ip, username, action, http_code)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        timestamp,
                        log_type.value,
                        remote_ip,
                        username,
                        action,
                        http_code
                    ))
                conn.commit()
        except Exception as e:
            print(f"Error al guardar log en base de datos: {e}")
```

Se creó una tabla logs dentro del esquema bank para almacenar la información de los logs. La estructura de la tabla es la siguiente:


```python
CREATE SCHEMA IF NOT EXISTS bank AUTHORIZATION postgres;

CREATE TABLE IF NOT EXISTS bank.logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    log_type VARCHAR(10) NOT NULL,
    remote_ip VARCHAR(15) NOT NULL,
    username VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    http_code INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

```
Para registrar las acciones realizadas por los usuarios, se integró el logger con los endpoints de la API usando el decorador log_request. Este decorador captura la IP del cliente, el nombre de usuario, la acción realizada, y el código HTTP de la respuesta.

# ASEGURAR SERIVICIO DE COMPRA CON TARJETAS DE CREDITO
### Clase de Credit_Service y Credit_logger
La clase de credit_service se encarga de crear una transaccion segura y validar el OTP. Para la verificacion del otp se añade el campo de email en el JWT
### Variables de entorno
```
      ENCRYPTION_KEY: tu_clave_segura_aqui
      SMTP_SERVER: smtp.gmail.com
      SMTP_PORT: 587
      SMTP_EMAIL: tu_email
      SMTP_PASSWORD: email_password
```

```python
import re
from datetime import datetime
import secrets
import hashlib
from typing import Dict, Tuple
import os
from app.db import get_connection
from app.loggers.credit_logger import credit_logger, CreditLogType


class CreditCardService:
    def __init__(self):
        pass

    def validate_card_number(self, card_number: str) -> bool:
        """Implementa el algoritmo de Luhn para validar números de tarjeta."""
        if not re.match(r'^\d{16}$', card_number):
            return False

        digits = [int(d) for d in card_number]
        checksum = 0
        is_even = False

        for digit in reversed(digits):
            if is_even:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
            is_even = not is_even

        return (checksum % 10) == 0

    def get_card_type(self, card_number: str) -> str:
        """Determina el tipo de tarjeta basado en el número."""
        if card_number.startswith('4'):
            return 'VISA'
        elif card_number.startswith(('51', '52', '53', '54', '55')):
            return 'MASTERCARD'
        elif card_number.startswith(('34', '37')):
            return 'AMEX'
        return 'UNKNOWN'

    def generate_otp(self) -> str:
        """Genera un código OTP de 6 dígitos."""
        return ''.join(secrets.choice('0123456789') for _ in range(6))

    def send_otp_email(self, email: str, otp: str) -> bool:
        """Simula el envío del código OTP por email."""
        print(f"[SIMULATED] Sending OTP {otp} to {email}")
        return True

    def validate_stored_card(self, user_id: int, card_id: int, cvv: str) -> bool:
        """Valida que la tarjeta almacenada pertenezca al usuario y esté activa."""
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, is_active 
                FROM bank.encrypted_cards 
                WHERE id = %s AND user_id = %s
            """, (card_id, user_id))

            card = cur.fetchone()
            if not card:
                raise ValueError("Invalid card or unauthorized access")

            if not card[1]:  # is_active
                raise ValueError("Card is inactive")

            if not re.match(r'^\d{3}$', cvv):
                raise ValueError("Invalid CVV format")

            return True

        finally:
            cur.close()
            conn.close()

    def save_card(self, user_id: int, card_number: str, expiry_month: int, expiry_year: int) -> int:
        """Guarda una nueva tarjeta y retorna su ID."""
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO bank.encrypted_cards 
                (user_id, card_number_hash, card_type, last_four, expiry_date)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                hashlib.sha256(card_number.encode()).hexdigest(),
                self.get_card_type(card_number),
                card_number[-4:],
                f"{expiry_year}-{expiry_month:02d}-01"
            ))

            card_id = cur.fetchone()[0]
            conn.commit()
            return card_id

        finally:
            cur.close()
            conn.close()

    def process_payment(self, user_id: int, user_email: str, data: Dict) -> Tuple[int, str]:
        """Procesa el pago con tarjeta de crédito (nueva o almacenada)."""
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        try:
            # Verificar el establecimiento
            cur.execute("""
                SELECT id, name FROM bank.merchants 
                WHERE id = %s AND status = true
            """, (data['merchant_id'],))
            merchant = cur.fetchone()
            if not merchant:
                raise ValueError("Invalid or inactive merchant")

            # Validar CVV básico
            if not re.match(r'^\d{3}$', data['cvv']):
                raise ValueError("Invalid CVV format")

            # Procesar según el tipo de pago (nueva tarjeta o tarjeta guardada)
            if 'card_id' in data:
                # Pago con tarjeta guardada
                if not self.validate_stored_card(user_id, data['card_id'], data['cvv']):
                    raise ValueError("Invalid stored card or CVV")
                card_id = data['card_id']
            else:
                # Pago con nueva tarjeta
                if not self.validate_card_number(data['card_number']):
                    raise ValueError("Invalid card number")

                # Si se solicita guardar la tarjeta, la guardamos primero
                if data.get('save_card', False):
                    card_id = self.save_card(
                        user_id,
                        data['card_number'],
                        data['expiry_month'],
                        data['expiry_year']
                    )
                    # Log card saved event
                    credit_logger.log_transaction(
                        CreditLogType.CARD_SAVED,
                        0, user_id, merchant[0], 0,
                        'CARD_SAVED',
                        {'card_type': self.get_card_type(data['card_number'])}
                    )
                else:
                    # Guardar la tarjeta temporalmente para la transacción
                    cur.execute("""
                        INSERT INTO bank.encrypted_cards 
                        (user_id, card_number_hash, card_type, last_four, expiry_date, is_active)
                        VALUES (%s, %s, %s, %s, %s, false)
                        RETURNING id
                    """, (
                        user_id,
                        hashlib.sha256(data['card_number'].encode()).hexdigest(),
                        self.get_card_type(data['card_number']),
                        data['card_number'][-4:],
                        f"{data['expiry_year']}-{data['expiry_month']:02d}-01"
                    ))
                    card_id = cur.fetchone()[0]

            # Generar y enviar OTP
            otp = self.generate_otp()
            if not self.send_otp_email(user_email, otp):
                raise ValueError("Failed to send OTP")

            # Crear la transacción
            cur.execute("""
                INSERT INTO bank.credit_transactions 
                (merchant_id, card_id, amount, status, otp_code)
                VALUES (%s, %s, %s, 'PENDING', %s)
                RETURNING id
            """, (data['merchant_id'], card_id, data['amount'], otp))

            transaction_id = cur.fetchone()[0]

            # Log payment initiated
            credit_logger.log_transaction(
                CreditLogType.PAYMENT_INITIATED,
                transaction_id, user_id, merchant[0],
                data['amount'], 'PENDING'
            )

            conn.commit()
            return transaction_id, "Transaction initiated"

        except Exception as e:
            conn.rollback()
            credit_logger.log_transaction(
                CreditLogType.PAYMENT_FAILED,
                0, user_id, data.get('merchant_id', 0),
                data.get('amount', 0), 'FAILED',
                {'error': str(e)}
            )
            raise
        finally:
            cur.close()
            conn.close()

    def verify_otp(self, user_id: int, transaction_id: int, otp_code: str) -> Tuple[float, str]:
        """Verifica el código OTP y completa la transacción."""
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        try:
            # Get transaction data including card ownership verification
            cur.execute("""
                SELECT t.id, t.amount, t.otp_code, m.name as merchant_name, 
                       m.id as merchant_id, ec.user_id
                FROM bank.credit_transactions t
                JOIN bank.merchants m ON t.merchant_id = m.id
                JOIN bank.encrypted_cards ec ON t.card_id = ec.id
                WHERE t.id = %s AND t.status = 'PENDING'
            """, (transaction_id,))

            transaction = cur.fetchone()
            if not transaction:
                raise ValueError("Invalid or expired transaction")

            # Verify card ownership
            if transaction[5] != user_id:
                raise ValueError("Unauthorized transaction")

            if transaction[2] != otp_code:
                raise ValueError("Invalid OTP code")

            # Completar la transacción
            cur.execute("""
                UPDATE bank.credit_transactions 
                SET status = 'COMPLETED', otp_verified = true
                WHERE id = %s
            """, (transaction[0],))

            # Eliminar tarjetas temporales si existen
            cur.execute("""
                DELETE FROM bank.encrypted_cards
                WHERE id IN (
                    SELECT card_id 
                    FROM bank.credit_transactions 
                    WHERE id = %s
                ) AND is_active = false
            """, (transaction[0],))

            # Log successful verification
            credit_logger.log_transaction(
                CreditLogType.PAYMENT_COMPLETED,
                transaction[0], user_id, transaction[4],
                transaction[1], 'COMPLETED'
            )

            conn.commit()
            return float(transaction[1]), transaction[3]

        except Exception as e:
            conn.rollback()
            credit_logger.log_transaction(
                CreditLogType.PAYMENT_FAILED,
                transaction_id, user_id, 0, 0, 'FAILED',
                {'error': str(e)}
            )
            raise
        finally:
            cur.close()
            conn.close()


# Crear una instancia global del servicio
credit_service = CreditCardService()
```

Luego la clase de credit_logger se encarga de guardar la informacion e la transaccion en un repositorio distinto al de logs:
```python
# app/loggers/credit_logger.py

from datetime import datetime
from enum import Enum
import json
from decimal import Decimal
from app.db import get_connection
from flask import request


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class CreditLogType(Enum):
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    OTP_SENT = "OTP_SENT"
    OTP_VERIFIED = "OTP_VERIFIED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CARD_SAVED = "CARD_SAVED"
    CARD_REMOVED = "CARD_REMOVED"


class CreditTransactionLogger:
    def log_transaction(self,
                        log_type: CreditLogType,
                        transaction_id: int,
                        user_id: int,
                        merchant_id: int,
                        amount: float,
                        status: str,
                        extra_data: dict = None):
        """
        Registra una transacción de tarjeta de crédito en la base de datos.
        Los datos sensibles nunca se registran.
        """
        try:
            # Preparar los datos para el log
            extra_data_safe = None
            if extra_data:
                # Filtrar datos sensibles
                safe_data = {
                    k: float(v) if isinstance(v, Decimal) else v
                    for k, v in extra_data.items()
                    if k not in ['card_number', 'cvv', 'encrypted_data']
                }
                extra_data_safe = json.dumps(safe_data, cls=DecimalEncoder)

            # Obtener la IP del cliente
            ip_address = request.remote_addr if request else None

            # Conectar a la base de datos
            conn = get_connection()
            cur = conn.cursor()

            try:
                # Insertar el log en la base de datos
                cur.execute("""
                    INSERT INTO bank.credit_transaction_logs 
                    (log_type, transaction_id, user_id, merchant_id, amount, status, extra_data, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                """, (
                    log_type.value,
                    transaction_id,
                    user_id,
                    merchant_id,
                    amount,
                    status,
                    extra_data_safe,
                    ip_address
                ))

                log_id = cur.fetchone()[0]
                conn.commit()

                print(f"Transaction log saved successfully. ID: {log_id}")

            except Exception as db_error:
                conn.rollback()
                print(f"Database error while saving log: {str(db_error)}")
                raise
            finally:
                cur.close()
                conn.close()

        except Exception as e:
            print(f"Error logging transaction: {str(e)}")

    def get_transaction_logs(self,
                             user_id: int = None,
                             transaction_id: int = None,
                             start_date: datetime = None,
                             end_date: datetime = None,
                             limit: int = 100) -> list:
        """
        Recupera logs de transacciones con varios filtros opcionales.
        """
        try:
            conn = get_connection()
            cur = conn.cursor()

            query = """
                SELECT 
                    id, 
                    log_type, 
                    transaction_id,
                    user_id,
                    merchant_id,
                    amount,
                    status,
                    extra_data,
                    ip_address,
                    created_at
                FROM bank.credit_transaction_logs 
                WHERE 1=1
            """
            params = []

            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)

            if transaction_id is not None:
                query += " AND transaction_id = %s"
                params.append(transaction_id)

            if start_date is not None:
                query += " AND created_at >= %s"
                params.append(start_date)

            if end_date is not None:
                query += " AND created_at <= %s"
                params.append(end_date)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            logs = cur.fetchall()

            # Convertir a lista de diccionarios
            result = []
            for log in logs:
                result.append({
                    'id': log[0],
                    'log_type': log[1],
                    'transaction_id': log[2],
                    'user_id': log[3],
                    'merchant_id': log[4],
                    'amount': float(log[5]) if log[5] else None,
                    'status': log[6],
                    'extra_data': log[7],
                    'ip_address': log[8],
                    'created_at': log[9].isoformat()
                })

            return result

        except Exception as e:
            print(f"Error retrieving logs: {str(e)}")
            return []
        finally:
            cur.close()
            conn.close()


# Crear una instancia global del logger
credit_logger = CreditTransactionLogger()
```
## Cambios realizados
### 1. requirements.txt
primero se añade una nueva dependencia a requirements.txt
-cryptography
### 2.Creacion de nuevas tablas 
```python
  # Crear tabla de merchants
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.merchants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            status BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Crear tabla de tarjetas encriptadas
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.encrypted_cards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES bank.users(id),
            card_number_hash TEXT NOT NULL,
            card_type TEXT NOT NULL,
            last_four CHAR(4) NOT NULL,
            expiry_date DATE NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
           CREATE TABLE IF NOT EXISTS bank.credit_transaction_logs (
               id SERIAL PRIMARY KEY,
               log_type VARCHAR(50) NOT NULL,
               transaction_id INTEGER,
               user_id INTEGER,
               merchant_id INTEGER,
               amount DECIMAL,
               status VARCHAR(50),
               extra_data JSONB,
               ip_address VARCHAR(45),
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           );

           -- Crear índices para mejorar las búsquedas
           CREATE INDEX IF NOT EXISTS idx_credit_logs_transaction_id 
               ON bank.credit_transaction_logs(transaction_id);
           CREATE INDEX IF NOT EXISTS idx_credit_logs_user_id 
               ON bank.credit_transaction_logs(user_id);
           CREATE INDEX IF NOT EXISTS idx_credit_logs_created_at 
               ON bank.credit_transaction_logs(created_at);
           """)
```
### 3.Implementacion de nuevos modelos para las tarjetas y verificacion OTP
```python
credit_payment_model = bank_ns.model('CreditPayment', {
    'merchant_id': fields.Integer(required=True, description='ID del establecimiento', example=1),
    'card_number': fields.String(required=False, description='Número de tarjeta', example='4532015112830366'),
    'cvv': fields.String(required=True, description='Código CVV', example='123'),
    'expiry_month': fields.Integer(required=False, description='Mes de expiración', example=12),
    'expiry_year': fields.Integer(required=False, description='Año de expiración', example=2025),
    'amount': fields.Float(required=True, description='Monto de la compra', example=100.50)
})

verify_otp_model = bank_ns.model('VerifyOTP', {
    'transaction_id': fields.Integer(required=True, description='ID de la transacción', example=1),
    'otp_code': fields.String(required=True, description='Código OTP', example='123456')
})
```
## Para realizar pruebas:
### 1.Ingresar a la app
```bash
curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"user1","password":"pass1"}'
```
### 2.1 Pago con datos de tarjeta
```bash
curl -X POST localhost:8000/bank/credit-payment
     -H "Content-Type: application/json" \
     -d '{
    "merchant_id": 1,
    "card_number": "4532015112830366",
    "cvv": "123",
    "expiry_month": 12,
    "expiry_year": 2025,
    "amount": 1002,
    "save_card": true
}'
```
### 2.2 Pago con tarjeta guardada

```bash
curl -X POST localhost:8000/bank/credit-payment
     -H "Content-Type: application/json" \
     -d '{
    "merchant_id": 2,
    "card_id": 1,
    "cvv": "123",
    "amount": 100.50
}'
```
### 3. Verificación OTP
la verificacion OTP esta simulada. el codigo se presenta en la consola. 
```bash
curl -X POST localhost:8000/bank/verify-otp
     -H "Content-Type: application/json" \
     -d '{
    "transaction_id": 2,
    "otp_code": "653785"
}'
```
