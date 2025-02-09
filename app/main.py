import secrets
from app.auth import generate_jwt_token
from app.auth import jwt_required
from flask import Flask, request, g
from flask_restx import Api, Resource, fields # type: ignore
from functools import wraps
from app.db import get_connection, init_db
import logging
from app.services.credit_service import credit_service

# COLOCA EL CÓDIGO DE INTEGRACIÓN AQUÍ ↓
from app.logger import logger, LogType

def log_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        remote_ip = request.remote_addr
        username = g.user.get('username', 'anonymous') if hasattr(g, 'user') else 'anonymous'
        
        action = f"{request.method} {request.path}"
        logger.log(LogType.INFO, remote_ip, username, action, "200")

        try:
            response = f(*args, **kwargs)
            return response
        except Exception as e:
            logger.log(LogType.ERROR, remote_ip, username, action, "500", {"error": str(e)})
            raise
    return decorated

# Define a simple in-memory token store
tokens = {}

# Configure Swagger security scheme for Bearer tokens
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Enter your token in the format **Bearer <token>**"
    }
}

app = Flask(__name__)
api = Api(
    app,
    version='1.0',
    title='Core Bancario API',
    description='API para operaciones bancarias, incluyendo autenticación y operaciones de cuenta.',
    doc='/swagger',  # Swagger UI endpoint
    authorizations=authorizations,
    security='Bearer'
)

# Create namespaces for authentication and bank operations
auth_ns = api.namespace('auth', description='Operaciones de autenticación')
bank_ns = api.namespace('bank', description='Operaciones bancarias')

# Define the expected payload models for Swagger
login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Nombre de usuario', example='user1'),
    'password': fields.String(required=True, description='Contraseña', example='pass1')
})

deposit_model = bank_ns.model('Deposit', {
    'account_number': fields.Integer(required=True, description='Número de cuenta', example=123),
    'amount': fields.Float(required=True, description='Monto a depositar', example=100)
})

withdraw_model = bank_ns.model('Withdraw', {
    'amount': fields.Float(required=True, description='Monto a retirar', example=100)
})

transfer_model = bank_ns.model('Transfer', {
    'target_username': fields.String(required=True, description='Usuario destino', example='user2'),
    'amount': fields.Float(required=True, description='Monto a transferir', example=100)
})

# Reemplaza el modelo credit_payment_model existente con estos nuevos modelos
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

pay_credit_balance_model = bank_ns.model('PayCreditBalance', {
    'amount': fields.Float(required=True, description='Monto a abonar a la deuda de la tarjeta', example=50)
})

# ---------------- Authentication Endpoints ----------------

@auth_ns.route('/login')
class Login(Resource):
    @log_request
    @auth_ns.expect(login_model, validate=True)
    @auth_ns.doc('login')
    def post(self):
        print("🔥 ENTRANDO A LOGIN")
        """Inicia sesión y devuelve un token de autenticación."""
        data = api.payload
        username = data.get("username")
        password = data.get("password")
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, role, full_name, email FROM bank.users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user and user[2] == password:

            # Generate a new token for the user
            user_data={
                'id': user[0],
                'username': user[1],
                'role': user[3],
                'full_name': user[4],
                'email': user[5],
            }

            token = generate_jwt_token(user_data)
            cur.close()
            conn.close()
            return {"message": "Login successful", "token": token, "user":user_data}, 200
        else:
            cur.close()
            conn.close()
            api.abort(401, "Invalid credentials")

@auth_ns.route('/logout')
class Logout(Resource):
    @log_request
    @auth_ns.doc('logout')
    def post(self):
        """Invalida el token de autenticación."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            api.abort(401, "Authorization header missing or invalid")
        token = auth_header.split(" ")[1]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM bank.tokens WHERE token = %s", (token,))
        if cur.rowcount == 0:
            conn.commit()
            cur.close()
            conn.close()
            api.abort(401, "Invalid token")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Logout successful"}, 200

# ---------------- Token-Required Decorator ----------------

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            api.abort(401, "Authorization header missing or invalid")
        token = auth_header.split(" ")[1]
        logging.debug("Token: "+str(token))
        conn = get_connection()
        cur = conn.cursor()
        # Query the token in the database and join with users table to retrieve user info
        cur.execute("""
            SELECT u.id, u.username, u.role, u.full_name, u.email 
            FROM bank.tokens t
            JOIN bank.users u ON t.user_id = u.id
            WHERE t.token = %s
        """, (token,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if not user:
            api.abort(401, "Invalid or expired token")
        g.user = {
            "id": user[0],
            "username": user[1],
            "role": user[2],
            "full_name": user[3],
            "email": user[4]
        }
        return f(*args, **kwargs)
    return decorated

# ---------------- Banking Operation Endpoints ----------------

@bank_ns.route('/deposit')
class Deposit(Resource):
    logging.debug("Entering....")
    @log_request
    @bank_ns.expect(deposit_model, validate=True)
    @bank_ns.doc('deposit')
    @jwt_required
    def post(self):
        """
        Realiza un depósito en la cuenta especificada.
        Se requiere el número de cuenta y el monto a depositar.
        """
        data = api.payload
        account_number = data.get("account_number")
        amount = data.get("amount", 0)
        
        if amount <= 0:
            api.abort(400, "Amount must be greater than zero")
        
        conn = get_connection()
        cur = conn.cursor()
        # Update the specified account using its account number (primary key)
        cur.execute(
            "UPDATE bank.accounts SET balance = balance + %s WHERE id = %s RETURNING balance",
            (amount, account_number)
        )
        result = cur.fetchone()
        if not result:
            conn.rollback()
            cur.close()
            conn.close()
            api.abort(404, "Account not found")
        new_balance = float(result[0])
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Deposit successful", "new_balance": new_balance}, 200

@bank_ns.route('/withdraw')
class Withdraw(Resource):
    @log_request
    @bank_ns.expect(withdraw_model, validate=True)
    @bank_ns.doc('withdraw')
    @jwt_required
    def post(self):
        """Realiza un retiro de la cuenta del usuario autenticado."""
        data = api.payload
        amount = data.get("amount", 0)
        if amount <= 0:
            api.abort(400, "Amount must be greater than zero")
        user_id = g.user['id']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT balance FROM bank.accounts WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            api.abort(404, "Account not found")
        current_balance = float(row[0])
        if current_balance < amount:
            cur.close()
            conn.close()
            api.abort(400, "Insufficient funds")
        cur.execute("UPDATE bank.accounts SET balance = balance - %s WHERE user_id = %s RETURNING balance", (amount, user_id))
        new_balance = float(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Withdrawal successful", "new_balance": new_balance}, 200

@bank_ns.route('/transfer')
class Transfer(Resource):
    @log_request
    @bank_ns.expect(transfer_model, validate=True)
    @bank_ns.doc('transfer')
    @jwt_required
    def post(self):
        """Transfiere fondos desde la cuenta del usuario autenticado a otra cuenta."""
        data = api.payload
        target_username = data.get("target_username")
        amount = data.get("amount", 0)
        if not target_username or amount <= 0:
            api.abort(400, "Invalid data")
        if target_username == g.user['username']:
            api.abort(400, "Cannot transfer to the same account")
        conn = get_connection()
        cur = conn.cursor()
        # Check sender's balance
        cur.execute("SELECT balance FROM bank.accounts WHERE user_id = %s", (g.user['id'],))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            api.abort(404, "Sender account not found")
        sender_balance = float(row[0])
        if sender_balance < amount:
            cur.close()
            conn.close()
            api.abort(400, "Insufficient funds")
        # Find target user
        cur.execute("SELECT id FROM bank.users WHERE username = %s", (target_username,))
        target_user = cur.fetchone()
        if not target_user:
            cur.close()
            conn.close()
            api.abort(404, "Target user not found")
        target_user_id = target_user[0]
        try:
            cur.execute("UPDATE bank.accounts SET balance = balance - %s WHERE user_id = %s", (amount, g.user['id']))
            cur.execute("UPDATE bank.accounts SET balance = balance + %s WHERE user_id = %s", (amount, target_user_id))
            cur.execute("SELECT balance FROM bank.accounts WHERE user_id = %s", (g.user['id'],))
            new_balance = float(cur.fetchone()[0])
            conn.commit()
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            api.abort(500, f"Error during transfer: {str(e)}")
        cur.close()
        conn.close()
        return {"message": "Transfer successful", "new_balance": new_balance}, 200


@bank_ns.route('/credit-payment')
class CreditPayment(Resource):
    @log_request
    @bank_ns.expect(credit_payment_model, validate=True)
    @bank_ns.doc('credit_payment')
    @jwt_required
    def post(self):
        """
        Realiza un pago seguro con tarjeta de crédito:
        - Valida el establecimiento
        - Verifica y procesa la tarjeta
        - Genera y envía código OTP
        - Registra la transacción
        """
        try:
            if not g.user.get('email'):
                return {"message": "User email is required for OTP verification"}, 400

            transaction_id, message = credit_service.process_payment(
                g.user['id'],
                g.user['email'],
                api.payload
            )

            return {
                       "message": message,
                       "transaction_id": transaction_id
                   }, 200

        except ValueError as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred processing the payment"}, 500


@bank_ns.route('/verify-otp')
class VerifyOTP(Resource):
    @log_request
    @bank_ns.expect(verify_otp_model, validate=True)
    @bank_ns.doc('verify_otp')
    @jwt_required
    def post(self):
        """
        Verifica el código OTP y completa la transacción:
        - Valida el código OTP
        - Actualiza el estado de la transacción
        - Registra la confirmación
        """
        try:
            amount, merchant = credit_service.verify_otp(
                g.user['id'],
                api.payload['transaction_id'],
                api.payload['otp_code']
            )

            return {
                       "message": "Transaction completed successfully",
                       "amount": amount,
                       "merchant": merchant
                   }, 200

        except ValueError as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred verifying the OTP"}, 500
@bank_ns.route('/pay-credit-balance')
class PayCreditBalance(Resource):
    @log_request
    @bank_ns.expect(pay_credit_balance_model, validate=True)
    @bank_ns.doc('pay_credit_balance')
    @jwt_required
    def post(self):
        """
        Realiza un abono a la deuda de la tarjeta:
        - Descuenta el monto (o el máximo posible) de la cuenta.
        - Reduce la deuda de la tarjeta de crédito.
        """
        data = api.payload
        amount = data.get("amount", 0)
        if amount <= 0:
            api.abort(400, "Amount must be greater than zero")
        user_id = g.user['id']
        conn = get_connection()
        cur = conn.cursor()
        # Check account funds
        cur.execute("SELECT balance FROM bank.accounts WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            api.abort(404, "Account not found")
        account_balance = float(row[0])
        if account_balance < amount:
            cur.close()
            conn.close()
            api.abort(400, "Insufficient funds in account")
        # Get current credit card debt
        cur.execute("SELECT balance FROM bank.credit_cards WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            api.abort(404, "Credit card not found")
        credit_debt = float(row[0])
        payment = min(amount, credit_debt)
        try:
            cur.execute("UPDATE bank.accounts SET balance = balance - %s WHERE user_id = %s", (payment, user_id))
            cur.execute("UPDATE bank.credit_cards SET balance = balance - %s WHERE user_id = %s", (payment, user_id))
            cur.execute("SELECT balance FROM bank.accounts WHERE user_id = %s", (user_id,))
            new_account_balance = float(cur.fetchone()[0])
            cur.execute("SELECT balance FROM bank.credit_cards WHERE user_id = %s", (user_id,))
            new_credit_debt = float(cur.fetchone()[0])
            conn.commit()
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            api.abort(500, f"Error processing credit balance payment: {str(e)}")
        cur.close()
        conn.close()
        return {
            "message": "Credit card debt payment successful",
            "account_balance": new_account_balance,
            "credit_card_debt": new_credit_debt
        }, 200

@app.before_first_request
def initialize_db():
    init_db()

if __name__ == "__main__":
    print("Starting server...")
    app.run(host="0.0.0.0", port=8000, debug=True)

