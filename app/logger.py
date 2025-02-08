import datetime
import os

class Logger:
    def __init__(self, log_directory="logs"):
        self.log_directory = log_directory
        print(f"📁 Ruta de logs: {os.path.abspath(log_directory)}")
        
        # Crear el directorio de logs si no existe
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
    
    def _get_log_filename(self):
        """Genera el nombre del archivo de log basado en la fecha actual."""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_directory, f"bank_api_{current_date}.log")
    
    def log(self, log_type, remote_ip, username, action, http_code, additional_info=None):
        print("⚠️ Intentando escribir log...")  # Agrega esta línea
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


        """
        Registra un evento en el archivo de logs.
        
        Args:
            log_type: Tipo de log (INFO, ERROR, WARNING, etc)
            remote_ip: Dirección IP del cliente
            username: Nombre del usuario que realizó la acción
            action: Descripción de la acción realizada
            http_code: Código de respuesta HTTP
            additional_info: Información adicional opcional en formato diccionario
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = (
            f"[{timestamp}] | "
            f"{log_type:7} | "
            f"IP: {remote_ip:15} | "
            f"User: {username:20} | "
            f"Action: {action:30} | "
            f"HTTP: {http_code}"
        )
        
        if additional_info:
            log_entry += f" | Additional Info: {additional_info}"
        
        log_entry += "\n"
        
        with open(self._get_log_filename(), 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)

# Crear una instancia global del logger
logger = Logger()

# Constantes para tipos de log
class LogType:
    INFO = "INFO"
    ERROR = "ERROR"
    WARNING = "WARNING"
    AUTH = "AUTH"
    TRANSACTION = "TRANS"