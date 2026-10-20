"""Ask a local open-weight model (any OpenAI-compatible server, e.g. llama.cpp's llama-server) to READ one notification.

The model only reads: what kind of message it is, who paid, how much, when, the memo and the reference number,
each with the exact words it copied them from. Matching, sums and status are plain code (ledger.py)."""
import json
import time
import urllib.request

KINDS = ["money_received", "money_sent", "payment_request", "refund", "not_a_payment"]


def _field(t):
    return {"type": "object", "properties": {"value": {"type": t}, "quote": {"type": "string"}},
            "required": ["value", "quote"], "additionalProperties": False}


def json_schema():
    return {"type": "object", "additionalProperties": False,
            "required": ["kind", "payer", "amount", "date", "memo", "reference"],
            "properties": {"kind": {"type": "string", "enum": KINDS}, "payer": _field("string"),
                           "amount": _field("number"), "date": _field("string"),
                           "memo": _field("string"), "reference": _field("string")}}


SYSTEM = (
    "You read payment notification emails and texts for a small landlord. Decide what kind of message it is: "
    "money_received (someone paid the landlord), money_sent (the landlord paid someone), payment_request "
    "(a request for money that has not been paid), refund, or not_a_payment (ads, offers, security alerts). "
    "Then extract: payer (the person or business the money came FROM), amount (a number, no $ sign), "
    "date (YYYY-MM-DD, the date of the payment), memo (the note or description the payer wrote), and reference "
    "(the confirmation, transaction or trace number). For every field copy into 'quote' the shortest exact "
    "phrase from the message that states it, character for character. If a field is not in the message use "
    "an empty string or 0 and an empty quote. Do not guess."
)


def build_messages(text):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Message:\n<<<\n" + text.strip() + "\n>>>"}]


def extract(text, base_url="http://127.0.0.1:8080", model="local", timeout=600):
    body = {"model": model, "temperature": 0,
            "chat_template_kwargs": {"enable_thinking": False},  # Gemma 4: answer directly
            "messages": build_messages(text),
            "response_format": {"type": "json_schema", "json_schema": {"name": "notification", "schema": json_schema()}}}
    req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return json.loads(resp["choices"][0]["message"]["content"]), {
        "seconds": round(time.time() - t0, 1), "usage": resp.get("usage", {}), "model": resp.get("model", model)}
