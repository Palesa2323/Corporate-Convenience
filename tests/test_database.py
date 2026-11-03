"""Database privacy and access tests.  Run:  python -m unittest -v test_database

Uses a temporary database, so your real tickets.db is never touched.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import database as db


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._original_path = db.DATABASE_PATH
        db.DATABASE_PATH = Path(self._tmp.name) / "test.db"
        db.init_db()
        db.seed_test_accounts()

        self.admin = db.get_employee("ADMIN001")
        self.emp1 = db.get_employee("EMP001")
        self.emp2 = db.get_employee("EMP002")
        self.it = db.get_employee("IT001")
        self.hr = db.get_employee("HR001")

        self.t_it = db.save_employee_ticket(
            "Laptop will not boot", "IT", "EMP001", "Laptop", "High")
        self.t_hr = db.save_employee_ticket(
            "Question about leave", "HR", "EMP001", "Leave", "Low")
        self.t_fin = db.save_employee_ticket(
            "Payslip is wrong", "finance", "EMP002", "Payslip", "urgent")

    def tearDown(self):
        db.DATABASE_PATH = self._original_path
        self._tmp.cleanup()


class TestAccounts(DatabaseTestCase):

    def test_password_is_hashed(self):
        with db.get_connection() as c:
            stored = c.execute(
                "SELECT password_hash FROM employees WHERE employee_id='EMP001'"
            ).fetchone()[0]
        self.assertNotEqual(stored, db.TEST_PASSWORD)
        self.assertNotIn(db.TEST_PASSWORD, stored)

    def test_login_success_and_failure(self):
        user = db.verify_login("EMP001", db.TEST_PASSWORD)
        self.assertEqual(user["role"], "Employee")
        self.assertNotIn("password_hash", user)
        self.assertIsNone(db.verify_login("EMP001", "wrong-password"))
        self.assertIsNone(db.verify_login("NOBODY", db.TEST_PASSWORD))
        self.assertIsNone(db.verify_login("", ""))

    def test_get_employee_hides_hash(self):
        self.assertNotIn("password_hash", db.get_employee("EMP001"))

    def test_duplicate_id_and_email_rejected(self):
        with self.assertRaises(ValueError):
            db.create_employee(self.admin, "EMP001", "Password123!",
                               "Employee", "IT", "new@example.com")
        with self.assertRaises(ValueError):
            db.create_employee(self.admin, "EMP099", "Password123!",
                               "Employee", "IT", "emp001@example.com")

    def test_support_staff_requires_department(self):
        with self.assertRaises(ValueError):
            db.create_employee(self.admin, "IT002", "Password123!",
                               "Support Staff", None, "it2@example.com")

    def test_weak_password_rejected(self):
        with self.assertRaises(ValueError):
            db.create_employee(self.admin, "EMP050", "short",
                               "Employee", "IT", "e50@example.com")

    def test_only_admin_manages_accounts(self):
        for actor in (self.emp1, self.it):
            with self.assertRaises(PermissionError):
                db.create_employee(actor, "EMP077", "Password123!",
                                   "Employee", "IT", "x@example.com")
            with self.assertRaises(PermissionError):
                db.list_employees(actor)
            with self.assertRaises(PermissionError):
                db.reset_password(actor, "ADMIN001", "Hacked12345")

    def test_deactivated_user_cannot_log_in_or_access(self):
        db.update_employee(self.admin, "EMP001", is_active=False)
        self.assertIsNone(db.verify_login("EMP001", db.TEST_PASSWORD))
        with self.assertRaises(PermissionError):
            db.get_tickets_for_user(self.emp1)

    def test_cannot_deactivate_last_admin(self):
        with self.assertRaises(ValueError):
            db.update_employee(self.admin, "ADMIN001", is_active=False)

    def test_change_own_password(self):
        db.change_own_password(self.emp1, db.TEST_PASSWORD, "NewPassword99")
        self.assertIsNotNone(db.verify_login("EMP001", "NewPassword99"))
        with self.assertRaises(PermissionError):
            db.change_own_password(self.emp1, "wrong", "AnotherPass11")


class TestTicketPrivacy(DatabaseTestCase):

    def test_ticket_numbers_unique_and_formatted(self):
        numbers = {self.t_it["ticket_number"], self.t_hr["ticket_number"],
                   self.t_fin["ticket_number"]}
        self.assertEqual(len(numbers), 3)
        self.assertTrue(self.t_it["ticket_number"].startswith("TKT-"))

    def test_priority_and_department_normalised(self):
        self.assertEqual(self.t_fin["department"], "Finance")
        self.assertEqual(self.t_fin["priority"], "Urgent")

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            db.save_employee_ticket("x", "Legal", "EMP001")
        with self.assertRaises(ValueError):
            db.save_employee_ticket("   ", "IT", "EMP001")
        with self.assertRaises(ValueError):
            db.save_employee_ticket("x", "IT", "EMP001", priority="Panic")
        with self.assertRaises(ValueError):
            db.save_employee_ticket("x", "IT", "GHOST")

    def test_employee_sees_only_own_tickets(self):
        ids = {t["ticket_id"] for t in db.get_tickets_for_user(self.emp1)}
        self.assertEqual(ids, {self.t_it["ticket_id"], self.t_hr["ticket_id"]})
        ids2 = {t["ticket_id"] for t in db.get_tickets_for_user(self.emp2)}
        self.assertEqual(ids2, {self.t_fin["ticket_id"]})

    def test_employee_cannot_open_others_ticket(self):
        with self.assertRaises(PermissionError):
            db.get_ticket_for_user(self.emp1, self.t_fin["ticket_id"])

    def test_employee_cannot_view_department_queue_or_all(self):
        with self.assertRaises(PermissionError):
            db.get_department_tickets(self.emp1, "IT")
        with self.assertRaises(PermissionError):
            db.get_all_tickets(self.emp1)

    def test_support_sees_only_own_department(self):
        it_tickets = db.get_tickets_for_user(self.it)
        self.assertEqual([t["department"] for t in it_tickets], ["IT"])
        hr_tickets = db.get_tickets_for_user(self.hr)
        self.assertEqual([t["department"] for t in hr_tickets], ["HR"])

    def test_support_cannot_cross_departments(self):
        with self.assertRaises(PermissionError):
            db.get_department_tickets(self.it, "HR")
        with self.assertRaises(PermissionError):
            db.get_ticket_for_user(self.it, self.t_hr["ticket_id"])
        with self.assertRaises(PermissionError):
            db.get_all_tickets(self.it)

    def test_support_sees_employee_email(self):
        ticket = db.get_ticket_for_user(self.it, self.t_it["ticket_id"])
        self.assertEqual(ticket["employee_email"], "emp001@example.com")

    def test_admin_sees_everything(self):
        self.assertEqual(len(db.get_tickets_for_user(self.admin)), 3)
        self.assertEqual(len(db.get_all_tickets(self.admin)), 3)

    def test_forged_session_dict_cannot_escalate(self):
        forged = {"employee_id": "EMP001", "role": "Admin", "department": None}
        tickets = db.get_tickets_for_user(forged)
        self.assertEqual(len(tickets), 2)  # still treated as an Employee
        with self.assertRaises(PermissionError):
            db.get_all_tickets(forged)
        forged_staff = {"employee_id": "IT001", "role": "Support Staff",
                        "department": "HR"}
        with self.assertRaises(PermissionError):
            db.get_ticket_for_user(forged_staff, self.t_hr["ticket_id"])

    def test_unauthenticated_rejected(self):
        for bad in (None, {}, {"employee_id": "GHOST"}):
            with self.assertRaises(PermissionError):
                db.get_tickets_for_user(bad)

    def test_status_updates_are_restricted(self):
        updated = db.update_ticket_status(self.t_it["ticket_id"],
                                          "In Progress", self.it)
        self.assertEqual(updated["status"], "In Progress")
        with self.assertRaises(PermissionError):
            db.update_ticket_status(self.t_hr["ticket_id"], "Resolved", self.it)
        with self.assertRaises(PermissionError):
            db.update_ticket_status(self.t_it["ticket_id"], "Resolved",
                                    self.emp1)
        with self.assertRaises(ValueError):
            db.update_ticket_status(self.t_it["ticket_id"], "Done", self.admin)


class TestResponses(DatabaseTestCase):

    def test_draft_send_and_history(self):
        tid = self.t_it["ticket_id"]
        draft = db.save_draft(self.it, tid, "Friendly", "Hi, we are on it.")
        self.assertEqual(draft["status"], "Draft")

        sent = db.mark_response_sent(self.it, draft["response_id"],
                                     "Hi, we are on it. Please reboot.")
        self.assertEqual(sent["status"], "Sent")
        self.assertEqual(sent["sent_by"], "IT001")
        self.assertIsNotNone(sent["sent_at"])

        with self.assertRaises(ValueError):
            db.mark_response_sent(self.it, draft["response_id"], "again")

        staff_view = db.get_response_history(self.it, tid)
        self.assertEqual(len(staff_view), 1)
        self.assertEqual(staff_view[0]["draft_text"], "Hi, we are on it.")

    def test_employee_sees_sent_replies_only(self):
        tid = self.t_it["ticket_id"]
        unsent = db.save_draft(self.it, tid, "Formal", "Internal draft")
        self.assertEqual(db.get_response_history(self.emp1, tid), [])

        db.mark_response_sent(self.it, unsent["response_id"], "Final reply")
        db.save_draft(self.it, tid, "Formal", "Second internal draft")
        visible = db.get_response_history(self.emp1, tid)
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]["final_text"], "Final reply")
        self.assertNotIn("draft_text", visible[0])

    def test_cross_department_response_access_denied(self):
        draft = db.save_draft(self.it, self.t_it["ticket_id"],
                              "Formal", "Draft")
        with self.assertRaises(PermissionError):
            db.save_draft(self.hr, self.t_it["ticket_id"], "Formal", "Nope")
        with self.assertRaises(PermissionError):
            db.mark_response_sent(self.hr, draft["response_id"], "Nope")
        with self.assertRaises(PermissionError):
            db.get_response_history(self.emp2, self.t_it["ticket_id"])
        with self.assertRaises(PermissionError):
            db.get_response_history(self.hr, self.t_it["ticket_id"])

    def test_invalid_tone_rejected(self):
        with self.assertRaises(ValueError):
            db.save_draft(self.it, self.t_it["ticket_id"], "Rude", "text")

    def test_email_log(self):
        tid = self.t_it["ticket_id"]
        db.record_email_result(tid, "Confirmation", "emp001@example.com", True)
        db.record_email_result(tid, "Response", "emp001@example.com", False,
                               error="SMTP timeout")
        log = db.get_email_log(self.it, tid)
        self.assertEqual([r["success"] for r in log], [1, 0])
        self.assertEqual(log[1]["error"], "SMTP timeout")
        with self.assertRaises(PermissionError):
            db.get_email_log(self.hr, tid)


class TestMigration(unittest.TestCase):

    def test_old_schema_is_upgraded_and_backfilled(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = db.DATABASE_PATH
            db.DATABASE_PATH = Path(tmp) / "old.db"
            try:
                conn = sqlite3.connect(db.DATABASE_PATH)
                conn.executescript("""
                    CREATE TABLE tickets (
                        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        department TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Open');
                    CREATE TABLE employees (
                        employee_id TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (
                            role IN ('Employee','Support Staff','Admin')));
                    INSERT INTO tickets (message, department, created_at)
                        VALUES ('old ticket', 'IT', '2026-01-01');
                """)
                conn.commit()
                conn.close()

                db.init_db()

                ticket = db.get_ticket(1)
                self.assertEqual(ticket["ticket_number"], "TKT-000001")
                self.assertEqual(ticket["priority"], "Medium")
                db.init_db()  # running twice must be harmless
            finally:
                db.DATABASE_PATH = original


if __name__ == "__main__":
    unittest.main()
