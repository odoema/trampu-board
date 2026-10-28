"""Refresh the Trampu sales and marketing dashboard data.

Publishes aggregate numbers only:
  * trampu.online/api/health -> roster, joined, open offers, trips
  * Resend Email Metrics API -> real delivery/open/click/unsubscribe metrics
  * GitHub traffic -> board visits
  * campaigns.json -> local campaign catalogue
Never writes names, emails or phone numbers.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"
HISTORY = ROOT / "history.json"
CAMPAIGNS = ROOT / "campaigns.json"
LOGO = ROOT / "logo.png"
HEALTH_URL = os.environ.get("TRAMPU_HEALTH_URL", "https://trampu.online/api/health")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "odoema/trampu-board")
RESEND_API = "https://api.resend.com"


def get_json(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "trampu-board/1.2", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def trampu_stats():
    h = get_json(HEALTH_URL)
    return {
        "roster": int(h.get("roster_students_active") or 0),
        "joined": int(h.get("trampu_users_registered") or 0),
        "offers_open": int(h.get("offers_open") or 0),
        "trips_total": int(h.get("trips_total") or 0),
        "destinations": [str(d) for d in (h.get("destinations") or [])][:20],
    }


def resend_metrics(key):
    """Use Resend's official metrics endpoint rather than inferring engagement from message last_event."""
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    params = urllib.parse.urlencode({
        "start_date": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).date().isoformat(),
        "end_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "timezone": "Africa/Kampala",
        "granularity": "daily",
        "metrics": "sent,delivered,bounced,opened,unique_opened,clicked,unique_clicked,unsubscribed,complained,suppressed,delivery_rate,open_rate,click_rate,bounce_rate,unsubscribe_rate,complaint_rate",
        "dimensions": "broadcast",
    })
    raw = get_json(f"{RESEND_API}/emails/metrics?{params}", headers)
    totals = raw.get("totals") or {}
    return {
        "sent": int(totals.get("sent") or 0),
        "audience": int(totals.get("sent") or 0),
        "delivered": int(totals.get("delivered") or 0),
        "bounced": int(totals.get("bounced") or 0),
        "opened": int(totals.get("opened") or 0),
        "unique_opened": int(totals.get("unique_opened") or 0),
        "clicked": int(totals.get("clicked") or 0),
        "unique_clicked": int(totals.get("unique_clicked") or 0),
        "unsubscribed": int(totals.get("unsubscribed") or 0),
        "complained": int(totals.get("complained") or 0),
        "suppressed": int(totals.get("suppressed") or 0),
        "delivery_rate": float(totals.get("delivery_rate") or 0),
        "open_rate": float(totals.get("open_rate") or 0),
        "click_rate": float(totals.get("click_rate") or 0),
        "bounce_rate": float(totals.get("bounce_rate") or 0),
        "unsubscribe_rate": float(totals.get("unsubscribe_rate") or 0),
        "complaint_rate": float(totals.get("complaint_rate") or 0),
        "source": "Resend Email Metrics API",
        "live": True,
        "window_days": 7,
        "by_broadcast": raw.get("data") or [],
    }


def resend_broadcasts(key):
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        data = get_json(f"{RESEND_API}/broadcasts?limit=100", headers)
        return data.get("data") or []
    except Exception as e:
        print("Resend broadcasts unavailable:", e)
        return []


def github_views(token):
    if not token:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/traffic/views"
    data = get_json(url, {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return {
        "views_14d": int(data.get("count") or 0),
        "unique_views_14d": int(data.get("uniques") or 0),
        "source": "GitHub traffic",
        "live": True,
    }


def campaign_catalog(email, joined, broadcasts):
    rows = load(CAMPAIGNS, [])
    if not isinstance(rows, list):
        rows = []
    by_id = {str(b.get("id")): b for b in broadcasts if isinstance(b, dict)}
    by_name = {str(b.get("name") or "").strip().lower(): b for b in broadcasts if isinstance(b, dict)}
    metric_rows = {str(x.get("broadcast_id")): x for x in email.get("by_broadcast", []) if isinstance(x, dict)}

    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        bid = str(row.get("broadcast_id") or "")
        b = by_id.get(bid)
        if not b:
            b = by_name.get(str(row.get("name") or row.get("id") or "").strip().lower())
        m = metric_rows.get(str(b.get("id"))) if b else None
        result.append({
            "id": str(row.get("id") or b.get("name") if b else ""),
            "subject": str(row.get("subject") or (b or {}).get("subject") or ""),
            "cta_url": str(row.get("cta_url") or ""),
            "broadcast_id": str((b or {}).get("id") or bid),
            "status": str((b or {}).get("status") or ("sent" if row.get("sent") else "ready")),
            "sent": bool(b and (b.get("status") == "sent" or b.get("sent_at"))) or bool(row.get("sent")),
            "sent_count": int((m or {}).get("sent") or 0),
            "delivered": int((m or {}).get("delivered") or 0),
            "opened": int((m or {}).get("opened") or 0),
            "clicked": int((m or {}).get("clicked") or 0),
            "unique_clicked": int((m or {}).get("unique_clicked") or 0),
            "joined": 0,
        })
        seen.add(str((b or {}).get("id") or bid))

    # Also expose actual Resend broadcasts so the board cannot silently become stale
    # when a new campaign is sent but campaigns.json has not yet been updated.
    for b in broadcasts:
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id") or "")
        if not bid or bid in seen or b.get("status") not in ("sent", "scheduled", "queued"):
            continue
        m = metric_rows.get(bid) or {}
        result.append({
            "id": str(b.get("name") or bid),
            "subject": str(b.get("subject") or ""),
            "cta_url": "",
            "broadcast_id": bid,
            "status": str(b.get("status") or ""),
            "sent": bool(b.get("status") == "sent" or b.get("sent_at")),
            "sent_count": int(m.get("sent") or 0),
            "delivered": int(m.get("delivered") or 0),
            "opened": int(m.get("opened") or 0),
            "clicked": int(m.get("clicked") or 0),
            "unique_clicked": int(m.get("unique_clicked") or 0),
            "joined": 0,
        })
    return result


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    data = load(DATA, {})
    history = load(HISTORY, [])

    try:
        data["trampu"] = trampu_stats()
        data["trampu_ok"] = True
    except Exception as e:
        print("trampu.online unreachable:", e)
        data["trampu_ok"] = False

    key = os.environ.get("RESEND_API_KEY", "").strip()
    broadcasts = []
    if key:
        try:
            r = resend_metrics(key)
            data["email"] = {**data.get("email", {}), **r}
            broadcasts = resend_broadcasts(key)
        except Exception as e:
            print("Resend metrics unavailable, keeping last snapshot:", e)

    try:
        r = github_views(os.environ.get("GITHUB_TOKEN", "").strip())
        if r:
            data["board"] = r
    except Exception as e:
        print("GitHub traffic unavailable, keeping last board snapshot:", e)

    data["marketing"] = {
        "campaigns": campaign_catalog(data.get("email", {}), data.get("trampu", {}).get("joined", 0), broadcasts),
        "funnel_definition": ["email sends", "delivered", "opened", "clicked", "joined"],
        "attribution": "UTM-tagged campaign links; website visits are intentionally not inferred from email clicks.",
        "metrics_source": "Resend Email Metrics API",
    }
    data["updated_at"] = now.isoformat()
    DATA.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    t = data.get("trampu")
    if t and data.get("trampu_ok"):
        point = {"t": now.isoformat(), "joined": t["joined"], "offers_open": t["offers_open"], "trips_total": t["trips_total"]}
        last = history[-1] if history else None
        if not last or any(last.get(k) != point[k] for k in ("joined", "offers_open", "trips_total")) or dt.datetime.fromisoformat(last["t"]).date() != now.date():
            history.append(point)
        HISTORY.write_text(json.dumps(history[-2000:], indent=1) + "\n", encoding="utf-8")

    if not LOGO.exists():
        try:
            req = urllib.request.Request("https://trampu.online/static/logo.png", headers={"User-Agent": "trampu-board/1.2"})
            with urllib.request.urlopen(req, timeout=20) as r:
                LOGO.write_bytes(r.read())
        except Exception as e:
            print("logo download failed:", e)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
