import mysql.connector as mysql
import os
from dotenv import load_dotenv
import bcrypt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import json
import qrcode
import io
import base64

import resend

load_dotenv()

class SQL:
    def __init__(self):
        self.sql = mysql.connect(
            user= os.getenv("USER"),
            host= os.getenv("LOCALHOST"),
            database= os.getenv("DATABASE"),
            passwd= os.getenv("PASSW"),
            port=int(os.getenv("MYSQLPORT"))
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

    def getalluser(self, limit=5, offset=0):
        cur = self.sql.cursor()
        cur.execute("SELECT id, username, role, created_at FROM users LIMIT %s OFFSET %s", (limit, offset))
        users = cur.fetchall()
        cur.close()
        return users

    def countallusers(self):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        cur.close()
        return count

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

    # ─── Admin profile queries ─────────────────────────────

    def getadminbyid(self, id):
        """Return (username, email) for an admin row."""
        cur = self.sql.cursor()
        cur.execute("SELECT username, email FROM admin WHERE id=%s", (id,))
        row = cur.fetchone()
        cur.close()
        return row

    def updateadmin_email(self, id, email):
        """Update the admin's email address."""
        cur = self.sql.cursor()
        cur.execute("UPDATE admin SET email=%s WHERE id=%s", (email, id))
        self.sql.commit()
        cur.close()

    def updateadmin_password(self, id, new_password):
        """Hash and store a new password for the admin."""
        hashed = self._hash(new_password)
        cur = self.sql.cursor()
        cur.execute("UPDATE admin SET password=%s WHERE id=%s", (hashed, id))
        self.sql.commit()
        cur.close()

    def getadmin_password(self, id):
        """Return the raw stored password hash for the admin."""
        cur = self.sql.cursor()
        cur.execute("SELECT password FROM admin WHERE id=%s", (id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    # ─── QR queries ────────────────────────────────────────

    def getqrbydata(self, data):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE data=%s", (data,))
        qr = cur.fetchone()
        cur.close()
        return qr

    def getqrbyid(self, qr_id):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE id=%s", (qr_id,))
        qr = cur.fetchone()
        cur.close()
        return qr

    def getqrbyuser(self, user_id, limit=5, offset=0):
        cur = self.sql.cursor()
        cur.execute("""SELECT qrcode.*, users.username
                       FROM qrcode LEFT JOIN users ON qrcode.created_by = users.id
                       WHERE qrcode.created_by = %s
                       ORDER BY qrcode.created_at DESC LIMIT %s OFFSET %s""",
                    (user_id, limit, offset))
        qr = cur.fetchall()
        cur.close()
        return qr
    
    def getqrstats(self):
        cur = self.sql.cursor()
        cur.execute("""SELECT status,expiry
                       FROM qrcode""",
                    )
        qr = cur.fetchall()
        cur.close()
        return qr
        

    def countqrbyuser(self, user_id):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM qrcode WHERE created_by=%s", (user_id,))
        count = cur.fetchone()[0]
        cur.close()
        return count

    def getqrbyowner_email(self, email):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM qrcode WHERE owner_email=%s ORDER BY created_at DESC", (email,))
        qr = cur.fetchall()
        cur.close()
        return qr

    def getallqr(self, limit=5, offset=0):
        cur = self.sql.cursor()
        cur.execute("""SELECT qrcode.*, users.username
                       FROM qrcode LEFT JOIN users ON qrcode.created_by = users.id
                       ORDER BY qrcode.created_at DESC LIMIT %s OFFSET %s""",
                    (limit, offset))
        result = cur.fetchall()
        cur.close()
        return result

    def countallqr(self):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM qrcode")
        count = cur.fetchone()[0]
        cur.close()
        return count

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

    def renewqr_any(self, qr_id, new_expiry):
        cur = self.sql.cursor()
        cur.execute(
            "UPDATE qrcode SET expiry=%s, status='active', car_status=NULL WHERE id=%s",
            (new_expiry, qr_id)
        )
        self.sql.commit()
        cur.close()

    def deleteqr(self, qr_id, user_id):
        cur = self.sql.cursor()
        cur.execute("DELETE FROM qrcode WHERE id=%s AND created_by=%s", (qr_id, user_id))
        self.sql.commit()
        cur.close()

    def inserthistory(self, data, guard, status, action="entry"):
        cur = self.sql.cursor()
        cur.execute(
            "INSERT INTO history(data, guard, status, action) VALUES (%s, %s, %s, %s)",
            (data, guard, status, action)
        )
        self.sql.commit()
        cur.close()

    def gethistory(self, limit=5, offset=0):
        cur = self.sql.cursor()
        cur.execute("SELECT * FROM history ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
        data = cur.fetchall()
        cur.close()
        return data

    def counthistory(self):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM history")
        count = cur.fetchone()[0]
        cur.close()
        return count

    def gethistory_full(self, limit=5, offset=0):
        """History joined with users (guard name) and qrcode (plate) for admin report logs."""
        cur = self.sql.cursor()
        cur.execute("""
            SELECT h.id,
                   h.created_at                    AS date,
                   COALESCE(u.username, '—')       AS guard_name,
                   COALESCE(q.plate, '—')          AS plate,
                   h.data                          AS qr_code,
                   COALESCE(h.action, 'entry')     AS action,
                   h.status                        AS scan_result
            FROM   history h
            LEFT JOIN users   u ON h.guard = u.id
            LEFT JOIN qrcode  q ON h.data  = q.data
            ORDER  BY h.id DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        data = cur.fetchall()
        cur.close()
        return data

    def gethistorybyguard(self, guard_id):
        """Fetch all scan history for a specific guard, joined with qrcode for plate/owner info.
        Requires the migrate_history.sql migration to have been applied so that
        h.created_at and h.action columns exist."""
        cur = self.sql.cursor()
        cur.execute("""
            SELECT h.id,
                   h.data,
                   h.status,
                   h.created_at                   AS created_at,
                   COALESCE(q.plate, '')          AS plate,
                   COALESCE(q.owner_name, '')     AS owner_name,
                   COALESCE(h.action, 'entry')    AS action
            FROM history h
            LEFT JOIN qrcode q ON h.data = q.data
            WHERE h.guard = %s
            ORDER BY h.id DESC
        """, (guard_id,))
        data = cur.fetchall()
        cur.close()
        return data

    def updateparking(self):
        try:
            with open(self.parking_file, "r") as f:
                data = json.load(f)

            res = self.get_total_entry_exit()
            entry = res["entry"]
            data["occupied"] = min(entry, data["total"])
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

    def get_total_entry_exit(self):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM qrcode WHERE car_status = 'IN'")
        entry = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM qrcode WHERE car_status = 'OUT'")
        exit_ = cur.fetchone()[0]
        cur.close()
        return {"entry": entry, "exit": exit_}

    def get_total_scan(self):
        cur = self.sql.cursor()
        cur.execute("SELECT COUNT(*) FROM history")
        total = cur.fetchone()[0]
        cur.close()
        return total

    def _generate_qr_image(self, data: str) -> bytes:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#2563eb", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    
    
    
        

def send_qr_email(self, to_email: str, owner_name: str, qr_data: str,
                  plate: str = "", valid_until: str = "") -> bool:

    api_key = os.getenv("RESEND_API", "")
    if not api_key:
        print("Email error: RESEND_API_KEY not set")
        return False

    try:
        resend.api_key = api_key

        # Generate QR image and convert to base64 for embedding
        qr_bytes = self._generate_qr_image(qr_data)
        qr_b64   = base64.b64encode(qr_bytes).decode("utf-8")

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;
                    background:#f5f9ff;border:1px solid #c7d9f5;border-radius:12px;
                    overflow:hidden;">

          <div style="background:linear-gradient(135deg,#2563eb,#0ea5e9);
                      padding:28px 32px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:22px;letter-spacing:2px;">
              🅿️ GSD PARKING
            </h1>
            <p style="color:rgba(255,255,255,.8);margin:6px 0 0;font-size:12px;
                       letter-spacing:1px;">VEHICLE MONITORING SYSTEM</p>
          </div>

          <div style="padding:32px;text-align:center;">
            <h2 style="color:#0f172a;margin:0 0 8px;">Hello, {owner_name}!</h2>
            <p style="color:#64748b;font-size:14px;margin:0 0 28px;">
              Your parking QR pass is ready. Show this code at the entrance.
            </p>

            <div style="background:#fff;border:2px dashed #c7d9f5;border-radius:12px;
                        padding:28px 36px;display:inline-block;margin-bottom:28px;">
              <p style="margin:0 0 14px;font-size:10px;font-weight:700;color:#94a3b8;
                         letter-spacing:2px;text-transform:uppercase;">YOUR QR CODE</p>
              <img src="data:image/png;base64,{qr_b64}"
                   alt="QR Code" width="200" height="200"
                   style="display:block;margin:0 auto 16px;border-radius:8px;
                          border:1px solid #ddeaff;" />
              <p style="margin:0;font-size:18px;font-weight:800;color:#2563eb;
                         font-family:monospace;letter-spacing:3px;">{qr_data}</p>
            </div>

            <table style="margin:0 auto;border-collapse:collapse;font-size:13px;
                          width:100%;max-width:340px;background:#f8faff;
                          border:1px solid #ddeaff;border-radius:8px;overflow:hidden;">
              <tr style="border-bottom:1px solid #ddeaff;">
                <td style="padding:10px 16px;color:#94a3b8;font-weight:700;text-align:left;">PLATE</td>
                <td style="padding:10px 16px;color:#0f172a;font-weight:700;text-align:right;">{plate or "—"}</td>
              </tr>
              <tr>
                <td style="padding:10px 16px;color:#94a3b8;font-weight:700;text-align:left;">VALID UNTIL</td>
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

        params = {
            "from": "GSD Parking <onboarding@resend.dev>",  # use this until you verify a domain
            "to": [to_email],
            "subject": "Your GSD Parking QR Code",
            "html": html_body,
        }

        response = resend.Emails.send(params)
        print("Email sent:", response)
        return True

    except Exception as e:
        print("Email error:", e)
        return False