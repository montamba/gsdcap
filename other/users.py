from flask import Blueprint, session, request, redirect,jsonify, render_template
from other.mysql_ import SQL

class Users:
    def __init__(self, sql):
        self.users = Blueprint("users",__name__, url_prefix="/users")
        self.sql:SQL = sql
        
        self.routes()
        
        
    def _protect(self):
            if "user_id" not in session or session["role"] != "user":
            #if True:
                if request.is_json:
                    return (
                        jsonify({"status": "unauthenticated", "message": "Please log in"}),
                        401,
                    )
                return redirect("/progress")
            if session.get("role") not in ("user", "guard", "staff"):
                return (
                    jsonify({"status": "forbidden", "message": "Staff access required"}),
                    403,
                )
    
    def routes(self):
        self.users.before_request(self._protect)
        
        @self.users.route("/status")
        def staus():
            return render_template("users/userqr.html")
        
        @self.users.route("/profile")
        def profile():
            return render_template("users/userprofile.html")
        
        
        @self.users.route("get_profile",methods=["GET"])
        def get_profile():
            data = self.sql.getuserbyemailandrole(session["email"],session["role"])
            print(data)
            
            if data:
                response = {
                    "status":"good",
                    "username":data[1],
                    "email":data[2]
                }
                return response
            
            return {"status":"bad", "message":"Try again"}
    
    
    
    
        @self.users.route("/myemail", methods=["GET"])
        def myemail():
            return jsonify({
                "data":{"email":session["email"]}
            })
        
            
    
        @self.users.route("/get_request", methods=["GET"])
        def get_request():
            limit = int(request.args.get("limit",5))
            page = int(request.args.get("page",1))
            page = (page-1) * limit
            res = self.sql.fetchselfrequest(session["email"], limit, page)
            total = self.sql.countallselfrequest(session["user_id"])
            
            print("respose=====123  ")
            print(res)
            
            
            
            
            return jsonify({
                "status":"success",
                "data":res,
                "pages":total
            })
    
        @self.users.route("/add_request", methods=["POST"])
        def add_request():
            data:dict = request.get_json()
            plate = (data.get("plate")).strip()
            owner = (data.get("user_name")).strip()
            email = (data.get("email")).strip()
            phone = (data.get("phone")).strip()
            vtype = (data.get("vtype")).strip()
            
            required_fields = [plate, owner, email, vtype]

            if not all(required_fields):
                return jsonify({"error": "All fields are required"}), 400
            
            if email != session["email"]:
                return jsonify({
                    "status":"failed",
                    "message":"Did you just change the email?"
                })
                
            
            
            res = self.sql.addqrrequest(plate, owner, session["email"], phone, session["user_id"],vtype)
            
            
            if res:
                return jsonify({
                    "status":"good",
                    "message":"successfully added the request"
                })
                
            return jsonify({
                    "status":"failed",
                    "message":"please try again "
                })
            
            
            
        def request_renewal():
            data: dict = request.get_json()
            code = data.get("qrcode","")
            
            
                