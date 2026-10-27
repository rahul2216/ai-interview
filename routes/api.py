import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, abort
from flask_login import current_user
from extensions import db
from models import Interview, InterviewQuestion, InterviewAnswer, UserProgress
from services.ai_service import ai_service

api_bp = Blueprint("api", __name__, url_prefix="/api")

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

def calculate_readiness(percentage):
    if percentage >= 85:
        return "Strongly Ready"
    elif percentage >= 70:
        return "Promising - Near Ready"
    elif percentage >= 50:
        return "Developing Competence"
    else:
        return "Foundational Practice Required"

def finalize_interview(interview):
    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    
    # Calculate totals
    total_score = 0.0
    max_score = 0.0
    for q in interview.questions:
        max_score += q.max_score
        if q.answer:
            total_score += q.answer.score

    interview.total_score = total_score
    interview.max_score = max_score if max_score > 0 else (interview.question_count * 100.0)
    interview.percentage_score = (total_score / interview.max_score * 100.0) if interview.max_score > 0 else 0.0
    interview.readiness_estimate = calculate_readiness(interview.percentage_score)

    # Update UserProgress if authenticated
    if interview.user_id:
        for q in interview.questions:
            if q.answer and q.answer.correctness_status != "skipped":
                prog = UserProgress.query.filter_by(
                    user_id=interview.user_id,
                    interview_type=interview.interview_type,
                    topic=q.topic
                ).first()
                if prog:
                    prog.attempts += 1
                    prog.average_score = ((prog.average_score * (prog.attempts - 1)) + q.answer.score) / prog.attempts
                    prog.last_practiced_at = datetime.now(timezone.utc)
                else:
                    prog = UserProgress(
                        user_id=interview.user_id,
                        interview_type=interview.interview_type,
                        topic=q.topic,
                        attempts=1,
                        average_score=q.answer.score,
                        last_practiced_at=datetime.now(timezone.utc)
                    )
                    db.session.add(prog)

    db.session.commit()

@api_bp.route("/interviews", methods=["POST"])
def create_interview():
    data = request.get_json() or {}
    
    # Validate required fields
    candidate_name = data.get("candidate_name", "").strip()
    target_company = data.get("target_company", "").strip()
    target_role = data.get("target_role", "").strip()
    technical_skills = data.get("technical_skills", "").strip()
    
    if not candidate_name or not target_company or not target_role or not technical_skills:
        return jsonify({"error": "Please provide your name, target company, target role, and technical skills."}), 400

    candidate_type = data.get("candidate_type", "Fresher")
    try:
        experience_years = float(data.get("experience_years", 0))
    except (ValueError, TypeError):
        experience_years = 0.0
        
    current_role = data.get("current_role", "").strip() or None
    job_description = data.get("job_description", "").strip() or None
    programming_languages = data.get("programming_languages", "").strip() or None
    interview_type = data.get("interview_type", "Technical Interview")
    difficulty = data.get("difficulty", "Medium")
    language = data.get("language", "English")
    answer_mode = data.get("answer_mode", "Voice & Text")
    
    try:
        question_count = int(data.get("question_count", 5))
        if question_count not in [5, 10, 15, 20]:
            question_count = 5
    except (ValueError, TypeError):
        question_count = 5

    session_id = str(uuid.uuid4())
    guest_id = session.get("guest_id")
    if not current_user.is_authenticated and not guest_id:
        guest_id = str(uuid.uuid4())
        session["guest_id"] = guest_id

    interview = Interview(
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=session_id,
        guest_session_id=guest_id if not current_user.is_authenticated else None,
        candidate_name=candidate_name,
        candidate_type=candidate_type,
        experience_years=experience_years,
        current_role=current_role,
        target_company=target_company,
        target_role=target_role,
        job_description=job_description,
        technical_skills=technical_skills,
        programming_languages=programming_languages,
        interview_type=interview_type,
        difficulty=difficulty,
        language=language,
        answer_mode=answer_mode,
        question_count=question_count,
        status="configured"
    )
    db.session.add(interview)
    db.session.commit()

    return jsonify({
        "message": "Interview session initialized.",
        "session_id": session_id,
        "redirect_url": f"/interview/{session_id}/consent"
    }), 201

@api_bp.route("/interviews/<session_id>/start", methods=["POST"])
def start_interview(session_id):
    interview = get_authorized_interview(session_id)
    
    if interview.status == "configured":
        interview.status = "in_progress"
        interview.started_at = datetime.now(timezone.utc)
        db.session.commit()

    # If first question does not exist, generate it
    first_q = InterviewQuestion.query.filter_by(interview_id=interview.id, sequence_number=1).first()
    if not first_q:
        q_data = ai_service.generate_question(interview, 1)
        first_q = InterviewQuestion(
            interview_id=interview.id,
            sequence_number=1,
            question_text=q_data["question_text"],
            topic=q_data["topic"],
            difficulty=q_data["difficulty"],
            question_type=q_data["question_type"],
            max_score=q_data["max_score"],
            status="presented"
        )
        db.session.add(first_q)
        db.session.commit()

    return jsonify({
        "status": interview.status,
        "question": first_q.to_dict(),
        "total_questions": interview.question_count
    })

@api_bp.route("/interviews/<session_id>/question", methods=["GET"])
def get_current_question(session_id):
    interview = get_authorized_interview(session_id)
    if interview.status == "completed":
        return jsonify({"completed": True, "redirect_url": f"/interview/{session_id}/report"})

    # Look for the earliest question that has not been answered or skipped
    current_q = InterviewQuestion.query.filter(
        InterviewQuestion.interview_id == interview.id,
        InterviewQuestion.status.in_(["pending", "presented"])
    ).order_by(InterviewQuestion.sequence_number.asc()).first()

    if not current_q:
        # Determine current answered count
        answered_count = InterviewQuestion.query.filter_by(interview_id=interview.id).count()
        if answered_count < interview.question_count:
            # Generate next question
            next_seq = answered_count + 1
            # Gather previous qa
            prev_questions = InterviewQuestion.query.filter_by(interview_id=interview.id).all()
            prev_qa = []
            for pq in prev_questions:
                if pq.answer:
                    prev_qa.append({"seq": pq.sequence_number, "question": pq.question_text, "score": pq.answer.score})
            
            q_data = ai_service.generate_question(interview, next_seq, prev_qa)
            current_q = InterviewQuestion(
                interview_id=interview.id,
                sequence_number=next_seq,
                question_text=q_data["question_text"],
                topic=q_data["topic"],
                difficulty=q_data["difficulty"],
                question_type=q_data["question_type"],
                max_score=q_data["max_score"],
                status="presented"
            )
            db.session.add(current_q)
            db.session.commit()
        else:
            finalize_interview(interview)
            return jsonify({"completed": True, "redirect_url": f"/interview/{session_id}/report"})

    return jsonify({
        "completed": False,
        "question": current_q.to_dict(),
        "total_questions": interview.question_count,
        "interview_type": interview.interview_type,
        "difficulty": interview.difficulty,
        "answer_mode": interview.answer_mode
    })

@api_bp.route("/interviews/<session_id>/answer", methods=["POST"])
def submit_answer(session_id):
    interview = get_authorized_interview(session_id)
    if interview.status == "completed":
        return jsonify({"error": "Interview has already been completed."}), 400

    data = request.get_json() or {}
    question_id = data.get("question_id")
    answer_text = data.get("answer_text", "").strip()
    transcript_text = data.get("transcript_text", "").strip() or None

    question = InterviewQuestion.query.filter_by(id=question_id, interview_id=interview.id).first_or_404()
    
    # Check if already answered
    if question.answer:
        return jsonify({"error": "This question has already been evaluated."}), 400

    # Evaluate using AI Service
    evaluation = ai_service.evaluate_answer(interview, question, answer_text, is_skipped=False)

    answer = InterviewAnswer(
        question_id=question.id,
        answer_text=answer_text,
        transcript_text=transcript_text,
        score=evaluation["score"],
        correctness_status=evaluation["correctness_status"],
        feedback=evaluation
    )
    question.status = "answered"
    db.session.add(answer)
    db.session.commit()

    # Check if this was the last question
    is_last = (question.sequence_number >= interview.question_count)
    if is_last:
        finalize_interview(interview)

    return jsonify({
        "success": True,
        "is_last": is_last,
        "evaluation": evaluation,
        "redirect_url": f"/interview/{session_id}/report" if is_last else None
    })

@api_bp.route("/interviews/<session_id>/skip", methods=["POST"])
def skip_question(session_id):
    interview = get_authorized_interview(session_id)
    if interview.status == "completed":
        return jsonify({"error": "Interview has already been completed."}), 400

    data = request.get_json() or {}
    question_id = data.get("question_id")
    question = InterviewQuestion.query.filter_by(id=question_id, interview_id=interview.id).first_or_404()

    if question.answer:
        return jsonify({"error": "This question was already evaluated."}), 400

    evaluation = ai_service.evaluate_answer(interview, question, "", is_skipped=True)
    answer = InterviewAnswer(
        question_id=question.id,
        answer_text="[Skipped by candidate]",
        score=0.0,
        correctness_status="skipped",
        feedback=evaluation
    )
    question.status = "skipped"
    db.session.add(answer)
    db.session.commit()

    is_last = (question.sequence_number >= interview.question_count)
    if is_last:
        finalize_interview(interview)

    return jsonify({
        "success": True,
        "is_last": is_last,
        "evaluation": evaluation,
        "redirect_url": f"/interview/{session_id}/report" if is_last else None
    })

@api_bp.route("/interviews/<session_id>/end", methods=["POST"])
def end_interview(session_id):
    interview = get_authorized_interview(session_id)
    finalize_interview(interview)
    return jsonify({
        "success": True,
        "redirect_url": f"/interview/{session_id}/report"
    })

@api_bp.route("/interviews/<session_id>", methods=["DELETE"])
def delete_interview(session_id):
    interview = get_authorized_interview(session_id)
    db.session.delete(interview)
    db.session.commit()
    return jsonify({"success": True, "message": "Interview session deleted."})
