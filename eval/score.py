"""Score recorded model replies against a hand-made answer key, before and after the rule checks.

python3 eval/score.py FIXTURE_DIR [SAMPLE_DIR]   (SAMPLE_DIR holds inbox/, rent_roll.csv, truth.json; default samples/)
Counts, per message, the fields kind / payer / amount / date (payer, amount, date only for money received).
'Wrong and not flagged' = the final value is wrong and the field isn't marked CHECK. Exit 1 if that's not 0
or if any unit's status differs from the key."""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rentsloth import ledger  # noqa: E402
from rentsloth.verify import verify  # noqa: E402


def same(k, got, want):
    if k == "amount": return abs(float(got or 0) - want) < 0.005
    if k == "date": return str(got) == want
    if k == "payer": return (got or "").strip().lower() == want.lower()
    return got == want


def main(fx, sd="samples"):
    truth = json.load(open(os.path.join(sd, "truth.json"))); units = ledger.load_roll(os.path.join(sd, "rent_roll.csv"))
    y, m = map(int, truth["month"].split("-")); as_of = dt.date.fromisoformat(truth["as_of"])
    raw = fixed = total = unflagged = flagged = 0; items = []; bad = []
    for name, t in sorted(truth["messages"].items()):
        text = open(os.path.join(sd, "inbox", name + ".txt")).read()
        reply = json.load(open(os.path.join(fx, name + ".json")))["reply"]; v = verify(reply, text); items.append((name, v))
        keys = ["kind"] + (["payer", "amount", "date"] if t["kind"] == "money_received" else [])
        for k in keys:
            total += 1
            rv = reply["kind"] if k == "kind" else reply[k]["value"]
            raw += same(k, rv, t[k]); ok = same(k, v[k]["value"], t[k]); fixed += ok
            if not ok and v[k]["status"] == "CHECK": flagged += 1
            if not ok and v[k]["status"] != "CHECK": unflagged += 1; bad.append(f"{name} {k}: {v[k]['value']!r} vs {t[k]!r}")
    rows, status, ignored, check = ledger.build(items, units, y, m, as_of)
    got_units = {s["unit"]: s["status"] for s in status}
    unit_ok = sum(got_units[u] == s for u, s in truth["units"].items())
    # where did every payment end up?
    placed = {r["source"]: (r["unit"] if r["status"] == "ok" else "CHECK") for r in rows}
    for src, why in ignored: placed[src] = "duplicate" if why.startswith("duplicate") else ("other month" if "outside" in why else "not counted")
    place_ok = sum(placed.get(n, "?") == t.get("unit", "not counted") for n, t in truth["messages"].items())
    print(f"fields {total}: model alone {raw}, after rules {fixed}, wrong but flagged CHECK {flagged}, wrong and NOT flagged {unflagged}")
    print(f"payments placed correctly {place_ok}/{len(truth['messages'])}; unit statuses {unit_ok}/{len(truth['units'])}")
    for b in bad: print("UNFLAGGED", b)
    for n, t in truth["messages"].items():
        if placed.get(n, "?") != t.get("unit", "not counted"): print("PLACED", n, placed.get(n), "vs", t.get("unit", "not counted"))
    for u, s in truth["units"].items():
        if got_units[u] != s: print("UNIT", u, got_units[u], "vs", s)
    return 0 if (unflagged == 0 and unit_ok == len(truth["units"])) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
