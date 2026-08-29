/**
 * API Wrapper Utility
 */
const API = {
    async sendData(url, data = {}, method = "GET") {
        try {
            const options = { method };

            if (method !== "GET" && method !== "DELETE") {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = JSON.stringify(data);
            }

            const resdata = await fetch(url, options);

            if (!resdata.ok) {
                const errorData = await resdata.json().catch(() => ({}));
                return {
                    status: "error",
                    message: errorData.message || `Server error: ${resdata.status}`
                };
            }

            return await resdata.json();
        } catch (error) {
            console.error("API Request Failed:", error);
            return {
                status: "error",
                message: "Network error or server unavailable."
            };
        } finally {
            hideLoading();
        }
    },

    login: (cred) => API.sendData("/auth/login", cred, "POST"),
    signup: (cred) => API.sendData("/user/signup", cred, "POST"),
    get: (url) => API.sendData(url),
    post: (url, data) => API.sendData(url, data, "POST"),
    put: (url, data) => API.sendData(url, data, "PUT"),
    delete: (url) => API.sendData(url, {}, "DELETE")
};

/**
 * XSS Helper Sanitizer
 */
function escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Display Alert/Message Modal Safely
 */
function showMessageModal(text, texttitle = "Notice") {
    // Remove existing modal if still open to avoid DOM piling
    const existingModal = document.getElementById("message-modal");
    if (existingModal) {
        existingModal.remove();
    }

    const dialog = document.createElement("dialog");
    dialog.id = "message-modal";

    // Safely insert sanitized values into HTML structure
    dialog.innerHTML = `
        <button class="messagex" id="btnCloseMsgModal" aria-label="Close">
            <i class="bi bi-x-lg"></i>
        </button>
        <div>
            <h1>${escapeHTML(texttitle)}</h1>
            <p>${escapeHTML(text)}</p>
        </div>
    `;

    document.body.prepend(dialog);

    // Secure click handler binding for modal close
    const closeBtn = dialog.querySelector("#btnCloseMsgModal");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            dialog.close();
            dialog.remove();
        });
    }

    // Auto cleanup when dialog closes natively
    dialog.addEventListener("close", () => dialog.remove());

    dialog.showModal();
}

/**
 * Loading Spinner Utilities
 */
function loadImage() {
    const loadingGif = "../../static/scripts/load.gif";
    const image = new Image();
    image.src = loadingGif;
    image.alt = "Loading...";
    return image;
}

const imageLoad = loadImage();

function showLoading() {
    let loading = document.getElementById("loading");

    if (loading) {
        loading.style.display = "grid";
        return;
    }

    const div = document.createElement("div");
    div.id = "loading";
    div.appendChild(imageLoad);

    document.body.appendChild(div);
}

function hideLoading() {
    const loading = document.getElementById("loading");
    if (loading) {
        loading.style.display = "none";
    }
}