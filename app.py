from flask import Flask,request,render_template,jsonify
from passs import PASSW
from other.admin import Admin

import mysql.connector as mysql



class Main:
    def __init__(self):
        self.app = Flask(__name__)
        self.sql = mysql.connect(
            user="root",
            host="localhost",
            database="gsdparking",
            passwd=PASSW
        )
        self.blueprints()
        
    def routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")
        
        @self.app.route("/auth/login", methods=["POST"])
        def login():
            data  = request.get_json()
            email = data["email"]
            password = data["password"]
            role = data["role"]
            
            cur = self.sql.cursor()
            
            user = None
            if role == "admin":
                cur.execute("SELECT * FROM admin WHERE email=%s and password=%s",(email, password))
                
            elif role == "users" or role == "guard":
                cur.execute("SELECT * FROM users WHERE email=%s AND password=%s",(email, password))
                
            user=cur.fetchone()
            
            cur.close()
            
            if user:
                return{
                    "message":"success",
                    "status":"Success"}
            else:
                return {"message":"Failed Please try again",
                        "status":"failed"
                        }
            
        
        @self.app.route("/auth/test", methods=["POST"])
        def test():
            return jsonify({"success":True})
        
    def blueprints(self):
        
        self.app.register_blueprint(Admin().admin)  
        
    def run(self):
        self.app.run(debug=True)
            


app = Main()

if __name__ == "__main__":
    app.routes()
    app.run()