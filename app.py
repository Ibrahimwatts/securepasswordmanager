from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import pymysql
from datetime import datetime, timedelta
import random
import string

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="Ibrahimwatts5@",
        database="password_manager",
        cursorclass=pymysql.cursors.DictCursor  # Use DictCursor here
    )


def calculate_remaining_time(requested_at):
    if requested_at is None:
        return "Not requested"

    # Ensure requested_at is a datetime object
    if isinstance(requested_at, str):
        requested_time = datetime.strptime(requested_at, "%Y-%m-%d %H:%M:%S")
    else:
        requested_time = requested_at

    reveal_time = requested_time + timedelta(hours=48)
    now = datetime.now()

    if now >= reveal_time:
        return "Ready to reveal"
    else:
        remaining_time = reveal_time - now
        return str(remaining_time)

# Home Page
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
                conn.commit()
            return redirect(url_for("login"))
        except Exception as e:
            return f"Error: {str(e)}"
    return render_template("register.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, password))
                user = cur.fetchone()
                if user:
                    session["user_id"] = user["id"]
                    return redirect(url_for("dashboard"))
                else:
                    return "Invalid credentials"
        except Exception as e:
            return f"Error: {str(e)}"
    return render_template("login.html")

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Fetch passwords and their statuses
            cur.execute(
                """
                SELECT id, password_value, requested_at, 
                       revealed_at, is_revealed 
                FROM passwords WHERE user_id = %s
                """,
                (session["user_id"],)
            )
            passwords = cur.fetchall()

        # Add dynamic remaining time for each password
        for password in passwords:
            password["remaining_time"] = calculate_remaining_time(password["requested_at"])

        return render_template("dashboard.html", passwords=passwords)
    except Exception as e:
        return f"Error: {str(e)}"


# Logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))


@app.route("/generate_password", methods=["POST"])
def generate_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    password_length = 12
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=password_length))

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO passwords (user_id, password_value) VALUES (%s, %s)",
                (user_id, password)
            )
            conn.commit()
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Error: {str(e)}"



# Request Password Reveal
@app.route("/request_reveal/<int:password_id>", methods=["POST"])
def request_reveal(password_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Update the `requested_at` field and reset the reveal status
            cur.execute(
                """
                UPDATE passwords 
                SET requested_at = NOW(), revealed_at = NULL, is_revealed = FALSE
                WHERE id = %s AND user_id = %s
                """,
                (password_id, session["user_id"])
            )
            conn.commit()
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Error: {str(e)}"

# Cancel Password Reveal
@app.route("/cancel_reveal/<int:password_id>", methods=["POST"])
def cancel_reveal(password_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE passwords SET requested_at = NULL, revealed_at = NULL WHERE id = %s",
                (password_id,)
            )
            conn.commit()
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)