// Live Interview Logic Controller

class InterviewController {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.currentQuestion = null;
        this.totalQuestions = 5;
        this.isSubmitting = false;

        this.initDOMElements();
        this.bindEvents();
        this.loadCurrentQuestion();
    }

    initDOMElements() {
        this.questionSeqEl = document.getElementById('currentSeqText');
        this.totalSeqEl = document.getElementById('totalQuestionsText');
        this.questionTextEl = document.getElementById('questionContentText');
        this.questionTopicEl = document.getElementById('questionTopicBadge');
        this.progressFillEl = document.getElementById('interviewProgressFill');
        this.progressPercentEl = document.getElementById('progressPercentText');

        this.answerTextEl = document.getElementById('answerText');
        this.submitBtn = document.getElementById('submitAnswerBtn');
        this.skipBtn = document.getElementById('skipQuestionBtn');
        this.endInterviewBtn = document.getElementById('endInterviewBtn');
        this.retryBanner = document.getElementById('retryBanner');
        this.submittingOverlay = document.getElementById('submittingOverlay');

        // Audio controls
        this.readAloudBtn = document.getElementById('readAloudBtn');
        this.stopAudioBtn = document.getElementById('stopAudioBtn');
        this.toggleVoiceQuestionsBtn = document.getElementById('toggleVoiceQuestionsBtn');

        // Code mode switch
        this.modeTextBtn = document.getElementById('modeTextBtn');
        this.modeCodeBtn = document.getElementById('modeCodeBtn');
    }

    bindEvents() {
        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', () => this.submitAnswer());
        }
        if (this.skipBtn) {
            this.skipBtn.addEventListener('click', () => this.skipQuestion());
        }
        if (this.endInterviewBtn) {
            this.endInterviewBtn.addEventListener('click', () => this.endInterviewEarly());
        }

        // Audio buttons
        if (this.readAloudBtn) {
            this.readAloudBtn.addEventListener('click', () => {
                if (this.currentQuestion) {
                    window.audioCameraManager.speak(this.currentQuestion.question_text);
                }
            });
        }
        if (this.stopAudioBtn) {
            this.stopAudioBtn.addEventListener('click', () => {
                window.audioCameraManager.stopSpeech();
            });
        }
        if (this.toggleVoiceQuestionsBtn) {
            this.toggleVoiceQuestionsBtn.addEventListener('click', () => {
                const enabled = window.audioCameraManager.toggleVoiceQuestions();
                this.toggleVoiceQuestionsBtn.innerHTML = enabled
                    ? '<i class="fa-solid fa-volume-high"></i> Voice Questions: ON'
                    : '<i class="fa-solid fa-volume-xmark"></i> Voice Questions: OFF';
                this.toggleVoiceQuestionsBtn.classList.toggle('active', enabled);
            });
        }

        // Camera toggle
        const cameraBtn = document.getElementById('cameraToggleBtn');
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => {
                window.audioCameraManager.toggleCamera();
            });
        }

        // Microphone toggle
        const micBtn = document.getElementById('micToggleBtn');
        if (micBtn) {
            micBtn.addEventListener('click', () => {
                window.audioCameraManager.toggleMicrophone();
            });
        }

        // Text / Code Mode
        if (this.modeTextBtn && this.modeCodeBtn && this.answerTextEl) {
            this.modeTextBtn.addEventListener('click', () => {
                this.modeTextBtn.classList.add('active');
                this.modeCodeBtn.classList.remove('active');
                this.answerTextEl.classList.remove('code-font');
                this.answerTextEl.setAttribute('placeholder', 'Type or dictate your structured professional answer here...');
            });

            this.modeCodeBtn.addEventListener('click', () => {
                this.modeCodeBtn.classList.add('active');
                this.modeTextBtn.classList.remove('active');
                this.answerTextEl.classList.add('code-font');
                this.answerTextEl.setAttribute('placeholder', '// Write your code solution, algorithm logic, and edge cases here...\n\nfunction solution() {\n    \n}');
            });
        }

        // Clean up on leave
        window.addEventListener('beforeunload', () => {
            window.audioCameraManager.cleanup();
        });
    }

    async loadCurrentQuestion() {
        try {
            this.hideRetryBanner();
            const res = await window.apiFetch(`/api/interviews/${this.sessionId}/question`);
            if (!res.ok) throw new Error("Failed to load question.");
            const data = await res.json();

            if (data.completed) {
                window.location.href = data.redirect_url;
                return;
            }

            this.currentQuestion = data.question;
            this.totalQuestions = data.total_questions;
            this.renderQuestion();
        } catch (err) {
            console.error("Error loading question:", err);
            this.showRetryBanner("Could not load the question. Please check connection and retry.", () => this.loadCurrentQuestion());
        }
    }

    renderQuestion() {
        if (!this.currentQuestion) return;

        const seq = this.currentQuestion.sequence_number;
        const total = this.totalQuestions;

        if (this.questionSeqEl) this.questionSeqEl.textContent = seq;
        if (this.totalSeqEl) this.totalSeqEl.textContent = total;
        if (this.questionTopicEl) this.questionTopicEl.textContent = this.currentQuestion.topic || 'General';
        if (this.questionTextEl) this.questionTextEl.textContent = this.currentQuestion.question_text;

        // Update progress
        const percent = Math.round(((seq - 1) / total) * 100);
        if (this.progressFillEl) this.progressFillEl.style.width = `${percent}%`;
        if (this.progressPercentEl) this.progressPercentEl.textContent = `${percent}% Completed`;

        // Clear answer box
        if (this.answerTextEl) {
            this.answerTextEl.value = '';
        }

        // Automatically speak if voice is enabled
        window.audioCameraManager.speak(this.currentQuestion.question_text);
    }

    async submitAnswer() {
        if (this.isSubmitting || !this.currentQuestion) return;

        const answerText = this.answerTextEl ? this.answerTextEl.value.trim() : '';
        if (!answerText) {
            if (!confirm("Your answer is blank. Would you like to skip this question instead, or write your thoughts first?")) {
                return;
            }
            return this.skipQuestion();
        }

        this.setSubmittingState(true, "AI is evaluating your response against industry rubrics...");
        this.hideRetryBanner();

        try {
            const res = await window.apiFetch(`/api/interviews/${this.sessionId}/answer`, {
                method: 'POST',
                body: JSON.stringify({
                    question_id: this.currentQuestion.id,
                    answer_text: answerText
                })
            });

            if (!res.ok) {
                throw new Error("Evaluation request failed.");
            }

            const data = await res.json();
            this.setSubmittingState(false);

            if (data.is_last || data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                // Advance to next question
                await this.loadCurrentQuestion();
            }
        } catch (err) {
            console.error("Answer submission failed:", err);
            this.setSubmittingState(false);
            this.showRetryBanner("Evaluation connection error. Your answer has been saved in the editor. Click retry to submit again.", () => this.submitAnswer());
        }
    }

    async skipQuestion() {
        if (this.isSubmitting || !this.currentQuestion) return;

        if (!confirm("Are you sure you want to skip this question? Skipped questions receive 0 points in the final evaluation.")) {
            return;
        }

        this.setSubmittingState(true, "Skipping question...");
        this.hideRetryBanner();

        try {
            const res = await window.apiFetch(`/api/interviews/${this.sessionId}/skip`, {
                method: 'POST',
                body: JSON.stringify({
                    question_id: this.currentQuestion.id
                })
            });

            if (!res.ok) throw new Error("Skip request failed.");
            const data = await res.json();
            this.setSubmittingState(false);

            if (data.is_last || data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                await this.loadCurrentQuestion();
            }
        } catch (err) {
            console.error("Skip failed:", err);
            this.setSubmittingState(false);
            this.showRetryBanner("Could not skip question. Please retry.", () => this.skipQuestion());
        }
    }

    async endInterviewEarly() {
        if (this.isSubmitting) return;

        if (!confirm("Are you sure you want to conclude the interview early? All completed questions will be tallied and your final performance report will be generated.")) {
            return;
        }

        this.setSubmittingState(true, "Finalizing your interview results...");
        try {
            const res = await window.apiFetch(`/api/interviews/${this.sessionId}/end`, {
                method: 'POST'
            });
            const data = await res.json();
            window.location.href = data.redirect_url;
        } catch (err) {
            console.error("End interview failed:", err);
            this.setSubmittingState(false);
            alert("Error ending interview. Please try again.");
        }
    }

    setSubmittingState(active, message = "Processing...") {
        this.isSubmitting = active;
        if (this.submitBtn) this.submitBtn.disabled = active;
        if (this.skipBtn) this.skipBtn.disabled = active;
        if (this.endInterviewBtn) this.endInterviewBtn.disabled = active;

        if (this.submittingOverlay) {
            this.submittingOverlay.style.display = active ? 'flex' : 'none';
            const msgEl = this.submittingOverlay.querySelector('.overlay-msg');
            if (msgEl) msgEl.textContent = message;
        }
    }

    showRetryBanner(message, retryCallback) {
        if (!this.retryBanner) return;
        this.retryBanner.style.display = 'flex';
        const msgText = this.retryBanner.querySelector('.retry-text');
        const retryBtn = this.retryBanner.querySelector('.retry-btn');
        if (msgText) msgText.textContent = message;
        if (retryBtn) {
            retryBtn.onclick = () => {
                this.hideRetryBanner();
                if (retryCallback) retryCallback();
            };
        }
    }

    hideRetryBanner() {
        if (this.retryBanner) {
            this.retryBanner.style.display = 'none';
        }
    }
}

window.InterviewController = InterviewController;
