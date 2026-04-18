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

        @self.guard.route("/scan")
        def scanner():
            return render_template("guard/scanner.html")

        @self.guard.route("/check_qr", methods=["POST"])
        def check_qr():
            data = request.get_json()
            qrdata = (data.get("data") or "").strip()
            action = (data.get("action") or "entry").strip()  
            
            new_action = "IN" if action ==  "entry" else "OUT"
            print(action, new_action)

            if not qrdata:
                return jsonify({"status": "bad", "message": "No QR data provided"})

            qr = self.sql.getqrbydata(qrdata)

            # ── QR NOT FOUND ──────────────────────────────
            if not qr:
                self._log(qrdata, "failed")
                return jsonify({
                    "status":  "bad",
                    "message": "QR code not recognized",
                    "scan_result": "failed"
                })

            # qrcode columns:
            # 0:id  1:data  2:plate  3:owner_name  4:owner_email
            # 5:expiry  6:status  7:created_by  8:created_at  9:car_status
            plate = qr[2] or "—"
            owner_name  = qr[3] or "—"
            owner_email = qr[4] or "—"
            expiry = qr[5]          
            qr_status = (qr[6] or "active").lower()
            car_status = qr[9]

            # ── REVOKED ───────────────────────────────────
            if qr_status == "revoked":
                self._log(qrdata, "failed")
                return jsonify({
                    "status": "bad",
                    "message": "QR code has been revoked",
                    "scan_result": "failed",
                    "owner_name": owner_name,
                    "plate": plate
                })

            # ── EXPIRED ───────────────────────────────────
            if expiry and datetime.now() > expiry:
                self._log(qrdata, "expired")
                return jsonify({
                    "status": "expired",
                    "message": "QR code has expired",
                    "scan_result": "expired",
                    "owner_name": owner_name,
                    "plate": plate,
                    "valid_until": str(expiry)
                })
                
            if car_status == new_action:
                self._log(qrdata, "failed")
                return jsonify({
                    "status": "Invalid",
                    "message": "The vehicle already " + car_status,
                    "scan_result": "Invalid",
                    "owner_name": owner_name,
                    "plate": plate,
                    "valid_until": str(expiry)
                })
                
                

            # ── ACCEPTED ──────────────────────────────────
            self._log(qrdata, "accepted")

            try:
                cur = self.sql.sql.cursor()
                if action == "entry":
                    cur.execute(
                        "UPDATE qrcode SET car_status='IN' WHERE data=%s", (qrdata,)
                    )
                    self.sql.sql.commit()
                    self.sql.updateparking()
                else:
                    cur.execute(
                        "UPDATE qrcode SET car_status='OUT' WHERE data=%s", (qrdata,)
                    )
                    self.sql.updateparking()

                    self.sql.sql.commit()
                cur.close()
            except Exception as e:
                print("Parking update error:", e)

            return jsonify({
                "status": "good",
                "message": "Access Granted",
                "scan_result": "accepted",
                "action": action,
                "owner_name": owner_name,
                "owner_email": owner_email,
                "plate": plate,
                "valid_until": str(expiry) if expiry else "—"
            })

    def _log(self, qrdata, status):
        try:
            cur = self.sql.sql.cursor()
            cur.execute(
                "INSERT INTO history(data, guard, status) VALUES (%s, %s, %s)",
                (qrdata, session["user_id"], status)
            )
            self.sql.sql.commit()
            cur.close()
        except Exception as e:
            print("History log error:", e)