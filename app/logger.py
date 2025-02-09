from enum import Enum
import datetime
from contextlib import contextmanager
from app.db import get_connection

class LogType(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    CRITICAL = "CRITICAL"

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
        print("⚠️ Intentando escribir log...")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:  # Ahora está correctamente indentado dentro del método log
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

# Crear una instancia global del logger
logger = Logger(get_connection)