
import unittest

from backend.authy import (
    register_employee,
    authenticate_employee,
    provision_employee_account
)
from backend.database import get_connection


class TestAuthentication(unittest.TestCase):

    def setUp(self):
        self.employee_id = "TEST_EMP_AUTH"
        self.admin_id = "TEST_ADMIN_AUTH"
        self.support_id = "TEST_SUPPORT_AUTH"

        # Remove test accounts before each test.
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM employees
                WHERE employee_id IN (?, ?, ?)
                """,
                (
                    self.employee_id,
                    self.admin_id,
                    self.support_id
                )
            )

            # Create a controlled test Admin account.
            connection.execute(
                """
                INSERT INTO employees (
                    employee_id, password_hash, role, department
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    self.admin_id,
                    "test-placeholder",
                    "Admin",
                    None
                )
            )

    def test_employee_registration_and_login(self):
        register_employee(
            self.employee_id,
            "TestPassword123!"
        )

        employee = authenticate_employee(
            self.employee_id,
            "TestPassword123!"
        )

        self.assertIsNotNone(employee)
        self.assertEqual(employee["role"], "Employee")

    def test_incorrect_password(self):
        register_employee(
            self.employee_id,
            "TestPassword123!"
        )

        result = authenticate_employee(
            self.employee_id,
            "WrongPassword"
        )

        self.assertIsNone(result)

    def test_duplicate_employee_id(self):
        register_employee(
            self.employee_id,
            "TestPassword123!"
        )

        with self.assertRaises(ValueError):
            register_employee(
                self.employee_id,
                "AnotherPassword123!"
            )

    def test_employee_cannot_register_as_admin(self):
        with self.assertRaises(ValueError):
            register_employee(
                self.employee_id,
                "TestPassword123!",
                role="Admin"
            )

    def test_non_admin_cannot_create_support_account(self):
        register_employee(
            self.employee_id,
            "TestPassword123!"
        )

        with self.assertRaises(PermissionError):
            provision_employee_account(
                admin_id=self.employee_id,
                employee_id=self.support_id,
                password="SupportPassword123!",
                role="Support Staff",
                department="IT"
            )

    def test_admin_can_create_support_account(self):
        provision_employee_account(
            admin_id=self.admin_id,
            employee_id=self.support_id,
            password="SupportPassword123!",
            role="Support Staff",
            department="IT"
        )

        with get_connection() as connection:
            support = connection.execute(
                """
                SELECT role, department
                FROM employees
                WHERE employee_id = ?
                """,
                (self.support_id,)
            ).fetchone()

        self.assertEqual(support["role"], "Support Staff")
        self.assertEqual(support["department"], "IT")

    def test_support_staff_requires_department(self):
        with self.assertRaises(ValueError):
            provision_employee_account(
                admin_id=self.admin_id,
                employee_id=self.support_id,
                password="SupportPassword123!",
                role="Support Staff"
            )

    def test_admin_can_create_another_admin(self):
        provision_employee_account(
            admin_id=self.admin_id,
            employee_id=self.employee_id,
            password="NewAdminPassword123!",
            role="Admin"
        )

        new_admin = authenticate_employee(
            self.employee_id,
            "NewAdminPassword123!"
        )

        self.assertIsNotNone(new_admin)
        self.assertEqual(new_admin["role"], "Admin")


if __name__ == "__main__":
    unittest.main()
