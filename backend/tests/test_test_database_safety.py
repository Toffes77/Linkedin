import unittest

from src.db.test_safety import assert_safe_test_database_url


class TestDatabaseSafetyTests(unittest.TestCase):
    def test_principal_postgres_database_is_rejected(self):
        with self.assertRaises(RuntimeError):
            assert_safe_test_database_url("postgresql://user:password@localhost/Linkedin")

    def test_only_isolated_postgres_prefix_and_sqlite_are_allowed(self):
        assert_safe_test_database_url("postgresql://user:password@localhost/atanes_test_abc123")
        assert_safe_test_database_url("sqlite://")
