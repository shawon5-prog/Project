import os, json, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

management_bp = Blueprint("management", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_FILE = os.path.join(BASE_DIR, "..", "users.json")
LOG_FILE = os.path.join(BASE_DIR, "..", "activity_logs.json")


# 🔄 Load all users
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# 💾 Save all users
def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

# 🧾 Log an activity
def log_activity(user_id, action):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    logs.append({
        "id": str(uuid.uuid4()),
        "user": user_id,
        "action": action
    })
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

# ✅ Add Member
@management_bp.route("/management/add_members", methods=["GET", "POST"])
def add_members():
    if request.method == "POST":
        users = load_users()
        user_id = request.form.get("user_id", "").strip()

        if not user_id:
            flash("User ID is required.", "danger")
            return redirect(url_for("management.add_members"))

        if any(u["user_id"] == user_id for u in users):
            flash("User ID already exists!", "danger")
            return redirect(url_for("management.add_members"))

        new_user = {
            "user_id": user_id,
            "pin": request.form.get("pin", "").strip(),
            "email": request.form.get("email", "").strip(),
            "password": request.form.get("password", "").strip(),
            "permissions": [],
            "info": {},
            "status": "active",
            "role": "viewer",
            "photo": "",
            "name": "",
            "mobile": ""
        }

        users.append(new_user)
        save_users(users)
        log_activity(session.get("user", "admin"), f"Added new member: {user_id}")
        flash("✅ Member added successfully!", "success")
        return redirect(url_for("management.add_members"))

    return render_template("pages/add_members.html")

# ✅ Permission Setup via PIN
@management_bp.route("/management/permission", methods=["GET", "POST"])
def permission_setup():
    users = load_users()
    selected_user_pin = request.form.get("user_pin") if request.method == "POST" else request.args.get("user_pin")
    selected_user = next((u for u in users if u.get("pin") == selected_user_pin), None)

    if request.method == "POST" and "permissions" in request.form:
        permissions = request.form.getlist("permissions")
        if selected_user:
            selected_user["permissions"] = permissions
            save_users(users)
            log_activity(session.get("user", "admin"), f"Updated permissions for PIN: {selected_user_pin}")
            flash("✅ Permissions updated!", "success")
        return redirect(url_for("management.permission_setup", user_pin=selected_user_pin))

    return render_template("pages/permission_setup.html",
                           users=users,
                           selected_user=selected_user,
                           selected_user_pin=selected_user_pin)

# ✅ Edit User Info
@management_bp.route("/management/user_info_edit", methods=["GET", "POST"])
def user_info_edit():
    users = load_users()
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        for user in users:
            if user["user_id"] == user_id:
                user["info"] = {
                    "name": request.form.get("name", "").strip(),
                    "phone": request.form.get("phone", "").strip(),
                    "designation": request.form.get("designation", "").strip()
                }
                save_users(users)
                log_activity(session.get("user", "admin"), f"Edited info for {user_id}")
                flash("✅ Info updated successfully!", "success")
                return redirect(url_for("management.user_info_edit"))

        flash("User not found.", "danger")
        return redirect(url_for("management.user_info_edit"))

    return render_template("pages/user_info_edit.html", users=users)

# ✅ View Activity Logs
@management_bp.route("/management/activity_logs")
def activity_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    return render_template("pages/activity_logs.html", logs=logs)
