const componentsGrid = document.getElementById("components-grid");
const typeFilter = document.getElementById("type-filter");
const searchInput = document.getElementById("search-input");

async function fetchComponents() {
    const type = typeFilter.value;
    const search = searchInput.value.trim();
    let query = "";
    if (type) query += `?component_type=${type}`;
    if (search) query += `${query ? '&' : '?'}search=${search}`;

    try {
        const components = await api_get(`/components/${query}`);
        renderComponents(components);
    } catch (error) {
        console.error("Failed to fetch components:", error);
    }
}

async function renderComponents(components) {
    if (!components.length) {
        componentsGrid.innerHTML = `<div class="col-span-full py-20 text-center text-slate-500 italic">No components found matching your criteria.</div>`;
        return;
    }

    componentsGrid.innerHTML = "";
    components.forEach(comp => {
        const card = document.createElement("div");
        card.className = "glass-panel rounded-3xl p-6 space-y-4 hover:border-blue-600/50 transition-all flex flex-col justify-between";
        
        const specsHtml = Object.entries(comp.specs)
            .map(([k, v]) => `<div class="flex justify-between items-center text-xs"><span class="text-slate-500 capitalize">${k}</span><span class="text-slate-300">${v}</span></div>`)
            .join("");

        card.innerHTML = `
            <div class="space-y-4">
                <div class="flex justify-between items-start">
                    <div class="bg-blue-600/20 text-blue-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-md">
                        ${comp.component_type.replace('_', ' ')}
                    </div>
                    <div class="flex items-center gap-1 text-xs text-yellow-500">
                        <i class="fas fa-star"></i>
                        <span>${comp.rating}</span>
                    </div>
                </div>
                <div class="space-y-1">
                    <h3 class="text-lg font-bold text-white">${comp.name}</h3>
                    <p class="text-sm text-slate-500">${comp.brand}</p>
                </div>
                <div class="space-y-2 border-y border-white/5 py-3">
                    ${specsHtml}
                </div>
            </div>
            <div class="flex justify-between items-center pt-2">
                <span class="text-lg font-bold text-blue-500">$${comp.price_range || "N/A"}</span>
                <button class="text-xs bg-slate-800 hover:bg-slate-700 font-semibold px-4 py-2 rounded-xl transition-colors">Details</button>
            </div>
        `;
        componentsGrid.appendChild(card);
    });
}

// Event Listeners
typeFilter.addEventListener("change", fetchComponents);
let searchTimeout;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(fetchComponents, 300);
});

// Load on start
document.addEventListener("DOMContentLoaded", fetchComponents);
