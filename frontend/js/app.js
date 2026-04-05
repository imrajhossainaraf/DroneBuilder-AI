document.addEventListener("DOMContentLoaded", async () => {
    console.log("DroneMate initialized!");
    // Check API status
    try {
        const status = await api_get("/status");
        console.log("Backend Status:", status);
    } catch (error) {
        console.error("Backend connection failed.", error);
    }
});
