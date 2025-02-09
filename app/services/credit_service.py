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