from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .security import hash_password, verify_password


@dataclass(frozen=True)
class User:
    username: str
    role: str


class Database:
    def __init__(self, db_path: str | Path = "students.db") -> None:
        self.db_path = str(db_path)
        self.conn = self._connect_with_retry(self.db_path)

    def _connect_with_retry(self, path: str) -> sqlite3.Connection:
        last_err: Exception | None = None
        start = time.time()
        while time.time() - start < 6.0:
            try:
                # Allow the SQLite connection to be used from multiple threads.
                # Flask's development server (and other WSGI servers) may handle
                # requests on worker threads, which otherwise triggers
                # sqlite3.ProgrammingError (from different threads).
                conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
                conn.execute("PRAGMA foreign_keys = ON;")
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                except sqlite3.OperationalError:
                    # If DB is locked, we may still be able to proceed without WAL.
                    pass
                conn.row_factory = sqlite3.Row
                return conn
            except sqlite3.OperationalError as e:
                last_err = e
                time.sleep(0.4)
        raise RuntimeError(
            "Database is locked. Close any app that might be using 'students.db' "
            "(another Python run, SQLite browser, etc.) and try again."
        ) from last_err

    def close(self) -> None:
        self.conn.close()

    def migrate(self) -> None:
        start = time.time()
        last_err: Exception | None = None

        while time.time() - start < 6.0:
            try:
                cur = self.conn.cursor()

                def table_exists(name: str) -> bool:
                    cur.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (name,),
                    )
                    return cur.fetchone() is not None

                def columns_of(name: str) -> set[str]:
                    cur.execute(f"PRAGMA table_info({name})")
                    return {row["name"] for row in cur.fetchall()}

                students_cols = columns_of("students") if table_exists("students") else set()
                subjects_cols = columns_of("subjects") if table_exists("subjects") else set()
                has_marks = table_exists("marks")

                students_is_new = "class_id" in students_cols and "name" in students_cols
                subjects_is_new = "name" in subjects_cols and "id" in subjects_cols

                legacy_detected = (
                    (table_exists("students") and not students_is_new)
                    or (table_exists("subjects") and not subjects_is_new)
                    or (not has_marks)
                )

                students_src = "students_legacy_src"
                subjects_src = "subjects_legacy_src"

                # If legacy schema is detected, rename legacy tables away so we can create the new schema cleanly.
                if legacy_detected:
                    if table_exists("students") and not students_is_new and not table_exists(students_src):
                        cur.execute(f"ALTER TABLE students RENAME TO {students_src}")
                    if table_exists("subjects") and not subjects_is_new and not table_exists(subjects_src):
                        cur.execute(f"ALTER TABLE subjects RENAME TO {subjects_src}")

                # New schema
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        salt BLOB NOT NULL,
                        password_hash BLOB NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('admin','staff'))
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS classes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS students (
                        student_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        program TEXT,
                        class_id INTEGER,
                        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE SET NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS subjects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS marks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT NOT NULL,
                        subject_id INTEGER NOT NULL,
                        term TEXT NOT NULL,
                        mark INTEGER NOT NULL CHECK(mark BETWEEN 0 AND 100),
                        UNIQUE(student_id, subject_id, term),
                        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                        FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                    )
                    """
                )

                # Migrate legacy data into the new structure (term is assumed as "Term 1")
                if table_exists(students_src) and table_exists(subjects_src):
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO students (student_id, name, program, class_id)
                        SELECT student_id, name, program, NULL FROM students_legacy_src
                        """
                    )
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO subjects (name)
                        SELECT DISTINCT subject FROM subjects_legacy_src
                        """
                    )
                    cur.execute(
                        """
                        INSERT INTO marks (student_id, subject_id, term, mark)
                        SELECT
                            l.student_id,
                            s.id,
                            'Term 1' AS term,
                            l.mark
                        FROM subjects_legacy_src l
                        JOIN students st ON st.student_id = l.student_id
                        JOIN subjects s ON s.name = l.subject
                        ON CONFLICT(student_id, subject_id, term) DO UPDATE SET mark=excluded.mark
                        """
                    )

                self.conn.commit()
                self._ensure_default_admin()
                return
            except sqlite3.OperationalError as e:
                last_err = e
                if "locked" not in str(e).lower():
                    raise
                time.sleep(0.4)

        raise RuntimeError(
            "Database is locked. Close any app that might be using 'students.db' "
            "(another Python run, SQLite browser, etc.) and try again."
        ) from last_err

    def _ensure_default_admin(self) -> None:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        if int(cur.fetchone()["c"]) > 0:
            return
        salt, pw_hash = hash_password("admin123")
        cur.execute(
            "INSERT INTO users (username, salt, password_hash, role) VALUES (?, ?, ?, ?)",
            ("admin", salt, pw_hash, "admin"),
        )
        self.conn.commit()

    # -------------------------
    # Auth / Users
    # -------------------------
    def authenticate(self, username: str, password: str) -> Optional[User]:
        cur = self.conn.cursor()
        cur.execute("SELECT username, salt, password_hash, role FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        if not verify_password(password, row["salt"], row["password_hash"]):
            return None
        return User(username=row["username"], role=row["role"])

    def create_user(self, username: str, password: str, role: str) -> None:
        if role not in ("admin", "staff"):
            raise ValueError("role must be admin or staff")
        salt, pw_hash = hash_password(password)
        self.conn.execute(
            "INSERT INTO users (username, salt, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, salt, pw_hash, role),
        )
        self.conn.commit()

    def list_users(self) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, username, role FROM users ORDER BY username")
        return cur.fetchall()

    def delete_user(self, user_id: int) -> None:
        self.conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        self.conn.commit()

    # -------------------------
    # Classes
    # -------------------------
    def upsert_class(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Class name required")
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO classes (name) VALUES (?)", (name,))
        cur.execute("SELECT id FROM classes WHERE name=?", (name,))
        self.conn.commit()
        return int(cur.fetchone()["id"])

    def list_classes(self) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM classes ORDER BY name")
        return cur.fetchall()

    # -------------------------
    # Students
    # -------------------------
    def add_student(self, student_id: str, name: str, program: str | None, class_id: int | None) -> None:
        self.conn.execute(
            "INSERT INTO students (student_id, name, program, class_id) VALUES (?, ?, ?, ?)",
            (student_id.strip(), name.strip(), (program or "").strip(), class_id),
        )
        self.conn.commit()

    def update_student(self, student_id: str, *, name: str, program: str, class_id: int | None) -> None:
        self.conn.execute(
            "UPDATE students SET name=?, program=?, class_id=? WHERE student_id=?",
            (name.strip(), program.strip(), class_id, student_id),
        )
        self.conn.commit()

    def delete_student(self, student_id: str) -> None:
        self.conn.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        self.conn.commit()

    def list_students(self, *, class_id: int | None = None, q: str | None = None) -> list[sqlite3.Row]:
        where = []
        params: list[object] = []
        if class_id is not None:
            where.append("s.class_id=?")
            params.append(class_id)
        if q:
            where.append("(s.student_id LIKE ? OR s.name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        sql = """
            SELECT s.student_id, s.name, s.program, c.name AS class_name, s.class_id
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY s.name"
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def get_student(self, student_id: str) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT s.student_id, s.name, s.program, c.name AS class_name, s.class_id
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE s.student_id=?
            """,
            (student_id,),
        )
        return cur.fetchone()

    # -------------------------
    # Subjects / Marks
    # -------------------------
    def upsert_subject(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Subject name required")
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
        cur.execute("SELECT id FROM subjects WHERE name=?", (name,))
        self.conn.commit()
        return int(cur.fetchone()["id"])

    def list_subjects(self) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM subjects ORDER BY name")
        return cur.fetchall()

    def set_mark(self, student_id: str, subject_id: int, term: str, mark: int) -> None:
        self.conn.execute(
            """
            INSERT INTO marks (student_id, subject_id, term, mark)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, subject_id, term) DO UPDATE SET mark=excluded.mark
            """,
            (student_id, subject_id, term.strip(), int(mark)),
        )
        self.conn.commit()

    def get_student_marks(self, student_id: str, term: str | None = None) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        sql = """
            SELECT sub.name AS subject, m.term, m.mark
            FROM marks m
            JOIN subjects sub ON sub.id = m.subject_id
            WHERE m.student_id=?
        """
        params: list[object] = [student_id]
        if term:
            sql += " AND m.term=?"
            params.append(term)
        sql += " ORDER BY m.term, sub.name"
        cur.execute(sql, params)
        return cur.fetchall()

    def list_marks(self) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT s.name AS student_name, sub.name AS subject_name, m.term, m.mark,
                   CASE 
                       WHEN m.mark >= 90 THEN 'A'
                       WHEN m.mark >= 80 THEN 'B'
                       WHEN m.mark >= 70 THEN 'C'
                       WHEN m.mark >= 60 THEN 'D'
                       ELSE 'F'
                   END AS grade
            FROM marks m
            JOIN students s ON s.student_id = m.student_id
            JOIN subjects sub ON sub.id = m.subject_id
            ORDER BY s.name, sub.name, m.term
        """)
        return cur.fetchall()

    def get_dashboard_stats(self) -> dict[str, int | float]:
        cur = self.conn.cursor()
        stats = {}
        
        cur.execute("SELECT COUNT(*) AS c FROM students")
        stats["total_students"] = int(cur.fetchone()["c"])
        
        cur.execute("SELECT COUNT(*) AS c FROM classes")
        stats["total_classes"] = int(cur.fetchone()["c"])
        
        cur.execute("SELECT COUNT(*) AS c FROM subjects")
        stats["total_subjects"] = int(cur.fetchone()["c"])
        
        cur.execute("SELECT AVG(mark) AS a FROM marks")
        avg = cur.fetchone()["a"]
        stats["avg_mark"] = round(float(avg), 1) if avg is not None else 0.0
        
        cur.execute("SELECT COUNT(*) AS c FROM users")
        stats["total_users"] = int(cur.fetchone()["c"])
        
        return stats

    def class_averages(self, class_id: int, term: str) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT s.student_id, s.name, ROUND(AVG(m.mark), 2) AS avg_mark
            FROM students s
            JOIN marks m ON m.student_id = s.student_id
            WHERE s.class_id=? AND m.term=?
            GROUP BY s.student_id, s.name
            ORDER BY avg_mark DESC
            """,
            (class_id, term),
        )
        return cur.fetchall()

