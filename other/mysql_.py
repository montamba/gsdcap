import mysql.connector as mysql
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()
class SQL:
    def __init__(self):
        self.sql = mysql.connect(
            user= os.getenv("USER"),
            host= os.getenv("LOCALHOST"),
            database= os.getenv("DATABASE"),
            passwd= os.getenv("PASSW")
        )


    def _hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _check(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8") if isinstance(hashed, str) else hashed
            )
        except Exception:
            return False

    # ─── User queries ──────────────────────────────────────

    def getalluser(self):
        cur = self.sql.cursor()
        cur.execute("SELECT id, username, role, created_at FROM users")
        users = cur.fetchall()
        cur.close()
        return users

    def getuser(self, id):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (id,))
        user = cur.fetchone()
        cur.close()
        return user

    def getuserbyemail(self, email: str):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        return user

    def getuserbyusername(self, username: str):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        return user

    def deleteuser(self, id):
        cur = self.sql.cursor()
        cur.execute("DELETE FROM users WHERE id=%s", (id,))
        self.sql.commit()
        cur.close()

    def adduser(self, username: str, email: str, password: str, role: str):
        """Insert a new user with a bcrypt-hashed password."""
        hashed = self._hash(password)
        cur = self.sql.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed, role)
            )
        except mysql.connector.errors.IntegrityError as e:
            print(e)
        self.sql.commit()
        cur.close()

    def updateuser(self, id, username="", email="", password="", role=""):
        """Update user fields. If password provided, it is re-hashed."""
        user = self.getuser(id)
        if not user:
            return {"status": "error", "message": "User not found"}

        new_password = self._hash(password) if password else user[3]

        updated = (
            username or user[1],
            email    or user[2],
            new_password,
            role     or user[4]
        )

        cur = self.sql.cursor()
        cur.execute(
            "UPDATE users SET username=%s, email=%s, password=%s, role=%s WHERE id=%s",
            (*updated, id)
        )
        self.sql.commit()
        cur.close()

    def verifyuser(self, email: str, password: str):
        """Return the user row if credentials match, else None."""
        user = self.getuserbyemail(email)
        if not user:
            return None
        hashed = user[3]
        if self._check(password, hashed):
            return user
        return None
    
    
    def getqrbydata(self,data):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE data=%s", (data,))
        qr = cur.fetchone()
        cur.close()
        return qr
    
    def getqrbyuser(self,id):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE created_by=%s", (id,))
        qr = cur.fetchall()
        cur.close()
        return qr
    
    def getallqr(self, limit=0, offset=0):
        cur = self.sql.cursor()
        if limit:
            cur.execute("""SELECT qrcode.*, users.* 
                                FROM qrcode LEFT JOIN users 
                                ON qrcode.created_by = users.id 
                                ORDER BY qrcode.created_at DESC LIMIT %s OFFSET %s""",
                                (limit, offset)
                                )
        else:
            cur.execute("""SELECT qrcode.*, users.* 
                                FROM qrcode LEFT JOIN users 
                                ON qrcode.created_by = users.id 
                                ORDER BY qrcode.created_at DESC"""
                                )
        result = cur.fetchall()
        cur.close()
        
            
        return result
            
        
        
    def saveqr(self, data, plate,expiry,created_by):
        cur = self.sql.cursor()
        
        cur.execute("""INSERT INTO 
                    qrcode(data,plate,expiry,created_by)
                    VALUES (%s,%s,%s,%s)
                    """,(data,plate,expiry,created_by))
        
        self.sql.commit()
        cur.close()
        
        
    def getuserbyid(self,id):
        cur = self.sql.cursor()
        cur.execute("SELECT username, email, role FROM users WHERE id=%s",(id,))
        user = cur.fetchone()
        cur.close()
        return user
    
    def updateuser(self, username, email, id):
        cur = self.sql.cursor()
        cur.execute("UPDATE users SET username=%s, email=%s WHERE id=%s", (username, email, id))
        self.sql.commit()
        cur.close()
        
    def inserthistory(self,data, guard, status):
        cur = self.sql.cursor()
        cur.execute("INSERT INTO history(data, guard, status) VALUES (%s,%s,%s)", (data,guard,status))
        self.sql.commit()
        cur.close()
        
        
        
        
