import mysql.connector as mysql
import os
from dotenv import load_dotenv
import bcrypt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json

load_dotenv()

class SQL:
    def __init__(self):
        self.sql = mysql.connect(
            user= os.getenv("USER"),
            host= os.getenv("LOCALHOST"),
            database= os.getenv("DATABASE"),
            passwd= os.getenv("PASSW"),
            port=int(os.getenv("PORT"))
        )
        self.parking_file = os.path.join(os.path.dirname(__file__), "parking.json")

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

    def verifyuser(self, email: str, password: str):
        user = self.getuserbyemail(email)
        if not user:
            return None
        if self._check(password, user[3]):
            return user
        return None

    def getuserbyid(self, id):
        cur = self.sql.cursor()
        cur.execute("SELECT username, email, role FROM users WHERE id=%s", (id,))
        user = cur.fetchone()
        cur.close()
        return user

    def updateuser(self, username, email, id):
        cur = self.sql.cursor()
        cur.execute("UPDATE users SET username=%s, email=%s WHERE id=%s", (username, email, id))
        self.sql.commit()
        cur.close()

    # ─── QR queries ────────────────────────────────────────

    def getqrbydata(self, data):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE data=%s", (data,))
        qr = cur.fetchone()
        cur.close()
        return qr

    def getqrbyuser(self, id):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE created_by=%s ORDER BY created_at DESC", (id,))
        qr = cur.fetchall()
        cur.close()
        return qr

    def getqrbyowner_email(self, email):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE owner_email=%s ORDER BY created_at DESC", (email,))
        qr = cur.fetchall()
        cur.close()
        return qr

    def getallqr(self, limit=0, offset=0):
        cur = self.sql.cursor()
        if limit:
            cur.execute("""SELECT qrcode.*, users.username
                           FROM qrcode LEFT JOIN users ON qrcode.created_by = users.id
                           ORDER BY qrcode.created_at DESC LIMIT %s OFFSET %s""",
                        (limit, offset))
        else:
            cur.execute("""SELECT qrcode.*, users.username
                           FROM qrcode LEFT JOIN users ON qrcode.created_by = users.id
                           ORDER BY qrcode.created_at DESC""")
        result = cur.fetchall()
        cur.close()
        return result

    def saveqr(self, data, plate, expiry, created_by, owner_name="", owner_email=""):
        cur = self.sql.cursor()
        cur.execute(
            """INSERT INTO qrcode(data, plate, owner_name, owner_email, expiry, created_by)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (data, plate, owner_name, owner_email, expiry, created_by)
        )
        self.sql.commit()
        cur.close()

    def renewqr(self, qr_id, new_expiry, owner_id):
        cur = self.sql.cursor()
        cur.execute(
            "UPDATE qrcode SET expiry=%s, status='active' WHERE id=%s AND created_by=%s",
            (new_expiry, qr_id, owner_id)
        )
        self.sql.commit()
        cur.close()

    def deleteqr(self, qr_id, user_id):
        cur = self.sql.cursor()
        cur.execute("DELETE FROM qrcode WHERE id=%s AND created_by=%s", (qr_id, user_id))
        self.sql.commit()
        cur.close()

    # ─── History queries ───────────────────────────────────

    def inserthistory(self, data, guard, status, action="entry"):
        cur = self.sql.cursor()
        cur.execute(
            "INSERT INTO history(data, guard, status, action) VALUES (%s, %s, %s, %s)",
            (data, guard, status, action)
        )
        self.sql.commit()
        cur.close()

    # ─── Parking Management ────────────────────────────────

    def updateparking(self, action="entry"):
        try:
            with open(self.parking_file, "r") as f:
                data = json.load(f)
            
            if action == "entry":
                data["occupied"] = min(data["occupied"] + 1, data["total"])
                data["available"] = data["total"] - data["occupied"]
            elif action == "exit":
                data["occupied"] = max(data["occupied"] - 1, 0)
                data["available"] = data["total"] - data["occupied"]
            
            with open(self.parking_file, "w") as f:
                json.dump(data, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error updating parking: {e}")
            return False

    def getparking(self):
        try:
            with open(self.parking_file, "r") as f:
                return json.load(f)
        except:
            return {"total": 0, "occupied": 0, "available": 0}

   
        """
        Sends the QR data code (plain string) to the owner's email.
        No image is generated server-side — the JS on the client renders the QR from this code.
        """
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_EMAIL", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_pass:
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Your GSD Parking QR Code"
            msg["From"]    = smtp_user
            msg["To"]      = to_email

            html_body = f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                        background:#f5f9ff;border:1px solid #c7d9f5;border-radius:12px;overflow:hidden;">

              <div style="background:linear-gradient(135deg,#2563eb,#0ea5e9);
                          padding:28px 32px;text-align:center;">
                <h1 style="color:#fff;margin:0;font-size:22px;letter-spacing:2px;">
                  🅿️ GSD PARKING
                </h1>
                <p style="color:rgba(255,255,255,.8);margin:6px 0 0;font-size:12px;letter-spacing:1px;">
                  VEHICLE MONITORING SYSTEM
                </p>
              </div>

              <div style="padding:32px;text-align:center;">
                <h2 style="color:#0f172a;margin:0 0 8px;">Hello, {owner_name}!</h2>
                <p style="color:#64748b;font-size:14px;margin:0 0 28px;">
                  Your parking QR pass is ready. Show this code at the entrance — the guard will scan it.
                </p>

                <div style="background:#fff;border:2px dashed #c7d9f5;border-radius:12px;
                            padding:28px 36px;display:inline-block;margin-bottom:28px;">
                  <p style="margin:0 0 10px;font-size:10px;font-weight:700;color:#94a3b8;
                             letter-spacing:2px;text-transform:uppercase;">
                    YOUR QR CODE
                  </p>
                  <p style="margin:0;font-size:28px;font-weight:800;color:#2563eb;
                             font-family:monospace;letter-spacing:4px;word-break:break-all;">
                    {qr_data}
                  </p>
                  <p style="margin:10px 0 0;font-size:11px;color:#94a3b8;">
                    Give this code to the guard or use the Owner Portal to view your QR pass.
                  </p>
                </div>

                <table style="margin:0 auto;border-collapse:collapse;font-size:13px;
                              width:100%;max-width:320px;background:#f8faff;
                              border:1px solid #ddeaff;border-radius:8px;">
                  <tr style="border-bottom:1px solid #ddeaff;">
                    <td style="padding:10px 16px;color:#94a3b8;font-weight:700;">PLATE</td>
                    <td style="padding:10px 16px;color:#0f172a;font-weight:700;text-align:right;">{plate or "—"}</td>
                  </tr>
                  <tr>
                    <td style="padding:10px 16px;color:#94a3b8;font-weight:700;">VALID UNTIL</td>
                    <td style="padding:10px 16px;color:#0f172a;font-weight:700;text-align:right;">{valid_until or "—"}</td>
                  </tr>
                </table>
              </div>

              <div style="background:#f5f9ff;border-top:1px solid #ddeaff;padding:14px;
                          text-align:center;font-size:10px;color:#94a3b8;letter-spacing:1px;">
                GSD PARKING MONITORING SYSTEM &mdash; DO NOT SHARE THIS CODE
              </div>
            </div>
            """

            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())

            return True

        except Exception as e:
            print("Email error:", e)
            return False