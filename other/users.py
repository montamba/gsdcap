from flask import Blueprint, session, request, redirect, jsonify, render_template
from other.mysql_ import SQL


class Users:
    def __init__(self, sql):
        self.users = Blueprint("users", __name__, url_prefix="/users")
        self.sql: SQL = sql

        self.routes()

    def _protect(self):
        if "user_id" not in session or session["role"] != "user":
            if request.is_json:
                return (
                    jsonify({"status": "unauthenticated", "message": "Please log in"}),
                    401,
                )
            return redirect("/")
        if session.get("role") not in ("user", "guard", "staff"):
            return (
                jsonify({"status": "forbidden", "message": "Staff access required"}),
                403,
            )

    def routes(self):
        self.users.before_request(self._protect)

        # ─── PAGES ────────────────────────────────────────

        @self.users.route("/status")
        def staus():
            return render_template("users/userqr.html")

        @self.users.route("/profile")
        def profile():
            return render_template("users/userprofile.html")

        # ─── PROFILE ──────────────────────────────────────

        @self.users.route("/get_profile", methods=["GET"])
        def get_profile():
            data = self.sql.getuserbyemailandrole(session["email"], session["role"])

            if data:
                return jsonify(
                    {
                        "status": "good",
                        "username": data[1],
                        "email": data[2],
                    }
                )

            return jsonify({"status": "bad", "message": "Try again"})

        @self.users.route("/myemail", methods=["GET"])
        def myemail():
            return jsonify({"data": {"email": session["email"]}})

        @self.users.route("/update_username", methods=["POST"])
        def update_username():
            data: dict = request.get_json()
            new_username = (data.get("newusername") or "").strip()
            password = (data.get("password") or "").strip()

            if len(new_username) < 3:
                return jsonify({"status": "bad", "message": "Invalid username"})

            valid = self.sql.verifyuser(session["email"], password)
            if not valid:
                return jsonify({"status": "bad", "message": "Wrong Credentials"})

            current = self.sql.getuserbyid(session["user_id"])
            if not current:
                return jsonify({"status": "bad", "message": "User not found"})

            ok = self.sql.updateuser(new_username, current[1], session["user_id"])
            if ok:
                return jsonify(
                    {"status": "good", "message": "Username updated successfully"}
                )
            return jsonify(
                {"status": "bad", "message": "Something went wrong, please try again"}
            )

        @self.users.route("/update_email", methods=["PUT"])
        def update_email():
            data = request.get_json()
            email = (data.get("email") or "").strip().lower()

            if not email:
                return jsonify({"status": "bad", "message": "Email is required"})
            if "@" not in email:
                return jsonify(
                    {"status": "bad", "message": "Enter a valid email address"}
                )

            current = self.sql.getuserbyid(session["user_id"])
            if not current:
                return jsonify({"status": "bad", "message": "User not found"})

            ok = self.sql.updateuser(current[0], email, session["user_id"])
            if not ok:
                return jsonify({"status": "bad", "message": "Failed to update email"})

            session["email"] = email
            return jsonify({"status": "good", "message": "Email updated successfully"})

        @self.users.route("/update_password", methods=["PUT"])
        def update_password():
            data = request.get_json()
            current_pw = data.get("current_password", "")
            new_pw = data.get("new_password", "")
            confirm_pw = data.get("confirm_password", "")

            if not all([current_pw, new_pw, confirm_pw]):
                return jsonify(
                    {"status": "bad", "message": "All password fields are required"}
                )
            if len(new_pw) < 8:
                return jsonify(
                    {
                        "status": "bad",
                        "message": "New password must be at least 8 characters",
                    }
                )
            if new_pw != confirm_pw:
                return jsonify(
                    {"status": "bad", "message": "New passwords do not match"}
                )

            result = self.sql.update_password(session["user_id"], current_pw, new_pw)
            return jsonify(
                {
                    "status": "good" if result["ok"] else "bad",
                    "message": result["message"],
                }
            )

        # ─── QR REQUESTS ──────────────────────────────────

        @self.users.route("/get_request", methods=["GET"])
        def get_request():
            limit = int(request.args.get("limit", 5))
            page = int(request.args.get("page", 1))
            offset = (page - 1) * limit

            res = self.sql.fetchselfrequest(session["email"], limit, offset)
            total = self.sql.countallselfrequest(session["user_id"]) or 0
            pages = max(1, -(-total // limit)) if limit else 1

            serialized = [
                [
                    str(v) if not isinstance(v, (int, str, float, type(None))) else v
                    for v in row
                ]
                for row in (res or [])
            ]

            return jsonify(
                {
                    "status": "good",
                    "data": serialized,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": pages,
                }
            )
            
        @self.users.route("/myqr", methods=["GET"])
        def myqr():
            limit = int(request.args.get("limit", 5))
            page = int(request.args.get("page", 1))
            offset = (page - 1) * limit

            res = self.sql.getqrbyemailandhasdata(session["email"], limit, offset)
            print("my email ===================", session["email"])
            print(res)
            total = self.sql.countqrbyemailandhasdata(session["email"]) or 0
            print("================================Toootal: ", total)
            pages = max(1, -(-total // limit)) if limit else 1

            

            return jsonify(
                {
                    "status": "good",
                    "data": res,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": pages,
                }
            )


        @self.users.route("/add_request", methods=["POST"])
        def add_request():
            data: dict = request.get_json()
            plate = (data.get("plate") or "").strip()
            owner = (data.get("user_name") or "").strip()
            email = (data.get("email") or "").strip().lower()
            phone = (data.get("phone") or "").strip()
            vtype = (data.get("vtype") or "").strip().lower()

            required_fields = [plate, owner, email, vtype]

            if not all(required_fields):
                return jsonify({"status": "bad", "message": "All fields are required"})

            if email != session["email"].strip().lower():
                return jsonify(
                    {
                        "status": "failed",
                        "message": "Did you just change the email?",
                    }
                )

            res = self.sql.addqrrequest(
                plate, owner, session["email"], phone, session["user_id"], vtype
            )

            if res:
                return jsonify(
                    {"status": "good", "message": "successfully added the request"}
                )

            return jsonify({"status": "failed", "message": "please try again"})

        @self.users.route("/request_renewal", methods=["POST"])
        def request_renewal():
            data: dict = request.get_json()
            code = (data.get("qrcode") or "").strip()

            if not code:
                return jsonify({"status": "bad", "message": "QR code is required"})

            ok = self.sql.requestrenewal(code, session["user_id"])
            if ok:
                return jsonify(
                    {"status": "good", "message": "Renewal request submitted"}
                )
            return jsonify(
                {"status": "bad", "message": "Failed to submit renewal request"}
            )