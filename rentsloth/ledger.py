"""Plain, tested code: match checked payments to the rent roll, drop duplicates, total each unit, write the summary."""
import calendar
import csv
import datetime as dt
import re

UNIT_RX = re.compile(r"\b(?:unit|apt|apartment|suite|#)\s*([0-9]+[A-Za-z]?)\b", re.I)


def load_roll(path):
    units = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            units.append({"unit": r["unit"].strip(), "tenants": [t.strip() for t in r["tenants"].split(";") if t.strip()],
                          "rent": float(r["rent"]), "due_day": int(r.get("due_day") or 1), "grace_days": int(r.get("grace_days") or 0)})
    return units


def _words(s):
    return re.findall(r"[a-z][a-z'-]*", (s or "").lower())


def match_unit(payer, memo, units):
    """Return (unit, how) or (None, reason). Unit numbers in the memo win only if names don't point elsewhere."""
    m = re.match(r"^\s*([A-Za-z'-]+),\s*([A-Za-z'-]+)", payer or "")  # bank style "ALVAREZ, BETH M"
    if m:
        payer = f"{m.group(2)} {m.group(1)}"
    text = f"{payer} {memo}"
    by_unit = set(m.group(1).upper() for m in UNIT_RX.finditer(text))
    codes = {u["unit"].upper(): u for u in units}
    for tok in re.findall(r"\b([0-9]+[A-Za-z]?)\b", memo or ""):
        if tok.upper() in codes: by_unit.add(tok.upper())
    by_unit &= set(codes)
    by_name = set()
    low = " ".join(_words(text))
    for u in units:
        for t in u["tenants"]:
            if " ".join(_words(t)) and re.search(r"\b" + re.escape(" ".join(_words(t))) + r"\b", low):
                by_name.add(u["unit"].upper())
    if not by_name and payer:
        pw = _words(payer)
        for u in units:
            for t in u["tenants"]:
                tw = _words(t)
                if pw and tw and pw[-1] == tw[-1] and (pw[0].startswith(tw[0]) or tw[0].startswith(pw[0])):
                    by_name.add(u["unit"].upper())
    if len(by_name) > 1:
        return None, "name matches more than one unit"
    if by_name and by_unit and by_name != by_unit:
        return None, f"name says {sorted(by_name)[0]}, memo says {sorted(by_unit)[0]}"
    hit = by_name or by_unit
    if len(hit) == 1:
        how = "name" if by_name else "unit in memo"
        return codes[next(iter(hit))]["unit"], how
    return None, "no tenant or unit matched"


def month_window(year, month, due_day):
    due = dt.date(year, month, min(due_day, calendar.monthrange(year, month)[1]))
    return due - dt.timedelta(days=10), dt.date(year, month, calendar.monthrange(year, month)[1]), due


def money(x):
    return f"${x:,.2f}"


def build(items, units, year, month, as_of):
    """items: list of (source, verified_fields). Returns rows, per-unit status, notes for the summary."""
    seen = {}; rows = []; ignored = []; check = []
    for src, v in items:
        kind = v["kind"]["value"]
        if kind != "money_received":
            ignored.append((src, kind)); continue
        key = v["reference"]["value"] or (v["payer"]["value"].lower(), v["amount"]["value"], str(v["date"]["value"]))
        if key in seen:
            ignored.append((src, f"duplicate of {seen[key]}")); continue
        seen[key] = src
        unit, how = match_unit(v["payer"]["value"], v["memo"]["value"], units)
        d = v["date"]["value"]
        lo, hi, _ = month_window(year, month, (next(u for u in units if u["unit"] == unit)["due_day"] if unit else 1))
        if d and not (lo <= d <= hi):
            ignored.append((src, f"dated {d}, outside {calendar.month_abbr[month]} {year}")); continue
        flags = [k for k in ("amount", "date", "payer") if v[k]["status"] == "CHECK" and not (k == "payer" and unit)]
        row = {"date": d, "unit": unit or "", "payer": v["payer"]["value"], "amount": v["amount"]["value"],
               "memo": v["memo"]["value"], "reference": v["reference"]["value"], "matched_by": how if unit else "",
               "status": "CHECK" if (not unit or flags) else "ok",
               "note": "; ".join(([how] if not unit else []) + [f"{k}: {v[k]['note']}" for k in flags]), "source": src}
        rows.append(row)
        if row["status"] == "CHECK": check.append(row)
    status = []
    for u in units:
        paid = sum(r["amount"] for r in rows if r["unit"] == u["unit"] and r["status"] == "ok")
        _, _, due = month_window(year, month, u["due_day"]); late_after = due + dt.timedelta(days=u["grace_days"])
        if paid >= u["rent"] - 0.005:
            s = "Paid" if paid <= u["rent"] + 0.005 else f"Paid ({money(paid - u['rent'])} over)"
        elif paid > 0:
            s = f"Partial ({money(u['rent'] - paid)} short)"
        else:
            s = "Late" if as_of > late_after else "Not yet"
        status.append({"unit": u["unit"], "tenants": " & ".join(u["tenants"]), "rent": u["rent"], "paid": round(paid, 2),
                       "status": s, "late_after": late_after})
    return rows, status, ignored, check


def summary(status, check, year, month):
    full = [s for s in status if s["status"].startswith("Paid")]
    got = sum(min(s["paid"], s["rent"]) for s in status); due = sum(s["rent"] for s in status)
    l1 = (f"{calendar.month_name[month]} {year} rent: {len(full)} of {len(status)} units paid in full, "
          f"{money(got)} of {money(due)} collected.")
    parts = []
    short = [s for s in status if s["status"].startswith("Partial")]
    if short: parts.append("Short: " + ", ".join(f"{s['unit']} {s['tenants']} {money(s['rent'] - s['paid'])}" for s in short) + ".")
    late = [s for s in status if s["status"] == "Late"]
    if late: parts.append("Late: " + ", ".join(f"{s['unit']} {s['tenants']}" for s in late) + ".")
    wait = [s for s in status if s["status"] == "Not yet"]
    if wait: parts.append("Not yet: " + ", ".join(f"{s['unit']} {s['tenants']} (late after {s['late_after']:%b} {s['late_after'].day})" for s in wait) + ".")
    if check:
        parts.append(f"Check {len(check)} payment{'s' if len(check) > 1 else ''}: " + ", ".join(
            f"{money(r['amount'])} {('from ' + r['payer']) if r['payer'] else '(no payer named)'} on {r['date']:%b} {r['date'].day}" for r in check) + ".")
    return l1 + "\n" + (" ".join(parts) if parts else "Nothing to chase.")


def write_csv(path, rows):
    cols = ["date", "unit", "payer", "amount", "memo", "reference", "matched_by", "status", "note", "source"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in sorted(rows, key=lambda r: (str(r["date"]), r["unit"])): w.writerow({k: r[k] for k in cols})
