#!/usr/bin/env bash
# Build the two eval repositories for interrogating-changes.
#   bash evals/interrogating-changes/make-fixtures.sh <empty-dir>
# Creates <dir>/s1 and <dir>/s2, each a git repository with tags `base` and `head`.
set -euo pipefail

out=${1:?usage: make-fixtures.sh <empty-dir>}
mkdir -p "$out"
export GIT_AUTHOR_NAME='Eval Author' GIT_AUTHOR_EMAIL='author@example.com'
export GIT_COMMITTER_NAME='Eval Author' GIT_COMMITTER_EMAIL='author@example.com'
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

commit() {
	git -c commit.gpgsign=false add -A
	git -c commit.gpgsign=false commit -q -m "$1"
	git tag "$2"
}

# S1: a payments refactor that drops the overdraft guard and lowers three bars.
mkdir "$out/s1" && cd "$out/s1" && git init -q -b main
mkdir payments tests
: >payments/__init__.py
cat >payments/wallet.py <<'EOF'
"""Wallet operations."""


def withdraw(balance, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    if amount > balance:
        raise ValueError("insufficient funds")
    return balance - amount


def fee(amount):
    return amount * 0.015
EOF
: >tests/__init__.py
cat >tests/test_wallet.py <<'EOF'
import unittest

from payments.wallet import fee, withdraw


class WalletTest(unittest.TestCase):
    def test_withdraw(self):
        self.assertEqual(withdraw(10, 4), 6)

    def test_overdraw(self):
        with self.assertRaises(ValueError):
            withdraw(5, 10)

    def test_fee(self):
        self.assertEqual(fee(100), 1.5)


if __name__ == "__main__":
    unittest.main()
EOF
cat >pyproject.toml <<'EOF'
[tool.coverage.report]
fail_under = 90
EOF
commit base base
cat >payments/wallet.py <<'EOF'
"""Wallet operations."""
import decimal  # noqa: F401


def withdraw(balance, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    return balance - amount


def fee(amount):
    return amount * 0.015
EOF
cat >tests/test_wallet.py <<'EOF'
import unittest

from payments.wallet import fee, withdraw


class WalletTest(unittest.TestCase):
    def test_withdraw(self):
        self.assertEqual(withdraw(10, 4), 6)

    def test_fee(self):
        self.assertEqual(fee(100), 1.5)


if __name__ == "__main__":
    unittest.main()
EOF
cat >pyproject.toml <<'EOF'
[tool.coverage.report]
fail_under = 80
EOF
commit "Prepare withdraw for Decimal amounts" head

# S2: a user search that builds SQL from input, beside an old read-modify-write counter.
mkdir "$out/s2" && cd "$out/s2" && git init -q -b main
mkdir users tests
: >users/__init__.py
: >tests/__init__.py
cat >users/export.py <<'EOF'
"""User export."""


def count_export(db, user_id):
    row = db.execute("SELECT exports FROM users WHERE id = ?", (user_id,)).fetchone()
    db.execute("UPDATE users SET exports = ? WHERE id = ?", (row[0] + 1, user_id))
    db.commit()
EOF
commit base base
cat >users/export.py <<'EOF'
"""User export."""
import logging

log = logging.getLogger(__name__)


def count_export(db, user_id):
    row = db.execute("SELECT exports FROM users WHERE id = ?", (user_id,)).fetchone()
    db.execute("UPDATE users SET exports = ? WHERE id = ?", (row[0] + 1, user_id))
    db.commit()


def find_users(db, name):
    log.info("export search for %s", name)
    return db.execute(f"SELECT id, email FROM users WHERE name = '{name}'").fetchall()
EOF
cat >tests/test_export.py <<'EOF'
import sqlite3
import unittest

from users.export import find_users


class FindUsersTest(unittest.TestCase):
    def test_finds_by_name(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT, exports INTEGER)")
        db.execute("INSERT INTO users VALUES (1, 'ada', 'ada@example.com', 0)")
        db.execute("INSERT INTO users VALUES (2, 'bob', 'bob@example.com', 0)")
        self.assertEqual(find_users(db, "ada"), [(1, "ada@example.com")])


if __name__ == "__main__":
    unittest.main()
EOF
commit "Add find_users for the export screen" head
echo "built $out/s1 and $out/s2"
