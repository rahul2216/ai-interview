import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, Interview

auth_bp = Blueprint("auth", __name__)

def transfer_guest_interviews(user):
    guest_id = session.get("guest_id")
    if guest_id:
        transferred = Interview.query.filter_by(guest_session_id=guest_id, user_id=None).all()
        if transferred:
            for item in transferred:
                item.user_id = user.id
            db.session.commit()
            flash(f"Successfully linked {len(transferred)} previous guest interview(s) to your account!", "success")
        session.pop("guest_id", None)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
        
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        experience_level = request.form.get("experience_level", "Fresher")
        
        # Validations
        if not full_name or not email or not password:
            flash("All required fields must be completed.", "danger")
            return render_template("auth/register.html", full_name=full_name, email=email, experience_level=experience_level)
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", full_name=full_name, email=email, experience_level=experience_level)
            
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", full_name=full_name, email=email, experience_level=experience_level)
            
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please sign in.", "warning")
            return redirect(url_for("auth.login"))
            
        user = User(
            full_name=full_name,
            email=email,
            experience_level=experience_level
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        transfer_guest_interviews(user)
        flash(f"Welcome to AI Mock Interview, {user.full_name}!", "success")
        return redirect(url_for("main.dashboard"))
        
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            transfer_guest_interviews(user)
            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")
            
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("main.home"))

@auth_bp.route("/guest")
def guest_mode():
    if "guest_id" not in session:
        session["guest_id"] = str(uuid.uuid4())
    flash("Continuing in Guest Mode. Your session data is isolated. You can convert to a full account anytime to permanently save your progress.", "info")
    return redirect(url_for("interview.setup"))
