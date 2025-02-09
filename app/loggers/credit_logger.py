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