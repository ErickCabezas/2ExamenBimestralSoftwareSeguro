
import os
import psycopg2

# Variables de entorno (definidas en docker-compose o con valores por defecto)
DB_HOST = os.environ.get('POSTGRES_HOST', 'db')
DB_PORT = os.environ.get('POSTGRES_PORT', '5432')
DB_NAME = os.environ.get('POSTGRES_DB', 'corebank')
DB_USER = os.environ.get('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'postgres')


def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Comenzar una transacción
        cur.execute("BEGIN;")

        # Crear schema si no existe
        cur.execute("CREATE SCHEMA IF NOT EXISTS bank AUTHORIZATION postgres;")

        # Crear la tabla de usuarios
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT,
            email TEXT
        );
        """)

        # Crear la tabla de cuentas
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.accounts (
            id SERIAL PRIMARY KEY,
            balance NUMERIC NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES bank.users(id)
        );
        """)

        # Crear la tabla de tarjetas de crédito
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.credit_cards (
            id SERIAL PRIMARY KEY,
            limit_credit NUMERIC NOT NULL DEFAULT 1,
            balance NUMERIC NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES bank.users(id)
        );
        """)

        # Crear la tabla de logs
        cur.execute("""
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
        """)

        # Crear tabla de tokens
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES bank.users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

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

        # Crear tabla de transacciones de crédito
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bank.credit_transactions (
            id SERIAL PRIMARY KEY,
            merchant_id INTEGER REFERENCES bank.merchants(id),
            card_id INTEGER REFERENCES bank.encrypted_cards(id),
            amount NUMERIC NOT NULL,
            status TEXT NOT NULL,
            otp_code TEXT,
            otp_verified BOOLEAN DEFAULT false,
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

        # Insertar datos de ejemplo si no existen usuarios
        cur.execute("SELECT COUNT(*) FROM bank.users;")
        count = cur.fetchone()[0]
        if count == 0:
            # Insertar usuarios de ejemplo
            sample_users = [
                ('user1', 'pass1', 'cliente', 'Usuario Uno', 'user1@example.com'),
                ('user2', 'pass2', 'cliente', 'Usuario Dos', 'user2@example.com'),
                ('user3', 'pass3', 'cajero', 'Usuario Tres', 'user3@example.com')
            ]
            for username, password, role, full_name, email in sample_users:
                cur.execute("""
                    INSERT INTO bank.users (username, password, role, full_name, email)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """, (username, password, role, full_name, email))
                user_id = cur.fetchone()[0]
                # Crear una cuenta con saldo inicial 1000
                cur.execute("""
                    INSERT INTO bank.accounts (balance, user_id)
                    VALUES (%s, %s);
                """, (1000, user_id))
                # Crear una tarjeta de crédito con límite 5000 y deuda 0
                cur.execute("""
                    INSERT INTO bank.credit_cards (limit_credit, balance, user_id)
                    VALUES (%s, %s, %s);
                """, (5000, 0, user_id))

            # Insertar merchants de ejemplo
            cur.execute("""
                INSERT INTO bank.merchants (name) VALUES
                ('Tienda A'),
                ('Tienda B'),
                ('Supermercado C');
            """)

        # Confirmar todos los cambios
        cur.execute("COMMIT;")

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error initializing database: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()