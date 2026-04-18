from flask import Blueprint, request, jsonify, render_template, session, redirect
from other.mysql_ import SQL


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

        @self.guard.route("/scan")
        def scanner():
            return render_template("guard/scanner.html")

        @self.guard.route("/check_qr", methods=["POST"])
        def check_qr():
            data = request.get_json()
            qrdata = data.get("data", "").strip()

            if not qrdata:
                return jsonify({"status": "bad", "message": "No QR data provided"})

            qr = self.sql.getqrbydata(qrdata)

            if qr:
                # qr columns: 0:id, 1:data, 2:plate, 3:owner_name, 4:owner_email, 5:expiry, 6:status, 7:created_by, 8:created_at
                # (adjust indices to match your actual DB column order after migration)
                plate      = qr[2] or None
                owner_name = qr[3] if len(qr) > 3 else None
                owner_email= qr[4] if len(qr) > 4 else None
                expiry     = str(qr[5]) if len(qr) > 5 and qr[5] else None

                self.sql.inserthistory(qrdata, session["user_id"], "accepted")

                return jsonify({
                    "status":      "good",
                    "message":     "Access Granted",
                    "owner_name":  owner_name or "—",
                    "owner_email": owner_email or "—",
                    "plate":       plate or "—",
                    "valid_until": expiry or "—"
                })

            self.sql.inserthistory(qrdata, session["user_id"], "failed")
            return jsonify({
                "status":  "bad",
                "message": "QR code not recognized"
            })