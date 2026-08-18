from flask import Blueprint, session, request, redirect,jsonify
from other.mysql_ import SQL

class Users:
    def __init__(self, sql):
        self.users = Blueprint("users",__name__, url_prefix="/users")
        self.sql:SQL = sql
        
        
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
    
    def routes(self):
        #self.staff.before_request(self._protect)
    
    
    
        
            
    
        @self.users.route("/get_request")
        def get_request():
            res = self.sql.fetchselfrequest(session["users_id"])
            
            return res
    
        @self.users.route("/add_request")
        def add_request():
            
            data:dict = request.get_json()
            plate = data.get("plate")
            owner = data.get("user_name")
            email = data.get("email")
            vtype = data.get("vtype")
            vspace = data.get("vspace")
            
            res = self.sql.addqrrequest(plate, owner, email,session["user_id"],vtype,vspace)
            
            if res:
                return {
                    "status":"good",
                    "message":"successfully added the request"
                }
                
            return {
                    "status":"failed",
                    "message":"please try again "
                }
            
            
            
        def request_renewal():
            data: dict = request.get_json()
            code = data.get("qrcode","")
            
            
                