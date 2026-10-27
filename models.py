import json
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    experience_level = db.Column(db.String(50), nullable=True, default="Fresher")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    interviews = db.relationship("Interview", backref="user", lazy=True, cascade="all, delete-orphan")
    progress = db.relationship("UserProgress", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "experience_level": self.experience_level,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Interview(db.Model):
    __tablename__ = "interviews"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    guest_session_id = db.Column(db.String(64), nullable=True, index=True)
    
    # Candidate details
    candidate_name = db.Column(db.String(120), nullable=False)
    candidate_type = db.Column(db.String(50), nullable=False, default="Fresher") # Fresher, Experienced Professional, Career Switcher
    experience_years = db.Column(db.Float, default=0.0)
    current_role = db.Column(db.String(120), nullable=True)
    target_company = db.Column(db.String(120), nullable=False)
    target_role = db.Column(db.String(120), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    technical_skills = db.Column(db.Text, nullable=False)
    programming_languages = db.Column(db.Text, nullable=True)
    interview_type = db.Column(db.String(50), nullable=False, default="Technical Interview")
    difficulty = db.Column(db.String(50), nullable=False, default="Medium")
    language = db.Column(db.String(50), nullable=False, default="English")
    answer_mode = db.Column(db.String(50), nullable=False, default="Voice & Text")
    question_count = db.Column(db.Integer, default=5)
    
    # Session state
    status = db.Column(db.String(30), default="configured") # configured, in_progress, completed, abandoned
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Scores
    total_score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    percentage_score = db.Column(db.Float, default=0.0)
    readiness_estimate = db.Column(db.String(50), default="Developing")
    prompt_version = db.Column(db.String(50), default="2.1.0-job-ready")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    questions = db.relationship("InterviewQuestion", backref="interview", lazy=True, cascade="all, delete-orphan", order_by="InterviewQuestion.sequence_number")
    
    def duration_formatted(self):
        if not self.started_at:
            return "0m"
        end = self.completed_at or datetime.now(timezone.utc)
        start = self.started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        diff = int((end - start).total_seconds())
        minutes = diff // 60
        seconds = diff % 60
        return f"{minutes}m {seconds}s"

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "candidate_name": self.candidate_name,
            "candidate_type": self.candidate_type,
            "target_company": self.target_company,
            "target_role": self.target_role,
            "interview_type": self.interview_type,
            "difficulty": self.difficulty,
            "question_count": self.question_count,
            "status": self.status,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage_score": round(self.percentage_score, 1),
            "readiness_estimate": self.readiness_estimate,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration_formatted()
        }

class InterviewQuestion(db.Model):
    __tablename__ = "interview_questions"
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    question_type = db.Column(db.String(50), nullable=False) # technical, coding, behavioral, hr
    max_score = db.Column(db.Float, default=100.0)
    status = db.Column(db.String(30), default="pending") # pending, presented, answered, skipped
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    answer = db.relationship("InterviewAnswer", backref="question", uselist=False, lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "sequence_number": self.sequence_number,
            "question_text": self.question_text,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question_type": self.question_type,
            "max_score": self.max_score,
            "status": self.status,
            "answer": self.answer.to_dict() if self.answer else None
        }

class InterviewAnswer(db.Model):
    __tablename__ = "interview_answers"
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    answer_text = db.Column(db.Text, nullable=False)
    transcript_text = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, default=0.0)
    correctness_status = db.Column(db.String(30), default="partially_correct") # correct, partially_correct, incorrect, skipped
    feedback_data = db.Column(db.Text, nullable=False) # JSON-encoded feedback
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @property
    def feedback(self):
        try:
            return json.loads(self.feedback_data) if self.feedback_data else {}
        except Exception:
            return {}
            
    @feedback.setter
    def feedback(self, value):
        self.feedback_data = json.dumps(value) if isinstance(value, dict) else value

    def to_dict(self):
        return {
            "id": self.id,
            "question_id": self.question_id,
            "answer_text": self.answer_text,
            "transcript_text": self.transcript_text,
            "score": self.score,
            "correctness_status": self.correctness_status,
            "feedback": self.feedback,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None
        }

class UserProgress(db.Model):
    __tablename__ = "user_progress"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_type = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(120), nullable=False)
    attempts = db.Column(db.Integer, default=1)
    average_score = db.Column(db.Float, default=0.0)
    last_practiced_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "interview_type": self.interview_type,
            "topic": self.topic,
            "attempts": self.attempts,
            "average_score": round(self.average_score, 1),
            "last_practiced_at": self.last_practiced_at.isoformat() if self.last_practiced_at else None
        }
