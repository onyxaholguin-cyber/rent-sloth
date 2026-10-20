"""python3 -m rentsloth INBOX --roll rent_roll.csv --month 2026-11 [--as-of 2026-11-04] [--out DIR]

Reads every .txt/.eml in INBOX with a local model (or recorded replies via --from-json), checks each reading with
rules, and writes ledger.csv, audit.md and a two-line summary.txt. Exit code 1 if anything needs a human look."""
import argparse
import datetime as dt
import glob
import json
import os
import sys

from . import ledger
from .verify import verify


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rentsloth")
    ap.add_argument("inbox"); ap.add_argument("--roll", required=True); ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--as-of", default=dt.date.today().isoformat()); ap.add_argument("--out", default="rent-sloth-out")
    ap.add_argument("--server", default=os.environ.get("RENT_SLOTH_SERVER", "http://127.0.0.1:8080"))
    ap.add_argument("--from-json", help="directory of recorded model replies (<name>.json); no model needed")
    ap.add_argument("--record", help="save each model reply to this directory")
    a = ap.parse_args(argv)
    year, month = map(int, a.month.split("-")); as_of = dt.date.fromisoformat(a.as_of)
    units = ledger.load_roll(a.roll); os.makedirs(a.out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.inbox, "*.txt")) + glob.glob(os.path.join(a.inbox, "*.eml")))
    items = []; audit = ["# Rent Sloth audit", ""]
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]; text = open(f, encoding="utf-8", errors="replace").read()
        if a.from_json:
            reply = json.load(open(os.path.join(a.from_json, name + ".json")))["reply"]; secs = None
        else:
            from .extract import extract
            reply, meta = extract(text, a.server); secs = meta["seconds"]
            if a.record:
                os.makedirs(a.record, exist_ok=True)
                json.dump({"reply": reply, "meta": meta}, open(os.path.join(a.record, name + ".json"), "w"), indent=1, ensure_ascii=False)
        v = verify(reply, text); items.append((name, v))
        print(f"read {name}" + (f" ({secs} s)" if secs else "") + f": {v['kind']['value']} {v['amount']['value']}", file=sys.stderr)
        audit += [f"## {name}", ""] + [f"- **{k}**: {v[k]['value']!s} `{v[k]['status']}` {v[k].get('note', '')}".rstrip()
                                       for k in ("kind", "payer", "amount", "date", "memo", "reference")] + [""]
    rows, status, ignored, check = ledger.build(items, units, year, month, as_of)
    ledger.write_csv(os.path.join(a.out, "ledger.csv"), rows)
    text = ledger.summary(status, check, year, month)
    open(os.path.join(a.out, "summary.txt"), "w").write(text + "\n")
    audit += ["## Units", ""] + [f"- {s['unit']} {s['tenants']}: {ledger.money(s['paid'])} of {ledger.money(s['rent'])}, {s['status']}" for s in status]
    audit += ["", "## Not counted", ""] + [f"- {src}: {why}" for src, why in ignored]
    open(os.path.join(a.out, "audit.md"), "w").write("\n".join(audit) + "\n")
    print(text)
    return 1 if check else 0


if __name__ == "__main__":
    sys.exit(main())
