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
            data   = request.get_json()
            qrdata = data.get("data", "").strip()

            if not qrdata:
                return jsonify({"status": "bad", "message": "No QR data provided"})

            qr = self.sql.getqrbydata(qrdata)

            if qr:
                plate = qr[2] if qr[2] else None
                self.sql.inserthistory(qrdata, session["user_id"], "accepted")
                msg = f"Property of {plate}" if plate else "Access granted"
                return jsonify({"status": "good", "message": msg})

            self.sql.inserthistory(qrdata, session["user_id"], "failed")
            return jsonify({"status": "bad", "message": "QR code not recognized"})