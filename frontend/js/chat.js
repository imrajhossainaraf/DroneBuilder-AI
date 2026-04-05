let currentSessionId = localStorage.getItem("droneMate_sessionId") || null;

const chatContainer = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const suggestedQuestionsContainer = document.getElementById("suggested-questions");
const aiProviderSelect = document.getElementById("ai-provider-select");
const responseDetailSelect = document.getElementById("response-detail-select");

const LS_AI_PROVIDER = "droneMate_aiProvider";
const LS_RESPONSE_DETAIL = "droneMate_responseDetail";

function loadChatPreferences() {
    const ap = localStorage.getItem(LS_AI_PROVIDER);
    const rd = localStorage.getItem(LS_RESPONSE_DETAIL);
    if (ap && aiProviderSelect) aiProviderSelect.value = ap;
    if (rd && responseDetailSelect) responseDetailSelect.value = rd;
}

async function refreshProviderAvailability() {
    if (!aiProviderSelect) return;
    try {
        const st = await api_get("/status");
        const map = {
            auto: () => false,
            ollama: () => !(st.ollama && st.ollama.running),
            openai: () => !st.openai_configured,
            groq: () => !st.groq_configured,
            openrouter: () => !st.openrouter_configured,
            gemini: () => !st.gemini_configured,
        };
        aiProviderSelect.querySelectorAll("option").forEach((opt) => {
            const v = opt.value;
            const disable = map[v] ? map[v]() : false;
            opt.disabled = disable;
        });
        const selected = aiProviderSelect.options[aiProviderSelect.selectedIndex];
        if (selected && selected.disabled) {
            aiProviderSelect.value = "auto";
            localStorage.setItem(LS_AI_PROVIDER, "auto");
        }
    } catch (e) {
        console.warn("Could not load /api/status for AI provider UI", e);
    }
}

// ─── Simple Markdown Renderer ───────────────────────────
function renderMarkdown(text) {
    if (!text) return '';
    let html = text
        // Escape HTML first
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code class="bg-slate-700 px-1.5 py-0.5 rounded text-sm text-emerald-400">$1</code>')
        // Headers (## and ###)
        .replace(/^### (.+)$/gm, '<h4 class="text-sm font-semibold text-white mt-3 mb-1">$1</h4>')
        .replace(/^## (.+)$/gm, '<h3 class="text-base font-semibold text-white mt-3 mb-1">$1</h3>')
        // Numbered lists
        .replace(/^(\d+)\.\s+(.+)$/gm, '<div class="flex gap-2 ml-1 my-0.5"><span class="text-blue-400 font-medium shrink-0">$1.</span><span>$2</span></div>')
        // Bullet lists
        .replace(/^[-•]\s+(.+)$/gm, '<div class="flex gap-2 ml-1 my-0.5"><span class="text-blue-400">•</span><span>$1</span></div>')
        // Warning emoji lines (⚠️)
        .replace(/^(⚠️.+)$/gm, '<div class="bg-amber-900/30 border border-amber-700/30 rounded-lg px-3 py-1.5 my-1 text-amber-300 text-sm">$1</div>')
        // Line breaks
        .replace(/\n\n/g, '<div class="h-2"></div>')
        .replace(/\n/g, '<br>');
    return html;
}

// ─── Component Card Renderer ────────────────────────────
function renderComponentCards(components) {
    if (!components || !components.length) return '';
    let html = '<div class="mt-3 space-y-2">';
    html += '<div class="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Relevant Components</div>';
    components.forEach(c => {
        const specs = c.specs || {};
        const specStr = Object.entries(specs).slice(0, 4).map(([k,v]) => `${k}: ${v}`).join(' · ');
        const stars = '★'.repeat(Math.round(c.rating || 0)) + '☆'.repeat(5 - Math.round(c.rating || 0));
        html += `
            <div class="bg-slate-800/80 rounded-xl p-3 border border-white/5 hover:border-blue-500/30 transition-colors">
                <div class="flex items-center justify-between mb-1">
                    <span class="font-medium text-sm text-white">${c.name || ''}</span>
                    <span class="text-xs text-amber-400">${stars}</span>
                </div>
                <div class="text-xs text-slate-400 mb-1">${c.brand || ''} · ${specStr}</div>
                <div class="flex items-center gap-3 text-xs">
                    <span class="text-emerald-400 font-medium">$${c.price_range || 'N/A'}</span>
                    ${(c.pros || []).slice(0, 2).map(p => `<span class="text-slate-500">✓ ${p}</span>`).join('')}
                </div>
            </div>`;
    });
    html += '</div>';
    return html;
}

// ─── Send Message ───────────────────────────────────────
async function sendMessage() {
    const question = chatInput.value.trim();
    if (!question) return;

    addMessageToUI("user", question);
    chatInput.value = "";
    sendBtn.disabled = true;
    chatInput.disabled = true;

    const loadingId = addMessageToUI("assistant", null, true);

    try {
        const response = await api_post("/chat", {
            question,
            session_id: currentSessionId,
            ai_provider: aiProviderSelect ? aiProviderSelect.value : "auto",
            response_detail: responseDetailSelect ? responseDetailSelect.value : "standard",
        });

        if (response.session_id) {
            currentSessionId = response.session_id;
            localStorage.setItem("droneMate_sessionId", currentSessionId);
        }

        removeMessageFromUI(loadingId);
        addMessageToUI("assistant", response.response, false, response.source, response.relevant_components);
        updateSuggestions(response.suggested_questions);

    } catch (error) {
        removeMessageFromUI(loadingId);
        const hint = error && error.message ? String(error.message) : "Unknown error";
        console.error("Chat request failed:", hint);
        addMessageToUI(
            "assistant",
            "⚠️ Could not reach the API. Open the app at **http://127.0.0.1:8000** (not a local file) and ensure the backend is running. "
                + `Details: ${hint}`,
            false,
            "error"
        );
    }

    sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
}

// ─── Add Message to UI ──────────────────────────────────
function addMessageToUI(sender, content, isLoading = false, source = null, components = null) {
    const messageId = "msg-" + Date.now() + "-" + Math.floor(Math.random() * 1000);
    const messageDiv = document.createElement("div");
    messageDiv.id = messageId;
    messageDiv.className = "flex gap-4";
    messageDiv.style.animation = "fadeSlideIn 0.3s ease-out";

    const isUser = sender === "user";
    const avatarGradient = isUser ? "from-slate-700 to-slate-800" : "from-blue-600 to-blue-700";
    const icon = isUser ? "fa-user" : "fa-robot";
    const label = isUser ? "You" : "DroneMate Assistant";

    // Source badge
    let sourceBadge = "";
    if (source && !isUser) {
        const badgeColors = {
            "database_enhanced": "bg-emerald-900/40 text-emerald-400 border-emerald-500/20",
            "database": "bg-blue-900/40 text-blue-400 border-blue-500/20",
            "ai": "bg-purple-900/40 text-purple-400 border-purple-500/20",
            "error": "bg-red-900/40 text-red-400 border-red-500/20",
        };
        const colors = badgeColors[source] || badgeColors["ai"];
        const labels = {
            "database_enhanced": "Engine: Hybrid",
            "database": "Engine: Database",
            "ai": "Engine: LLM",
            "error": "Error",
        };
        sourceBadge = `<span class="text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border ${colors}">${labels[source] || source}</span>`;
    }

    // Content rendering
    let renderedContent = "";
    if (isLoading) {
        renderedContent = `
            <div class="flex items-center gap-2 text-slate-400">
                <div class="flex gap-1.5">
                    <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                    <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
                    <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                </div>
                <span class="text-xs font-medium uppercase tracking-widest ml-2">Calculating...</span>
            </div>`;
    } else if (isUser) {
        renderedContent = `<p class="leading-relaxed text-slate-200">${content}</p>`;
    } else {
        renderedContent = `<div class="leading-relaxed prose-sm text-slate-200">${renderMarkdown(content)}</div>`;
        if (components && components.length > 0) {
            renderedContent += renderComponentCards(components);
        }
    }

    messageDiv.innerHTML = `
        <div class="w-10 h-10 rounded-2xl bg-gradient-to-br ${avatarGradient} flex items-center justify-center flex-shrink-0 mt-1 shadow-lg shadow-black/20">
            <i class="fas ${icon} text-sm text-white"></i>
        </div>
        <div class="space-y-2 max-w-[85%] min-w-0">
            <div class="flex items-center gap-3">
                <span class="text-xs font-bold ${isUser ? 'text-slate-400' : 'text-blue-400'} uppercase tracking-widest">${label}</span>
                ${sourceBadge}
            </div>
            <div class="bg-slate-800/40 backdrop-blur-md p-5 rounded-2xl ${isUser ? 'rounded-tr-none' : 'rounded-tl-none'} border border-white/5 shadow-sm">
                ${renderedContent}
            </div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageId;
}

function removeMessageFromUI(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

// ─── Suggestions ────────────────────────────────────────
function updateSuggestions(suggestions) {
    if (!suggestions || !suggestions.length) return;
    suggestedQuestionsContainer.innerHTML = "";
    suggestions.forEach(suggestion => {
        const btn = document.createElement("button");
        btn.className = "text-left text-sm p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5 text-slate-400 hover:text-white hover:border-blue-500/30 duration-200";
        btn.innerText = suggestion;
        btn.onclick = () => {
            chatInput.value = suggestion;
            sendMessage();
        };
        suggestedQuestionsContainer.appendChild(btn);
    });
}

// ─── Event Listeners ────────────────────────────────────
sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

const clearChatBtn = document.getElementById("clear-chat-btn");
const mobileMenuBtn = document.getElementById("mobile-menu-btn");
const sidebar = document.getElementById("sidebar");

function setupUIInteractions() {
    // Mobile Sidebar Toggle
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.onclick = () => {
            sidebar.classList.toggle("hidden");
            sidebar.classList.toggle("flex");
            sidebar.classList.toggle("absolute");
            sidebar.classList.toggle("inset-0");
            sidebar.classList.toggle("z-[60]");
            sidebar.classList.toggle("bg-slate-900/95");
            sidebar.classList.toggle("p-6");
        };
    }

    // Clear Chat
    if (clearChatBtn) {
        clearChatBtn.onclick = () => {
            if (confirm("Are you sure you want to clear this conversation?")) {
                chatContainer.innerHTML = `
                    <div class="flex gap-4">
                        <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
                            <i class="fas fa-robot text-sm text-white"></i>
                        </div>
                        <div class="space-y-2 max-w-[85%]">
                            <div class="text-xs font-bold text-blue-400 uppercase tracking-widest">DroneMate Assistant</div>
                            <div class="bg-slate-800/40 backdrop-blur-md p-5 rounded-2xl rounded-tl-none border border-white/10 shadow-sm">
                                <p class="leading-relaxed text-slate-200">Conversation cleared. How else can I help you today?</p>
                            </div>
                        </div>
                    </div>
                `;
                currentSessionId = null;
                localStorage.removeItem("droneMate_sessionId");
            }
        };
    }
}

// ─── Init ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadChatPreferences();
    refreshProviderAvailability();
    setupUIInteractions();

    aiProviderSelect?.addEventListener("change", () => {
        localStorage.setItem(LS_AI_PROVIDER, aiProviderSelect.value);
    });
    responseDetailSelect?.addEventListener("change", () => {
        localStorage.setItem(LS_RESPONSE_DETAIL, responseDetailSelect.value);
    });

    updateSuggestions([
        "What motor should I use for a 5-inch racing drone?",
        "My drone won't arm — what should I check?",
        "Recommend a beginner-friendly build under $300"
    ]);
});
