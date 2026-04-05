let currentSessionId = localStorage.getItem("droneMate_sessionId") || null;

const chatContainer = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const suggestedQuestionsContainer = document.getElementById("suggested-questions");

async function sendMessage() {
    const question = chatInput.value.trim();
    if (!question) return;

    // Add User Message to UI
    addMessageToUI("user", question);
    chatInput.value = "";

    // Show Loading
    const loadingId = addMessageToUI("assistant", "Typing...", true);

    try {
        const response = await api_post("/chat", {
            question,
            session_id: currentSessionId
        });

        // Update Session ID if new
        if (response.session_id) {
            currentSessionId = response.session_id;
            localStorage.setItem("droneMate_sessionId", currentSessionId);
        }

        // Remove Loading and Add AI Response
        removeMessageFromUI(loadingId);
        addMessageToUI("assistant", response.response, false, response.source);
        
        // Update Suggestions
        updateSuggestions(response.suggested_questions);

    } catch (error) {
        removeMessageFromUI(loadingId);
        addMessageToUI("assistant", "I'm sorry, I'm having trouble connecting to the server. Please check if the backend is running.", false, "error");
    }
}

async function addMessageToUI(sender, content, isLoading = false, source = null) {
    const messageId = "msg-" + Date.now();
    const messageDiv = document.createElement("div");
    messageDiv.id = messageId;
    messageDiv.className = "flex gap-4 animate-in slide-in-from-bottom-2 fade-in duration-300";
    
    const isUser = sender === "user";
    const avatarColor = isUser ? "bg-slate-700" : "bg-blue-600";
    const icon = isUser ? "fa-user" : "fa-robot";
    const label = isUser ? "You" : "DroneMate";
    const sourceLabel = source ? `<span class="text-xs text-slate-500 uppercase ml-2">[${source}]</span>` : "";

    messageDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full ${avatarColor} flex items-center justify-center flex-shrink-0">
            <i class="fas ${icon} text-xs text-white"></i>
        </div>
        <div class="space-y-2 max-w-[85%]">
            <div class="text-sm font-medium text-slate-400">${label} ${sourceLabel}</div>
            <div class="bg-slate-800/50 p-4 rounded-2xl ${isUser ? 'rounded-tr-none' : 'rounded-tl-none'} border border-white/5">
                <p class="leading-relaxed whitespace-pre-wrap">${content}</p>
            </div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageId;
}

async function removeMessageFromUI(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

async function updateSuggestions(suggestions) {
    if (!suggestions || !suggestions.length) return;
    suggestedQuestionsContainer.innerHTML = "";
    suggestions.forEach(suggestion => {
        const btn = document.createElement("button");
        btn.className = "text-left text-sm p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5 text-slate-400 hover:text-white";
        btn.innerText = suggestion;
        btn.onclick = () => {
            chatInput.value = suggestion;
            sendMessage();
        };
        suggestedQuestionsContainer.appendChild(btn);
    });
}

// Event Listeners
sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});

// Initialize suggestions on load
async function initSuggestions() {
    // Show some default ones
    const defaults = [
        "What motor should I use for a 5-inch racing drone?",
        "My drone won't arm — what should I check?",
        "Recommend a beginner-friendly build under $300"
    ];
    updateSuggestions(defaults);
}

document.addEventListener("DOMContentLoaded", initSuggestions);
