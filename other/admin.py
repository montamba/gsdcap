from flask import Blueprint, render_template, request, jsonify
import json,os
from other.mysql_ import SQL

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "parking.json")

class Admin:
    def __init__(self):
        self.admin = Blueprint('admin', __name__, url_prefix="/admin")
        self.sql = SQL()
        
        self.routes()
        
    def routes(self):
        @self.admin.route("/dashboard")
        def dashboard():
            return render_template("admin/dashboard.html")
        
        @self.admin.route("/park")
        def park():
            return render_template("admin/park.html")
        
        @self.admin.route("/reports")
        def reports():
            return render_template("admin/reports.html")
        
        @self.admin.route("/users")
        def users():
            return render_template("admin/users.html")
        
        
        
        @self.admin.route("/parking", methods=["GET"])
        def parking():
            message = {
                "status":"failed",
                "message":"Sorry something went wrong"
            }
            
            data = None
            

            with open(file_path, "r") as file:
                data = json.load(file)
                
            if data:
                message["status"] = "good"
                message["message"] = "Scuccess"
                message["data"] = data
                
            return message
        
        #==============================================================
        
       
        
        @self.admin.route("/setparking", methods=["PUT"])
        def setParking():
            redata = request.get_json()
            total = int(redata["total"])
            
            message = {
                "status":"failed",
                "message":"sorry "
            }
            
            jdata = None
            with open(file_path, "r") as file:
                jdata = json.load(file)
                
            jdata["total"] = total
            
            with open(file_path, "w") as file:
                json.dump(jdata, file, indent=4)
                
            if jdata:
                message["status"] = "ok"
                message["message"] = "all goood"
                message["total"] = total
                
            return message
        #===================================================
        
        @self.admin.route("/getusers", methods=["GET"])
        def getUsers():
            users = self.sql.getalluser()
            
            print(users)
            
            message = {
                "status":"bad",
                "message":"no data availabe"
            }
            
            
            if users:
                return {
                    "status":"good",
                    "data":users
                }
                
            return message
        
        #=================================
        
        @self.admin.route("/delete_user/<int:id>", methods=["DELETE"])
        def deleteUser(id):
            self.sql.deleteuser(id)
            return {
                "status":"ok",
                "message":"succesfull deleted user"
            }
            
        @self.admin.route("/add_user", methods=["POST"])
        def add_user():
            message = {
                "status":"bad",
                "message":"sorry cant add usr at the moment"
            }
            
            data = request.get_json()
            username = data["username"]
            email = data["email"]
            password = data["password"]
            role = data["role"]
            
            if len(password) < 8:
                message["message"] = "password too short"
                return message
            
            
            
            self.sql.adduser(username,email,password,role)
            
            message["message"] = "successfully added"
            message["status"] = "good"
            
            return message
            
            
            
        
            
            
            
                
            
            
            
            
                
                
            
        
        
        
        
