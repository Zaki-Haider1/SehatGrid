"""Transactional, consent-gated WhatsApp preview outbox. No network sending."""

from .common import stamp


def queue_update(s, referral, event):
    r = s["requests"][referral["request_id"]]
    if not r.get("whatsapp_consent") or not r.get("whatsapp_phone"):
        return
    key = f"{referral['id']}:{event}"
    outbox = s.setdefault("notifications", {})
    if key in outbox:
        return
    f = s["facilities"][referral["facility_id"]]
    name = (
        f.get("directory_context", {}).get("name", f["name"]) if f["name"].startswith("Demo ") else f["name"]
    )
    if event == "CONFIRMED":
        services = "Primary-care consultation"
        if r.get("required_tests"):
            services += " and " + ", ".join(r["required_tests"])
        message = (
            f"SEHAT GRID: Referral {r['reference']} confirmed. Go to {name}, {f['address']} "
            f"on {referral['date']} for {services}. Report to reception with your reference. "
            "This is a service date, not an appointment time. Contact your sending hospital for assistance."
        )
    else:
        message = (
            f"SEHAT GRID: Referral {r['reference']} to {name} on {referral['date']} is no longer active. "
            "Please contact your sending hospital before travelling. A replacement destination is only final after confirmation."
        )
    outbox[key] = {
        "id": key,
        "request_id": r["id"],
        "referral_id": referral["id"],
        "event": event,
        "status": "PREVIEW_ONLY",
        "message": message,
        "created_at": stamp(),
        "recipient": r["whatsapp_phone"],
    }
