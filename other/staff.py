from flask import Blueprint, render_template, request, jsonify, session, redirect
import re
from datetime import datetime
from other.cache import cache

def _ser(rows):
    return [[str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in r] for r in (rows or [])]
import random


class Staff:
    def __init__(self, sql):
        self.staff = Blueprint("staff", __name__, url_prefix="/staff")
        self.sql = sql
        self.cache = cache

        self.routes()

    def _protect(self):
        if "user_id" not in session or session["role"] != "staff":
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
            
    def _generate_unique_code(self):
        abc = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
        while True:
            code = "GSD-" + "".join(random.sample(abc, 5)) + "-" + "".join(random.sample(abc, 5))
            if not self.sql.codeindata(code):
                return code

    def routes(self):
        self.staff.before_request(self._protect)

        @self.staff.route("/generate")
        def generate():
            return render_template("staff/generate.html")

        @self.staff.route("/history")
        def history():
            return render_template("staff/history.html")

        @self.staff.route("/search")
        def search():
            return render_template("staff/search.html")

        @self.staff.route("/profile")
        def profile():
            return render_template("staff/profile.html")
        
        @self.staff.route("/request_page")
        def request_page():
            return render_template("staff/request.html")
        
        
     
            
        
        @self.staff.route("/generate_code")
        def generate_code():
            return jsonify({"code": self._generate_unique_code()})

        @self.staff.route("/userreques")
        def user_request_page():
            return render_template("staff/userrequest.html")

        @self.staff.route("/qr_requests", methods=["GET"])
        def qr_requests():
            page = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            
            
            for i in range(3):
                data = self.sql.getqrrequestwithusersandqrcode(limit=limit, offset=offset)
                if data: break
            
            
            total = self.sql.count_qr_pending_by_type("request_qr")

            
            return jsonify({
                "status": "good",
                "data": _ser(data),
                "total": total,
                "page": page,
                "pages": max(1, -(-total // limit)),
            })

        @self.staff.route("/qr_renewals", methods=["GET"])
        def qr_renewals():
            page = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit


            for i in range(3):
                data = self.sql.getqrrenewalwithusersandqrcode(limit=limit, offset=offset)
                if data: break
            
            
            total = self.sql.count_qr_pending_by_type("qr_renewal")

            
            return jsonify({
                "status": "good",
                "data": _ser(data),
                "total": total,
                "page": page,
                "pages": max(1, -(-total // limit)),
            })

        @self.staff.route("/request_detail/<int:pending_id>", methods=["GET"])
        def request_detail(pending_id):
            row = self.sql.get_qr_pending_detail(pending_id)
            if not row:
                return jsonify({"status": "bad", "message": "Request not found"})
            serialized = [
                str(v) if not isinstance(v, (int, str, float, type(None))) else v for v in row
            ]
            return jsonify({"status": "good", "data": serialized})

        @self.staff.route("/approve_request/<int:pending_id>", methods=["PUT"])
        def approve_request(pending_id):
            detail = self.sql.get_qr_pending_detail(pending_id)
            if not detail:
                return jsonify({"status": "bad", "message": "Request not found"})
            if detail[2] != "pending":
                return jsonify({"status": "bad", "message": "Request already reviewed"})

            qr_id = detail[4]
            code = self._generate_unique_code()
            ok = self.sql.approve_qr_request(pending_id, qr_id, code, session["user_id"])
            if ok:
                self.cache.deletethathas("qrcode")
                return jsonify({"status": "good", "message": f"Approved — QR code: {code}"})
            return jsonify({"status": "bad", "message": "Failed to approve request"})

        @self.staff.route("/approve_renewal/<int:pending_id>", methods=["PUT"])
        def approve_renewal(pending_id):
            data = request.get_json() or {}
            new_expiry = (data.get("expiry") or "").strip()
            if not new_expiry:
                return jsonify({"status": "bad", "message": "New expiry date is required"})
            try:
                if datetime.strptime(new_expiry[:10], "%Y-%m-%d").date() < datetime.now().date():
                    return jsonify({"status": "bad", "message": "Expiry is in the past"})
            except ValueError:
                return jsonify({"status": "bad", "message": "Invalid date"})

            detail = self.sql.get_qr_pending_detail(pending_id)
            if not detail:
                return jsonify({"status": "bad", "message": "Request not found"})
            if detail[2] != "pending":
                return jsonify({"status": "bad", "message": "Request already reviewed"})

            qr_id = detail[4]
            ok = self.sql.approve_qr_renewal(pending_id, qr_id, new_expiry, session["user_id"])
            if ok:
                self.cache.deletethathas("qrcode")
                return jsonify({"status": "good", "message": "Renewal approved"})
            return jsonify({"status": "bad", "message": "Failed to approve renewal"})

        @self.staff.route("/reject_request/<int:pending_id>", methods=["PUT"])
        def reject_request(pending_id):
            detail = self.sql.get_qr_pending_detail(pending_id)
            if not detail:
                return jsonify({"status": "bad", "message": "Request not found"})
            if detail[2] != "pending":
                return jsonify({"status": "bad", "message": "Request already reviewed"})

            ok = self.sql.reject_qr_pending(pending_id, session["user_id"])
            if ok:
                return jsonify({"status": "good", "message": "Request rejected"})
            return jsonify({"status": "bad", "message": "Failed to reject request"})

        @self.staff.route("/getuserdata", methods=["GET"])
        def getuserdata():
            try:
                data = self.sql.getuserbyid(session["user_id"])
            except:
                return {"status": "bad", "message": "Sorry something went wrong"}
            return jsonify({"status": "good", "data": data})

        @self.staff.route("/request_deletion", methods=["POST"])
        def request_deletion():
            data = request.get_json()
            password = (data.get("password") or "").strip()
            if not password:
                return jsonify(
                    {"status": "bad", "message": "Password is required to confirm."}
                )

            # Verify the user's current password before scheduling deletion
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

        @self.staff.route("/update_password", methods=["PUT"])
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
            return jsonify(
                {
                    "status": "good" if result["ok"] else "bad",
                    "message": result["message"],
                }
            )

        @self.staff.route("/updateuser", methods=["PUT"])
        def updateuser():
            data = request.get_json(silent=True) or {}
            username = (data.get("username") or "").strip()
            email = (data.get("email") or "").strip().lower()
            if len(username) < 3 or "@" not in email:
                return jsonify({"status": "bad", "message": "Enter a valid username and email"})
            if not self.sql.updateuser(username, email, session["user_id"]):
                return jsonify({"status": "bad", "message": "Username or email already taken"})
            session["email"] = email
            self.cache.deletethathas("users")
            return jsonify({"status": "good", "message": "Updated successfully"})

        @self.staff.route("/recentqr")
        def recent():
            name = "staff_qrcode"
            keyname = name + str(0)
            try:
                if not self.cache.check_key(keyname):
                    sqldata = self.sql.getallqr(limit=5, offset=0)
                    self.cache.add(keyname, sqldata)
                data = self.cache.get(keyname)

                serialized = [
                    [
                        (
                            str(v)
                            if not isinstance(v, (int, str, float, type(None)))
                            else v
                        )
                        for v in row
                    ]
                    for row in data
                ]
                return jsonify({"status": "good", "data": serialized})
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "error"})
            

        @self.staff.route("/all_qr", methods=["GET"])
        def all_qr():
            name = "staff_qrcode"
            page = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            keyname = name + str(offset)
            if not self.cache.check_key(keyname):
                sqlqrs = self.sql.getallqr(limit=limit, offset=offset)
                self.cache.add(keyname, sqlqrs)
            qrs = self.cache.get(keyname)
            print(qrs)
            

            keyname1 = name + "count"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.countallqr()
                self.cache.add(keyname1, sqltotal)
            total = self.cache.get(keyname1)

            serialized = [
                [
                    str(v) if not isinstance(v, (int, str, float, type(None))) else v
                    for v in row
                ]
                for row in qrs
            ]
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

        @self.staff.route("/my_qr", methods=["GET"])
        def my_qr():
            name = "staff_qrcode"
            page = max(1, int(request.args.get("page", 1)))
            limit = int(request.args.get("limit", 5))
            offset = (page - 1) * limit

            keyname = name + str(offset) + str(session["user_id"])
            if not self.cache.check_key(keyname):
                sqlqrs = self.sql.getqrbyuser(
                    session["user_id"], limit=limit, offset=offset
                )
                self.cache.add(keyname, sqlqrs)
            qrs = self.cache.get(keyname)

            keyname1 = name + "count_by_user"
            if not self.cache.check_key(keyname1):
                sqltotal = self.sql.countqrbyuser(session["user_id"])
                self.cache.add(keyname1, sqltotal)
            total = self.cache.get(keyname1)

            return jsonify(
                {
                    "status": "good",
                    "data": _ser(qrs),
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": max(1, -(-total // limit)),
                }
            )

        @self.staff.route("/stats")
        def getStats():
            keyname = "staff_qrcode_qrstats"
            if not self.cache.check_key(keyname):
                sqldata = self.sql.getqrstats()
                self.cache.add(keyname, sqldata)
            data = self.cache.get(keyname)
            
            data = {"data":data}

            return data

        @self.staff.route("/save_qr", methods=["POST"])
        def save_qr():
            d = request.get_json(silent=True) or {}
            s = lambda k: (d.get(k) or "").strip()
            code = s("data")
            plate = re.sub(r"\s+", "", s("plate")).upper()
            name, email = s("owner_name"), s("owner_email").lower()
            phone = s("owner_number") or None
            vtype, dept, expiry = s("vehicle_type").lower(), s("department").upper(), s("valid_until")
            if not all([code, plate, name, email, expiry, vtype, dept]):
                return jsonify({"status": "bad", "message": "Fill in all required fields"})
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                return jsonify({"status": "bad", "message": "Invalid email"})
            if len(plate) > 20:
                return jsonify({"status": "bad", "message": "Plate too long"})
            if vtype not in ("car", "motorcycle"):
                return jsonify({"status": "bad", "message": "Vehicle type must be car or motorcycle"})
            try:
                if datetime.strptime(expiry, "%Y-%m-%d").date() < datetime.now().date():
                    return jsonify({"status": "bad", "message": "Expiry is in the past"})
            except ValueError:
                return jsonify({"status": "bad", "message": "Invalid date"})
            if self.sql.codeindata(code):
                return jsonify({"status": "bad", "message": "Code already exists, regenerate"})
            if not self.sql.saveqr(code, plate, expiry, session["user_id"], name, email, phone, vtype, dept):
                return jsonify({"status": "bad", "message": "Save failed"})
            self.cache.deletethathas("qrcode")
            if not self.sql.getqrbydata(code):
                return jsonify({"status": "bad", "message": "Saved but could not verify"})
            return jsonify({"status": "good", "message": f"Saved and verified: {code}", "code": code})

        @self.staff.route("/renew_qr/<int:qr_id>", methods=["PUT"])
        def renew_qr(qr_id):
            """Set a new expiry date on any QR code — staff can manage all."""

            data = request.get_json(silent=True) or {}
            new_expiry = (data.get("expiry") or "").strip()
            if not new_expiry:
                return jsonify({"status": "bad", "message": "Expiry date is required"})
            try:
                if datetime.strptime(new_expiry[:10], "%Y-%m-%d").date() < datetime.now().date():
                    return jsonify({"status": "bad", "message": "Expiry is in the past"})
            except ValueError:
                return jsonify({"status": "bad", "message": "Invalid date"})
            try:
                self.sql.renewqr_any(qr_id, new_expiry)
                self.cache.deletethathas("qrcode")
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "Failed to renew QR"})
            return jsonify({"status": "good", "message": "QR renewed and reactivated"})

        @self.staff.route("/revoke_qr", methods=["PUT"])
        def revoke_qr():
            code = request.args.get("qrcode")
            plate = request.args.get("plate")
            try:
                qr = self.sql.getqrbydata(code)  
                was_in = qr and qr[11] == "IN"

                cur = self.sql._cursor()
                cur.execute(
                    "UPDATE qrcode SET status='revoked', car_status='OUT' WHERE data=%s AND plate=%s",
                    (code, plate),
                )
                self.sql._commit()
                cur.close()

                if was_in:
                    self.sql.updateparking(qr[13], "exit") 

                self.cache.deletethathas("qrcode")
                self.cache.deletethathas("history")
                return jsonify({"status": "good", "message": "QR revoked successfully"})
            except Exception as e:
                print(e)
                return jsonify({"status": "bad", "message": "Failed to revoke QR"})

        @self.staff.route("/send_qr_email", methods=["POST"])
        def send_qr_email():

            data = request.get_json(silent=True) or {}
            qr_data = (data.get("data") or "").strip()
            owner_name = (data.get("owner_name") or "Anonymous").strip()
            owner_email = (data.get("owner_email") or "").strip()
            plate = (data.get("plate") or "").strip()
            valid_until = (data.get("valid_until") or "").strip()


            if not owner_email:
                return jsonify(
                    {"status": "bad", "message": "Owner email is required to send"}
                )
            if not qr_data:
                return jsonify({"status": "bad", "message": "QR data is required"})
            if not self.sql.getqrbydata(qr_data):
                return jsonify({"status": "bad", "message": "Save the QR code first"})
            ok = self.sql.send_qr_email(owner_email, owner_name, qr_data, plate, valid_until)
            if not ok:
                return jsonify({"status": "bad", "message": "Email failed to send. Check SMTP settings."})
            return jsonify({"status": "good", "message": f"QR sent to {owner_email}"})

        @self.staff.route("/delete_qr/<int:id>", methods=["DELETE"])
        def delete_qr(id):
            self.sql.deleteqr(id, session["user_id"])
            self.cache.deletethathas("qrcode")
            return jsonify({"status": "ok", "message": "QR deleted"})
