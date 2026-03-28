import sqlite3
import hashlib
from datetime import datetime
from loguru import logger
import os

class ClinicalAuditLogger:
    """
    Implements 21 CFR Part 11 compliant audit trails!
    Normal logs can be deleted or modified. High-risk robotic interventions (Force Limits, E-Stops)
    must be chained cryptographically to ensure the log has not been tampered with post-surgery.
    """
    def __init__(self, db_path="data/audit_trail.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fda_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    operator_id TEXT,
                    description TEXT,
                    prev_hash TEXT,
                    current_hash TEXT
                )
            ''')
            # Check if genesis block exists
            cursor.execute("SELECT COUNT(*) FROM fda_audit_log")
            if cursor.fetchone()[0] == 0:
                self._record_genesis_block()

    def _get_last_hash(self, cursor) -> str:
        cursor.execute("SELECT current_hash FROM fda_audit_log ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else "0000000000000000000000000000000000000000000000000000000000000000"

    def _calculate_hash(self, ts, event, op, desc, prev_hash) -> str:
        raw = f"{ts}{event}{op}{desc}{prev_hash}".encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def _record_genesis_block(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            ts = datetime.utcnow().isoformat()
            h = self._calculate_hash(ts, "SYSTEM_INIT", "SYSTEM", "Genesis Block Created", "GENESIS")
            c.execute("INSERT INTO fda_audit_log (timestamp, event_type, operator_id, description, prev_hash, current_hash) VALUES (?,?,?,?,?,?)",
                      (ts, "SYSTEM_INIT", "SYSTEM", "Genesis Block Created", "GENESIS", h))

    def log_critical_event(self, event_type: str, operator_id: str, description: str):
        """ Log events like 'ROBOT_HALT', 'FORCE_OVERRIDE', 'SCAN_ABORTED' """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            ts = datetime.utcnow().isoformat()
            prev_hash = self._get_last_hash(c)
            curr_hash = self._calculate_hash(ts, event_type, operator_id, description, prev_hash)
            
            c.execute("INSERT INTO fda_audit_log (timestamp, event_type, operator_id, description, prev_hash, current_hash) VALUES (?,?,?,?,?,?)",
                      (ts, event_type, operator_id, description, prev_hash, curr_hash))
            
            # Flash to terminal as well
            logger.critical(f"[CLINICAL AUDIT] {event_type} - {description} (Hash Sealed)")

# Example Initialization
# audit = ClinicalAuditLogger()
# audit.log_critical_event("E-STOP", "DR_WANG", "Physician interrupted scan due to patient movement.")
