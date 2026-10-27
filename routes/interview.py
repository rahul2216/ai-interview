import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort, send_file
from flask_login import current_user
from extensions import db
from models import Interview, InterviewQuestion, InterviewAnswer
from services.pdf_service import PDFReportService

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")

def get_authorized_interview(session_id):
    interview = Interview.query.filter_by(session_id=session_id).first_or_404()
    guest_id = session.get("guest_id")

    if interview.user_id:
        if not current_user.is_authenticated or current_user.id != interview.user_id:
            abort(403)
    else:
        if interview.guest_session_id != guest_id:
            abort(403)

    return interview

@interview_bp.route("/setup")
def setup():
    # If user is not authenticated and has no guest id, generate a guest id
    if not current_user.is_authenticated and "guest_id" not in session:
        session["guest_id"] = str(uuid.uuid4())

    initial_type = request.args.get("type", "Technical Interview")
    # Clean parameter
    type_map = {
        "technical": "Technical Interview",
        "hr": "HR Interview",
        "coding": "Coding Interview",
        "behavioral": "Behavioral Interview",
        "tech_hr": "Technical + HR Interview",
        "company": "Company-Specific Interview"
    }
    selected_type = type_map.get(initial_type.lower(), initial_type)

    return render_template(
        "interview/setup.html",
        selected_type=selected_type,
        user=current_user if current_user.is_authenticated else None
    )

@interview_bp.route("/<session_id>/consent")
def consent(session_id):
    interview = get_authorized_interview(session_id)
    return render_template("interview/consent.html", interview=interview)

@interview_bp.route("/<session_id>/live")
def live(session_id):
    interview = get_authorized_interview(session_id)
    if interview.status == "completed":
        flash("This interview has already been completed. Here is your evaluation report.", "info")
        return redirect(url_for("interview.report", session_id=session_id))
    return render_template("interview/live.html", interview=interview)

@interview_bp.route("/<session_id>/report")
def report(session_id):
    interview = get_authorized_interview(session_id)
    # Calculate questions statistics
    total_q = len(interview.questions)
    answered_q = sum(1 for q in interview.questions if q.answer and q.answer.correctness_status != "skipped")
    correct_q = sum(1 for q in interview.questions if q.answer and q.answer.correctness_status == "correct")
    partial_q = sum(1 for q in interview.questions if q.answer and q.answer.correctness_status == "partially_correct")
    incorrect_q = sum(1 for q in interview.questions if q.answer and q.answer.correctness_status == "incorrect")
    skipped_q = sum(1 for q in interview.questions if not q.answer or q.answer.correctness_status == "skipped")

    stats = {
        "total": total_q,
        "answered": answered_q,
        "correct": correct_q,
        "partially_correct": partial_q,
        "incorrect": incorrect_q,
        "skipped": skipped_q
    }

    return render_template("interview/report.html", interview=interview, stats=stats)

@interview_bp.route("/<session_id>/pdf")
def download_pdf(session_id):
    interview = get_authorized_interview(session_id)
    pdf_buffer = PDFReportService.generate_interview_pdf(interview)
    filename = f"AI_Mock_Interview_{interview.target_company}_{interview.target_role}_{interview.session_id[:8]}.pdf".replace(" ", "_")
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

@interview_bp.route("/<session_id>/repeat")
def repeat(session_id):
    interview = get_authorized_interview(session_id)
    new_session_id = str(uuid.uuid4())
    guest_id = session.get("guest_id")

    new_interview = Interview(
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=new_session_id,
        guest_session_id=guest_id if not current_user.is_authenticated else None,
        candidate_name=interview.candidate_name,
        candidate_type=interview.candidate_type,
        experience_years=interview.experience_years,
        current_role=interview.current_role,
        target_company=interview.target_company,
        target_role=interview.target_role,
        job_description=interview.job_description,
        technical_skills=interview.technical_skills,
        programming_languages=interview.programming_languages,
        interview_type=interview.interview_type,
        difficulty=interview.difficulty,
        language=interview.language,
        answer_mode=interview.answer_mode,
        question_count=interview.question_count,
        status="configured"
    )
    db.session.add(new_interview)
    db.session.commit()
    flash("Configured new interview using previous settings. Review the guidelines to begin.", "info")
    return redirect(url_for("interview.consent", session_id=new_session_id))
