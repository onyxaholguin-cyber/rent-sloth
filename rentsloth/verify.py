"""Check the model's reading with plain rules. Every field ends up 'ok', 'FIXED' (a rule corrected it) or 'CHECK'
(a human should look). The rules only use the message text, so a wrong reading can't invent money."""
import datetime as dt
import re

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
SERVICES = re.compile(r"\b(bank|credit union|venmo|cash ?app|zelle|paypal|apple cash|square|chase|wells fargo)\b|@", re.I)
NAME = r"([A-Z][\w.'-]*(?: [A-Z][\w.'-]*){0,3})"
PAYER_PATTERNS = [re.compile(r"^\s*" + NAME + r" (?:sent you|paid you)\b", re.M),
                  re.compile(r"\b(?:received|got) \$[\d,]+(?:\.\d\d)? from " + NAME + r"\s*$", re.M),
                  re.compile(r"\bfrom " + NAME + r"(?: for| \(|\.|,|$)", re.M)]
KIND_RULES = [  # first match wins; checked against the body (subject + text, not the From line)
    ("money_sent", re.compile(r"\byou (?:sent|paid)\b", re.I)),
    ("payment_request", re.compile(r"\b(?:you requested|requested \$|is requesting|request sent)\b", re.I)),
    ("refund", re.compile(r"\brefund(?:ed)? (?:of |to )?you\b|\bissued (?:you )?a refund\b", re.I)),
    ("money_received", re.compile(r"\b(?:sent you|paid you|you received|you've got money|deposit of \$[\d,.]+ (?:posted|was received)"
                                  r"|deposit of \$[\d,.]+ posted|received your mobile check deposit|money credited)\b", re.I)),
]
AD = re.compile(r"\b(advertisement|offer|bonus|promo|terms apply)\b", re.I)
MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)|(?<![\d/.,])(\d{1,3}(?:,\d{3})*\.\d\d|\d+\.\d\d)(?![\d/])")


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def in_text(quote, text):
    return bool(quote) and norm(quote) in norm(text)


def header(text, name):
    m = re.search(r"^" + name + r":\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def body(text):
    return re.sub(r"^(From|To|Date):.*$", "", text, flags=re.M)


def header_date(text):
    m = re.search(r"(\d{1,2}) ([A-Za-z]{3}) (\d{4})", header(text, "Date"))
    return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))) if m else None


def parse_dates(s, year=None):
    out = []
    for m in re.finditer(r"\b(\d{4})-(\d\d)-(\d\d)\b", s):
        out.append(dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", s):
        out.append(dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r"\b([A-Z][a-z]{2,8})\.? (\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{4}))?\b", s):
        mon = MONTHS.get(m.group(1)[:3].lower())
        y = int(m.group(3)) if m.group(3) else year
        if mon and y:
            try: out.append(dt.date(y, mon, int(m.group(2))))
            except ValueError: pass
    for m in re.finditer(r"\b(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})\b", s):
        mon = MONTHS.get(m.group(2).lower())
        if mon: out.append(dt.date(int(m.group(3)), mon, int(m.group(1))))
    return out


def amounts(s):
    return [float((a or b).replace(",", "")) for a, b in MONEY.findall(s or "")]


def rule_kind(text):
    b = body(text)
    for kind, rx in KIND_RULES:
        if rx.search(b):
            return kind
    return "not_a_payment" if AD.search(b) or not amounts(b) else None


def rule_payer(text):
    b = body(text)
    for rx in PAYER_PATTERNS:
        m = rx.search(b)
        if m and not SERVICES.search(m.group(1)) and m.group(1).lower() not in ("you", "your"):
            return m.group(1).strip(), m.group(0).strip()
    return "", ""


def verify(reply, text):
    """Return a dict of checked fields: {name: {'value', 'quote', 'status', 'note'}} plus 'kind'."""
    out = {}
    hdate = header_date(text)
    # kind
    rk, mk = rule_kind(text), reply.get("kind")
    if rk and rk != mk:
        out["kind"] = {"value": rk, "status": "FIXED", "note": f"model said {mk}; the wording says {rk}"}
    elif rk:
        out["kind"] = {"value": mk, "status": "ok", "note": ""}
    else:
        out["kind"] = {"value": mk, "status": "CHECK", "note": "no wording rule matched"}
    # amount
    a = reply.get("amount", {}); q = a.get("quote", ""); v = float(a.get("value") or 0)
    if in_text(q, text) and any(abs(v - x) < 0.005 for x in amounts(q)):
        out["amount"] = {"value": v, "quote": q, "status": "ok", "note": ""}
    elif in_text(q, text) and len(set(amounts(q))) == 1:
        out["amount"] = {"value": amounts(q)[0], "quote": q, "status": "FIXED", "note": f"model said {v}; quote says {amounts(q)[0]}"}
    else:
        out["amount"] = {"value": v, "quote": q, "status": "CHECK", "note": "amount not found in its quote"}
    # date
    d = reply.get("date", {}); q = d.get("quote", ""); y = hdate.year if hdate else None
    try: mv = dt.date.fromisoformat(d.get("value", ""))
    except ValueError: mv = None
    qd = parse_dates(q, y) if in_text(q, text) else []
    if mv and mv in qd:
        out["date"] = {"value": mv, "quote": q, "status": "ok", "note": ""}
    elif len(set(qd)) == 1:
        out["date"] = {"value": qd[0], "quote": q, "status": "FIXED", "note": f"model said {mv}; quote says {qd[0]}"}
    elif hdate:
        out["date"] = {"value": hdate, "quote": header(text, "Date"), "status": "FIXED", "note": "used the message's Date header"}
    else:
        out["date"] = {"value": mv, "quote": q, "status": "CHECK", "note": "no date found"}
    # payer: must be a person/business named in the text, not the bank or app that sent the alert
    if out["kind"]["value"] != "money_received":
        out["payer"] = {"value": "", "quote": "", "status": "n/a", "note": "not money received"}
    p = reply.get("payer", {}); pv = (p.get("value") or "").strip(); q = p.get("quote", "")
    sender = header(text, "From").lower()
    bad = (not pv or SERVICES.search(pv) or pv.lower() in sender or not in_text(q, text) or norm(pv) not in norm(q))
    lf = re.match(r"^([A-Za-z'-]+),\s*([A-Za-z'-]+)(?:\s+[A-Za-z]\.?)?$", pv)  # bank style "ALVAREZ, BETH M"
    if out["kind"]["value"] != "money_received":
        pass
    elif not bad and lf:
        out["payer"] = {"value": f"{lf.group(2).title()} {lf.group(1).title()}", "quote": q, "status": "FIXED", "note": f"reordered {pv!r}"}
    elif not bad:
        out["payer"] = {"value": pv, "quote": q, "status": "ok", "note": ""}
    else:
        rv, rq = rule_payer(text)
        if rv:
            out["payer"] = {"value": rv, "quote": rq, "status": "FIXED", "note": f"model said {pv!r}"}
        else:
            out["payer"] = {"value": "", "quote": "", "status": "CHECK", "note": f"no payer named (model said {pv!r})"}
    # memo and reference: keep only if quoted from the text
    for k in ("memo", "reference"):
        f = reply.get(k, {}); fv = (f.get("value") or "").strip().strip('"'); q = f.get("quote", "")
        if fv.lower() in ("", "(none)", "none"):
            out[k] = {"value": "", "quote": "", "status": "ok", "note": ""}
        elif in_text(fv, text):
            out[k] = {"value": fv, "quote": q, "status": "ok", "note": ""}
        else:
            out[k] = {"value": "", "quote": "", "status": "FIXED", "note": f"dropped {fv[:40]!r}: not in the message"}
    return out
