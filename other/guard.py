from flask import Blueprint, request, jsonify, render_template, session, redirect
from datetime import datetime
from other.cache import cache
from other.mysql_ import SQL


class Guard:
    def __init__(self, sql):
        self.guard = Blueprint("guard", __name__, url_prefix="/guard")
        self.sql:SQL = sql
        self.cache = cache

        self.routes()

    def _protect(self):
        if "user_id" not in session or session["role"] != "guard":
            if request.is_json:
                return (
                    jsonify({"status": "unauthenticated", "message": "Please log in"}),
                    401,
                )
            return redirect("/")
        if session.get("role") not in ("guard", "user", "staff"):
            return (
                jsonify({"status": "forbidden", "message": "Guard access required"}),
                403,
            )

    def routes(self):
        self.guard.before_request(self._protect)

        # ─── PAGES ────────────────────────────────────────

        @self.guard.route("/scan")
        def scanner():
            return render_template("guard/scanner.html")

        @self.guard.route("/history")
        def history():
            return render_template("guard/history.html")

        @self.guard.route("/parking")
        def parking():
            return render_template("guard/parking.html")

        # ─── API ──────────────────────────────────────────

        @self.guard.route("/profile")
        def profile():
            return render_template("guard/profile.html")

        @self.guard.route("/getuserdata", methods=["GET"])
        def getuserdata():
            try:
                data = self.sql.getuserbyid(session["user_id"])
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "Something went wrong"})
            return jsonify({"status": "good", "data": data})

        @self.guard.route("/update_password", methods=["PUT"])
        def update_password():
            data = request.get_json()
            cur_pw = data.get("current_password", "")
            new_pw = data.get("new_password", "")
            con_pw = data.get("confirm_password", "")
            if not all([cur_pw, new_pw, con_pw]):
                return jsonify({"status": "bad", "message": "All fields are required."})
            if len(new_pw) < 8:
                return jsonify(
                    {
                        "status": "bad",
                        "message": "New password must be at least 8 characters.",
                    }
                )
            if new_pw != con_pw:
                return jsonify(
                    {"status": "bad", "message": "New passwords do not match."}
                )
            result = self.sql.update_password(session["user_id"], cur_pw, new_pw)
            status = "good" if result["ok"] else "bad"
            return jsonify({"status": status, "message": result["message"]})

        @self.guard.route("/request_deletion", methods=["POST"])
        def request_deletion():
            data = request.get_json()
            password = (data.get("password") or "").strip()
            if not password:
                return jsonify(
                    {"status": "bad", "message": "Password is required to confirm."}
                )
            try:
                cur = self.sql._cursor()
                cur.execute(
                    "SELECT password FROM users WHERE id = %s", (session["user_id"],)
                )
                row = cur.fetchone()
                cur.close()
                if not row or not self.sql._check(password, row[0]):
                    return jsonify(
                        {
                            "status": "bad",
                            "message": "Incorrect password. Please try again.",
                        }
                    )
            except Exception as e:
                print(e)
                return jsonify(
                    {"status": "bad", "message": "Could not verify password."}
                )

            ok = self.sql.request_deletion(session["user_id"])
            if ok:
                return jsonify(
                    {
                        "status": "good",
                        "message": "Your account has been scheduled for deletion in 30 days. You will now be logged out.",
                    }
                )
            return jsonify(
                {"status": "bad", "message": "Something went wrong. Please try again."}
            )
            
        

        @self.guard.route("/getParking")
        def getParking():
            parking = self.sql.getparking()
            return jsonify(parking)

        @self.guard.route("/my_history", methods=["GET"])
        def my_history():
            try:
                page = max(1, int(request.args.get("page", 1)))
                limit = min(100, max(1, int(request.args.get("limit", 10))))
                year = int(request.args["year"]) if request.args.get("year") else None
                month = int(request.args["month"]) if request.args.get("month") else None
                day = int(request.args["day"]) if request.args.get("day") else None
                if year is not None and not 1900 <= year <= 9999:
                    raise ValueError
                if month is not None and not 1 <= month <= 12:
                    raise ValueError
                if day is not None and not 1 <= day <= 31:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({"status": "bad", "message": "Invalid date filter"}), 400
            offset = (page - 1) * limit

            try:
                data = self.sql.gethistorybyguard(
                    session["user_id"], limit=limit, offset=offset,
                    year=year, month=month, day=day
                )
                total = self.sql.counthistorybyguard(
                    session["user_id"], year=year, month=month, day=day
                )

                serialized = []
                for row in data:
                    serialized.append(
                        [
                            (
                                str(v)
                                if not isinstance(v, (int, str, float, type(None)))
                                else v
                            )
                            for v in row
                        ]
                    )

                return jsonify(
                    {
                        "status": "good",
                        "data": serialized,
                        "total": total,
                        "page": page,
                        "limit": limit,
                        "pages": max(1, -(-total // limit)),
                    }
                )
            except Exception as e:
                print("History error:", e)
                return jsonify({"status": "bad", "message": "Failed to fetch history"})
            
        @self.guard.route("/manual_entry", methods=["POST"])
        def manual_entry():
            data = request.get_json(silent=True) or {}
            plate = (data.get("plate") or "").strip().upper()
            vehicle_type = (data.get("vehicle_type") or "car").strip().lower()
            action = (data.get("action") or "").strip().lower()
            department = (data.get("department") or "VISITOR").strip().upper()
            if not plate or len(plate) > 20 or action not in ("entry", "exit") or vehicle_type not in ("car", "motorcycle"):
                return jsonify({"status": "bad", "message": "Invalid input"})
            space = 2 if vehicle_type == "car" else 1
            if action == "entry":
                p = self.sql.getparking()
                free = int(round((p["total"] - p["total_occupied"]) * 2))
                if free < space:
                    return jsonify({"status": "bad", "message": "Parking lot has no available space"})
            is_authorized = self.sql.isplateauthorized(plate)
            if not self._log(None, "accepted", action, department, plate, is_authorized=is_authorized):
                return jsonify({"status": "bad", "message": "Please try again"})
            self.sql.updateparking(space, action)
            self.cache.deletethathas("history")
            message = (
                "Added successfully"
                if is_authorized
                else "Access granted. Plate not found in registered records; marked unauthorized."
            )
            return jsonify({"status": "good", "message": message, "is_authorized": is_authorized})
            
                    

        @self.guard.route("/check_qr", methods=["POST"])
        def check_qr():
            data = request.get_json(silent=True) or {}
            qrdata = (data.get("data") or "").strip()
            action = (data.get("action") or "entry").strip().lower()

            if action not in ("entry", "exit"):
                return jsonify({"status": "bad", "message": "Invalid action", "scan_result": "failed"})
            if not qrdata:
                return jsonify({"status": "bad", "message": "No QR data provided", "scan_result": "failed"})

            new_action = "IN" if action == "entry" else "OUT"

            def finish(status, message, scan_result, log_status, info=None, **extra):
                """Log the scan, clear cached history/QR data, and build the response."""
                info = info or {}
                self._log(qrdata, log_status, action, info.get("department"), info.get("plate"))
                self.cache.deletethathas("history")
                self.cache.deletethathas("qrcode")
                payload = {"status": status, "message": message, "scan_result": scan_result, **info, **extra}
                return jsonify(payload)

            qr = self.sql.getqrbydata(qrdata)

            # ── QR NOT FOUND ──
            if not qr:
                return finish("bad", "QR code not recognized", "failed", "failed")

            # qrcode columns:
            # 0:id 1:code 2:plate 3:owner_name 4:owner_email 5:owner_phone
            # 6:department 7:expiry 8:status 9:created_by 10:created_at
            # 11:car_status 12:vehicle_type 13:space_units
            plate = qr[2] or "—"
            expiry = qr[7]
            qr_status = (qr[8] or "active").lower()
            car_status = qr[11]
            vehicle_type = qr[12] or "car"
            units = qr[13] or (1 if vehicle_type == "motorcycle" else 2)  # car = 2, motorcycle = 1

            info = {
                "owner_name": qr[3] or "—",
                "owner_email": qr[4] or "—",
                "plate": plate,
                "department": qr[6],
                "vehicle_type": vehicle_type,
                "valid_until": str(expiry) if expiry else "—",
            }

            # ── NOT ACTIVE (revoked / still pending approval) ──
            if qr_status == "revoked":
                return finish("bad", "QR code has been revoked", "failed", "failed", info)
            if qr_status != "active":
                return finish("bad", "QR code is not active yet", "failed", "failed", info)

            # ── EXPIRED ──
            if expiry and datetime.now() > expiry:
                return finish("expired", "QR code has expired", "expired", "expired", info)

            # ── DUPLICATE ACTION ──
            if car_status == new_action:
                return finish("Invalid", f"The vehicle is already {car_status}", "failed", "failed", info)

            # ── CAPACITY (entry only) ──
            if new_action == "IN":
                parking = self.sql.getparking()
                free_units = int(round((parking["total"] - parking["total_occupied"]) * 2))
                if free_units < units:
                    return finish("bad", "Parking lot has no available space", "failed", "failed", info)

            # ── ACCEPTED: update parking first, then the car status ──
            if not self.sql.updateparking(units, action):
                return finish("bad", "Could not update parking, please try again", "failed", "failed", info)

            if not self.sql.set_car_status(qrdata, new_action):
                # undo the parking change so the count never drifts from the car status
                self.sql.updateparking(units, "exit" if action == "entry" else "entry")
                return finish("bad", "Could not update vehicle status, please try again", "failed", "failed", info)

            return finish("good", "Access Granted", "accepted", "accepted", info, action=action)

    def _log(self, qrdata, status, action="entry", department=None, plate=None, is_authorized=None):
        """Insert a scan record into history. action is 'entry' or 'exit'."""
        if is_authorized is None:
            is_authorized = status == "accepted" and qrdata is not None
        inserted = self.sql.inserthistory(
            qrdata, session["user_id"], status, action, plate, department,
            is_authorized=is_authorized
        )
        
        return inserted
