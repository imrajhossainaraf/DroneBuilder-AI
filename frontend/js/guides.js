const guidesList = document.getElementById("guides-list");
const guideDetail = document.getElementById("guide-detail");

async function fetchGuides() {
    try {
        const guides = await api_get("/guides/");
        renderGuides(guides);
    } catch (error) {
        console.error("Failed to fetch guides:", error);
    }
}

async function renderGuides(guides) {
    if (!guides.length) {
        guidesList.innerHTML = `<div class="py-20 text-center text-slate-500 italic">No guides available yet.</div>`;
        return;
    }

    guidesList.innerHTML = "";
    guides.forEach(guide => {
        const item = document.createElement("div");
        item.className = "glass-panel rounded-3xl p-6 flex justify-between items-center hover:border-blue-600/50 transition-all cursor-pointer";
        item.onclick = () => showGuide(guide);

        item.innerHTML = `
            <div class="space-y-1">
                <div class="flex gap-2 items-center text-xs text-blue-400 font-bold uppercase tracking-wider">
                    <span>${guide.drone_type}</span>
                    <span class="w-1 h-1 rounded-full bg-slate-600"></span>
                    <span>${guide.difficulty}</span>
                </div>
                <h3 class="text-xl font-bold text-white">${guide.title}</h3>
                <p class="text-sm text-slate-500">Estimated time: ${guide.estimated_time} • Budget: $${guide.budget}</p>
            </div>
            <div class="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-blue-500 hover:bg-blue-600 hover:text-white transition-all">
                <i class="fas fa-chevron-right"></i>
            </div>
        `;
        guidesList.appendChild(item);
    });
}

async function showGuide(guide) {
    guidesList.classList.add("hidden");
    guideDetail.classList.remove("hidden");

    const stepsHtml = guide.steps.map(step => `
        <div class="glass-panel rounded-2xl p-6 space-y-3 relative overflow-hidden group">
            <div class="absolute top-0 left-0 w-1 h-full bg-blue-600"></div>
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                    ${step.step_number}
                </div>
                <h4 class="text-lg font-bold text-white">${step.title}</h4>
                <span class="text-xs text-slate-500 ml-auto">${step.duration || ""}</span>
            </div>
            <p class="text-slate-400 text-sm leading-relaxed">${step.description}</p>
            <div class="pt-2">
                ${step.tips.map(tip => `<div class="text-xs text-slate-500 flex items-start gap-2 pt-1"><i class="fas fa-lightbulb text-yellow-500 flex-shrink-0 pt-0.5"></i><span>${tip}</span></div>`).join("")}
            </div>
        </div>
    `).join("");

    guideDetail.innerHTML = `
        <div class="flex items-center justify-between border-b border-white/5 pb-6">
            <button onclick="hideGuide()" class="text-sm font-medium text-slate-400 hover:text-white flex items-center gap-2 transition-all">
                <i class="fas fa-chevron-left"></i> Back to Guides
            </button>
            <div class="flex gap-4">
                <a href="${guide.video_url}" target="_blank" class="bg-red-600/10 hover:bg-red-600/20 text-red-500 px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2">
                    <i class="fab fa-youtube"></i> Watch on YouTube
                </a>
            </div>
        </div>
        <div class="space-y-4">
            <h2 class="text-3xl font-bold text-white">${guide.title}</h2>
            <div class="flex flex-wrap gap-4 text-sm text-slate-500">
                <span class="flex items-center gap-2"><i class="fas fa-clock"></i> ${guide.estimated_time}</span>
                <span class="flex items-center gap-2"><i class="fas fa-wallet"></i> Budget: $${guide.budget}</span>
                <span class="flex items-center gap-2"><i class="fas fa-tools"></i> ${guide.required_tools.length} Tools needed</span>
            </div>
        </div>
        <div class="space-y-6">
            <h3 class="text-xl font-bold text-slate-300">Detailed Steps</h3>
            <div class="grid gap-6">
                ${stepsHtml}
            </div>
        </div>
    `;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function hideGuide() {
    guideDetail.classList.add("hidden");
    guidesList.classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", fetchGuides);
