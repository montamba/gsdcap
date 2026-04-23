from flask import Blueprint, request, jsonify, render_template, session, redirect
from other.mysql_ import SQL
from datetime import datetime


class Guard:
    def __init__(self):
        self.guard = Blueprint("guard", __name__, url_prefix="/guard")
        self.sql = SQL()
        self.routes()

    def _protect(self):
        if "user_id" not in session or session["role"] != "guard":
            if request.is_json:
                return jsonify({"status": "unauthenticated", "message": "Please log in"}), 401
            return redirect("/")
        if session.get("role") not in ("guard", "user", "staff"):
            return jsonify({"status": "forbidden", "message": "Guard access required"}), 403

    def routes(self):
        self.guard.before_request(self._protect)

        # ─── PAGES ────────────────────────────────────────

        @self.guard.route("/scan")
        def scanner():
            return render_template("guard/scanner.html")

        @self.guard.route("/history")
        def history():
            return render_template("guard/history.html")

        # ─── API ──────────────────────────────────────────

        @self.guard.route("/my_history", methods=["GET"])
        def my_history():
            try:
                data = self.sql.gethistorybyguard(session["user_id"])
                serialized = []
                for row in data:
                    serialized.append([
                        str(v) if not isinstance(v, (int, str, float, type(None))) else v
                        for v in row
                    ])
                return jsonify({"status": "good", "data": serialized})
            except Exception as e:
                print("History error:", e)
                return jsonify({"status": "bad", "message": "Failed to fetch history"})

        @self.guard.route("/check_qr", methods=["POST"])
        def check_qr():
            data = request.get_json()
            qrdata = (data.get("data") or "").strip()
            action = (data.get("action") or "entry").strip()   # "entry" or "exit"

            new_action = "IN" if action == "entry" else "OUT"

            if not qrdata:
                return jsonify({"status": "bad", "message": "No QR data provided"})

            qr = self.sql.getqrbydata(qrdata)

            # ── QR NOT FOUND ──────────────────────────────
            if not qr:
                self._log(qrdata, "failed", action)
                return jsonify({
                    "status":      "bad",
                    "message":     "QR code not recognized",
                    "scan_result": "failed"
                })

            # qrcode columns:
            # 0:id  1:data  2:plate  3:owner_name  4:owner_email
            # 5:expiry  6:status  7:created_by  8:created_at  9:car_status
            plate       = qr[2] or "—"
            owner_name  = qr[3] or "—"
            owner_email = qr[4] or "—"
            expiry      = qr[5]
            qr_status   = (qr[6] or "active").lower()
            car_status  = qr[9]

            if qr_status == "revoked":
                self._log(qrdata, "failed", action)
                return jsonify({
                    "status":      "bad",
                    "message":     "QR code has been revoked",
                    "scan_result": "failed",
                    "owner_name":  owner_name,
                    "plate":       plate
                })

            # ── EXPIRED ───────────────────────────────────
            if expiry and datetime.now() > expiry:
                self._log(qrdata, "expired", action)
                return jsonify({
                    "status":      "expired",
                    "message":     "QR code has expired",
                    "scan_result": "expired",
                    "owner_name":  owner_name,
                    "plate":       plate,
                    "valid_until": str(expiry)
                })

            # ── DUPLICATE ACTION ──────────────────────────
            if car_status == new_action:
                self._log(qrdata, "failed", action)
                return jsonify({
                    "status":      "Invalid",
                    "message":     f"The vehicle is already {car_status}",
                    "scan_result": "failed",
                    "owner_name":  owner_name,
                    "plate":       plate,
                    "valid_until": str(expiry) if expiry else "—"
                })

            # ── ACCEPTED ──────────────────────────────────
            self._log(qrdata, "accepted", action)

            try:
                cur = self.sql.sql.cursor()
                if action == "entry":
                    cur.execute("UPDATE qrcode SET car_status='IN' WHERE data=%s", (qrdata,))
                else:
                    cur.execute("UPDATE qrcode SET car_status='OUT' WHERE data=%s", (qrdata,))
                self.sql.sql.commit()
                cur.close()
                self.sql.updateparking()
            except Exception as e:
                print("Parking update error:", e)

            return jsonify({
                "status":      "good",
                "message":     "Access Granted",
                "scan_result": "accepted",
                "action":      action,
                "owner_name":  owner_name,
                "owner_email": owner_email,
                "plate":       plate,
                "valid_until": str(expiry) if expiry else "—"
            })

    def _log(self, qrdata, status, action="entry"):
        """Insert a scan record into history. action is 'entry' or 'exit'."""
        try:
            cur = self.sql.sql.cursor()
            cur.execute(
                "INSERT INTO history(data, guard, status, action) VALUES (%s, %s, %s, %s)",
                (qrdata, session["user_id"], status, action)
            )
            self.sql.sql.commit()
            cur.close()
        except Exception as e:
            print("History log error:", e)