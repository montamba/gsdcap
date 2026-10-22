/**
 * API Wrapper Utility
 */
const API = {
    async sendData(url, data = {}, method = "GET") {
        try {
            const options = { method, headers: { 'X-Requested-With': 'XMLHttpRequest' } };

            if (method !== "GET" && method !== "DELETE") {
                if (data instanceof FormData) {
                    // let the browser set the multipart boundary header
                    options.body = data;
                } else {
                    options.headers['Content-Type'] = 'application/json';
                    options.body = JSON.stringify(data);
                }
            }

            const resdata = await fetch(url, options);
            if (resdata.redirected || resdata.status === 401) {
                window.location.href = "/";
                return { status: "error", message: "Session expired" };
            }

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

/**
 * Requirement image upload helpers (OR / CR / etc.)
 * Keys must match KINDS in other/blob.py
 */
const REQ_KINDS = {
    or: "OR (Official Receipt)",
    cr: "CR (Certificate of Registration)",
    driver_license: "Driver's license",
    employee_id: "Employee / school ID",
    registration_form: "Registration form",
    affidavit: "Affidavit"
};

function renderReqFields(containerId, prefix = "req_") {
    const box = document.getElementById(containerId);
    if (!box) return;
    box.innerHTML = "";
    for (const [k, label] of Object.entries(REQ_KINDS)) {
        const wrap = document.createElement("div");
        wrap.className = "form-group full field";

        const lab = document.createElement("label");
        lab.htmlFor = prefix + k;
        lab.textContent = label;

        const input = document.createElement("input");
        input.type = "file";
        input.id = prefix + k;
        input.accept = "image/jpeg,image/png,image/webp";

        wrap.appendChild(lab);
        wrap.appendChild(input);
        box.appendChild(wrap);
    }
}

function appendReqFiles(fd, prefix = "req_") {
    let count = 0;
    for (const k of Object.keys(REQ_KINDS)) {
        const f = document.getElementById(prefix + k)?.files[0];
        if (f) { fd.append(k, f); count++; }
    }
    return count;
}