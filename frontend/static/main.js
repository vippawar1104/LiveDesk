// --- Main Application Logic ---

const statusDiv = document.getElementById("status");
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const sessionEndSection = document.getElementById("session-end-section");
const restartBtn = document.getElementById("restartBtn");
const micBtn = document.getElementById("micBtn");
const cameraBtn = document.getElementById("cameraBtn");
const screenBtn = document.getElementById("screenBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const videoPreview = document.getElementById("video-preview");
const videoPlaceholder = document.getElementById("video-placeholder");
const connectBtn = document.getElementById("connectBtn");
const connectBtnNav = document.getElementById("connectBtnNav");
const connectBtnLaunch = document.getElementById("connectBtnLaunch");
const feedbackBtn = document.getElementById("feedbackBtn");
const feedbackBtnHero = document.getElementById("feedbackBtnHero");
const feedbackModal = document.getElementById("feedbackModal");
const modelSelect = document.getElementById("modelSelect");
const voiceSelect = document.getElementById("voiceSelect");
const activeModelPill = document.getElementById("activeModelPill");
const activeVoicePill = document.getElementById("activeVoicePill");

const MODEL_LABELS = {
  "gemini-3.1-flash-live-preview": "Gemini 3.1 Flash Live Preview",
  "gemini-2.5-flash-native-audio-preview-12-2025": "Gemini 2.5 Flash Live Preview",
};

const VOICE_LABELS = {
  Puck: "Puck",
  Kore: "Kore",
  Charon: "Charon",
  Aoede: "Aoede",
  Fenrir: "Fenrir",
  Leda: "Leda",
};

function setConnectButtonsDisabled(disabled) {
  [connectBtn, connectBtnNav, connectBtnLaunch].forEach((btn) => {
    if (btn) btn.disabled = disabled;
  });
}

function getSelectedModel() {
  return modelSelect?.value || "gemini-3.1-flash-live-preview";
}

function getSelectedModelLabel() {
  return MODEL_LABELS[getSelectedModel()] || getSelectedModel();
}

function getSelectedVoice() {
  return voiceSelect?.value || "Puck";
}

function getSelectedVoiceLabel() {
  return VOICE_LABELS[getSelectedVoice()] || getSelectedVoice();
}

function setSessionSelectsDisabled(disabled) {
  if (modelSelect) modelSelect.disabled = disabled;
  if (voiceSelect) voiceSelect.disabled = disabled;
}

function updateSessionMetaPills() {
  if (activeModelPill) {
    activeModelPill.textContent = `Model: ${getSelectedModelLabel()}`;
  }
  if (activeVoicePill) {
    activeVoicePill.textContent = `Voice: ${getSelectedVoiceLabel()}`;
  }
}

const feedbackForm = document.getElementById("feedbackForm");
const feedbackName = document.getElementById("feedbackName");
const feedbackEmail = document.getElementById("feedbackEmail");
const feedbackRating = document.getElementById("feedbackRating");
const feedbackMessage = document.getElementById("feedbackMessage");
const closeFeedbackBtn = document.getElementById("closeFeedbackBtn");
const cancelFeedbackBtn = document.getElementById("cancelFeedbackBtn");
const chatLog = document.getElementById("chat-log");
const noticeBanner = document.getElementById("noticeBanner");
const emptyState = document.getElementById("emptyState");

let currentGeminiMessageDiv = null;
let currentUserMessageDiv = null;

function setNotice(message, type = "neutral") {
  noticeBanner.textContent = message;
  noticeBanner.className = `notice-banner ${type}`;
}

function updateEmptyState() {
  emptyState.classList.toggle("hidden", chatLog.children.length > 0);
}

function resetConversationState() {
  currentGeminiMessageDiv = null;
  currentUserMessageDiv = null;
  chatLog.innerHTML = "";
  updateEmptyState();
}

function openFeedbackModal() {
  feedbackModal.classList.remove("hidden");
  feedbackMessage.focus();
}

function closeFeedbackModal() {
  feedbackModal.classList.add("hidden");
  feedbackForm.reset();
}

function setWorkspaceControls(isConnected) {
  disconnectBtn.disabled = !isConnected;
  textInput.disabled = !isConnected;
  sendBtn.disabled = !isConnected;
  cameraBtn.disabled = !isConnected;
  screenBtn.disabled = !isConnected;
}

function resetSessionControls() {
  micBtn.textContent = "Start Mic";
  cameraBtn.textContent = "Start Camera";
  screenBtn.textContent = "Share Screen";
}

const mediaHandler = new MediaHandler();
const geminiClient = new GeminiClient({
  onOpen: () => {
    statusDiv.textContent = "Connected";
    statusDiv.className = "status connected";
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    setWorkspaceControls(true);
    setSessionSelectsDisabled(true);
    updateSessionMetaPills();
    setNotice(
      `Live session connected with ${getSelectedModelLabel()} and ${getSelectedVoiceLabel()} voice. You can speak, type, or share visuals.`,
      "success",
    );
    textInput.focus();

    geminiClient.sendText(
      `Introduce yourself as Live Desk in one short sentence.
       Mention that you can help through voice, typing, camera, or screen sharing.
       Mention that you can continue in the user's preferred language.
       Ask what they want help with next.`,
    );
  },
  onMessage: (event) => {
    if (typeof event.data === "string") {
      try {
        const msg = JSON.parse(event.data);
        handleJsonMessage(msg);
      } catch (e) {
        console.error("Parse error:", e);
      }
    } else {
      mediaHandler.playAudio(event.data);
    }
  },
  onClose: (e) => {
    console.log("WS Closed:", e);
    mediaHandler.stopAudioPlayback();
    if (statusDiv.classList.contains("error")) {
      setConnectButtonsDisabled(false);
      setWorkspaceControls(false);
      setSessionSelectsDisabled(false);
      return;
    }
    statusDiv.textContent = "Disconnected";
    statusDiv.className = "status disconnected";
    setNotice(
      "Session ended. Start a new session when you are ready.",
      "neutral",
    );
    setWorkspaceControls(false);
    setSessionSelectsDisabled(false);
    showSessionEnd();
  },
  onError: (e) => {
    console.error("WS Error:", e);
    statusDiv.textContent = "Connection Error";
    statusDiv.className = "status error";
    setNotice("Connection error. Check the backend and try again.", "error");
  },
});

function handleJsonMessage(msg) {
  if (msg.type === "error") {
    statusDiv.textContent = msg.error || "Session error";
    statusDiv.className = "status error";
    setConnectButtonsDisabled(false);
    setSessionSelectsDisabled(false);
    setNotice(msg.error || "Session error", "error");
  } else if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
    setNotice("The assistant stopped its previous response.", "neutral");
  } else if (msg.type === "turn_complete") {
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
  } else if (msg.type === "user") {
    if (currentUserMessageDiv) {
      currentUserMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentUserMessageDiv = appendMessage("user", msg.text);
    }
  } else if (msg.type === "gemini") {
    if (currentGeminiMessageDiv) {
      currentGeminiMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentGeminiMessageDiv = appendMessage("gemini", msg.text);
    }
  }
}

function appendMessage(type, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${type}`;
  msgDiv.textContent = text;
  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
  updateEmptyState();
  return msgDiv;
}

async function startMicCapture() {
  try {
    if (mediaHandler.isRecording) {
      return true;
    }
    await mediaHandler.startAudio((data) => {
      if (geminiClient.isConnected()) {
        geminiClient.send(data);
      }
    });
    micBtn.textContent = "Stop Mic";
    setNotice("Microphone is live.", "success");
    return true;
  } catch (e) {
    setNotice("Microphone access is required to start the session.", "error");
    return false;
  }
}

async function connectSession() {
  resetConversationState();
  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
  videoPlaceholder.classList.remove("hidden");
  resetSessionControls();

  statusDiv.textContent = "Connecting...";
  setConnectButtonsDisabled(true);
  setSessionSelectsDisabled(true);
  updateSessionMetaPills();
  setNotice("Requesting microphone access and opening session...", "neutral");

  try {
    // Initialize audio context on user gesture
    await mediaHandler.initializeAudio();

    const micStarted = await startMicCapture();
    if (!micStarted) {
      statusDiv.textContent = "Microphone access required";
      statusDiv.className = "status error";
      setConnectButtonsDisabled(false);
      setSessionSelectsDisabled(false);
      return;
    }

    geminiClient.connect(getSelectedModel(), getSelectedVoice());
  } catch (error) {
    console.error("Connection error:", error);
    statusDiv.textContent = "Connection Failed: " + error.message;
    statusDiv.className = "status error";
    mediaHandler.stopAudio();
    resetSessionControls();
    setConnectButtonsDisabled(false);
    setSessionSelectsDisabled(false);
    setNotice(
      "Connection failed. Check the backend server and retry.",
      "error",
    );
  }
}

// Wire up all connect buttons
connectBtn.onclick = () => connectSession();
if (connectBtnNav) connectBtnNav.onclick = () => connectSession();
if (connectBtnLaunch) connectBtnLaunch.onclick = () => connectSession();

// Feedback buttons
feedbackBtn.onclick = openFeedbackModal;
if (feedbackBtnHero) feedbackBtnHero.onclick = openFeedbackModal;
closeFeedbackBtn.onclick = closeFeedbackModal;
cancelFeedbackBtn.onclick = closeFeedbackModal;
feedbackForm.onsubmit = submitFeedback;

feedbackModal.addEventListener("click", (event) => {
  if (event.target?.dataset?.closeFeedback !== undefined) {
    closeFeedbackModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !feedbackModal.classList.contains("hidden")) {
    closeFeedbackModal();
  }
});

// Smooth scroll for nav links
document.querySelectorAll('.navbar-links a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (e) => {
    e.preventDefault();
    const target = document.querySelector(anchor.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

// UI Controls
disconnectBtn.onclick = () => {
  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
  videoPlaceholder.classList.remove("hidden");
  resetSessionControls();
  setNotice("Disconnecting session...", "neutral");
  geminiClient.disconnect();
};

micBtn.onclick = async () => {
  if (mediaHandler.isRecording) {
    mediaHandler.stopAudio();
    micBtn.textContent = "Start Mic";
    setNotice("Microphone paused.", "neutral");
  } else {
    await startMicCapture();
  }
};

cameraBtn.onclick = async () => {
  if (cameraBtn.textContent === "Stop Camera") {
    mediaHandler.stopVideo(videoPreview);
    cameraBtn.textContent = "Start Camera";
    screenBtn.textContent = "Share Screen";
    videoPlaceholder.classList.remove("hidden");
    setNotice("Camera stopped.", "neutral");
  } else {
    // If another stream is active (e.g. Screen), stop it first
    if (mediaHandler.videoStream) {
      mediaHandler.stopVideo(videoPreview);
      screenBtn.textContent = "Share Screen";
    }

    try {
      await mediaHandler.startVideo(videoPreview, (base64Data) => {
        if (geminiClient.isConnected()) {
          geminiClient.sendImage(base64Data);
        }
      });
      cameraBtn.textContent = "Stop Camera";
      screenBtn.textContent = "Share Screen";
      videoPlaceholder.classList.add("hidden");
      setNotice("Camera is live.", "success");
    } catch (e) {
      setNotice("Camera access was denied or unavailable.", "error");
    }
  }
};

screenBtn.onclick = async () => {
  if (screenBtn.textContent === "Stop Sharing") {
    mediaHandler.stopVideo(videoPreview);
    screenBtn.textContent = "Share Screen";
    cameraBtn.textContent = "Start Camera";
    videoPlaceholder.classList.remove("hidden");
    setNotice("Screen sharing stopped.", "neutral");
  } else {
    // If another stream is active (e.g. Camera), stop it first
    if (mediaHandler.videoStream) {
      mediaHandler.stopVideo(videoPreview);
      cameraBtn.textContent = "Start Camera";
    }

    try {
      await mediaHandler.startScreen(
        videoPreview,
        (base64Data) => {
          if (geminiClient.isConnected()) {
            geminiClient.sendImage(base64Data);
          }
        },
        () => {
          // onEnded callback (e.g. user stopped sharing from browser)
          screenBtn.textContent = "Share Screen";
          videoPlaceholder.classList.remove("hidden");
          setNotice("Screen sharing stopped.", "neutral");
        },
      );
      screenBtn.textContent = "Stop Sharing";
      cameraBtn.textContent = "Start Camera";
      videoPlaceholder.classList.add("hidden");
      setNotice("Screen sharing is live.", "success");
    } catch (e) {
      setNotice("Screen sharing was cancelled or unavailable.", "error");
    }
  }
};

sendBtn.onclick = sendText;
textInput.onkeypress = (e) => {
  if (e.key === "Enter") sendText();
};

function sendText() {
  const text = textInput.value.trim();
  if (text && geminiClient.isConnected()) {
    geminiClient.sendText(text);
    appendMessage("user", text);
    textInput.value = "";
    setNotice("Message sent.", "neutral");
  }
}

function resetUI() {
  authSection.classList.remove("hidden");
  appSection.classList.add("hidden");
  sessionEndSection.classList.add("hidden");

  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
  videoPlaceholder.classList.remove("hidden");

  resetSessionControls();
  resetConversationState();
  setConnectButtonsDisabled(false);
  setSessionSelectsDisabled(false);
  setWorkspaceControls(false);
  updateSessionMetaPills();
  setNotice("Connect to begin a live session.", "neutral");
}

function showSessionEnd() {
  appSection.classList.add("hidden");
  sessionEndSection.classList.remove("hidden");
  mediaHandler.stopAudioPlayback();
  mediaHandler.stopAudio();
  mediaHandler.stopVideo(videoPreview);
}

async function submitFeedback(event) {
  event.preventDefault();
  const message = feedbackMessage.value.trim();
  if (!message) {
    setNotice("Feedback message is required.", "error");
    feedbackMessage.focus();
    return;
  }

  const submitBtn = feedbackForm.querySelector('button[type="submit"]');
  submitBtn.disabled = true;

  try {
    const response = await fetch("/api/feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        name: feedbackName.value.trim() || null,
        email: feedbackEmail.value.trim() || null,
        rating: feedbackRating.value ? Number(feedbackRating.value) : null,
        message,
        page: window.location.pathname,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Unable to submit feedback");
    }

    closeFeedbackModal();
    setNotice("Feedback saved. Thank you.", "success");
  } catch (error) {
    setNotice(error.message || "Unable to submit feedback.", "error");
  } finally {
    submitBtn.disabled = false;
  }
}

restartBtn.onclick = () => {
  resetUI();
};

setWorkspaceControls(false);
updateEmptyState();
updateSessionMetaPills();
