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
