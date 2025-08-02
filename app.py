import json
import os
from flask import Flask, render_template, request, redirect, session, url_for
from blueprints import register_blueprints

app = Flask(__name__)
app.secret_key = "your_secret_key"  # গোপন সেশন key

register_blueprints(app)  # ব্লুপ্রিন্টগুলো রেজিস্টার করা হবে

# ✅ ইউজার লোড ফাংশন (users.json থেকে)
def load_users():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "users.json")
    with open(file_path, "r") as f:
        return json.load(f)

# 🔐 লগইন রুট
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        users = load_users()
        for user in users:
            if user["user_id"] == user_id and user["password"] == password:
                session["user"] = user_id
                session["permissions"] = user.get("permissions", [])
                return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# ✅ ড্যাশবোর্ড
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        user=session["user"],
        permissions=session.get("permissions", [])
    )

# 🔓 লগআউট
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ✅ অ্যাপ রান
if __name__ == "__main__":
    app.run(debug=True)
