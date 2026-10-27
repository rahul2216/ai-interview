import unittest
import json
from app import create_app
from extensions import db
from models import User, Interview, InterviewQuestion, InterviewAnswer, UserProgress
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"

class AIMockInterviewTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_homepage(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI Mock", response.data)
        self.assertIn(b"Start Mock Interview", response.data)
        self.assertIn(b"Technical", response.data)
        self.assertIn(b"Coding", response.data)
        self.assertIn(b"HR & Behavioral", response.data)

    def test_interview_types_pages(self):
        for route in ["/interviews/technical", "/interviews/hr", "/interviews/coding"]:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200)

    def test_privacy_and_terms(self):
        p_res = self.client.get("/privacy")
        self.assertEqual(p_res.status_code, 200)
        self.assertIn(b"Privacy Policy", p_res.data)

        t_res = self.client.get("/terms")
        self.assertEqual(t_res.status_code, 200)
        self.assertIn(b"Terms of Service", t_res.data)

    def test_registration_and_login(self):
        reg_response = self.client.post("/register", data={
            "full_name": "Test Engineer",
            "email": "engineer@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "experience_level": "Experienced Professional"
        }, follow_redirects=True)
        self.assertEqual(reg_response.status_code, 200)
        user = User.query.filter_by(email="engineer@example.com").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password("password123"))

        # Logout
        self.client.get("/logout", follow_redirects=True)

        # Login
        login_response = self.client.post("/login", data={
            "email": "engineer@example.com",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)

    def test_interview_lifecycle(self):
        # 1. Create interview via API
        payload = {
            "candidate_name": "Sarah Connor",
            "candidate_type": "Experienced Professional",
            "experience_years": 4.5,
            "current_role": "Backend Developer",
            "target_company": "Stripe",
            "target_role": "Senior Infrastructure Engineer",
            "technical_skills": "Python, Distributed Systems, Redis, PostgreSQL",
            "interview_type": "Technical Interview",
            "difficulty": "Hard",
            "question_count": 5,
            "language": "English",
            "answer_mode": "Voice & Text"
        }
        res = self.client.post("/api/interviews", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        session_id = data["session_id"]
        self.assertIsNotNone(session_id)

        # 2. Start interview
        start_res = self.client.post(f"/api/interviews/{session_id}/start")
        self.assertEqual(start_res.status_code, 200)
        start_data = start_res.get_json()
        self.assertEqual(start_data["question"]["sequence_number"], 1)
        self.assertIn("question_text", start_data["question"])

        # 3. Retrieve current question
        q_res = self.client.get(f"/api/interviews/{session_id}/question")
        self.assertEqual(q_res.status_code, 200)
        q_data = q_res.get_json()
        question_id = q_data["question"]["id"]
        self.assertFalse(q_data["completed"])

        # 4. Submit Answer for Question 1
        ans_payload = {
            "question_id": question_id,
            "answer_text": "I implement idempotency keys using Redis cache with TTL to prevent duplicate transaction charges under heavy concurrent loads."
        }
        ans_res = self.client.post(f"/api/interviews/{session_id}/answer", data=json.dumps(ans_payload), content_type="application/json")
        self.assertEqual(ans_res.status_code, 200)
        ans_data = ans_res.get_json()
        self.assertTrue(ans_data["success"])
        self.assertGreater(ans_data["evaluation"]["score"], 0)

        # 5. Fetch Question 2
        q2_res = self.client.get(f"/api/interviews/{session_id}/question")
        q2_data = q2_res.get_json()
        self.assertFalse(q2_data["completed"])
        self.assertEqual(q2_data["question"]["sequence_number"], 2)

        # 6. Skip Question 2
        skip_payload = {"question_id": q2_data["question"]["id"]}
        skip_res = self.client.post(f"/api/interviews/{session_id}/skip", data=json.dumps(skip_payload), content_type="application/json")
        self.assertEqual(skip_res.status_code, 200)

        # 7. End interview early
        end_res = self.client.post(f"/api/interviews/{session_id}/end")
        self.assertEqual(end_res.status_code, 200)

        # 8. Check report page
        report_res = self.client.get(f"/interview/{session_id}/report")
        self.assertEqual(report_res.status_code, 200)
        self.assertIn(b"Performance Report", report_res.data)

        # 9. Test PDF Download
        pdf_res = self.client.get(f"/interview/{session_id}/pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, "application/pdf")
        self.assertGreater(len(pdf_res.data), 1000)

        # 10. Repeat Interview Configuration
        repeat_res = self.client.get(f"/interview/{session_id}/repeat", follow_redirects=False)
        self.assertEqual(repeat_res.status_code, 302)

        # 11. Delete Interview
        del_res = self.client.delete(f"/api/interviews/{session_id}")
        self.assertEqual(del_res.status_code, 200)
        interview = Interview.query.filter_by(session_id=session_id).first()
        self.assertIsNone(interview)

    def test_coding_interview_flow(self):
        payload = {
            "candidate_name": "Dev Algo",
            "candidate_type": "Fresher",
            "experience_years": 0.0,
            "target_company": "Amazon",
            "target_role": "Software Development Engineer I",
            "technical_skills": "Python, Data Structures, Algorithms",
            "programming_languages": "Python",
            "interview_type": "Coding Interview",
            "difficulty": "Medium",
            "question_count": 5
        }
        res = self.client.post("/api/interviews", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        session_id = res.get_json()["session_id"]

        start_res = self.client.post(f"/api/interviews/{session_id}/start")
        self.assertEqual(start_res.status_code, 200)
        q = start_res.get_json()["question"]
        self.assertEqual(q["question_type"], "coding")

        # Submit code solution
        ans_payload = {
            "question_id": q["id"],
            "answer_text": "def maxSubArray(nums):\n    max_sum = cur_sum = nums[0]\n    for x in nums[1:]:\n        cur_sum = max(x, cur_sum + x)\n        max_sum = max(max_sum, cur_sum)\n    return max_sum\n# Time: O(N), Space: O(1)"
        }
        ans_res = self.client.post(f"/api/interviews/{session_id}/answer", data=json.dumps(ans_payload), content_type="application/json")
        self.assertEqual(ans_res.status_code, 200)
        eval_data = ans_res.get_json()["evaluation"]
        self.assertIn("score", eval_data)
        self.assertIn("model_answer", eval_data)
        self.assertIn("rubric_breakdown", eval_data)

    def test_validation_errors(self):
        # Missing required fields
        res = self.client.post("/api/interviews", data=json.dumps({}), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_guest_mode_transfer(self):
        with self.client.session_transaction() as sess:
            sess["guest_id"] = "guest-uuid-12345"

        payload = {
            "candidate_name": "Guest Candidate",
            "candidate_type": "Fresher",
            "experience_years": 0.0,
            "target_company": "TechCorp",
            "target_role": "Junior Developer",
            "technical_skills": "Python, SQL",
            "interview_type": "Technical Interview",
            "difficulty": "Easy",
            "question_count": 5
        }
        res = self.client.post("/api/interviews", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        session_id = res.get_json()["session_id"]

        # Register user with guest session active
        self.client.post("/register", data={
            "full_name": "Transferred User",
            "email": "transferred@example.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)

        user = User.query.filter_by(email="transferred@example.com").first()
        self.assertIsNotNone(user)
        transferred_interview = Interview.query.filter_by(session_id=session_id).first()
        self.assertEqual(transferred_interview.user_id, user.id)

    def test_unauthorized_interview_access(self):
        # Create an interview under user A
        user_a = User(full_name="User A", email="usera@test.com")
        user_a.set_password("pass123")
        db.session.add(user_a)
        db.session.commit()

        interview_a = Interview(
            user_id=user_a.id,
            session_id="session-user-a-secret",
            candidate_name="User A",
            target_company="Google",
            target_role="Staff Engineer",
            technical_skills="Go, Kubernetes",
            interview_type="Technical Interview"
        )
        db.session.add(interview_a)
        db.session.commit()

        # Try to access as unauthorized guest
        res = self.client.get("/interview/session-user-a-secret/live")
        self.assertEqual(res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
