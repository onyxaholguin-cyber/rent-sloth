import datetime as dt
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from rentsloth import ledger  # noqa: E402
from rentsloth.verify import verify, amounts, parse_dates, rule_kind  # noqa: E402

ZELLE = """From: Riverbend Credit Union <alerts@riverbendcu.example>
Date: Sun, 1 Nov 2026 07:55:31 -0600

Ana Romero sent you $1,650.00
Memo: unit 3A
Date: November 1, 2026
Confirmation number: ZL1
"""


def reply(**kw):
    r = {"kind": "money_received", "payer": {"value": "Ana Romero", "quote": "Ana Romero sent you"},
         "amount": {"value": 1650, "quote": "$1,650.00"}, "date": {"value": "2026-11-01", "quote": "November 1, 2026"},
         "memo": {"value": "unit 3A", "quote": "Memo: unit 3A"}, "reference": {"value": "ZL1", "quote": "ZL1"}}
    for k, v in kw.items(): r[k] = v
    return r


ROLL = [{"unit": "1A", "tenants": ["Maria Lopez"], "rent": 1350.0, "due_day": 1, "grace_days": 5},
        {"unit": "3A", "tenants": ["Luis Romero", "Ana Romero"], "rent": 1650.0, "due_day": 1, "grace_days": 5}]


class Verify(unittest.TestCase):
    def test_clean_reading_is_ok(self):
        v = verify(reply(), ZELLE)
        self.assertEqual([v[k]["status"] for k in ("kind", "payer", "amount", "date")], ["ok"] * 4)

    def test_invented_amount_is_flagged(self):
        v = verify(reply(amount={"value": 1600, "quote": "Ana Romero sent you"}), ZELLE)
        self.assertEqual(v["amount"]["status"], "CHECK")

    def test_wrong_amount_with_clear_quote_is_fixed(self):
        v = verify(reply(amount={"value": 1600, "quote": "$1,650.00"}), ZELLE)
        self.assertEqual((v["amount"]["status"], v["amount"]["value"]), ("FIXED", 1650.0))

    def test_paraphrased_quote_is_not_trusted(self):
        v = verify(reply(amount={"value": 1650, "quote": "one thousand six hundred fifty"}), ZELLE)
        self.assertEqual(v["amount"]["status"], "CHECK")

    def test_bank_as_payer_is_replaced_by_the_named_person(self):
        v = verify(reply(payer={"value": "Riverbend Credit Union", "quote": "Riverbend Credit Union"}), ZELLE)
        self.assertEqual((v["payer"]["status"], v["payer"]["value"]), ("FIXED", "Ana Romero"))

    def test_payment_app_as_payer_is_replaced(self):
        v = verify(reply(payer={"value": "Zelle", "quote": "Zelle"}), ZELLE + "Sent with Zelle\n")
        self.assertEqual((v["payer"]["status"], v["payer"]["value"]), ("FIXED", "Ana Romero"))

    def test_you_sent_is_never_money_received(self):
        t = ZELLE.replace("Ana Romero sent you $1,650.00", "You sent $200.00 to Luis Romero")
        self.assertEqual(verify(reply(), t)["kind"]["value"], "money_sent")

    def test_request_is_not_a_payment(self):
        self.assertEqual(rule_kind("You requested $1,400.00 from Tom Becker"), "payment_request")

    def test_date_falls_back_to_header(self):
        v = verify(reply(date={"value": "2026-11-09", "quote": "Nov, 9"}), ZELLE)
        self.assertEqual((v["date"]["value"], v["date"]["status"]), (dt.date(2026, 11, 1), "FIXED"))

    def test_last_first_payer_is_reordered(self):
        t = ZELLE.replace("Ana Romero sent you", "Originator: ROMERO, ANA M\nsent you")
        v = verify(reply(payer={"value": "ROMERO, ANA M", "quote": "ROMERO, ANA M"}), t)
        self.assertEqual((v["payer"]["value"], v["payer"]["status"]), ("Ana Romero", "FIXED"))

    def test_parsers(self):
        self.assertEqual(amounts("$1,350.00 on 11/03/2026 and 650.00"), [1350.0, 650.0])
        self.assertEqual(parse_dates("11/03/2026, Nov 2 at 12:30 PM", 2026), [dt.date(2026, 11, 3), dt.date(2026, 11, 2)])

    def test_memo_not_in_message_is_dropped(self):
        v = verify(reply(memo={"value": "November rent", "quote": "November rent"}), ZELLE)
        self.assertEqual((v["memo"]["value"], v["memo"]["status"]), ("", "FIXED"))


class Ledger(unittest.TestCase):
    def items(self, *specs):
        out = []
        for i, (payer, amt, d, memo, ref) in enumerate(specs):
            out.append((f"m{i}", {"kind": {"value": "money_received"}, "payer": {"value": payer, "status": "ok"},
                                  "amount": {"value": amt, "status": "ok"}, "date": {"value": d, "status": "ok"},
                                  "memo": {"value": memo}, "reference": {"value": ref}}))
        return out

    def test_match_by_name_alias_and_unit(self):
        self.assertEqual(ledger.match_unit("Samuel Lopez", "", [{"unit": "1A", "tenants": ["Sam Lopez"]}])[0], "1A")
        self.assertEqual(ledger.match_unit("", "ACH CREDIT MARIA LOPEZ RENT", ROLL)[0], "1A")
        self.assertEqual(ledger.match_unit("J Smith", "Apt 3A", ROLL), ("3A", "unit in memo"))
        self.assertIsNone(ledger.match_unit("Maria Lopez", "unit 3A", ROLL)[0])  # conflict -> human

    def test_bank_style_last_first_name_matches(self):
        # found by the held-out set: "Originator: ALVAREZ, BETH M" went to CHECK instead of unit 201
        self.assertEqual(ledger.match_unit("ALVAREZ, BETH M", "RENT", [{"unit": "201", "tenants": ["Beth Alvarez"]}]), ("201", "name"))

    def test_duplicates_window_partial_late(self):
        D = dt.date
        items = self.items(("Maria Lopez", 1000, D(2026, 10, 30), "", "R1"), ("Maria Lopez", 1000, D(2026, 10, 30), "", "R1"),
                           ("Ana Romero", 1650, D(2026, 10, 2), "", "R2"))
        rows, status, ignored, check = ledger.build(items, ROLL, 2026, 11, D(2026, 11, 7))
        self.assertEqual([s["status"] for s in status], ["Partial ($350.00 short)", "Late"])
        self.assertEqual([w.split(" ")[0] for _, w in ignored], ["duplicate", "dated"])

    def test_overpaid_and_not_yet(self):
        D = dt.date
        rows, status, _, _ = ledger.build(self.items(("Maria Lopez", 1400, D(2026, 11, 1), "", "")), ROLL, 2026, 11, D(2026, 11, 3))
        self.assertEqual([s["status"] for s in status], ["Paid ($50.00 over)", "Not yet"])
        self.assertIn("Not yet: 3A Luis Romero & Ana Romero (late after Nov 6).", ledger.summary(status, [], 2026, 11))


class Recorded(unittest.TestCase):
    def test_recorded_runs_score_clean(self):
        for fx, sd in [("tests/fixtures/gemma-4-E2B-it-Q4_0", "samples"), ("tests/fixtures/holdout-gemma-4-E2B-it-Q4_0", "samples/holdout")]:
            if os.path.isdir(os.path.join(ROOT, fx)):
                r = subprocess.run([sys.executable, "eval/score.py", fx, sd], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout)

    def test_cli_summary_matches_example(self):
        r = subprocess.run([sys.executable, "-m", "rentsloth", "samples/inbox", "--roll", "samples/rent_roll.csv", "--month", "2026-11",
                            "--as-of", "2026-11-04", "--out", "/tmp/rent-sloth-test", "--from-json", "tests/fixtures/gemma-4-E2B-it-Q4_0"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)  # two payments need a human look
        self.assertEqual(r.stdout, open(os.path.join(ROOT, "examples", "summary.txt")).read())


if __name__ == "__main__":
    unittest.main()
