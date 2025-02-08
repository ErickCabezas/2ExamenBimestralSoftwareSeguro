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
```bash
Deberías ver (venv) al inicio de tu línea de comandos
```
(venv) PS C:\Users\USUARIO\source\repos\Examen2BSoftwareSeguro\core-bankec-python>

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
