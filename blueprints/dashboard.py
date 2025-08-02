from flask import Blueprint, render_template, session, redirect, url_for, request
from .mbbs_user_id import get_mbbs_ids
from .bds_user_id import get_bds_ids
from .mbbs_pass_recover import get_mbbs_pass
from .bds_pass_recover import get_bds_pass
from .mbbs_result import get_mbbs_results
from .bds_result import get_bds_results
from .management import load_users

dashboard_bp = Blueprint("dashboard", __name__)

# 🔒 Permission Checker Decorator (Optional Use)
def permission_required(permission):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            if permission and permission not in session.get("permissions", []):
                return "Access Denied", 403
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

# ✅ Dashboard Home Route
@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user = {
        "user_id": session.get("user_id"),
        "name": session.get("name", ""),
        "email": session.get("email", ""),
        "role": session.get("role", ""),
        "photo": session.get("photo", "")
    }
    permissions = session.get("permissions", [])
    return render_template("dashboard.html", user=user, permissions=permissions)

# ✅ Dynamic Content Loader (for sidebar click)
@dashboard_bp.route("/content/<page>", methods=["GET", "POST"])
def content_page(page):
    if "user_id" not in session:
        return "Unauthorized", 401

    try:
        match page:
            case "mbbs_user_id":
                return render_template("pages/mbbs_user_id.html", ids=get_mbbs_ids())

            case "bds_user_id":
                return render_template("pages/bds_user_id.html", ids=get_bds_ids())

            case "mbbs_pass_recover":
                return render_template("pages/mbbs_pass_recover.html", ids=get_mbbs_pass())

            case "bds_pass_recover":
                return render_template("pages/bds_pass_recover.html", ids=get_bds_pass())

            case "mbbs_result":
                return render_template("pages/mbbs_result.html", results=get_mbbs_results())

            case "bds_result":
                return render_template("pages/bds_result.html", results=get_bds_results())

            case "management":
                return render_template("pages/management.html", members=load_users())

            # Static page loader fallback
            case _:
                return render_template(f"pages/{page}.html")

    except Exception as e:
        print(f"🔴 Page Load Error: pages/{page}.html ->", e)
        return "Page not found", 404
