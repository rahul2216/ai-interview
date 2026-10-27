from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import Interview, InterviewQuestion, InterviewAnswer, UserProgress, User

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("index.html")

@main_bp.route("/interviews/technical")
def technical_interviews():
    return render_template("interview_types.html", active_tab="technical")

@main_bp.route("/interviews/hr")
def hr_interviews():
    return render_template("interview_types.html", active_tab="hr")

@main_bp.route("/interviews/coding")
def coding_interviews():
    return render_template("interview_types.html", active_tab="coding")

@main_bp.route("/dashboard")
def dashboard():
    guest_id = session.get("guest_id")
    if not current_user.is_authenticated and not guest_id:
        return redirect(url_for("auth.login", next=request.path))

    # Query interviews
    if current_user.is_authenticated:
        interviews = Interview.query.filter_by(user_id=current_user.id).order_by(Interview.created_at.desc()).all()
    else:
        interviews = Interview.query.filter_by(guest_session_id=guest_id, user_id=None).order_by(Interview.created_at.desc()).all()

    completed_interviews = [i for i in interviews if i.status == "completed"]
    total_completed = len(completed_interviews)
    avg_score = round(sum(i.percentage_score for i in completed_interviews) / total_completed, 1) if total_completed > 0 else 0.0
    highest_score = round(max((i.percentage_score for i in completed_interviews), default=0.0), 1)

    # Breakdown by interview type
    type_counts = {}
    for i in completed_interviews:
        type_counts[i.interview_type] = type_counts.get(i.interview_type, 0) + 1

    # Strengths and areas for improvement
    strong_topics = []
    weak_topics = []
    if current_user.is_authenticated:
        progress_items = UserProgress.query.filter_by(user_id=current_user.id).order_by(UserProgress.average_score.desc()).all()
        strong_topics = [p for p in progress_items if p.average_score >= 75][:5]
        weak_topics = [p for p in progress_items if p.average_score < 70][:5]

    return render_template(
        "dashboard/dashboard.html",
        interviews=interviews[:6],
        total_completed=total_completed,
        avg_score=avg_score,
        highest_score=highest_score,
        type_counts=type_counts,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
        is_guest=not current_user.is_authenticated
    )

@main_bp.route("/history")
def history():
    guest_id = session.get("guest_id")
    if not current_user.is_authenticated and not guest_id:
        return redirect(url_for("auth.login", next=request.path))

    if current_user.is_authenticated:
        interviews = Interview.query.filter_by(user_id=current_user.id).order_by(Interview.created_at.desc()).all()
    else:
        interviews = Interview.query.filter_by(guest_session_id=guest_id, user_id=None).order_by(Interview.created_at.desc()).all()

    return render_template("dashboard/history.html", interviews=interviews, is_guest=not current_user.is_authenticated)

@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        experience_level = request.form.get("experience_level", current_user.experience_level)
        new_password = request.form.get("new_password", "").strip()

        if not full_name:
            flash("Full name cannot be blank.", "danger")
        else:
            current_user.full_name = full_name
            current_user.experience_level = experience_level
            if new_password:
                if len(new_password) < 6:
                    flash("New password must be at least 6 characters.", "danger")
                else:
                    current_user.set_password(new_password)
                    flash("Password updated successfully.", "success")
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("main.profile"))

    stats = {
        "interviews_count": Interview.query.filter_by(user_id=current_user.id).count(),
        "completed_count": Interview.query.filter_by(user_id=current_user.id, status="completed").count()
    }
    return render_template("profile.html", stats=stats)

@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@main_bp.route("/terms")
def terms():
    return render_template("terms.html")
