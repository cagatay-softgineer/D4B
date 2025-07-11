# db/user_queries.py

from database.postgres import get_connection
import datetime
import bcrypt

def get_user_password_and_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email,password_hash FROM users WHERE email = %s", (email,))
            data = cur.fetchone()
            return data

def get_user_password_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            data = cur.fetchone()
            print(data)
            return data

def get_user_id_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            data = cur.fetchone()
            return data

def get_user_by_id(id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (id,))
            return cur.fetchone()

def get_user_role_by_id(id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE id = %s", (id,))
            return cur.fetchone()

def get_user_role_by_email(email: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE email = %s", (email,))
            return cur.fetchone()

def get_user_status_by_id(id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM users WHERE id = %s", (id,))
            return cur.fetchone()

def get_user_status_by_email(email: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM users WHERE email = %s", (email,))
            return cur.fetchone()

def get_user_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()

def insert_user(email: str, password: str) -> int:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.datetime.utcnow()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (email, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (email, hashed, now, now))
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id

def update_user_last_login(id: int):
    now = datetime.datetime.utcnow()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (now, id))
            conn.commit()

def store_user_refresh_token(id: int, refresh_token: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET refresh_token = %s WHERE id = %s", (refresh_token, id))
            conn.commit()

def get_one_user_by_email(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email, name, avatar_url, status, role FROM users WHERE email = %s", (email,))
            data = cur.fetchone()
            user = {
                    "email": data[0],
                    "name": data[1],
                    "avatar_url": data[2],
                    "status": data[3],
                    "role": data[4],
                }
            return user

def get_current_user_by_email(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email, name, avatar_url, status, role FROM users WHERE email = %s", (email,))
            data = cur.fetchone()
            user = {
                    "email": data[0],
                    "name": data[1],
                    "avatar_url": data[2],
                    "status": data[3],
                    "role": data[4],
                }
            return user

def get_all_users(page, page_size):
    offset = (page - 1) * page_size
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, name, avatar_url, status, role FROM users ORDER BY id LIMIT %s OFFSET %s",
                (page_size, offset)
            )
            users = [
                {
                    "email": row[0],
                    "name": row[1],
                    "avatar_url": row[2],
                    "status": row[3],
                    "role": row[4],
                }
                for row in cur.fetchall()
            ]
            # Get total count for pagination meta
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()[0]
    return users, total