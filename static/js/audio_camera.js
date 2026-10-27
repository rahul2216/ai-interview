// Speech Synthesis, Speech Recognition, and Camera Monitoring Manager

class AudioCameraManager {
    constructor() {
        // Speech Synthesis
        this.synth = window.speechSynthesis;
        this.voiceQuestionsEnabled = true;
        this.currentUtterance = null;

        // Speech Recognition
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.hasSpeechRec = !!SpeechRec;
        this.recognition = SpeechRec ? new SpeechRec() : null;
        this.isRecording = false;

        // Media Stream (Camera)
        this.cameraStream = null;
        this.isCameraActive = false;

        this.initSpeechRecognition();
    }

    initSpeechRecognition() {
        if (!this.hasSpeechRec) {
            console.warn("Web Speech Recognition API is not supported in this browser. Text input remains fully active.");
            return;
        }

        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isRecording = true;
            this.updateMicUI(true);
        };

        this.recognition.onend = () => {
            this.isRecording = false;
            this.updateMicUI(false);
        };

        this.recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            this.isRecording = false;
            this.updateMicUI(false);
            if (event.error === 'not-allowed') {
                alert("Microphone permission was denied. You can continue by typing your answer in the text box.");
            }
        };

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + ' ';
                }
            }

            if (finalTranscript) {
                const answerBox = document.getElementById('answerText');
                if (answerBox) {
                    const currentVal = answerBox.value.trim();
                    answerBox.value = currentVal ? `${currentVal} ${finalTranscript.trim()}` : finalTranscript.trim();
                    answerBox.dispatchEvent(new Event('input'));
                }
            }
        };
    }

    // Toggle Microphone
    toggleMicrophone() {
        if (!this.hasSpeechRec) {
            alert("Speech recognition is not supported on this browser. Please type your response directly.");
            return;
        }

        if (this.isRecording) {
            this.recognition.stop();
        } else {
            try {
                this.recognition.start();
            } catch (err) {
                console.warn("Recognition start conflict:", err);
            }
        }
    }

    updateMicUI(recording) {
        const micBtn = document.getElementById('micToggleBtn');
        const micStatus = document.getElementById('micStatusText');
        if (micBtn) {
            micBtn.classList.toggle('recording', recording);
            micBtn.setAttribute('title', recording ? 'Stop Microphone' : 'Start Microphone');
            const icon = micBtn.querySelector('i');
            if (icon) icon.className = recording ? 'fa-solid fa-microphone-slash' : 'fa-solid fa-microphone';
        }
        if (micStatus) {
            micStatus.textContent = recording ? 'Listening... Speak your response (auto-transcribing)' : 'Microphone ready. Click to speak.';
            micStatus.style.color = recording ? 'var(--danger)' : 'var(--text-secondary)';
        }
    }

    // Speech Synthesis
    speak(text, onEndCallback) {
        if (!this.synth) return;
        this.stopSpeech();

        if (!this.voiceQuestionsEnabled) return;

        this.currentUtterance = new SpeechSynthesisUtterance(text);
        this.currentUtterance.rate = 1.0;
        this.currentUtterance.pitch = 1.0;

        // Choose natural sounding voice if available
        const voices = this.synth.getVoices();
        const preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
        if (preferred) {
            this.currentUtterance.voice = preferred;
        }

        this.currentUtterance.onend = () => {
            this.updateAudioIndicator(false);
            if (onEndCallback) onEndCallback();
        };

        this.currentUtterance.onerror = () => {
            this.updateAudioIndicator(false);
        };

        this.updateAudioIndicator(true);
        this.synth.speak(this.currentUtterance);
    }

    stopSpeech() {
        if (this.synth) {
            this.synth.cancel();
            this.updateAudioIndicator(false);
        }
    }

    toggleVoiceQuestions() {
        this.voiceQuestionsEnabled = !this.voiceQuestionsEnabled;
        if (!this.voiceQuestionsEnabled) {
            this.stopSpeech();
        }
        return this.voiceQuestionsEnabled;
    }

    updateAudioIndicator(playing) {
        const indicator = document.getElementById('audioPlayingPill');
        if (indicator) {
            indicator.style.display = playing ? 'inline-flex' : 'none';
        }
        const playBtn = document.getElementById('readAloudBtn');
        if (playBtn) {
            const icon = playBtn.querySelector('i');
            if (icon) icon.className = playing ? 'fa-solid fa-volume-high' : 'fa-solid fa-volume-off';
        }
    }

    // Camera Management
    async startCamera() {
        try {
            const videoElem = document.getElementById('cameraVideo');
            const placeholder = document.getElementById('cameraPlaceholder');
            const toggleBtn = document.getElementById('cameraToggleBtn');
            const statusBadge = document.getElementById('cameraStatusBadge');

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 320, height: 240, facingMode: 'user' },
                audio: false
            });

            this.cameraStream = stream;
            this.isCameraActive = true;

            if (videoElem) {
                videoElem.srcObject = stream;
                videoElem.style.display = 'block';
                videoElem.play();
            }
            if (placeholder) placeholder.style.display = 'none';
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fa-solid fa-video-slash"></i> Turn Off Camera';
                toggleBtn.classList.remove('btn-primary');
                toggleBtn.classList.add('btn-secondary');
            }
            if (statusBadge) {
                statusBadge.textContent = 'Camera Active';
                statusBadge.className = 'status-badge status-correct';
            }
        } catch (err) {
            console.warn("Camera access denied or unavailable:", err);
            alert("Camera access was not granted. Camera is completely optional — you can proceed with the interview smoothly without it.");
            this.stopCamera();
        }
    }

    stopCamera() {
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
        this.isCameraActive = false;

        const videoElem = document.getElementById('cameraVideo');
        const placeholder = document.getElementById('cameraPlaceholder');
        const toggleBtn = document.getElementById('cameraToggleBtn');
        const statusBadge = document.getElementById('cameraStatusBadge');

        if (videoElem) {
            videoElem.srcObject = null;
            videoElem.style.display = 'none';
        }
        if (placeholder) placeholder.style.display = 'block';
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fa-solid fa-video"></i> Enable Camera Preview';
            toggleBtn.classList.remove('btn-secondary');
            toggleBtn.classList.add('btn-primary');
        }
        if (statusBadge) {
            statusBadge.textContent = 'Camera Off (Optional)';
            statusBadge.className = 'status-badge status-skipped';
        }
    }

    toggleCamera() {
        if (this.isCameraActive) {
            this.stopCamera();
        } else {
            this.startCamera();
        }
    }

    cleanup() {
        this.stopSpeech();
        if (this.isRecording && this.recognition) {
            this.recognition.stop();
        }
        this.stopCamera();
    }
}

window.audioCameraManager = new AudioCameraManager();
