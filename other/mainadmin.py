from flask import Blueprint, request, session, jsonify
from other.mysql_ import SQL
import secrets
from datetime import datetime, timedelta, timezone


class Token:
    def __init__(self):
        self.__temp_token = []

    def create_token(self):
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        self.__temp_token.append({
            "token": token,
            "expired": expires_at
        })

        return token

    def check_token(self, token):
        now = datetime.now(timezone.utc)

        self.__temp_token = [i for i in self.__temp_token if i["expired"] > now]

        for i in self.__temp_token:
            if i["token"] == token:
                return True

        return False


class MainAdmin:
    def __init__(self, sql):
        self.mainadmin: Blueprint = Blueprint(
            "mainadmin", __name__, url_prefix="/mainadmin"
        )
        self.sql: SQL = sql
        self.token: Token = Token()

        self.routes()

    def routes(self):
        @self.mainadmin.route("/generate_token", methods=["POST"])
        def generate():
            data: dict = request.get_json()
            email = data.get("email", "").strip()
            password = data.get("password", "").strip()

            check = self.sql.check_magic(email, password)
            if not check:
                return jsonify({"status": "bad", "message": "Invalid input"})

            token = self.token.create_token()
            return jsonify({"status": "good", "message": str(token)})

        @self.mainadmin.route("/add_admin", methods=["POST"])
        def add_admin():
            data: dict = request.get_json()
            token = data.get("token", "")
            valid = self.token.check_token(token)

            if not valid:
                return jsonify({"status": "mad", "message": "Fail"})

            email = data.get("email").strip()
            password = data.get("password").strip()
            username = data.get('username').strip()
            

            emailexist = self.sql.getadminbyemail(email)
            if emailexist:
                return jsonify({"status": "bad", "message": "email already exist"})
            isadd = self.sql.add_admin(username,email, password)

            if isadd:
                return jsonify({"status": "good", "message": "user as=dded as admin"})
