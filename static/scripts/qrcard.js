/**
 * QR card viewer — shared by staff/search.html and users/userqr.html
 *
 * Needs on the page: qrcode.min.js, html2canvas.min.js, bootstrap-icons, qrcard.css
 *
 * QrCard.open(row, {
 *   mode: "staff" | "user",
 *   onRenew(row, newDate), onRevoke(row), onEmail(row),   // staff
 *   onRequestRenewal(row),                                // user
 *   onEmailRequirements(row, addressTag)                  // staff
 * });
 *
 * row = [0 id, 1 code, 2 plate, 3 owner, 4 email, 5 phone, 6 department,
 *        7 expiry, 8 status, 9 created_by, 10 created_at, 11 car_status,
 *        12 vehicle_type, 13 space_units, 14 username]
 */
const QrCard = (() => {
    const config = {
        // the header image of the portrait card (page 2) — put your file here
        topImage: "/static/img/bg.png"
    };

    const PAGES = {
        staff: [
            { title: "QR Details",   icon: "bi-qr-code",         buttons: ["renew", "revoke", "email"] },
            { title: "QR Card",      icon: "bi-credit-card-2-front", buttons: ["print", "save"] },
            { title: "Car Details",  icon: "bi-car-front-fill",  buttons: [] },
            { title: "Requirements", icon: "bi-card-checklist",  buttons: ["emailReq"] }
        ],
        user: [
            { title: "My QR",        icon: "bi-qr-code",         buttons: ["requestRenewal"] },
            { title: "QR Card",      icon: "bi-credit-card-2-front", buttons: ["print", "save"] },
            { title: "Car Details",  icon: "bi-car-front-fill",  buttons: [] },
            { title: "Requirements", icon: "bi-card-checklist",  buttons: ["attach"] }
        ]
    };

    let root = null;
    let page = 0;
    let row = null;
    let opts = {};
    let renewing = false;

    const $ = (id) => document.getElementById(id);
    const show = (v) => (v === null || v === undefined || v === "" || v === "None") ? "—" : String(v);

    function effectiveStatus(status, expiry) {
        if (status && status !== "active") return status;
        if (expiry && expiry !== "None") {
            const d = new Date(String(expiry).replace(" ", "T"));
            if (!isNaN(d) && d < new Date()) return "expired";
        }
        return status || "active";
    }

    function setBadge(el, text, cls) {
        el.textContent = text;
        el.className = "qc-badge " + cls;
    }

    function drawQR(holderId, code, size) {
        const holder = $(holderId);
        holder.innerHTML = "";
        if (!code || code === "pending") {
            holder.textContent = "No QR code yet";
            return;
        }
        new QRCode(holder, { text: String(code), width: size, height: size, correctLevel: QRCode.CorrectLevel.H });
    }

    // ─── build the modal once ───
    function build() {
        root = document.createElement("div");
        root.className = "qc-overlay";
        root.id = "qcOverlay";
        root.innerHTML = `
        <div class="qc-holder" role="dialog" aria-modal="true" aria-labelledby="qcTitle">
            <div class="qc-head">
                <h1 class="qc-title"><i class="bi bi-qr-code" id="qcTitleIcon"></i> <span id="qcTitle">QR Details</span></h1>
                <div class="qc-head-right">
                    <span class="qc-count" id="qcCount">1 / 4</span>
                    <button type="button" class="qc-close" id="qcClose" aria-label="Close"><i class="bi bi-x-lg"></i></button>
                </div>
            </div>

            <div class="qc-pages"><div class="qc-track" id="qcTrack">

                <section class="qc-slide" aria-label="QR details">
                    <div class="qc-page1">
                        <div class="qc-qr-side">
                            <div class="qc-qrholder" id="qcQr1"></div>
                            <h2 class="qc-code" id="qcCode">—</h2>
                        </div>
                        <div class="qc-info-side">
                            <div class="qc-field"><p>Expiry</p><h3 id="qcExpiry">—</h3></div>
                            <div class="qc-field"><p>Status</p><h3><span class="qc-badge" id="qcStatus">—</span></h3></div>
                            <div class="qc-field"><p>Car status</p><h3><span class="qc-badge" id="qcCar">—</span></h3></div>
                            <div class="qc-field"><p>Created at</p><h3 id="qcCreated">—</h3></div>
                        </div>
                    </div>
                </section>

                <section class="qc-slide" aria-label="QR card">
                    <div class="qc-page2" id="qcPage2">
                        <div class="qc-top"><img id="qcTopImg" src="bg.png" alt=""></div>
                        <div class="qc-body">
                            <div class="qc-qrimage" id="qcQr2"></div>
                            <div class="qc-plate" id="qcPlate2">—</div>
                            <div class="qc-owner" id="qcOwner2">—</div>
                            <div class="qc-expiry-box"><p>Expiry</p><h3 id="qcExpiry2">—</h3></div>
                        </div>
                    </div>
                </section>

                <section class="qc-slide" aria-label="Car details">
                    <div class="qc-page3">
                        <div class="qc-sheet-head"><i class="bi bi-car-front-fill"></i> Car details</div>
                        <div>
                            <div class="qc-detail-row"><span class="qc-lbl">Plate</span><span class="qc-val" id="qcD-plate">—</span></div>
                            <div class="qc-detail-row"><span class="qc-lbl">Vehicle type</span><span class="qc-val" id="qcD-type">—</span></div>
                            <div class="qc-detail-row"><span class="qc-lbl">Owner</span><span class="qc-val" id="qcD-owner">—</span></div>
                            <div class="qc-detail-row"><span class="qc-lbl">Email</span><span class="qc-val" id="qcD-email">—</span></div>
                            <div class="qc-detail-row"><span class="qc-lbl">Phone</span><span class="qc-val" id="qcD-phone">—</span></div>
                            <div class="qc-detail-row"><span class="qc-lbl">Department</span><span class="qc-val" id="qcD-dept">—</span></div>
                            <div class="qc-detail-row" id="qcD-byRow"><span class="qc-lbl">Created by</span><span class="qc-val" id="qcD-by">—</span></div>
                        </div>
                    </div>
                </section>

                <section class="qc-slide" aria-label="Requirements">
                    <div class="qc-page4">
                        <div class="qc-sheet-head"><i class="bi bi-card-checklist"></i> Requirements</div>
                        <div class="qc-req-body">
                            <div class="qc-attach-box" id="qcAttachBox">
                                <div><i class="bi bi-image"></i><br>No image attached yet</div>
                            </div>
                            <div class="qc-tag-group" id="qcTagGroup">
                                <label for="qcAddressTag">Address tag</label>
                                <input id="qcAddressTag" type="text" maxlength="120" placeholder="e.g. Pick up at GSD office">
                            </div>
                        </div>
                    </div>
                </section>

            </div></div>

            <div class="qc-controls">
                <div class="prev-but"><button type="button" class="qc-nav" id="qcPrev" aria-label="Previous page"><i class="bi bi-chevron-left"></i></button></div>
                <div class="qc-actions other-but" id="qcActions"></div>
                <div class="next-but"><button type="button" class="qc-nav" id="qcNext" aria-label="Next page"><i class="bi bi-chevron-right"></i></button></div>
                <div class="qc-dots" id="qcDots"></div>
            </div>
        </div>`;
        document.body.appendChild(root);

        $("qcClose").addEventListener("click", close);
        $("qcPrev").addEventListener("click", () => goTo(page - 1));
        $("qcNext").addEventListener("click", () => goTo(page + 1));
        root.addEventListener("click", (e) => { if (e.target === root) close(); });
        document.addEventListener("keydown", (e) => {
            if (!root.classList.contains("show")) return;
            if (e.key === "Escape") close();
            if (e.target.tagName === "INPUT") return;
            if (e.key === "ArrowLeft") goTo(page - 1);
            if (e.key === "ArrowRight") goTo(page + 1);
        });

        // header image: hide the <img> if the file is missing so the green stays clean
        const img = $("qcTopImg");
        img.addEventListener("error", () => { img.style.display = "none"; });
        img.addEventListener("load", () => { img.style.display = "block"; });
    }

    // ─── fill from one row ───
    function fill(d, mode) {
        const status = effectiveStatus(d[8], d[7]);
        const car = (d[11] || "").toUpperCase();

        drawQR("qcQr1", d[1], 128);
        $("qcCode").textContent = d[1] ? show(d[1]) : "Not issued yet";
        $("qcExpiry").textContent = show(d[7]);
        setBadge($("qcStatus"), status, status);
        setBadge($("qcCar"), car || "NOT SCANNED", car === "IN" ? "in" : "out");
        $("qcCreated").textContent = show(d[10]);

        drawQR("qcQr2", d[1], 118);
        $("qcPlate2").textContent = show(d[2]);
        $("qcOwner2").textContent = show(d[3]);
        $("qcExpiry2").textContent = show(d[7]).split(" ")[0];
        const img = $("qcTopImg");
        img.src = config.topImage;

        $("qcD-plate").textContent = show(d[2]);
        $("qcD-type").textContent = show(d[12]);
        $("qcD-owner").textContent = show(d[3]);
        $("qcD-email").textContent = show(d[4]);
        $("qcD-phone").textContent = show(d[5]);
        $("qcD-dept").textContent = show(d[6]);
        $("qcD-by").textContent = show(d[14]);
        $("qcD-byRow").style.display = mode === "staff" ? "flex" : "none";

        // page 4: staff sets the address tag, users only see the attach area
        $("qcTagGroup").style.display = mode === "staff" ? "flex" : "none";
        $("qcAddressTag").value = "";
    }

    // ─── buttons ───
    function actionDefs() {
        return {
            renew:   { label: "Renew",  icon: "bi-calendar-check",    cls: "renew",  fn: startRenew,
                       disabled: false },
            revoke:  { label: "Revoke", icon: "bi-slash-circle",      cls: "revoke", fn: () => confirmThen("Revoke this QR code?", opts.onRevoke),
                       disabled: effectiveStatus(row[8], row[7]) === "revoked" },
            email:   { label: "Email",  icon: "bi-envelope-arrow-up", cls: "email",  fn: () => opts.onEmail && opts.onEmail(row),
                       disabled: !row[4] || row[4] === "None" },
            requestRenewal: { label: "Request Renewal", icon: "bi-arrow-repeat", cls: "renew",
                       fn: () => opts.onRequestRenewal && opts.onRequestRenewal(row),
                       disabled: !row[1] || row[1] === "pending" },
            print:   { label: "Print",         icon: "bi-printer", cls: "ghost", fn: () => window.print(), disabled: false },
            save:    { label: "Save as image", icon: "bi-download", cls: "renew", fn: saveImage, disabled: !row[1] },
            emailReq:{ label: "Email requirements", icon: "bi-envelope-arrow-up", cls: "email", fn: emailRequirements,
                       disabled: !row[4] || row[4] === "None" },
            // placeholder only — the attach logic is not written yet
            attach:  { label: "Attach image", icon: "bi-paperclip", cls: "renew", fn: null, disabled: false }
        };
    }

    function renderActions() {
        const box = $("qcActions");
        box.innerHTML = "";

        if (renewing) {
            const input = document.createElement("input");
            input.type = "date";
            input.className = "qc-renew-input";
            input.setAttribute("aria-label", "New expiry date");
            if (row[7] && row[7] !== "None") input.value = String(row[7]).split(" ")[0];
            box.appendChild(input);

            box.appendChild(makeBtn({ label: "Confirm", icon: "bi-check-lg", cls: "email", disabled: false,
                fn: () => {
                    if (!input.value) { showMessageModal("Please pick a new expiry date.", "Missing Date"); return; }
                    opts.onRenew && opts.onRenew(row, input.value);
                } }));
            box.appendChild(makeBtn({ label: "Cancel", icon: "bi-x-lg", cls: "ghost", disabled: false,
                fn: () => { renewing = false; renderActions(); } }));
            input.focus();
            return;
        }

        const defs = actionDefs();
        PAGES[opts.mode][page].buttons.forEach((key) => box.appendChild(makeBtn(defs[key], key)));
    }

    function makeBtn(def, key) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "qc-btn " + def.cls;
        btn.innerHTML = `<i class="bi ${def.icon}"></i> ${def.label}`;
        btn.disabled = !!def.disabled;
        if (key) btn.dataset.action = key;
        if (def.fn) btn.addEventListener("click", () => def.fn(btn));
        return btn;
    }

    function startRenew() { renewing = true; renderActions(); }

    function confirmThen(message, fn) {
        if (fn && confirm(message)) fn(row);
    }

    function emailRequirements() {
        const tag = $("qcAddressTag").value.trim();
        if (!tag) { showMessageModal("Type an address tag first.", "Missing Address Tag"); return; }
        opts.onEmailRequirements && opts.onEmailRequirements(row, tag);
    }

    async function saveImage(btn) {
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving…';
        try {
            const canvas = await html2canvas($("qcPage2"), { scale: 3, backgroundColor: null, useCORS: true });
            const link = document.createElement("a");
            link.download = `qr-card-${row[2] || "vehicle"}.png`;
            link.href = canvas.toDataURL("image/png");
            link.click();
        } catch (err) {
            console.error(err);
            showMessageModal("Could not save the card as an image.", "Save Failed");
        } finally {
            btn.disabled = false;
            btn.innerHTML = original;
        }
    }

    // ─── carousel ───
    function goTo(n) {
        const pages = PAGES[opts.mode];
        page = Math.max(0, Math.min(pages.length - 1, n));
        renewing = false;

        $("qcTrack").style.transform = `translateX(-${page * 100}%)`;
        $("qcTitle").textContent = pages[page].title;
        $("qcTitleIcon").className = "bi " + pages[page].icon;
        $("qcCount").textContent = `${page + 1} / ${pages.length}`;
        $("qcPrev").disabled = page === 0;
        $("qcNext").disabled = page === pages.length - 1;

        root.querySelectorAll(".qc-slide").forEach((s, i) => s.setAttribute("aria-hidden", i === page ? "false" : "true"));
        root.querySelectorAll(".qc-dot").forEach((d, i) => d.classList.toggle("on", i === page));
        renderActions();
    }

    function buildDots() {
        const dots = $("qcDots");
        dots.innerHTML = "";
        PAGES[opts.mode].forEach((p, i) => {
            const dot = document.createElement("button");
            dot.type = "button";
            dot.className = "qc-dot";
            dot.setAttribute("aria-label", "Go to " + p.title);
            dot.addEventListener("click", () => goTo(i));
            dots.appendChild(dot);
        });
    }

    // ─── public ───
    function open(data, options = {}) {
        if (!root) build();
        row = data;
        opts = Object.assign({ mode: "staff" }, options);
        fill(row, opts.mode);
        buildDots();
        root.classList.add("show");
        goTo(0);
    }

    function close() {
        if (root) root.classList.remove("show");
        renewing = false;
    }

    return { open, close, config };
})();
