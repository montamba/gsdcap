from flask import Blueprint, request, jsonify, render_template, session
from other.mysql_ import SQL

class Guard:
    def __init__(self):
        self.guard = Blueprint("guard", __name__, url_prefix="/guard")
        self.sql = SQL()
        
        self.routes()
        
    def routes(self):
        @self.guard.route("/scan")
        def scanner():
            return render_template("/guard/scanner.html")
        
        @self.guard.route("/check_qr")
        def qr_code():
            data = request.get_json()
            qrdata = data.get("data")
            
            qr = self.sql.getqrbydata(qrdata)
            
            if qr:
                plate = qr["plate"]
                
                self.sql.inserthistory(qrdata, session["user_id"], "accepted")
                
                if plate:
                    return jsonify({
                        "status":"good",
                        "message":"Property of " + plate
                    })
                return jsonify({
                    "status":"good",
                    "message":"sucess"
                })
                
                
            self.sql.inserthistory(qrdata, session["user_id"], "failed")
            return jsonify({"status":"bad","message":"No qr found"})
            
        
            
            