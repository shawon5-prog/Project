import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint("auth", __name__)

# ✅ ইউজার লিস্ট JSON ফাইল থেকে লোড করা
def load_users():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    file_path = os.path.join(project_root, "users.json")
    
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# ✅ লগইন রুট
@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()
        for user in users:
            if user.get("user_id") == user_id and user.get("password") == password:
                # Full info under session["user"]
                session["user"] = {
                    "user_id": user_id,
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "role": user.get("role", "viewer"),
                    "photo": user.get("photo", "")
                }
                # Flat session values for convenience
                session["user_id"] = user_id
                session["name"] = user.get("name", "")
                session["email"] = user.get("email", "")
                session["role"] = user.get("role", "viewer")
                session["permissions"] = user.get("permissions", [])

                flash("✅ Login successful", "success")
                return redirect(url_for("dashboard.dashboard"))

        error = "❌ Invalid User ID or Password"
        return render_template("login.html", error=error)

    return render_template("login.html")

# ✅ লগআউট রুট
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("🔒 Logged out successfully", "info")
    return redirect(url_for("auth.login"))
