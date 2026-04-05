// Use backend URL when page is opened via file:// or opaque origin (must run server at :8000)
function getApiBaseUrl() {
    try {
        const p = window.location.protocol;
        if (p === "file:" || p === "null:" || !window.location.hostname) {
            return "http://127.0.0.1:8000/api";
        }
        return window.location.origin + "/api";
    } catch {
        return "http://127.0.0.1:8000/api";
    }
}
const API_BASE_URL = getApiBaseUrl();

async function api_get(endpoint) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API GET Error:", error);
        throw error;
    }
}

async function api_post(endpoint, data) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API POST Error:", error);
        throw error;
    }
}
