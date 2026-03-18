from flask import Blueprint, render_template, request, jsonify, session, redirect
from other.mysql_ import SQL


class Staff:
    def __init__(self):
        self.staff = Blueprint("staff", __name__, url_prefix="/staff")
        self.sql = SQL()
        self.routes()

    def _protect(self):
        if "user_id" not in session or session["role"] != "staff":
            if request.is_json:
                return jsonify({"status": "unauthenticated", "message": "Please log in"}), 401
            return redirect("/")
        if session.get("role") not in ("user", "guard", "staff"):
            return jsonify({"status": "forbidden", "message": "Staff access required"}), 403

    def routes(self):
        self.staff.before_request(self._protect)

        # ─── PAGES ────────────────────────────────────────

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
        
        @self.staff.route("/getuserdata", methods=["GET"])
        def getuserdata():
            try:
                data = self.sql.getuserbyid(session["user_id"])
            except:
                return {"status":"bad", "messages": "sorry something went wrong"}
            return jsonify({"status":"good", "data":data})
        
        @self.staff.route("/updateuser",methods=["PUT"])
        def updateuser():
            data = request.get_json()
            username = data.get("username")
            email = data.get("email")
            
            try:
                self.sql.updateuser(username,email, session["user_id"])
    
            except:
                return jsonify({"status":"bad", "message":"Failed to update"})
            
            return jsonify({"status":"good", "message":"Updated succesfully"})
            
            

        # ─── QR API ───────────────────────────────────────

        @self.staff.route("/my_qr", methods=["GET"])
        def my_qr():
            qrs = self.sql.getqrbyuser(session["user_id"])
            if qrs:
                return jsonify({"status": "good", "data": qrs})
            
            return jsonify({"status": "empty", "message": "No QR codes found"})

        @self.staff.route("/save_qr", methods=["POST"])
        def save_qr():
            data = request.get_json()
            qr_data = data.get("data").strip()
            plate = data.get("plate").strip()
            valid_until = data.get("valid_until")

            if not qr_data:
                return jsonify({"status": "bad", "message": "QR data is required"})
            try:
                self.sql.saveqr(qr_data,plate,valid_until,session["user_id"])
            except:
                return jsonify({"status":"bad", "message": "Please fill the valid dates"})
            return jsonify({"status": "good", "message": "QR saved successfully"})
        
        @self.staff.route("/test",methods=["POST"])
        def test():
            return {"test":"complete"}

        @self.staff.route("/delete_qr/<int:id>", methods=["DELETE"])
        def delete_qr(id):
            self.sql.deleteqr(id, session["user_id"])
            return jsonify({"status": "ok", "message": "QR deleted"})
        
