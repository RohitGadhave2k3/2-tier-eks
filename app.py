# import time
# from datetime import datetime
# import os
# from flask import Flask, request, render_template, flash, url_for, redirect
# import mysql.connector
# from mysql.connector import pooling, IntegrityError
# from dotenv import load_dotenv

# # Load .env
# load_dotenv()

# DB_CONFIG = {
#     "host": os.getenv("DB_HOST", "hostel-db"),
#     "user": os.getenv("DB_USER", "root"),  # default to root for k8s secret
#     "password": os.getenv("DB_PASSWORD", "admin@123"),
#     "database": os.getenv("DB_NAME", "hostel_db"),
#     "port": int(os.getenv("DB_PORT", 3306)),
#     "ssl_disabled": True,
# }

# POOL_NAME = "hostel_pool"
# POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

# try:
#     cnxpool = pooling.MySQLConnectionPool(pool_name=POOL_NAME, pool_size=POOL_SIZE, **DB_CONFIG)
# except mysql.connector.Error as e:
#     raise SystemExit(f"Failed to initialize MySQL pool: {e}")

# app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")

# def get_conn():
#     conn = cnxpool.get_connection()
#     # Ensure autocommit for DDL/short transactions
#     try:
#         conn.autocommit = True
#     except Exception:
#         pass
#     return conn

# @app.context_processor
# def inject_now():
#     return {"now": datetime.utcnow}

# def init_db():
#     """Create required tables if they don't exist."""
#     conn = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("""
#         CREATE TABLE IF NOT EXISTS students (
#           id INT AUTO_INCREMENT PRIMARY KEY,
#           name VARCHAR(100) NOT NULL,
#           room VARCHAR(50) NOT NULL,
#           phone VARCHAR(50),
#           email VARCHAR(255),
#           fees_paid TINYINT(1) DEFAULT 0,
#           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#         """)
#         print("✅ Students table ensured")
#     finally:
#         cursor.close()
#         conn.close()

# def init_db_with_retry(retries=10, delay=3):
#     for i in range(1, retries + 1):
#         try:
#             init_db()
#             return
#         except Exception as e:
#             print(f"DB init failed ({i}/{retries}): {e}")
#             time.sleep(delay)
#     raise SystemExit("Could not initialize DB after retries")

# # ----------------- Routes -----------------
# @app.route("/health")
# def health():
#     return {"status": "ok"}, 200

# @app.route("/")
# def index():
#     keyword = request.args.get("keyword", "")
#     conn = get_conn()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         if keyword:
#             like = f"%{keyword}%"
#             sql = """
#             SELECT * FROM students
#             WHERE CAST(id AS CHAR) LIKE %s OR name LIKE %s OR room LIKE %s OR phone LIKE %s
#             ORDER BY created_at DESC
#             """
#             cursor.execute(sql, (like, like, like, like))
#         else:
#             cursor.execute("SELECT * FROM students ORDER BY created_at DESC")
#         students = cursor.fetchall()
#     finally:
#         cursor.close()
#         conn.close()
#     return render_template("index.html", students=students, keyword=keyword)

# @app.route("/add", methods=["GET", "POST"])
# def add_student():
#     if request.method == "POST":
#         try:
#             name = request.form["name"].strip()
#             room = request.form["room"].strip()
#             phone = request.form.get("phone", "").strip() or None
#             email = request.form.get("email", "").strip() or None
#         except (KeyError, ValueError):
#             flash("Invalid form data", "danger")
#             return redirect(url_for("add_student"))

#         conn = get_conn()
#         cursor = conn.cursor()
#         try:
#             query = "INSERT INTO students (name, room, phone, email) VALUES (%s, %s, %s, %s)"
#             cursor.execute(query, (name, room, phone, email))
#             flash("Student added successfully", "success")
#             return redirect(url_for("index"))
#         except IntegrityError as e:
#             flash(f"Error: {str(e)}", "danger")
#             return redirect(url_for("add_student"))
#         finally:
#             cursor.close()
#             conn.close()
#     return render_template("add_edit_student.html", action="Add", student=None)

# @app.route("/edit/<int:sid>", methods=["GET", "POST"])
# def edit_student(sid):
#     conn = get_conn()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         if request.method == "POST":
#             name = request.form["name"].strip()
#             room = request.form["room"].strip()
#             phone = request.form.get("phone", "").strip() or None
#             email = request.form.get("email", "").strip() or None

#             cursor2 = conn.cursor()
#             try:
#                 cursor2.execute("UPDATE students SET name=%s, room=%s, phone=%s, email=%s WHERE id=%s",
#                                 (name, room, phone, email, sid))
#                 flash("Student updated", "success")
#                 return redirect(url_for("index"))
#             except Exception as e:
#                 flash(f"Update failed: {e}", "danger")
#             finally:
#                 cursor2.close()

#         cursor.execute("SELECT * FROM students WHERE id=%s", (sid,))
#         student = cursor.fetchone()
#         if not student:
#             flash("Student not found", "warning")
#             return redirect(url_for("index"))
#     finally:
#         cursor.close()
#         conn.close()
#     return render_template("add_edit_student.html", action="Edit", student=student)

# @app.route("/pay/<int:sid>")
# def pay_fees(sid):
#     conn = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("UPDATE students SET fees_paid = 1 WHERE id = %s", (sid,))
#         flash("Fees marked as paid", "success")
#     except Exception as e:
#         flash(f"Could not mark fees: {e}", "danger")
#     finally:
#         cursor.close()
#         conn.close()
#     return redirect(url_for("index"))

# @app.route("/delete/<int:sid>", methods=["GET", "POST"])
# def delete_student(sid):
#     if request.method == "POST":
#         conn = get_conn()
#         cursor = conn.cursor()
#         try:
#             cursor.execute("DELETE FROM students WHERE id=%s", (sid,))
#             flash("Student deleted", "success")
#         except Exception as e:
#             flash(f"Delete failed: {e}", "danger")
#         finally:
#             cursor.close()
#             conn.close()
#         return redirect(url_for("index"))

#     conn = get_conn()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT * FROM students WHERE id=%s", (sid,))
#         student = cursor.fetchone()
#         if not student:
#             flash("Student not found", "warning")
#             return redirect(url_for("index"))
#     finally:
#         cursor.close()
#         conn.close()
#     return render_template("confirm_delete.html", student=student)

# # Call only the retry wrapper
# init_db_with_retry()

# if __name__ == "__main__":
#     debug = os.getenv("FLASK_DEBUG", "0") == "1"
#     app.run(host="0.0.0.0", port=5000, debug=debug)


import time
from datetime import datetime
import os
from flask import Flask, request, render_template, flash, url_for, redirect
import mysql.connector
from mysql.connector import pooling, IntegrityError
from dotenv import load_dotenv

# Load .env (useful for local dev)
load_dotenv()

# ----------------------------
# Database Configuration
# ----------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "hostel-db"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "admin@123"),
    "database": os.getenv("DB_NAME", "hostel_db"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "ssl_disabled": True,
}

POOL_NAME = "hostel_pool"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

# Initialize database pool
try:
    cnxpool = pooling.MySQLConnectionPool(
        pool_name=POOL_NAME, pool_size=POOL_SIZE, **DB_CONFIG
    )
    print("✔ MySQL Connection Pool Initialized")
except mysql.connector.Error as e:
    raise SystemExit(f"❌ Failed to initialize MySQL pool: {e}")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

# Get connection from pool
def get_conn():
    conn = cnxpool.get_connection()
    conn.autocommit = True
    return conn

@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

# ----------------------------
# Database Initialization
# ----------------------------
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          room VARCHAR(50) NOT NULL,
          phone VARCHAR(50),
          email VARCHAR(255),
          fees_paid TINYINT(1) DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("✔ Students table ready")
    finally:
        cursor.close()
        conn.close()

def init_db_with_retry(retries=15, delay=4):
    """Ensure DB is ready before app starts."""
    for i in range(1, retries + 1):
        try:
            init_db()
            print("✔ DB Initialization Successful")
            return
        except Exception as e:
            print(f"⏳ DB init failed ({i}/{retries}): {e}")
            time.sleep(delay)
    raise SystemExit("❌ Could not initialize DB after retries")

# ----------------------------
# Routes
# ----------------------------
@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/")
def index():
    keyword = request.args.get("keyword", "")

    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        if keyword:
            like = f"%{keyword}%"
            sql = """
            SELECT * FROM students
            WHERE CAST(id AS CHAR) LIKE %s OR name LIKE %s OR room LIKE %s OR phone LIKE %s
            ORDER BY created_at DESC
            """
            cursor.execute(sql, (like, like, like, like))
        else:
            cursor.execute("SELECT * FROM students ORDER BY created_at DESC")

        students = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("index.html", students=students, keyword=keyword)

@app.route("/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form["name"].strip()
        room = request.form["room"].strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None

        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO students (name, room, phone, email) VALUES (%s, %s, %s, %s)",
                (name, room, phone, email),
            )
            flash("Student added successfully!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Error adding student: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("add_edit_student.html", action="Add", student=None)

@app.route("/edit/<int:sid>", methods=["GET", "POST"])
def edit_student(sid):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == "POST":
            name = request.form["name"].strip()
            room = request.form["room"].strip()
            phone = request.form.get("phone", "").strip() or None
            email = request.form.get("email", "").strip() or None

            cursor2 = conn.cursor()
            try:
                cursor2.execute(
                    "UPDATE students SET name=%s, room=%s, phone=%s, email=%s WHERE id=%s",
                    (name, room, phone, email, sid),
                )
                flash("Student updated successfully!", "success")
                return redirect(url_for("index"))
            except Exception as e:
                flash(f"Update failed: {e}", "danger")
            finally:
                cursor2.close()

        cursor.execute("SELECT * FROM students WHERE id=%s", (sid,))
        student = cursor.fetchone()

        if not student:
            flash("Student not found", "warning")
            return redirect(url_for("index"))

    finally:
        cursor.close()
        conn.close()

    return render_template("add_edit_student.html", action="Edit", student=student)

@app.route("/pay/<int:sid>")
def pay_fees(sid):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE students SET fees_paid = 1 WHERE id = %s", (sid,))
        flash("Fees marked as paid!", "success")
    except Exception as e:
        flash(f"Could not update fees: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("index"))

@app.route("/delete/<int:sid>", methods=["GET", "POST"])
def delete_student(sid):
    if request.method == "POST":
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM students WHERE id=%s", (sid,))
            flash("Student deleted successfully!", "success")
        except Exception as e:
            flash(f"Delete failed: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("index"))

    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM students WHERE id=%s", (sid,))
        student = cursor.fetchone()

        if not student:
            flash("Student not found", "warning")
            return redirect(url_for("index"))

    finally:
        cursor.close()
        conn.close()

    return render_template("confirm_delete.html", student=student)

# Initialize DB on startup
init_db_with_retry()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)

