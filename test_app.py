import os
import tempfile
import unittest
from datetime import date, timedelta

import app as lib


class FineTests(unittest.TestCase):
    def test_no_fine_when_on_time(self):
        self.assertEqual(lib.calculate_fine(date.today().isoformat()), 0)

    def test_fine_for_late_return(self):
        due = (date.today() - timedelta(days=3)).isoformat()
        self.assertEqual(lib.calculate_fine(due), 3 * lib.FINE_PER_DAY)

    def test_fine_uses_return_date(self):
        self.assertEqual(lib.calculate_fine("2026-01-01", "2026-01-05"), 4 * lib.FINE_PER_DAY)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()
        lib.app.config.update(DATABASE=self.path, TESTING=True)
        lib.init_db()
        self.client = lib.app.test_client()
        self.client.post("/books/add", data=dict(title="Clean Code", author="R. Martin", copies=1))
        self.client.post("/members", data=dict(name="Monica", email="m@example.com"))

    def tearDown(self):
        os.close(self.fd)
        os.unlink(self.path)

    def test_issue_reduces_stock_and_return_restores_it(self):
        self.client.post("/issue", data=dict(book_id=1, member_id=1))
        self.assertIn(b"Out of stock", self.client.get("/").data)
        self.client.post("/return/1")
        self.assertNotIn(b"Out of stock", self.client.get("/").data)

    def test_cannot_issue_without_stock(self):
        self.client.post("/issue", data=dict(book_id=1, member_id=1))
        r = self.client.post("/issue", data=dict(book_id=1, member_id=1), follow_redirects=True)
        self.assertIn(b"no copies available", r.data)

    def test_duplicate_email_rejected(self):
        r = self.client.post("/members", data=dict(name="Other", email="m@example.com"), follow_redirects=True)
        self.assertIn(b"already exists", r.data)


if __name__ == "__main__":
    unittest.main()
