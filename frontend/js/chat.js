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
    const avatarColor = isUser ? "bg-slate-700" : "bg-blue-600";
    const icon = isUser ? "fa-user" : "fa-robot";
    const label = isUser ? "You" : "DroneMate";

    // Source badge
    let sourceBadge = "";
    if (source && !isUser) {
        const badgeColors = {
            "database_enhanced": "bg-emerald-900/50 text-emerald-400 border-emerald-700/30",
            "database": "bg-blue-900/50 text-blue-400 border-blue-700/30",
            "ai": "bg-purple-900/50 text-purple-400 border-purple-700/30",
            "error": "bg-red-900/50 text-red-400 border-red-700/30",
        };
        const colors = badgeColors[source] || badgeColors["ai"];
        const labels = {
            "database_enhanced": "DB + AI",
            "database": "Database",
            "ai": "AI Generated",
            "error": "Error",
        };
        sourceBadge = `<span class="text-[10px] uppercase px-2 py-0.5 rounded-full border ${colors}">${labels[source] || source}</span>`;
    }

    // Content rendering
    let renderedContent = "";
    if (isLoading) {
        renderedContent = `
            <div class="flex items-center gap-2 text-slate-400">
                <div class="flex gap-1">
                    <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                    <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.15s"></span>
                    <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0.3s"></span>
                </div>
                <span class="text-sm">Thinking...</span>
            </div>`;
    } else if (isUser) {
        renderedContent = `<p class="leading-relaxed">${content}</p>`;
    } else {
        renderedContent = `<div class="leading-relaxed prose-sm">${renderMarkdown(content)}</div>`;
        if (components && components.length > 0) {
            renderedContent += renderComponentCards(components);
        }
    }

    messageDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full ${avatarColor} flex items-center justify-center flex-shrink-0 mt-1">
            <i class="fas ${icon} text-xs text-white"></i>
        </div>
        <div class="space-y-1.5 max-w-[85%] min-w-0">
            <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-slate-400">${label}</span>
                ${sourceBadge}
            </div>
            <div class="bg-slate-800/50 p-4 rounded-2xl ${isUser ? 'rounded-tr-none' : 'rounded-tl-none'} border border-white/5">
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

// ─── Init ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadChatPreferences();
    refreshProviderAvailability();

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
