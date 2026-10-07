import mysql.connector as mysql
import os
import time
import io
import json
import smtplib
import qrcode
import bcrypt
import math
import random
from html import escape

from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

load_dotenv()

QR_COLS = """q.id, q.code, c.plate, c.owner_name, c.owner_email, c.owner_phone,
             c.department, q.expiry, q.status, q.created_by, q.created_at,
             q.car_status, c.vehicle_type, c.space_units"""
QR_FROM = "FROM qrcode q JOIN car_details c ON c.id = q.car_details_id"
QR_FROM_USER = QR_FROM + " LEFT JOIN users u ON q.created_by = u.id"

PENDING_SELECT = """
    SELECT p.id, p.request_type, p.actions, p.request_by,
           q.id, q.code, c.plate, c.owner_name, c.owner_email,
           c.owner_phone, c.department, q.expiry, q.status,
           c.vehicle_type, c.space_units, q.created_at,
           u.username
    FROM qrpending p
    LEFT JOIN qrcode q ON p.qrid = q.id
    LEFT JOIN car_details c ON q.car_details_id = c.id
    LEFT JOIN users u ON p.request_by = u.id
"""


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
        
    def _rollback(self):
        try:
            self.sql.rollback()
        except Exception:
            pass

    def _insert_car(self, cur, plate, owner_name, owner_email, owner_phone,
                    department, vehicle_type):
        """Insert a car_details row using an existing cursor (same transaction)."""
        vehicle_type = "motorcycle" if vehicle_type == "motorcycle" else "car"
        space_units = 1 if vehicle_type == "motorcycle" else 2
        cur.execute(
            """INSERT INTO car_details
            (plate, owner_name, owner_email, owner_phone, department, vehicle_type, space_units)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (plate, owner_name, owner_email, owner_phone, department, vehicle_type, space_units),
        )
        return cur.lastrowid

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


    def countqrbyemailandhasdata(self, email):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT COUNT(*) FROM qrcode q
                   JOIN car_details c ON c.id = q.car_details_id
                   WHERE c.owner_email=%s AND q.code IS NOT NULL""",
                (email,),
            )
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] countqrbyemailandhasdata error: {e}")
            return 0
        

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

    def countusersbyrole(self):
        try:
            cur = self._cursor()
            cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            result = dict(cur.fetchall())
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] countusersbyrole error: {e}")
            return {}

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
    def codeindata(self, code):
        try:
            cur = self._cursor()
            cur.execute("SELECT 1 FROM qrcode WHERE code=%s", (code,))
            result = cur.fetchone()
            cur.close()
            return bool(result)
        except Exception as e:
            print(f"[DB] codeindata error: {e}")
            return False
        

    def getqrbydata(self, data: str):
        try:
            cur = self._cursor()
            cur.execute(f"SELECT {QR_COLS} {QR_FROM} WHERE q.code=%s", (data,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrbydata error: {e}")
            return None

    def isplateauthorized(self, plate: str) -> bool:
        """Return whether a plate is registered in the QR vehicle records."""
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT 1 FROM qrcode WHERE UPPER(TRIM(plate)) = %s LIMIT 1",
                (plate.strip().upper(),),
            )
            result = cur.fetchone()
            cur.close()
            return result is not None
        except Exception as e:
            print(f"[DB] isplateauthorized error: {e}")
            return False
        
        
    def getqrbyemailandhasdata(self, email, limit, offset):
        try:
            cur = self._cursor()
            cur.execute(
                f"""SELECT {QR_COLS} {QR_FROM}
                    WHERE q.code IS NOT NULL AND c.owner_email=%s
                    ORDER BY q.id DESC LIMIT %s OFFSET %s""",
                (email, limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrbyemailandhasdata error: {e}")
            return None

    def getqrbyid(self, qr_id):
        try:
            cur = self._cursor()
            cur.execute(f"SELECT {QR_COLS} {QR_FROM} WHERE q.id=%s", (qr_id,))
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
                f"""SELECT {QR_COLS}, u.username {QR_FROM_USER}
                    WHERE q.created_by = %s
                    ORDER BY q.created_at DESC
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
                f"""SELECT {QR_COLS}, u.username {QR_FROM_USER}
                    ORDER BY q.created_at DESC
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
                    COALESCE(SUM(status = 'active' AND (expiry IS NULL OR expiry >= NOW())), 0),
                    COALESCE(SUM(status <> 'revoked' AND expiry < NOW()), 0),
                    COALESCE(SUM(status = 'revoked'), 0),
                    COUNT(*)
                FROM qrcode
            """)

            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrstats error: {e}")
            return []
        
    def saveqr(self, code: str, plate: str, expiry, created_by,
               owner_name: str = "", owner_email: str = "", owner_number: str = "",
               vehicle_type: str = "car", department: str = "Null") -> bool:
        try:
            cur = self._cursor()
            car_id = self._insert_car(cur, plate, owner_name, owner_email,
                                      owner_number, department, vehicle_type)
            cur.execute(
                """INSERT INTO qrcode (code, car_details_id, expiry, created_by)
                   VALUES (%s,%s,%s,%s)""",
                (code, car_id, expiry, created_by),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
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
                "SELECT car_details_id FROM qrcode WHERE id=%s AND created_by=%s",
                (qr_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                cur.close()
                return False
            car_id = row[0]
            cur.execute("DELETE FROM qrcode WHERE id=%s", (qr_id,))
            # remove the car record too if no other QR still uses it
            cur.execute(
                """DELETE FROM car_details WHERE id=%s
                   AND NOT EXISTS (SELECT 1 FROM qrcode WHERE car_details_id=%s)""",
                (car_id, car_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] deleteqr error: {e}")
            return False
        
    def set_car_status(self, code, status) -> bool:
        """status = 'IN' or 'OUT'"""
        try:
            cur = self._cursor()
            cur.execute("UPDATE qrcode SET car_status=%s WHERE code=%s", (status, code))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] set_car_status error: {e}")
            return False
        
    def revoke_qr(self, code, plate) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                """UPDATE qrcode q
                   JOIN car_details c ON c.id = q.car_details_id
                   SET q.status='revoked', q.car_status='OUT'
                   WHERE q.code=%s AND c.plate=%s""",
                (code, plate),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] revoke_qr error: {e}")
            return False
        
    #------------------------Request
    def has_pending_request(self, data: str, request_type: str) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT p.id FROM qrpending p
                   JOIN qrcode q ON p.qrid = q.id
                   WHERE q.code=%s AND p.request_type=%s AND p.actions='pending'""",
                (data, request_type),
            )
            row = cur.fetchone()
            cur.close()
            return row is not None
        except Exception as e:
            print(f"[DB] has_pending_request error: {e}")
            return False
        
        
    def getqrrequestwithusersandqrcode(self, limit=10, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                PENDING_SELECT + """
                WHERE p.request_type = 'request_qr' AND p.actions = 'pending'
                ORDER BY p.id DESC LIMIT %s OFFSET %s""",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrrequestwithusersandqrcode error: {e}")
            return []
        

    def getqrrenewalwithusersandqrcode(self, limit=10, offset=0):
        try:
            cur = self._cursor()
            cur.execute(
                PENDING_SELECT + """
                WHERE p.request_type = 'qr_renewal' AND p.actions = 'pending'
                ORDER BY p.id DESC LIMIT %s OFFSET %s""",
                (limit, offset),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] getqrrenewalwithusersandqrcode error: {e}")
            return []

    def count_qr_pending_by_type(self, request_type):
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT COUNT(*) FROM qrpending WHERE request_type=%s AND actions='pending'",
                (request_type,),
            )
            count = cur.fetchone()[0]
            cur.close()
            return count
        except Exception as e:
            print(f"[DB] count_qr_pending_by_type error: {e}")
            return 0

    def get_qr_pending_detail(self, pending_id):
        try:
            cur = self._cursor()
            cur.execute(PENDING_SELECT + " WHERE p.id = %s", (pending_id,))
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] get_qr_pending_detail error: {e}")
            return None


    def approve_qr_request(self, pending_id, qr_id, code, reviewer_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute("UPDATE qrcode SET code=%s, status='active' WHERE id=%s", (code, qr_id))
            cur.execute(
                "UPDATE qrpending SET actions='approved', review_by=%s WHERE id=%s",
                (reviewer_id, pending_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] approve_qr_request error: {e}")
            return False

    def approve_qr_renewal(self, pending_id, qr_id, new_expiry, reviewer_id) -> bool:
        """Renewal approved: push the new expiry and reactivate the pass."""
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE qrcode SET expiry=%s, status='active', car_status=NULL WHERE id=%s",
                (new_expiry, qr_id),
            )
            cur.execute(
                "UPDATE qrpending SET actions='approved', review_by=%s WHERE id=%s",
                (reviewer_id, pending_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] approve_qr_renewal error: {e}")
            return False

    def reject_qr_pending(self, pending_id, reviewer_id) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE qrpending SET actions='rejected', review_by=%s WHERE id=%s",
                (reviewer_id, pending_id),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] reject_qr_pending error: {e}")
            return False

    # ========================================================================================================= users
    def fetchselfrequest(self, email, limit, offset):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT p.*, q.created_at FROM qrpending p
                   JOIN qrcode q ON p.qrid = q.id
                   JOIN car_details c ON q.car_details_id = c.id
                   WHERE c.owner_email=%s LIMIT %s OFFSET %s""",
                (email, limit, offset),
            )
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
        
        
        
    
    def addqrrequest(self, plate, owner_name, owner_email, owner_phone,
                     created_by, vehicle_type, department=None):
        try:
            cur = self._cursor()
            car_id = self._insert_car(cur, plate, owner_name, owner_email,
                                      owner_phone, department, vehicle_type)
            cur.execute(
                "INSERT INTO qrcode (car_details_id, created_by) VALUES (%s,%s)",
                (car_id, created_by),
            )
            qr_id = cur.lastrowid
            cur.execute(
                "INSERT INTO qrpending (qrid, request_type, request_by) VALUES (%s,%s,%s)",
                (qr_id, "request_qr", created_by),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] addqrrequest error: {e}")
            return False

    def add_public_qr_request(self, plate, owner_name, owner_email, owner_phone,
                              vehicle_type, department):
        try:
            cur = self._cursor()
            cur.execute(
                """SELECT p.id FROM qrpending p
                   JOIN qrcode q ON q.id = p.qrid
                   JOIN car_details c ON c.id = q.car_details_id
                   WHERE p.request_type='request_qr' AND p.actions='pending'
                   AND UPPER(c.plate)=UPPER(%s) AND LOWER(c.owner_email)=LOWER(%s)
                   LIMIT 1""",
                (plate, owner_email),
            )
            if cur.fetchone():
                cur.close()
                return "duplicate"
            car_id = self._insert_car(cur, plate, owner_name, owner_email,
                                      owner_phone, department, vehicle_type)
            cur.execute(
                "INSERT INTO qrcode (car_details_id, status) VALUES (%s,'pending')",
                (car_id,),
            )
            qr_id = cur.lastrowid
            cur.execute(
                "INSERT INTO qrpending (qrid, request_type, request_by) VALUES (%s,'request_qr',NULL)",
                (qr_id,),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] add_public_qr_request error: {e}")
            return False
        
    
    def requestrenewal(self, id, data):
        try:
            cur = self._cursor()
            cur.execute("SELECT id FROM qrcode WHERE code=%s", (id,))
            row = cur.fetchone()
            if not row:
                cur.close()
                return False
            cur.execute(
                "INSERT INTO qrpending (qrid, request_type, request_by) VALUES (%s,%s,%s)",
                (row[0], "qr_renewal", data),
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] requestrenewal error: {e}")
            return False
     

    # ──────────────────────────────────────────────────────────────
    # HISTORY QUERIES
    # ──────────────────────────────────────────────────────────────

    def inserthistory(
        self, data: str, guard, status: str, action: str = "entry", plate:str= None, department=None, is_authorized: bool = False
    ) -> bool:
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO history(data, guard, status, action, department,plate,is_authorized) VALUES (%s,%s,%s,%s, %s,%s,%s)",
                (data, guard, status, action, department, plate, int(bool(is_authorized))),
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
                          COALESCE(h.plate,   '—')        AS plate,
                          h.data                          AS qr_code,
                          COALESCE(h.action,  'entry')    AS action,
                          h.status                        AS scan_result
                   FROM   history h
                   LEFT JOIN users   u ON h.guard = u.id
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

    def gethistorybyguard(self, guard_id, limit=10, offset=0, year=None, month=None, day=None):
        try:
            cur = self._cursor()
            conditions = ["h.guard = %s"]
            params = [guard_id]
            if year is not None:
                conditions.append("YEAR(h.created_at) = %s")
                params.append(year)
            if month is not None:
                conditions.append("MONTH(h.created_at) = %s")
                params.append(month)
            if day is not None:
                conditions.append("DAY(h.created_at) = %s")
                params.append(day)
            params.extend([limit, offset])
            cur.execute(
                f"""SELECT h.* FROM history h
                   WHERE {' AND '.join(conditions)}
                   ORDER BY h.id DESC
                   LIMIT %s OFFSET %s""",
                tuple(params),
            )
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            print(f"[DB] gethistorybyguard error: {e}")
            return []

    def counthistorybyguard(self, guard_id, year=None, month=None, day=None) -> int:
        try:
            cur = self._cursor()
            conditions = ["guard = %s"]
            params = [guard_id]
            if year is not None:
                conditions.append("YEAR(created_at) = %s")
                params.append(year)
            if month is not None:
                conditions.append("MONTH(created_at) = %s")
                params.append(month)
            if day is not None:
                conditions.append("DAY(created_at) = %s")
                params.append(day)
            cur.execute(f"SELECT COUNT(*) FROM history WHERE {' AND '.join(conditions)}", tuple(params))
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
        default = {"total": 0, "occupied": 0, "available": 0, "total_occupied": 0}
        cur = None
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM parking WHERE id=1")
            parking = cur.fetchone()
            if not parking:
                return default
            return {
                "total": parking[3],
                "occupied": parking[2],
                "available": parking[1],
                "total_occupied": float(parking[4] or 0),
            }
        except Exception as e:
            print(f"[DB] getparking error: {e}")
            return default
        finally:
            if cur:
                cur.close()        # consumes the pending result
            self._rollback() 

    def setparkingslot(self, total):
        try:
            data = self.getparking()
            available = total - data.get("occupied", 0)
            cur = self._cursor()
            cur.execute("UPDATE parking SET available=%s, total=%s WHERE id=1", (available, total))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[DB] setparkingslot error: {e}")
            return False
        

    def updateparking(self, added, operation) -> bool:
        cur = None
        try:
            cur = self._cursor()
            # FOR UPDATE reads the latest committed row and locks it
            cur.execute("SELECT total, total_occupied FROM parking WHERE id=1 FOR UPDATE")
            row = cur.fetchone()
            cur.close()
            if not row:
                self._rollback()
                return False

            total, total_occupied = row[0], float(row[1] or 0)
            delta = added / 2
            total_occupied += delta if operation == "entry" else -delta
            total_occupied = max(0, total_occupied)

            occupied = math.ceil(total_occupied)
            available = total - occupied

            cur = self._cursor()
            cur.execute(
                "UPDATE parking SET available=%s, occupied=%s, total_occupied=%s WHERE id=1",
                (available, occupied, total_occupied),
            )
            self._commit()
            return True
        except Exception as e:
            self._rollback()
            print(f"[DB] updateparking error: {e}")
            return False
        finally:
            if cur:
                try: cur.close()
                except Exception: pass
        
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
                    COUNT(CASE WHEN action = 'entry' THEN 1 END),
                    COUNT(CASE WHEN action = 'exit' THEN 1 END)
                FROM history
                WHERE status = 'accepted' AND DATE(created_at) = CURDATE()
            """)

            entry, exit_ = cur.fetchone()
            cur.close()
            return {"entry": entry, "exit": exit_}
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
            owner_name = escape(owner_name or "")
            plate = escape(plate or "")
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
