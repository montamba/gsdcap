import mysql.connector as mysql
from passs import PASSW


class SQL:
    def __init__(self):
        self.sql = mysql.connect(
            user="root",
            host="localhost",
            database="gsdparking",
            passwd=PASSW
        )
        
    def getalluser(self):
        cur = self.sql.cursor()
        cur.execute("SELECT id,username, role, created_at FROM users")
        users = cur.fetchall()
        cur.close()
        return users

    def getuser(self, id):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (id,))
        user = cur.fetchone()
        cur.close()
        return user
    
    def deleteuser(self,id):
        cur = self.sql.cursor()
        cur.execute("DELETE FROM users WHERE id=%s",(id,))
        self.sql.commit()
        cur.close()


    def adduser(self, username, email, password, role):
        cur = self.sql.cursor()
        cur.execute(
            "INSERT INTO users(username,email,password,role) VALUES (%s,%s,%s,%s)",
            (username,email,password,role)
        )
        self.sql.commit()
        cur.close()


    def updateuser(self, id, username="", email="", password="", role=""):

        user = self.getuser(id)

        if not user:
            return {"status":"error", "message":"user not found"}

        olduser = (
            username or user[1],
            email or user[2],
            password or user[3],
            role or user[4]
        )

        cur = self.sql.cursor()

        cur.execute(
            "UPDATE users SET username=%s,email=%s,password=%s,role=%s WHERE id=%s",
            (*olduser, id)
        )

        self.sql.commit()
        cur.close()