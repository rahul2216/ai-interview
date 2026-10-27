import json
import logging
import re
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are the AI Interviewer for the AI Mock Interview platform.

Conduct a realistic professional job interview based on the candidate's supplied details.

Candidate context:
* Name: {candidate_name}
* Candidate type: {candidate_type}
* Experience: {experience_years} years
* Current role: {current_role}
* Target company: {target_company}
* Target designation: {target_role}
* Job description: {job_description}
* Technical skills: {skills}
* Programming languages: {programming_languages}
* Interview type: {interview_type}
* Difficulty: {difficulty}
* Question count: {question_count}
* Language: {language}
* Authorized prior performance: {prior_performance}

Instructions:
* Conduct only professional job interview practice.
* Do not generate academic viva or college examination questions.
* Ask exactly one question at a time.
* Wait for the candidate's answer.
* Evaluate answers fairly and provide constructive feedback.
* Generate questions relevant to the target job.
* For freshers, focus on fundamentals and entry-level skills.
* For experienced candidates, include role-specific scenarios and practical problem-solving.
* For coding interviews, evaluate logic, correctness, edge cases, and complexity where appropriate.
* For behavioral questions, evaluate relevance, clarity, reasoning, and examples.
* Do not confuse accent or speaking style with technical competence.
* Never claim that the candidate will definitely be hired or rejected.
* Do not infer dishonesty or unethical conduct from facial expressions or eye movements.
* Return validated structured JSON compatible with the backend schema.
* Never reveal the next question before the current answer is submitted.
* Follow the configured interview question limit."""

class AIService:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.model = Config.OPENAI_MODEL
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def get_system_prompt(self, interview, prior_performance="None recorded"):
        return SYSTEM_PROMPT_TEMPLATE.format(
            candidate_name=interview.candidate_name,
            candidate_type=interview.candidate_type,
            experience_years=interview.experience_years,
            current_role=interview.current_role or "Not specified",
            target_company=interview.target_company,
            target_role=interview.target_role,
            job_description=interview.job_description or "General industry standards for this role",
            skills=interview.technical_skills,
            programming_languages=interview.programming_languages or "Not specified",
            interview_type=interview.interview_type,
            difficulty=interview.difficulty,
            question_count=interview.question_count,
            language=interview.language,
            prior_performance=prior_performance
        )

    def generate_question(self, interview, sequence_number, previous_qa=None):
        """
        Generate the next single interview question in structured JSON.
        """
        if self.client and self.api_key:
            try:
                system_prompt = self.get_system_prompt(interview)
                prompt = (
                    f"Generate question #{sequence_number} out of {interview.question_count} for this candidate.\n"
                    f"Interview Type: {interview.interview_type}. Difficulty: {interview.difficulty}.\n"
                )
                if previous_qa:
                    prompt += "\nPreviously asked questions and brief summaries:\n"
                    for item in previous_qa[-3:]:
                        prompt += f"- Q{item['seq']}: {item['question']} (Candidate scored: {item['score']}/100)\n"
                    prompt += "\nEnsure this new question does not repeat previous topics, and appropriately adapts difficulty or dives into a fresh relevant competency."

                prompt += """
Return ONLY a valid JSON object with the following schema:
{
  "question_text": "Clear, professional, realistic interview question text",
  "topic": "Domain or skill topic name (e.g. System Design, REST APIs, STAR Behavioral, Asynchronous Python)",
  "difficulty": "Beginner|Easy|Medium|Hard|Expert",
  "question_type": "technical|coding|behavioral|hr",
  "max_score": 100
}
"""
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                return self._sanitize_question_data(data, sequence_number, interview)
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Falling back to internal engine.")

        return self._generate_fallback_question(interview, sequence_number, previous_qa)

    def evaluate_answer(self, interview, question, answer_text, is_skipped=False):
        """
        Evaluate candidate's answer using the appropriate rubric.
        """
        if is_skipped or not answer_text.strip():
            return {
                "score": 0.0,
                "correctness_status": "skipped",
                "rubric_breakdown": {"completion": 0, "accuracy": 0},
                "strengths": ["Question was skipped by candidate."],
                "missing_concepts": ["No response submitted."],
                "mistakes": ["Candidate elected to skip this question."],
                "explanation": "No answer was provided for evaluation.",
                "model_answer": self._get_fallback_model_answer(question, interview),
                "improved_answer": "In an actual interview, attempt to structure whatever partial thoughts or foundational understanding you have rather than passing entirely.",
                "improvement_tips": [
                    "Even if unsure, explain your reasoning process and fundamental principles.",
                    "Clarify requirements with the interviewer before giving up.",
                    "Review core concepts related to " + question.topic + "."
                ]
            }

        if self.client and self.api_key:
            try:
                system_prompt = self.get_system_prompt(interview)
                prompt = f"""
Evaluate the candidate's answer for Question #{question.sequence_number}.

QUESTION:
{question.question_text}

TOPIC: {question.topic} | QUESTION TYPE: {question.question_type} | TARGET ROLE: {interview.target_role} at {interview.target_company}
CANDIDATE TYPE: {interview.candidate_type} (Experience: {interview.experience_years} years)

CANDIDATE'S ANSWER:
\"\"\"{answer_text}\"\"\"

RUBRIC GUIDELINES:
- For Technical: Correctness (40), Conceptual Understanding (25), Completeness (15), Reasoning (10), Practical Examples (10).
- For Coding: Algorithmic Logic (30), Correctness (25), Edge Cases (15), Code Quality (10), Time & Space Complexity (20).
- For HR / Behavioral: Relevance (30), Clarity (25), Structure/STAR Method (20), Reasoning (15), Personal Impact & Metrics (10).

Instructions:
- Provide an honest, constructive score between 0 and 100.
- Determine correctness_status: 'correct' (>= 80), 'partially_correct' (40 - 79), or 'incorrect' (< 40).
- Give concrete strengths, specific missing concepts, mistakes (if any), a model answer, an improved version of the candidate's answer, and actionable tips.
- Do NOT make assumptions about honesty or hiring promises.

Return ONLY a valid JSON object matching this schema:
{{
  "score": 85.0,
  "correctness_status": "correct|partially_correct|incorrect",
  "rubric_breakdown": {{
     "correctness_or_logic": 35,
     "understanding_or_clarity": 22,
     "completeness_or_structure": 13,
     "reasoning": 8,
     "examples_or_complexity": 7
  }},
  "strengths": ["point 1", "point 2"],
  "missing_concepts": ["concept 1", "concept 2"],
  "mistakes": ["identified mistake or minor omission"],
  "explanation": "Detailed summary explaining the score and reasoning.",
  "model_answer": "A polished, benchmark professional response demonstrating master-level competency.",
  "improved_answer": "The candidate's own response restructured with better terminology and stronger examples.",
  "improvement_tips": ["Actionable tip 1", "Actionable tip 2", "Actionable tip 3"]
}}
"""
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.4
                )
                content = response.choices[0].message.content
                data = json.loads(content)
                return self._sanitize_evaluation_data(data)
            except Exception as e:
                logger.warning(f"OpenAI answer evaluation failed: {e}. Falling back to internal rubric evaluator.")

        return self._evaluate_answer_fallback(interview, question, answer_text)

    def _sanitize_question_data(self, data, sequence_number, interview):
        q_text = data.get("question_text", "").strip() or f"Describe your approach to designing scalable solutions in {interview.target_role}."
        topic = data.get("topic", "").strip() or "Core Competency"
        diff = data.get("difficulty", interview.difficulty)
        q_type = data.get("question_type", "technical")
        if q_type not in ["technical", "coding", "behavioral", "hr"]:
            q_type = "technical"
        return {
            "sequence_number": sequence_number,
            "question_text": q_text,
            "topic": topic,
            "difficulty": diff,
            "question_type": q_type,
            "max_score": 100.0
        }

    def _sanitize_evaluation_data(self, data):
        score = float(data.get("score", 70.0))
        score = max(0.0, min(100.0, score))
        status = data.get("correctness_status", "partially_correct")
        if score >= 80:
            status = "correct"
        elif score >= 40:
            status = "partially_correct"
        else:
            status = "incorrect"

        return {
            "score": round(score, 1),
            "correctness_status": status,
            "rubric_breakdown": data.get("rubric_breakdown", {"accuracy": int(score * 0.6), "depth": int(score * 0.4)}),
            "strengths": data.get("strengths") or ["Communicated clearly and addressed the core subject."],
            "missing_concepts": data.get("missing_concepts") or ["Could detail production edge cases and error recovery."],
            "mistakes": data.get("mistakes") or ["Minor lack of specificity regarding implementation."],
            "explanation": data.get("explanation") or "The answer demonstrates a solid grasp of foundational principles with room for deeper structural clarity.",
            "model_answer": data.get("model_answer") or "An ideal response articulates core architecture, performance trade-offs, and concrete industry best practices.",
            "improved_answer": data.get("improved_answer") or "By using the STAR framework or architectural diagrams, this response becomes significantly more impactful.",
            "improvement_tips": data.get("improvement_tips") or ["Highlight practical real-world trade-offs", "Quantify results where possible", "Structure points with clear headings"]
        }

    def _generate_fallback_question(self, interview, sequence_number, previous_qa=None):
        """
        High-quality curated question generator tailored to candidate profile, target role, and interview type.
        """
        role = interview.target_role.lower()
        skills = [s.strip() for s in interview.technical_skills.split(",") if s.strip()]
        first_skill = skills[0] if skills else "software engineering"
        itype = interview.interview_type.lower()
        cand_type = interview.candidate_type.lower()
        company = interview.target_company

        # Curate question bank by type
        technical_bank = [
            {
                "topic": f"{first_skill.title()} Architecture",
                "difficulty": interview.difficulty,
                "question_type": "technical",
                "question_text": f"How do you approach modular architecture and state management when building applications with {first_skill}? What trade-offs do you consider between simplicity and maintainability for {company}?"
            },
            {
                "topic": "API Design & Concurrency",
                "difficulty": interview.difficulty,
                "question_type": "technical",
                "question_text": f"Explain how you design resilient RESTful or GraphQL APIs that handle high concurrency, caching, and rate limiting in a production deployment at {company}."
            },
            {
                "topic": "Database Optimization & Transactions",
                "difficulty": interview.difficulty,
                "question_type": "technical",
                "question_text": "Describe the differences between optimistic and pessimistic locking in relational databases. How would you diagnose and resolve a severe slow-query bottleneck under heavy write loads?"
            },
            {
                "topic": "System Reliability & Observability",
                "difficulty": interview.difficulty,
                "question_type": "technical",
                "question_text": "Walk me through how you set up end-to-end observability (metrics, tracing, logging) and circuit breakers to prevent cascading service failures in microservices."
            },
            {
                "topic": "Security & Authentication",
                "difficulty": interview.difficulty,
                "question_type": "technical",
                "question_text": "What strategies do you enforce to safeguard against CSRF, SSRF, and SQL injection? How would you design a secure token-refresh mechanism using OAuth2 / JWT?"
            }
        ]

        coding_bank = [
            {
                "topic": "Algorithmic Problem Solving",
                "difficulty": interview.difficulty,
                "question_type": "coding",
                "question_text": f"Given an unsorted array of integers, write an optimal algorithm in {interview.programming_languages or 'Python/JavaScript'} to find the contiguous subarray that has the largest sum (Kadane's Algorithm). Explain its time and space complexity."
            },
            {
                "topic": "Data Structures & Two Pointers",
                "difficulty": interview.difficulty,
                "question_type": "coding",
                "question_text": f"Design and implement a function to detect whether a directed graph contains a cycle. What data structures will you use, and how do you handle disconnected components?"
            },
            {
                "topic": "Dynamic Programming & Optimization",
                "difficulty": interview.difficulty,
                "question_type": "coding",
                "question_text": "Write a clean function to solve the Longest Substring Without Repeating Characters problem. Provide step-by-step logic, edge cases handled, and asymptotic complexity."
            },
            {
                "topic": "String & Hash Table Logic",
                "difficulty": interview.difficulty,
                "question_type": "coding",
                "question_text": f"Implement an LRU (Least Recently Used) Cache with O(1) get and put operations. Outline the data structures required and provide sample pseudocode or implementation."
            }
        ]

        behavioral_bank = [
            {
                "topic": "Conflict Resolution & Teamwork",
                "difficulty": "Medium",
                "question_type": "behavioral",
                "question_text": f"Tell me about a time when you strongly disagreed with a senior engineer or product manager's technical decision. How did you communicate your perspective, and what was the eventual outcome?"
            },
            {
                "topic": "Prioritization & Deadlines",
                "difficulty": "Medium",
                "question_type": "behavioral",
                "question_text": f"Describe a high-stakes scenario where project requirements changed drastically days before a major release. How did you re-prioritize deliverables while maintaining code quality?"
            },
            {
                "topic": "Failure & Continuous Learning",
                "difficulty": "Medium",
                "question_type": "behavioral",
                "question_text": "Describe a production incident or bug you inadvertently introduced. How did you triage the issue, communicate with stakeholders, and institute post-mortem preventative measures?"
            },
            {
                "topic": "Initiative & Ownership",
                "difficulty": "Medium",
                "question_type": "behavioral",
                "question_text": f"Can you give an example of a technical debt or process inefficiency that was nobody's explicit responsibility, but you chose to take ownership and resolve it for your team?"
            }
        ]

        hr_bank = [
            {
                "topic": "Professional Background & Value Proposition",
                "difficulty": "Easy",
                "question_type": "hr",
                "question_text": f"Walk me through your background. What motivated you to apply for the {interview.target_role} position at {company}, and what distinctive strengths do you bring to our team?"
            },
            {
                "topic": "Career Goals & Growth Alignment",
                "difficulty": "Medium",
                "question_type": "hr",
                "question_text": f"Where do you envision your professional growth over the next 3 to 5 years, and how does contributing to {company}'s roadmap align with that vision?"
            },
            {
                "topic": "Working Under Pressure & Work Culture",
                "difficulty": "Medium",
                "question_type": "hr",
                "question_text": "What type of engineering management style and team culture empowers you to do your best work? How do you prevent burnout when working across rapid iterative release cycles?"
            }
        ]

        # Select pool based on interview_type
        if "coding" in itype:
            pool = coding_bank
        elif "hr" in itype and "technical" not in itype:
            pool = hr_bank + behavioral_bank
        elif "behavioral" in itype:
            pool = behavioral_bank
        elif "technical + hr" in itype:
            pool = [technical_bank[0], hr_bank[0], technical_bank[1], behavioral_bank[0], technical_bank[2]]
        else:
            pool = technical_bank + behavioral_bank

        idx = (sequence_number - 1) % len(pool)
        selected = pool[idx]

        return {
            "sequence_number": sequence_number,
            "question_text": selected["question_text"],
            "topic": selected["topic"],
            "difficulty": selected["difficulty"],
            "question_type": selected["question_type"],
            "max_score": 100.0
        }

    def _evaluate_answer_fallback(self, interview, question, answer_text):
        """
        Algorithmic rule-based evaluation when OpenAI client is offline or unavailable.
        Evaluates length, keyword relevance, structure, technical jargon, and reasoning.
        """
        words = re.findall(r"\w+", answer_text)
        word_count = len(words)
        
        # Analyze content characteristics
        has_examples = any(kw in answer_text.lower() for kw in ["for example", "such as", "specifically", "in my previous", "we used", "i implemented", "instance"])
        has_technical_reasoning = any(kw in answer_text.lower() for kw in ["because", "trade-off", "tradeoff", "complexity", "scalability", "latency", "architecture", "performance", "pattern", "efficiency", "security"])
        has_structure = ("1." in answer_text or "-" in answer_text or "firstly" in answer_text.lower() or "\n" in answer_text)
        
        # Base scoring
        score = 45.0
        if word_count > 30:
            score += 15
        if word_count > 70:
            score += 10
        if word_count > 120:
            score += 5
        if has_examples:
            score += 10
        if has_technical_reasoning:
            score += 10
        if has_structure:
            score += 5
            
        score = min(95.0, max(25.0, score))
        
        status = "correct" if score >= 80 else ("partially_correct" if score >= 50 else "incorrect")
        
        strengths = []
        if word_count >= 50:
            strengths.append("Provided a substantive answer with clear contextual explanations.")
        else:
            strengths.append("Directly addressed the question without unnecessary padding.")
        if has_technical_reasoning:
            strengths.append("Demonstrated good technical vocabulary and consideration of engineering trade-offs.")
        if has_examples:
            strengths.append("Supported points with practical references or situational examples.")
        if not strengths:
            strengths.append("Acknowledged key question requirements.")

        missing_concepts = []
        if not has_examples:
            missing_concepts.append("Concrete production examples or real-world project context.")
        if not has_technical_reasoning:
            missing_concepts.append("Explicit mention of trade-offs, edge cases, and failure recovery modes.")
        if word_count < 60:
            missing_concepts.append("Deeper technical exploration of underlying internal mechanisms.")
        if not missing_concepts:
            missing_concepts.append("Benchmarking metrics and automated verification strategies.")

        mistakes = []
        if word_count < 30:
            mistakes.append("Answer was somewhat brief for a rigorous senior interview setting.")
        else:
            mistakes.append("Could more sharply distinguish between high-level theory and implementation details.")

        explanation = (
            f"The candidate achieved a score of {score:.1f}/100. The response showed "
            f"{'strong' if score >= 80 else 'promising'} alignment with the core requirements of '{question.topic}'. "
            f"Key strengths included conceptual familiarity, while elevating the response with deeper metric-driven results and edge case analysis would maximize interview impact."
        )

        model_answer = self._get_fallback_model_answer(question, interview)
        improved_answer = (
            f"\"To address this effectively for {interview.target_company}: First, I establish the foundational requirement and constraints. "
            f"Next, I select the appropriate pattern—analyzing trade-offs between latency and throughput. "
            f"In practice, {answer_text.strip()} By incorporating automated telemetry and comprehensive unit tests, we guarantee robust operational stability.\""
        )

        tips = [
            f"When answering questions on {question.topic}, frame your response around: Problem -> Architectural Decision -> Trade-off -> Measurable Result.",
            "Explicitly mention edge cases such as network timeouts, high concurrency, or malformed data.",
            f"Tailor your response specifically to {interview.target_company}'s scale and product priorities."
        ]

        rubric = {
            "correctness_or_logic": round(score * 0.35, 1),
            "understanding_or_clarity": round(score * 0.25, 1),
            "completeness_or_structure": round(score * 0.20, 1),
            "reasoning": round(score * 0.10, 1),
            "examples_or_complexity": round(score * 0.10, 1)
        }

        return {
            "score": round(score, 1),
            "correctness_status": status,
            "rubric_breakdown": rubric,
            "strengths": strengths,
            "missing_concepts": missing_concepts,
            "mistakes": mistakes,
            "explanation": explanation,
            "model_answer": model_answer,
            "improved_answer": improved_answer,
            "improvement_tips": tips
        }

    def _get_fallback_model_answer(self, question, interview):
        return (
            f"A high-impact response for '{question.topic}' begins by defining the core challenge, outlining the target system constraints, "
            f"and presenting a structured solution. For {interview.target_role} at {interview.target_company}, a benchmark answer "
            f"demonstrates mastery of system boundaries, data integrity, time/space trade-offs, and operational telemetry. "
            f"It directly illustrates real-world problem-solving using measurable outcomes and clear architectural boundaries."
        )

ai_service = AIService()
