from flask import Blueprint, render_template, request, jsonify
import json,os
import mysql.connector

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "parking.json")

class Admin:
    def __init__(self, sql:mysql.connector):
        self.admin = Blueprint('admin', __name__, url_prefix="/admin")
        self.sql = sql
        
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
        
        @self.admin.route("/setparking", methods=["POST"])
        def setParking(self):
            redata = request.get_json()
            # total = redata["total"]
            
            # message = {
            #     "status":"failed",
            #     "message":"sorry "
            # }
            
            # jdata = None
            # with open(file_path, "r") as file:
            #     jdata = json.load(file)
                
            # jdata["total"] = total
            
            # with open(file_path, "w") as file:
            #     json.dump(jdata, file, indent=4)
                
            # if jdata:
            #     message["status"] = "ok"
            #     message["message"] = "all goood"
                
            return jsonify({"data":"00","dar":"op"})
                
            
            
            
                
            
            
            
            
                
                
            
        
        
        
        
