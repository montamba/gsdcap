import mysql.connector as mysql
import os
import time
import io
import json
import smtplib
import qrcode
import bcrypt
import math

from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

load_dotenv()


class SQL:
    def __init__(self):
        self.parking_file = os.path.join(os.path.dirname(__file__), "parking.json")
        self.sql = self._connect()
        self.ensure_vehicle_columns()

    def ensure_vehicle_columns(self):
        """Add the vehicle fields to older databases without removing existing data."""
        if not self.sql:
            return
        try:
            cur = self._cursor()
            cur.execute("SHOW COLUMNS FROM qrcode LIKE 'vehicle_type'")
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE qrcode ADD COLUMN vehicle_type VARCHAR(20) NOT NULL DEFAULT 'car'"
                )
            cur.execute("SHOW COLUMNS FROM qrcode LIKE 'space_units'")
            if not cur.fetchone():
                cur.execute(
                    "ALTER TABLE qrcode ADD COLUMN space_units TINYINT NOT NULL DEFAULT 2"
                )
            self._commit()
            cur.close()
        except Exception as e:
            print(f"[DB] vehicle column setup error: {e}")

    def _connect(self) -> mysql.MySQLConnection | None:
        for attempt in range(1, 6):
            try:
                conn = mysql.connect(
                    user=os.getenv("USER"),
                    host=os.getenv("LOCALHOST"),
                    database=os.getenv("DATABASE"),
                    passwd=os.getenv("PASSW"),
                    port=int(os.getenv("MYSQLPORT", 3306)),
                    connection_timeout=10,
                    autocommit=False,
                )
                print(f"[DB] Connected on attempt {attempt}")
                return conn
            except Exception as e:
                wait = 2 ** (attempt - 1)
                print(f"[DB] Attempt {attempt} failed: {e}  — retrying in {wait}s")
                time.sleep(wait)

        print("[DB] All connection attempts failed.")
        return None

    def request_deletion(self, user_id: int) -> bool:
        """Mark a user's account as pending deletion (sets deletion_requested_at to NOW)."""
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE users SET deletion_requested_at = NOW() WHERE id = %s",
                (user_id,),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] request_deletion error: {e}")
            return False

    def restore_user(self, user_id: int) -> bool:
        """Cancel a user's deletion request (clears deletion_requested_at)."""
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE users SET deletion_requested_at = NULL WHERE id = %s",
                (user_id,),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] restore_user error: {e}")
            return False
        
    

    def get_pending_deletions(self):
        """Return all users who have requested account deletion."""
        try:
            cur = self._cursor()
            cur.execute("""SELECT id, username, role, deletion_requested_at
                FROM users
                WHERE deletion_requested_at IS NOT NULL
                ORDER BY deletion_requested_at ASC""")
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] get_pending_deletions error: {e}")
            return []

    def purge_expired_deletions(self) -> int:
        """Hard-delete accounts whose 30-day window has elapsed. Returns count deleted."""
        try:
            cur = self._cursor()
            cur.execute("""DELETE FROM users
                WHERE deletion_requested_at IS NOT NULL
                    AND deletion_requested_at <= NOW() - INTERVAL 30 DAY""")
            count = cur.rowcount
            self._commit()
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] purge_expired_deletions error: {e}")
            return 0

    def update_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> dict:
        """Verify current password then update to the new hashed password."""
        try:
            cur = self._cursor()
            cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            cur.close()

            if not row:
                return {"ok": False, "message": "User not found"}

            if not self._check(current_password, row[0]):
                return {"ok": False, "message": "Current password is incorrect"}

            hashed = self._hash(new_password)
            cur = self._cursor()
            cur.execute(
                "UPDATE users SET password = %s WHERE id = %s", (hashed, user_id)
            )
            self._commit()
            cur.close()
            return {"ok": True, "message": "Password updated successfully"}
        except Exception as e:
            print(f"[DB] update_password error: {e}")
            return {"ok": False, "message": "Failed to update password"}

    def _ping(self) -> None:
        print("start to ping")
        try:
            # 1. Check if the object exists and thinks it's connected
            if self.sql and self.sql.is_connected():
                # 2. Ping with reconnect=False so it fails fast if socket is bad
                self.sql.ping(reconnect=False)
                return
        except Exception as e:
            print(f"[DB] Ping failed ({e}), forcing fresh connection...")

        # 3. If either check failed or threw an exception, recreate the connection
        self.sql = self._connect()

    # HELPERS ----------------------------------------------------

    def _hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _check(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode(),
                hashed.encode() if isinstance(hashed, str) else hashed,
            )
        except Exception:
            return False

    def _cursor(self):
        self._ping()
        return self.sql.cursor()

    def _commit(self):
        self.sql.commit()

    # USER QUERIES -----------------------------------------------------

    def getalluser(self, limit=0, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT id, username, role, created_at FROM users LIMIT %s OFFSET %s",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getalluser error: {e}")
            return []

    def countallusers(self) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] countallusers error: {e}")
            return 0

    def getuser(self, user_id):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getuser error: {e}")
            return None

    def getuserbyemail(self, email: str):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getuserbyemail error: {e}")
            return None
        
    def getuserbyemailandrole(self, email: str, role:str):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM users WHERE email=%s AND role=%s", (email, role,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getuserbyemailandrole error: {e}")
            return None

    def getuserbyusername(self, username: str):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getuserbyusername error: {e}")
            return None

    def getuserbyid(self, user_id):
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT username, email, role FROM users WHERE id=%s", (user_id,)
            )
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getuserbyid error: {e}")
            return None

    def adduser(self, username: str, email: str, password: str, role: str) -> bool:
        try:
            hashed = self._hash(password)
            cur = self._cursor()
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                (username, email, hashed, role),
            )
            self._commit()
            cur.close()
            return True
        except mysql.errors.IntegrityError as e:
            print(f"[DB] adduser integrity error: {e}")
            return False
        except Exception as e:
            print(f"[DB] adduser error: {e}")
            return False

    def deleteuser(self, user_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] deleteuser error: {e}")
            return False

    def updateuser(self, username: str, email: str, user_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE users SET username=%s, email=%s WHERE id=%s",
                (username, email, user_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] updateuser error: {e}")
            return False

    def verifyuser(self, email: str, password: str):
        user = self.getuserbyemail(email)
        if not user:
            return None
        return user if self._check(password, user[3]) else None

    # ADMIN PROFILE QUERIES ------------------------------------------

    def getadminbyid(self, admin_id):
        try:
            cur = self._cursor()
            cur.execute("SELECT username, email FROM admin WHERE id=%s", (admin_id,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getadminbyid error: {e}")
            return None

    def getadmin_password(self, admin_id):
        try:
            cur = self._cursor()
            cur.execute("SELECT password FROM admin WHERE id=%s", (admin_id,))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        except Exception as e:
            print(f"[DB] getadmin_password error: {e}")
            return None

    def updateadmin_email(self, admin_id, email: str) -> bool:
        try:
            cur = self._cursor()
            cur.execute("UPDATE admin SET email=%s WHERE id=%s", (email, admin_id))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] updateadmin_email error: {e}")
            return False

    def updateadmin_password(self, admin_id, new_password: str) -> bool:
        try:
            hashed = self._hash(new_password)
            cur = self._cursor()
            cur.execute("UPDATE admin SET password=%s WHERE id=%s", (hashed, admin_id))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] updateadmin_password error: {e}")
            return False

    # QR QUERIES --------------------------------------------------------------

    def getqrbydata(self, data: str):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM qrcode WHERE data=%s", (data,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrbydata error: {e}")
            return None

    def getqrbyid(self, qr_id):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM qrcode WHERE id=%s", (qr_id,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrbyid error: {e}")
            return None

    def getqrbyuser(self, user_id, limit=5, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT qrcode.*, users.username
                   FROM qrcode
                   LEFT JOIN users ON qrcode.created_by = users.id
                   WHERE qrcode.created_by = %s
                   ORDER BY qrcode.created_at DESC
                   LIMIT %s OFFSET %s""",
                (user_id, limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrbyuser error: {e}")
            return []

    def getallqr(self, limit=5, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT qrcode.*, users.username
                   FROM qrcode
                   LEFT JOIN users ON qrcode.created_by = users.id
                   ORDER BY qrcode.created_at DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getallqr error: {e}")
            return []

    def countallqr(self) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM qrcode")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] countallqr error: {e}")
            return 0

    def countqrbyuser(self, user_id) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM qrcode WHERE created_by=%s", (user_id,))
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] countqrbyuser error: {e}")
            return 0

    def getqrstats(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT 
                    SUM(status = 'active'),
                    SUM(status = 'revoke'),
                    SUM(expiry < NOW()),
                    COUNT(*)
                FROM qrcode
            """)

            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrstats error: {e}")
            return []

    def saveqr(
        self,
        data: str,
        plate: str,
        expiry,
        created_by,
        owner_name: str = "",
        owner_email: str = "",
        owner_number:str = "",
        vehicle_type: str = "car",
        department:"str" = "visitor"
    ) -> bool:
        try:
            vehicle_type = "motorcycle" if vehicle_type == "motorcycle" else "car"
            space_units = 1 if vehicle_type == "motorcycle" else 2
            cur = self._cursor()
            cur.execute(
                """INSERT INTO qrcode(data, plate, owner_name, owner_email, owner_phone, expiry, created_by, vehicle_type, space_units, department)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)""",
                (
                    data,
                    plate,
                    owner_name,
                    owner_email,
                    owner_number,
                    expiry,
                    created_by,
                    vehicle_type,
                    space_units,
                    department,
                ),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] saveqr error: {e}")
            return False

    def renewqr(self, qr_id, new_expiry, owner_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE qrcode SET expiry=%s, status='active' WHERE id=%s AND created_by=%s",
                (new_expiry, qr_id, owner_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] renewqr error: {e}")
            return False

    def renewqr_any(self, qr_id, new_expiry) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE qrcode SET expiry=%s, status='active', car_status=NULL WHERE id=%s",
                (new_expiry, qr_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] renewqr_any error: {e}")
            return False

    def deleteqr(self, qr_id, user_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "DELETE FROM qrcode WHERE id=%s AND created_by=%s", (qr_id, user_id)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] deleteqr error: {e}")
            return False

    # ========================================================================================================= users
    def fetchselfrequest(self, email, limit, offset):
        try:
            cur = self._cursor()
            
            cur.execute("""
                        SELECT qrpending.*, qrcode.created_at FROM qrpending LEFT JOIN  qrcode ON qrpending.qrid = qrcode.id WHERE qrcode.owner_email=%s LIMIT %s OFFSET %s
                        """, (email,limit,offset,))
            
            data = cur.fetchall()
            
            cur.close()
            return data
        except Exception as e:
            print(f"[DB] fetchselfrequest error: {e}")
            return None
        
    def countallselfrequest(self, id):
        try:
            cur = self._cursor()
                    
            cur.execute("""SELECT COUNT(*) FROM qrpending WHERE request_by=%s""", (id,))
                    
            data = cur.fetchone()[0]
                    
            cur.close()
            return data
        except Exception as e:
            print(f"[DB] countallselfrequest error: {e}")
            return None
        
        
        
    
    def addqrrequest(self, plate, owner_name, owner_email, owner_phone, created_by, vehicle_type):
        try:
            vehicle_type = "motorcycle" if vehicle_type == "motorcycle" else "car"
            space_units = 1 if vehicle_type == "motorcycle" else 2
            cur = self._cursor()
            cur.execute(
                """INSERT INTO 
                    qrcode (plate, owner_name, owner_email, owner_phone, created_by, vehicle_type, space_units) 
                    VALUES (%s,%s,%s,%s,%s,%s,%s);
                """,
                (plate, owner_name, owner_email, owner_phone, created_by, vehicle_type, space_units),
            )
            
            last = cur.lastrowid
            
            self._commit()
            
            #-------------

            
            
            
            # ------

            cur.execute(
                """INSERT INTO 
                    qrpending (qrid, request_type, request_by) 
                    VALUES (%s,%s,%s);
                """,
                (last, "request_qr", created_by,),
            )
            self._commit()
            

            cur.close()
            return True
        except Exception as e:
            print(f"[DB] addqrrequest error: {e}")
            return False
        
    
    def requestrenewal(self, id, data):
        try:
            cur = self._cursor()
            
            
            cur.execute("SELECT id FROM qrcode WHERE data=%s", (id,))
            qrid = cur.fetchone()[0]
            
            if not qrid:
                return False
            
            cur.execute("""INSERT INTO 
                        qrpending(qrid, request_type, request_by) 
                        VALUES (%s,%s,%s)
                        """, (qrid, "qr_renewal", id),)
            self.sql.commit()
            
        except:
            return False
        
        return True
     

    # ──────────────────────────────────────────────────────────────
    # HISTORY QUERIES
    # ──────────────────────────────────────────────────────────────

    def inserthistory(
        self, data: str, guard, status: str, action: str = "entry"
    ) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO history(data, guard, status, action) VALUES (%s,%s,%s,%s)",
                (data, guard, status, action),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] inserthistory error: {e}")
            return False

    def gethistory(self, limit=5, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] gethistory error: {e}")
            return []

    def counthistory(self) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM history")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] counthistory error: {e}")
            return 0

    def gethistory_full(self, limit=5, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT h.id,
                          h.created_at                    AS date,
                          COALESCE(u.username, '—')       AS guard_name,
                          COALESCE(q.plate,   '—')        AS plate,
                          h.data                          AS qr_code,
                          COALESCE(h.action,  'entry')    AS action,
                          h.status                        AS scan_result
                   FROM   history h
                   LEFT JOIN users   u ON h.guard = u.id
                   LEFT JOIN qrcode  q ON h.data  = q.data
                   ORDER  BY h.id DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] gethistory_full error: {e}")
            return []

    def gethistorybyguard(self, guard_id, limit=10, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT h.id,
                          h.data,
                          h.status,
                          h.created_at                   AS created_at,
                          COALESCE(q.plate,      '')     AS plate,
                          COALESCE(q.owner_name, '')     AS owner_name,
                          COALESCE(h.action,     'entry') AS action,
                          q.department
                   FROM history h
                   LEFT JOIN qrcode q ON h.data = q.data
                   WHERE h.guard = %s
                   ORDER BY h.id DESC
                   LIMIT %s OFFSET %s""",
                (guard_id, limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] gethistorybyguard error: {e}")
            return []

    def counthistorybyguard(self, guard_id) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM history WHERE guard = %s", (guard_id,))
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] counthistorybyguard error: {e}")
            return 0

    # ──────────────────────────────────────────────────────────────
    # PARKING
    # ──────────────────────────────────────────────────────────────

    def getparking(self) -> dict:
        try:
            cur = self._cursor()
            
            cur.execute("SELECT * FROM parking WHERE id=1")
            parking = cur.fetchone()
           
            data = {}
            data["total"] = parking[3]
            data["occupied"] = parking[2]
            data["available"] = parking[1]
            data["total_occupied"] = parking[0]
            
            return data
        except Exception as e:
            print(f"[DB] getparking error: {e}")
            return {"total": 0, "occupied": 0, "available": 0,"total_occupied":0}

    def setparkingslot(self, total):
        try:
            data  = self.getparking()
            
            available = total - data.get("occupied")
            
            
            cur = self._cursor()
            cur.execute("UPDATE parking SET available=%s, total=%s WHERE id=1",(available,total,))
            
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] counthistorybyguard error: {e}")
            return False
        

    def updateparking(self, added, operation) -> bool:
        try:
            print("updating")
            parking = self.getparking()
            
            occupied = parking.get("occupied")
            available = parking.get("available")
            total_occupied = parking.get("total_occupied")
            
            if operation == "entry":
                total_occupied += added / 2
                
            else:
                total_occupied -= added /2
            
            new_total_occupied = max(0, total_occupied)
            
            
            new_occupied = math.ceil(new_total_occupied)
            new_available = parking.get("total") - new_occupied
            cur = self._cursor()
            
            print(available, "========================")
            cur.execute("UPDATE parking SET available = %s, occupied = %s, total_occupied = %s WHERE id = 1",( new_available, new_occupied, new_total_occupied))
            
            self._commit()
            cur.close()
            print("update")
            return True

        except Exception as e:
            print(f"[DB] updateparking error: {e}")
            return False
        
    def change_admin_username(self, new_username, email):
        try:
            cur = self._cursor()
            
            cur.execute("UPDATE admin SET username=%s WHERE email=%s",(new_username,email,))
            
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] get_total_scan error: {e}")
            return False

    def get_total_entry_exit(self) -> dict:
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT
                    COUNT(CASE WHEN action = 'entry' THEN 1 END) AS entry,
                    COUNT(CASE WHEN action = 'exit' THEN 1 END) AS exit
                FROM history
            """)

            entry, exit_ = cur.fetchone()
            return {
                "entry": entry,
                "exit": exit_,
            }
        except Exception as e:
            print(f"[DB] get_total_entry_exit error: {e}")
            return {"entry": 0, "exit": 0}

    def get_total_scan(self) -> int:
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) FROM history")
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] get_total_scan error: {e}")
            return 0
        
    #===================================main admin
    def getadminbyemail(self, email):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM admin WHERE email=%s", (email,))
            admin  = cur.fetchone()[0]
            if admin:
                return True
                    
            return False
        except Exception as e:
            print(f"[DB] check_magic error: {e}")
            return False
        
    def check_magic(self, email, password):
        
        try:
            cur = self._cursor()
            print("num1")
            cur.execute("SELECT * FROM admin WHERE email=%s", (email,))
            print("num2")
            admin  = cur.fetchone()
            print(admin)
            print("num3")
            if not admin:
                return False
            
            print("num4")
            check = self._check(password, admin[3])
            print("num5")
            passmathc = password == admin[3]
            
            cur.close()
            if check or passmathc:
                return True
            
            return False
        except Exception as e:
            print(f"[DB] check_magic error: {e}")
            return False
    
    def guard_log(self, qrdata,user,status,action):
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO history(data, guard, status, action) VALUES (%s, %s, %s, %s)",
                (qrdata, user, status, action),
            )
            self._commit()
            cur.close()
        except Exception as e:
            print("[db] History log error:", e)
        
    def add_admin(self, username, email, password):
        try:
            cur = self._cursor()
            
            passhash = self._hash(password)
            
            cur.execute(
                "INSERT INTO admin(username, email, password) VALUES (%s,%s,%s)",
                (username, email, passhash,),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] add_admin error: {e}")
            return False
        
        

    # ──────────────────────────────────────────────────────────────
    # EMAIL
    # ──────────────────────────────────────────────────────────────

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

    def send_qr_email(
        self,
        to_email: str,
        owner_name: str,
        qr_data: str,
        plate: str = "",
        valid_until: str = "",
    ) -> bool:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_EMAIL", "gsdparking@gmail.com")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_pass:
            print("[EMAIL] SMTP credentials not configured")
            return False

        try:
            qr_bytes = self._generate_qr_image(qr_data)

            msg = MIMEMultipart("related")
            msg["Subject"] = "Your GSD Parking QR Code"
            msg["From"] = smtp_user
            msg["To"] = to_email

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
                  <img src="cid:qrimage" alt="QR Code" width="200" height="200"
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


            alt_part = MIMEMultipart("alternative")
            alt_part.attach(MIMEText(html_body, "html"))
            msg.attach(alt_part)

            img_part = MIMEImage(qr_bytes, _subtype="png")
            img_part.add_header("Content-ID", "<qrimage>")
            img_part.add_header("Content-Disposition", "inline", filename="qr_code.png")
            msg.attach(img_part)
            
            print("[EMAIL] SMTP host:", smtp_host)
            print("[EMAIL] SMTP port:", smtp_port)
            print("[EMAIL] SMTP user:", smtp_user)
            print("[EMAIL] SMTP password exists:", bool(smtp_pass))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                print("[EMAIL] SMTP connected")
                
                server.starttls()
                print("[EMAIL] TLS started")
                server.login(smtp_user, smtp_pass)
                print("[EMAIL] Login successful")
                
                server.sendmail(smtp_user, to_email, msg.as_string())
                print("[EMAIL] Message sent")

            print(f"[EMAIL] Sent to {to_email}")
            return True

        except Exception as e:
            import traceback
            print(f"[EMAIL] send_qr_email error: {repr(e)}")
            traceback.print_exc()
            return False
