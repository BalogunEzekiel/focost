// ==========================================================
// FOCOST AI CHAT + VOICE CLIENT
// ==========================================================
// This file intentionally keeps the existing financial-card rendering and
// chat endpoint contract intact while adding browser-native voice input/output.
// Voice is client-side: SpeechRecognition -> /ai/chat -> speechSynthesis.
//
// Backend authority remains unchanged:
// DashboardService -> AIContextService / AIService -> /ai/chat.
// This file must never calculate financial facts.

(function () {
    "use strict";

    // ----------------------------------------------------------
    // DOM HELPERS
    // ----------------------------------------------------------

    const widget = {
        root: document.getElementById("aiCoachWindow"),
        messages: document.querySelector("#aiCoachWindow #chatMessages"),
        input: document.querySelector("#aiCoachWindow #chatInput"),
        send: document.querySelector("#aiCoachWindow #sendAI"),
        voice: document.querySelector("#aiCoachWindow #voiceAI"),
        speak: document.querySelector("#aiCoachWindow #speakAI"),
        stop: document.querySelector("#aiCoachWindow #stopAI"),
        status: document.querySelector("#aiCoachWindow #voiceStatusAI"),
    };

    // The full-page AI Coach has its own controls. The global widget is
    // rendered by dashboard.html on the same page, so IDs such as
    // chatMessages can otherwise collide. Scope the page controls explicitly.
    const page = {
        root: document.querySelector(".ai-page-voice-toolbar")?.closest(".container-fluid") || null,
        messages: Array.from(document.querySelectorAll("#chatMessages"))
            .find(el => !el.closest("#aiCoachWindow")) || null,
        input: document.getElementById("question"),
        send: document.getElementById("sendBtn"),
        voice: document.getElementById("voicePageAI"),
        speak: document.getElementById("speakPageAI"),
        stop: document.getElementById("stopPageAI"),
        status: document.getElementById("voiceStatusPageAI"),
    };

    // Use only surfaces that actually exist on the current page.
    const surfaces = [widget, page].filter(surface =>
        surface.messages && surface.input && surface.send
    );

    if (!surfaces.length) {
        console.warn("FOCOST AI: no chat surface was found.");
        return;
    }

    // ----------------------------------------------------------
    // WINDOW STATE — FLOATING WIDGET
    // ----------------------------------------------------------

    const aiButton = document.getElementById("aiCoachButton");
    const aiWindow = widget.root;
    const chatHeader = document.getElementById("chatHeader");
    const minimizeBtn = document.getElementById("minimizeAI");
    const maximizeBtn = document.getElementById("maximizeAI");
    const closeBtn = document.getElementById("closeAI");

    let isDragging = false;
    let isMaximized = false;
    let isMinimized = false;
    let offsetX = 0;
    let offsetY = 0;
    let previousState = {};

    function restoreWidgetState() {
        if (!aiWindow) return;

        const savedDisplay = localStorage.getItem("ai_display");
        if (savedDisplay === "open") aiWindow.style.display = "flex";

        const savedLeft = localStorage.getItem("ai_left");
        const savedTop = localStorage.getItem("ai_top");
        if (savedLeft && savedTop) {
            aiWindow.style.left = savedLeft;
            aiWindow.style.top = savedTop;
            aiWindow.style.right = "auto";
            aiWindow.style.bottom = "auto";
        }

        const savedWidth = localStorage.getItem("ai_width");
        const savedHeight = localStorage.getItem("ai_height");
        if (savedWidth) aiWindow.style.width = savedWidth;
        if (savedHeight) aiWindow.style.height = savedHeight;

        if (localStorage.getItem("ai_minimized") === "true") {
            aiWindow.classList.add("minimized");
            isMinimized = true;
            if (minimizeBtn) minimizeBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
        }

        if (localStorage.getItem("ai_maximized") === "true") {
            aiWindow.classList.add("maximized");
            isMaximized = true;
            if (maximizeBtn) maximizeBtn.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
        }
    }

    function openWindow() {
        if (!aiWindow) return;
        aiWindow.style.display = "flex";
        localStorage.setItem("ai_display", "open");
        if (isMinimized) restoreWindow();
        widget.input?.focus();
    }

    function closeWindow() {
        if (!aiWindow) return;
        aiWindow.style.display = "none";
        localStorage.setItem("ai_display", "closed");
        if (isMinimized) restoreWindow();
    }

    function minimizeWindow() {
        if (!aiWindow) return;
        aiWindow.classList.add("minimized");
        isMinimized = true;
        if (minimizeBtn) minimizeBtn.innerHTML = '<i class="bi bi-plus-lg"></i>';
        localStorage.setItem("ai_minimized", "true");
    }

    function restoreWindow() {
        if (!aiWindow) return;
        aiWindow.classList.remove("minimized");
        isMinimized = false;
        if (minimizeBtn) minimizeBtn.innerHTML = '<i class="bi bi-dash-lg"></i>';
        localStorage.setItem("ai_minimized", "false");
    }

    function maximizeWindow() {
        if (!aiWindow || isMaximized) return;

        previousState = {
            left: aiWindow.style.left,
            top: aiWindow.style.top,
            right: aiWindow.style.right,
            bottom: aiWindow.style.bottom,
            width: aiWindow.style.width,
            height: aiWindow.style.height
        };

        aiWindow.classList.add("maximized");
        isMaximized = true;
        if (maximizeBtn) maximizeBtn.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
        localStorage.setItem("ai_maximized", "true");
    }

    function restoreMaximizedWindow() {
        if (!aiWindow) return;

        aiWindow.classList.remove("maximized");
        aiWindow.style.left = previousState.left || "";
        aiWindow.style.top = previousState.top || "";
        aiWindow.style.right = previousState.right || "";
        aiWindow.style.bottom = previousState.bottom || "";
        aiWindow.style.width = previousState.width || "";
        aiWindow.style.height = previousState.height || "";

        isMaximized = false;
        if (maximizeBtn) maximizeBtn.innerHTML = '<i class="bi bi-square"></i>';
        localStorage.setItem("ai_maximized", "false");
    }

    restoreWidgetState();

    if (aiButton && aiWindow) {
        const toggleWidget = () => {
            if (aiWindow.style.display === "flex") closeWindow();
            else openWindow();
        };

        aiButton.addEventListener("click", toggleWidget);
        aiButton.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggleWidget();
            }
        });
    }

    minimizeBtn?.addEventListener("click", () => {
        if (isMinimized) restoreWindow();
        else minimizeWindow();
    });

    closeBtn?.addEventListener("click", closeWindow);

    maximizeBtn?.addEventListener("click", () => {
        if (isMaximized) restoreMaximizedWindow();
        else maximizeWindow();
    });

    if (chatHeader && aiWindow) {
        chatHeader.addEventListener("mousedown", event => {
            if (isMaximized) return;
            isDragging = true;
            const rect = aiWindow.getBoundingClientRect();
            offsetX = event.clientX - rect.left;
            offsetY = event.clientY - rect.top;
            document.body.style.userSelect = "none";
        });

        document.addEventListener("mousemove", event => {
            if (!isDragging) return;

            aiWindow.style.left = `${event.clientX - offsetX}px`;
            aiWindow.style.top = `${event.clientY - offsetY}px`;
            aiWindow.style.right = "auto";
            aiWindow.style.bottom = "auto";
        });

        document.addEventListener("mouseup", () => {
            if (!isDragging) return;

            isDragging = false;
            document.body.style.userSelect = "";

            localStorage.setItem("ai_left", aiWindow.style.left);
            localStorage.setItem("ai_top", aiWindow.style.top);
        });
    }

    window.addEventListener("mouseup", () => {
        if (!aiWindow) return;

        localStorage.setItem("ai_width", `${aiWindow.offsetWidth}px`);
        localStorage.setItem("ai_height", `${aiWindow.offsetHeight}px`);
    });

    // ----------------------------------------------------------
    // MARKDOWN RENDERER
    // ----------------------------------------------------------

    function renderMarkdown(text) {
        if (!text) return "";

        if (typeof marked === "undefined") {
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\n/g, "<br>");
        }

        marked.setOptions({
            gfm: true,
            breaks: true
        });

        return marked.parse(text);
    }

    // ----------------------------------------------------------
    // VOICE ENGINE
    // ----------------------------------------------------------

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition ||
        null;

    const voiceState = {
        recognition: null,
        listening: false,
        activeSurface: null,
        requestId: 0,
        speechGeneration: 0,
        speaking: false,
        autoSpeak: localStorage.getItem("focost_ai_voice_output") !== "false",
        transcript: "",
        hadFinalResult: false,
        stopping: false,
    };

    function getSpeechLanguage() {
        const documentLanguage =
            document.documentElement?.lang?.trim();

        const browserLanguage =
            navigator.language?.trim();

        return documentLanguage ||
            browserLanguage ||
            "en-NG";
    }

    function setVoiceStatus(message, surface = null) {
        const targets = surface
            ? [surface]
            : surfaces;

        targets.forEach(item => {
            if (item.status) item.status.textContent = message || "";
        });
    }

    function updateVoiceButtons() {
        surfaces.forEach(surface => {
            const isActive = voiceState.activeSurface === surface && voiceState.listening;

            if (surface.voice) {
                surface.voice.classList.toggle("is-listening", isActive);
                surface.voice.classList.toggle("active", isActive);
                surface.voice.setAttribute("aria-pressed", String(isActive));

                const icon = surface.voice.querySelector("i");
                if (icon) {
                    icon.className = isActive
                        ? "bi bi-mic-fill"
                        : "bi bi-mic";
                }

                surface.voice.title = isActive
                    ? "Stop voice input"
                    : "Speak to FOCOST AI";
            }

            if (surface.speak) {
                surface.speak.classList.toggle("active", voiceState.autoSpeak);
                surface.speak.setAttribute(
                    "aria-pressed",
                    String(voiceState.autoSpeak)
                );

                const icon = surface.speak.querySelector("i");
                if (icon) {
                    icon.className = voiceState.autoSpeak
                        ? "bi bi-volume-up-fill"
                        : "bi bi-volume-mute-fill";
                }

                surface.speak.title = voiceState.autoSpeak
                    ? "Voice responses enabled"
                    : "Voice responses disabled";
            }

            if (surface.stop) {
                surface.stop.disabled = !voiceState.speaking;
            }
        });
    }

    function stopSpeaking() {
        voiceState.speechGeneration += 1;

        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }

        voiceState.speaking = false;
        updateVoiceButtons();
    }

    function cleanSpeechText(text) {
        const container = document.createElement("div");
        container.innerHTML = renderMarkdown(text || "");

        let value = container.innerText || container.textContent || "";

        // Remove common markdown remnants and excessive whitespace.
        value = value
            .replace(/```[\s\S]*?```/g, " ")
            .replace(/`([^`]+)`/g, "$1")
            .replace(/[*_#>~-]+/g, " ")
            .replace(/\s+/g, " ")
            .trim();

        return value;
    }

    function splitSpeechText(text, maxLength = 260) {
        if (text.length <= maxLength) return [text];

        const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
        const chunks = [];
        let current = "";

        sentences.forEach(sentence => {
            const candidate = `${current} ${sentence}`.trim();

            if (candidate.length <= maxLength) {
                current = candidate;
                return;
            }

            if (current) chunks.push(current);

            if (sentence.length <= maxLength) {
                current = sentence.trim();
                return;
            }

            const words = sentence.trim().split(/\s+/);
            current = "";

            words.forEach(word => {
                const next = `${current} ${word}`.trim();
                if (next.length <= maxLength) {
                    current = next;
                } else {
                    if (current) chunks.push(current);
                    current = word;
                }
            });
        });

        if (current) chunks.push(current);

        return chunks.filter(Boolean);
    }

    function speakText(text, surface = null) {
        if (!voiceState.autoSpeak || !("speechSynthesis" in window)) return;

        const cleaned = cleanSpeechText(text);
        if (!cleaned) return;

        stopSpeaking();

        const generation = voiceState.speechGeneration;
        const chunks = splitSpeechText(cleaned);
        let index = 0;

        voiceState.speaking = true;
        updateVoiceButtons();
        setVoiceStatus("Speaking…", surface);

        const speakNext = () => {
            if (
                generation !== voiceState.speechGeneration ||
                index >= chunks.length
            ) {
                if (generation === voiceState.speechGeneration) {
                    voiceState.speaking = false;
                    updateVoiceButtons();
                    setVoiceStatus("", surface);
                }
                return;
            }

            const utterance = new SpeechSynthesisUtterance(chunks[index++]);
            utterance.lang = getSpeechLanguage();
            utterance.rate = 1;
            utterance.pitch = 1;
            utterance.volume = 1;

            utterance.onend = speakNext;
            utterance.onerror = () => {
                if (generation === voiceState.speechGeneration) {
                    voiceState.speaking = false;
                    updateVoiceButtons();
                    setVoiceStatus("", surface);
                }
            };

            window.speechSynthesis.speak(utterance);
        };

        speakNext();
    }

    function stopListening() {
        if (voiceState.recognition) {
            voiceState.stopping = true;
            try {
                voiceState.recognition.stop();
            } catch (error) {
                console.debug("FOCOST AI recognition stop:", error);
            }
        }

        voiceState.listening = false;
        updateVoiceButtons();
    }

    function createRecognition(surface) {
        if (!SpeechRecognition) return null;

        const recognition = new SpeechRecognition();

        recognition.lang = getSpeechLanguage();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            voiceState.listening = true;
            voiceState.activeSurface = surface;
            voiceState.transcript = "";
            voiceState.hadFinalResult = false;
            voiceState.stopping = false;

            stopSpeaking();
            updateVoiceButtons();
            setVoiceStatus("Listening… speak naturally.", surface);
        };

        recognition.onresult = event => {
            let finalText = "";
            let interimText = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                const transcript = result[0]?.transcript || "";

                if (result.isFinal) finalText += transcript;
                else interimText += transcript;
            }

            const combined = `${finalText} ${interimText}`.trim();

            if (combined) {
                surface.input.value = combined;
                surface.input.dispatchEvent(new Event("input", { bubbles: true }));
            }

            if (finalText.trim()) {
                voiceState.transcript = finalText.trim();
                voiceState.hadFinalResult = true;
                setVoiceStatus("Processing your question…", surface);
            }
        };

        recognition.onerror = event => {
            console.warn("FOCOST AI voice input error:", event.error);

            voiceState.listening = false;
            updateVoiceButtons();

            const messages = {
                "not-allowed": "Microphone access was denied. Allow microphone permission and try again.",
                "service-not-allowed": "Speech recognition is not available for this site.",
                "no-speech": "I didn't hear anything. Please try speaking again.",
                "audio-capture": "No working microphone was detected.",
                "network": "Speech recognition could not reach the browser speech service.",
                "aborted": "Voice input stopped.",
            };

            setVoiceStatus(
                messages[event.error] || "Voice input could not be completed.",
                surface
            );
        };

        recognition.onend = async () => {
            const shouldSend =
                voiceState.hadFinalResult &&
                voiceState.transcript &&
                voiceState.activeSurface === surface &&
                !voiceState.stopping;

            voiceState.listening = false;
            voiceState.recognition = null;
            updateVoiceButtons();

            if (shouldSend) {
                setVoiceStatus("Sending…", surface);
                await sendMessage(surface);
            } else if (!voiceState.speaking) {
                setVoiceStatus("", surface);
            }
        };

        return recognition;
    }

    function startListening(surface) {
        if (!SpeechRecognition) {
            setVoiceStatus(
                "Voice input is not supported by this browser. Try a current Chrome or Edge browser.",
                surface
            );
            return;
        }

        if (voiceState.listening) {
            if (voiceState.activeSurface === surface) {
                stopListening();
            } else {
                stopListening();
                setTimeout(() => startListening(surface), 80);
            }
            return;
        }

        stopSpeaking();

        const recognition = createRecognition(surface);
        if (!recognition) return;

        voiceState.recognition = recognition;

        try {
            recognition.start();
        } catch (error) {
            console.error("FOCOST AI could not start voice input:", error);
            voiceState.recognition = null;
            voiceState.listening = false;
            updateVoiceButtons();
            setVoiceStatus("Unable to start the microphone.", surface);
        }
    }

    function toggleVoiceOutput(surface) {
        voiceState.autoSpeak = !voiceState.autoSpeak;
        localStorage.setItem(
            "focost_ai_voice_output",
            String(voiceState.autoSpeak)
        );

        if (!voiceState.autoSpeak) stopSpeaking();

        updateVoiceButtons();
        setVoiceStatus(
            voiceState.autoSpeak
                ? "Voice responses enabled."
                : "Voice responses disabled.",
            surface
        );

        window.setTimeout(() => {
            if (!voiceState.listening && !voiceState.speaking) {
                setVoiceStatus("", surface);
            }
        }, 1800);
    }

    // ----------------------------------------------------------
    // CHAT MESSAGE RENDERING
    // ----------------------------------------------------------

    function appendMessage(surface, sender, text, role, speak = false) {
        if (!surface?.messages) return;

        const row = document.createElement("div");
        row.className = role === "user"
            ? "message user"
            : "message assistant";

        const bubble = document.createElement("div");
        bubble.className = role === "user"
            ? "user-message"
            : "ai-message";

        const senderDiv = document.createElement("div");
        senderDiv.className = "message-sender";

        if (role === "assistant") {
            senderDiv.innerHTML = `
                <div class="d-flex align-items-center gap-2">
                    <strong>FOCOST AI</strong>
                    <span class="small text-success">● Online</span>
                </div>
            `;
        } else {
            senderDiv.textContent = sender || "You";
        }

        const body = document.createElement("div");
        body.className = "message-body";

        const financial = renderFinancialCards(text);

        if (financial) {
            body.innerHTML = financial;
        } else {
            body.innerHTML = renderMarkdown(text);
        }

        if (typeof hljs !== "undefined") {
            body.querySelectorAll("pre code").forEach(block => {
                try {
                    hljs.highlightElement(block);
                } catch (error) {
                    console.warn("Syntax highlighting failed:", error);
                }
            });
        }

        bubble.appendChild(senderDiv);
        bubble.appendChild(body);

        if (role === "assistant") {
            const tools = document.createElement("div");
            tools.className = "ai-message-tools";

            const speakButton = document.createElement("button");
            speakButton.type = "button";
            speakButton.className = "ai-speak-message";
            speakButton.title = "Read this response aloud";
            speakButton.setAttribute("aria-label", "Read this FOCOST AI response aloud");
            speakButton.innerHTML = '<i class="bi bi-volume-up" aria-hidden="true"></i>';

            speakButton.addEventListener("click", () => {
                speakText(text, surface);
            });

            tools.appendChild(speakButton);
            bubble.appendChild(tools);
        }

        row.appendChild(bubble);
        surface.messages.appendChild(row);
        scrollToBottom(surface);

        if (speak && role === "assistant") {
            speakText(text, surface);
        }
    }

    function scrollToBottom(surface) {
        if (surface?.messages) {
            surface.messages.scrollTop = surface.messages.scrollHeight;
        }
    }

    // ----------------------------------------------------------
    // CHAT HISTORY
    // ----------------------------------------------------------

    async function loadHistory() {
        try {
            const response = await fetch("/ai/history", {
                headers: { "Accept": "application/json" },
                credentials: "same-origin"
            });

            if (!response.ok) {
                throw new Error(`History request failed (${response.status})`);
            }

            const data = await response.json();

            surfaces.forEach(surface => {
                surface.messages.innerHTML = "";

                const firstName = data.first_name || "there";

                if (!Array.isArray(data.messages) || data.messages.length === 0) {
                    appendMessage(
                        surface,
                        "FOCOST AI",
                        `Hello **${firstName}** 👋\n**_I'm your financial coach._**\nHow can I help you with your finances today?`,
                        "assistant"
                    );
                    return;
                }

                data.messages.forEach(msg => {
                    appendMessage(
                        surface,
                        msg.sender,
                        msg.message,
                        msg.role
                    );
                });

                scrollToBottom(surface);
            });
        } catch (error) {
            console.error("Failed to load chat history:", error);

            surfaces.forEach(surface => {
                surface.messages.innerHTML = "";
                appendMessage(
                    surface,
                    "FOCOST AI",
                    "Sorry, I couldn't load your previous conversation. Please try again later.",
                    "assistant"
                );
            });
        }
    }

    // ----------------------------------------------------------
    // TYPING INDICATOR
    // ----------------------------------------------------------

    function showTyping(surface) {
        removeTyping(surface);

        const div = document.createElement("div");
        div.id = `typingIndicator-${surface === widget ? "widget" : "page"}`;
        div.className = "ai-typing";
        div.textContent = "FOCOST AI is thinking…";

        surface.messages.appendChild(div);
        scrollToBottom(surface);
    }

    function removeTyping(surface) {
        const id = `typingIndicator-${surface === widget ? "widget" : "page"}`;
        document.getElementById(id)?.remove();
    }

    // ----------------------------------------------------------
    // SEND MESSAGE
    // ----------------------------------------------------------

    async function sendMessage(surface) {
        if (!surface?.input || surface._sending) return;

        // A manual send takes precedence over an active microphone session.
        // Recognition.onend will not auto-submit after this explicit stop.
        if (voiceState.listening) {
            stopListening();
        }

        stopSpeaking();

        const question = surface.input.value.trim();
        if (!question) return;

        surface._sending = true;

        appendMessage(surface, "You", question, "user");
        surface.input.value = "";
        showTyping(surface);

        try {
            const response = await fetch("/ai/chat", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-CSRFToken":
                        document.querySelector('meta[name="csrf-token"]')?.content || ""
                },
                body: JSON.stringify({ message: question })
            });

            const contentType = response.headers.get("content-type") || "";
            let data = null;
            let rawResponse = "";

            if (contentType.includes("application/json")) {
                try {
                    data = await response.json();
                } catch (error) {
                    console.error("FOCOST AI returned invalid JSON:", error);
                }
            } else {
                try {
                    rawResponse = await response.text();
                } catch (error) {
                    console.error("Unable to read FOCOST AI response:", error);
                }
            }

            removeTyping(surface);

            if (!response.ok) {
                console.error("FOCOST AI request failed:", {
                    status: response.status,
                    statusText: response.statusText,
                    data,
                    rawResponse
                });

                const backendMessage =
                    data?.message ||
                    data?.error ||
                    (rawResponse && rawResponse.trim()) ||
                    `AI request failed (${response.status} ${response.statusText || ""})`.trim();

                appendMessage(surface, "FOCOST AI", backendMessage, "assistant");
                return;
            }

            if (data?.success) {
                const answer =
                    data.message ||
                    "FOCOST AI returned an empty response.";

                appendMessage(
                    surface,
                    "FOCOST AI",
                    answer,
                    "assistant",
                    true
                );
            } else {
                appendMessage(
                    surface,
                    "FOCOST AI",
                    data?.message ||
                        data?.error ||
                        "FOCOST AI returned an unexpected response.",
                    "assistant"
                );
            }
        } catch (error) {
            removeTyping(surface);

            console.error("FOCOST AI network/request error:", error);

            appendMessage(
                surface,
                "FOCOST AI",
                "Unable to reach the FOCOST AI service. Please check your connection and try again.",
                "assistant"
            );
        } finally {
            surface._sending = false;

            if (!voiceState.listening && !voiceState.speaking) {
                setVoiceStatus("", surface);
            }
        }
    }

    // ----------------------------------------------------------
    // EVENTS — CHAT SURFACES
    // ----------------------------------------------------------

    surfaces.forEach(surface => {
        surface.send.addEventListener("click", () => sendMessage(surface));

        surface.input.addEventListener("keydown", event => {
            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {
                event.preventDefault();
                sendMessage(surface);
            }
        });

        surface.voice?.addEventListener("click", () => {
            startListening(surface);
        });

        surface.speak?.addEventListener("click", () => {
            toggleVoiceOutput(surface);
        });

        surface.stop?.addEventListener("click", stopSpeaking);
    });

    // ----------------------------------------------------------
    // VOICE INITIALIZATION
    // ----------------------------------------------------------

    if (!SpeechRecognition) {
        surfaces.forEach(surface => {
            if (surface.voice) {
                surface.voice.title =
                    "Voice input is not supported by this browser";
                surface.voice.setAttribute(
                    "aria-label",
                    "Voice input is not supported by this browser"
                );
            }
        });
    }

    updateVoiceButtons();

    // Stop speech/recognition cleanly when leaving the page.
    window.addEventListener("pagehide", () => {
        stopListening();
        stopSpeaking();
    });

    window.addEventListener("beforeunload", () => {
        stopListening();
        stopSpeaking();
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth <= 767 && aiWindow) {
            aiWindow.style.left = "";
            aiWindow.style.top = "";
            aiWindow.style.right = "10px";
            aiWindow.style.bottom = "80px";
        }
    });

    // Expose only the small controls useful for future UI integrations.
    window.FocostAIVoice = Object.freeze({
        start: () => {
            const target = surfaces[0];
            if (target) startListening(target);
        },
        stopListening,
        speak: speakText,
        stopSpeaking,
        isSupported: Boolean(SpeechRecognition),
    });

    // Load existing session once both widget and page surfaces are known.
    loadHistory();
})();

// ==========================================================
// FINANCIAL CARD RENDERER
// ==========================================================

function renderFinancialCards(text) {

    if (!text)
        return null;

    //----------------------------------------------------------
    // Extract Card Type
    //----------------------------------------------------------

    const match = text.match(/^\[(.*?)\]/);

    if (!match)
        return null;

    const type = match[1];

    let payload;

    try {

        payload = JSON.parse(

            text.replace(match[0], "")

        );

    }

    catch {

        return null;

    }

    //----------------------------------------------------------
    // CARD ROUTER
    //----------------------------------------------------------

    switch (type) {

        case "BALANCE_CARD":
            return balanceCard(payload);

        case "INCOME_CARD":
            return incomeCard(payload);

        case "EXPENSE_CARD":
            return expenseCard(payload);

        case "BUDGET_CARD":
            return budgetCard(payload);

        case "GOAL_CARD":
            return goalCard(payload);

        case "HEALTH_CARD":
            return healthCard(payload);

        case "FORECAST_CARD":
            return forecastCard(payload);

        case "SPENDING_CARD":
            return spendingCard(payload);

        case "TOP_CATEGORY_CARD":
            return topCategoryCard(payload);

        case "TOP_MERCHANT_CARD":
            return topMerchantCard(payload);

        case "CASHFLOW_CARD":
            return cashflowCard(payload);

        case "INSIGHT_CARD":
            return insightCard(payload);

        case "RECOMMENDATION_CARD":
            return recommendationCard(payload);

        case "TABLE_CARD":
            return tableCard(payload);

        case "SUCCESS_CARD":
            return statusCard(payload, "success");

        case "WARNING_CARD":
            return statusCard(payload, "warning");

        case "ERROR_CARD":
            return statusCard(payload, "danger");

        default:
            return null;

    }

}

// ==========================================================
// HELPER FUNCTIONS
// ==========================================================

function money(value){

    return "₦" + Number(value).toLocaleString();

}

function percent(value){

    return Number(value).toFixed(1) + "%";

}

function badge(color,text){

    return `
        <span class="badge bg-${color}">
            ${text}
        </span>
    `;

}

// ==========================================================
// BALANCE CARD
// ==========================================================

function balanceCard(d){

return `

<div class="finance-card">

<div class="finance-header">

<h5>Available Balance</h5>

</div>

<div class="finance-big">

${money(d.balance)}

</div>

<div class="finance-grid">

<div>

<small>Income</small>

<h6>${money(d.income)}</h6>

</div>

<div>

<small>Expenses</small>

<h6>${money(d.expense)}</h6>

</div>

</div>

</div>

`;

}

// ==========================================================
// INCOME CARD
// ==========================================================

function incomeCard(d){

return `

<div class="finance-card">

<h5>Total Income</h5>

<div class="finance-big">

${money(d.total)}

</div>

<p>

Source:

<strong>${d.source||"All Sources"}</strong>

</p>

</div>

`;

}

// ==========================================================
// EXPENSE CARD
// ==========================================================

function expenseCard(d){

return `

<div class="finance-card">

<h5>Total Expenses</h5>

<div class="finance-big text-danger">

${money(d.total)}

</div>

<p>

Category:

<strong>${d.category||"All Categories"}</strong>

</p>

</div>

`;

}

// ==========================================================
// BUDGET CARD
// ==========================================================

function budgetCard(d){

return `

<div class="finance-card">

<h5>

Budget

</h5>

<div>

Used

${percent(d.used)}

</div>

<div class="progress">

<div

class="progress-bar"

style="width:${d.used}%">

</div>

</div>

<br>

Remaining

<strong>

${money(d.remaining)}

</strong>

</div>

`;

}

// ==========================================================
// GOAL CARD
// ==========================================================

function goalCard(d){

return `

<div class="finance-card">

<h5>

${d.goal}

</h5>

<div class="progress">

<div

class="progress-bar bg-success"

style="width:${d.progress}%">

</div>

</div>

<p>

${percent(d.progress)} Complete

</p>

<p>

Saved

${money(d.saved)}

of

${money(d.target)}

</p>

</div>

`;

}

// ==========================================================
// HEALTH CARD
// ==========================================================

function healthCard(d){

return `

<div class="finance-card">

<h5>

Financial Health

</h5>

<div class="finance-big">

${d.score}/100

</div>

${badge(

d.score>=80?

"success":

d.score>=60?

"warning":

"danger",

d.status

)}

</div>

`;

}

// ==========================================================
// FORECAST CARD
// ==========================================================

function forecastCard(d){

return `

<div class="finance-card">

<h5>

Forecast

</h5>

<div class="finance-big">

${money(d.balance)}

</div>

Projected Month-End Balance

</div>

`;

}

// ==========================================================
// SEPNDING CARD
// ==========================================================

function spendingCard(d){

return `

<div class="finance-card">

<h5>

Highest Spending

</h5>

<div class="finance-big">

${d.category}

</div>

${money(d.amount)}

</div>

`;

}

// ==========================================================
// TOP CATEGORY CARD
// ==========================================================

function topCategoryCard(d){

return `

<div class="finance-card">

<h5>

Top Category

</h5>

<div class="finance-big">

${d.category}

</div>

${money(d.total)}

</div>

`;

}

// ==========================================================
// TOP MERCHANT CARD
// ==========================================================

function topMerchantCard(d){

return `

<div class="finance-card">

<h5>

Top Merchant

</h5>

<div class="finance-big">

${d.merchant}

</div>

${money(d.total)}

</div>

`;

}

// ==========================================================
// CASH FLOW CARD
// ==========================================================

function cashflowCard(d){

return `

<div class="finance-card">

<h5>

Cash Flow

</h5>

<div class="finance-grid">

<div>

In

<h6>

${money(d.income)}

</h6>

</div>

<div>

Out

<h6>

${money(d.expense)}

</h6>

</div>

</div>

</div>

`;

}

// ==========================================================
// INSIGHT CARD
// ==========================================================

function insightCard(d){

return `

<div class="finance-card">

<h5>

AI Insight

</h5>

<p>

${d.message}

</p>

</div>

`;

}

// ==========================================================
// RECOMMENDATION CARD
// ==========================================================

function recommendationCard(d){

return `

<div class="finance-card">

<h5>

Recommendation

</h5>

<p>

${d.message}

</p>

</div>

`;

}

// ==========================================================
// TABLE CARD
// ==========================================================

function tableCard(d){

let rows="";

d.rows.forEach(r=>{

rows+=`

<tr>

<td>${r.name}</td>

<td>${money(r.amount)}</td>

</tr>

`;

});

return `

<div class="finance-card">

<h5>

Summary

</h5>

<table class="table table-sm">

<thead>

<tr>

<th>Name</th>

<th>Amount</th>

</tr>

</thead>

<tbody>

${rows}

</tbody>

</table>

</div>

`;

}

// ==========================================================
// STATUS CARD
// ==========================================================

function statusCard(d,color){

return `

<div class="alert alert-${color}">

<strong>

${d.title}

</strong>

<br>

${d.message}

</div>

`;

}

// ==========================================================
// MARKDOWN RENDERER
// ==========================================================

// ==========================================================
// MARKDOWN RENDERER
// ==========================================================

function renderMarkdown(text) {

    if (!text)
        return "";

    marked.setOptions({

        gfm: true,

        breaks: true

    });

    return marked.parse(text);

}


