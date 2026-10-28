"""Refresh the Trampu sales and marketing dashboard data.

Publishes aggregate numbers only:
  * trampu.online/api/health -> roster, joined, open offers, trips
  * Resend -> sender delivery/open/click totals
  * GitHub traffic -> board visits
  * campaigns.json -> safe campaign catalogue used by the dashboard
Never writes names, emails or phone numbers.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"
HISTORY = ROOT / "history.json"
CAMPAIGNS = ROOT / "campaigns.json"
LOGO = ROOT / "logo.png"
HEALTH_URL = os.environ.get("TRAMPU_HEALTH_URL", "https://trampu.online/api/health")
SENDER = os.environ.get("TRAMPU_SENDER", "trampu@").lower()
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "odoema/trampu-board")


def get_json(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "trampu-board/1.1", **(headers or {})})
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


def resend_stats(key):
    counts = {"audience": 0, "delivered": 0, "bounced": 0, "opened": 0, "clicked": 0}
    url = "https://api.resend.com/emails?limit=100"
    for _ in range(50):
        page = get_json(url, {"Authorization": f"Bearer {key}"})
        rows = page.get("data") or []
        for e in rows:
            if SENDER not in str(e.get("from", "")).lower():
                continue
            ev = str(e.get("last_event") or "").lower()
            counts["audience"] += 1
            if ev in ("delivered", "opened", "clicked"):
                counts["delivered"] += 1
            if ev in ("opened", "clicked"):
                counts["opened"] += 1
            if ev == "clicked":
                counts["clicked"] += 1
            if ev == "bounced":
                counts["bounced"] += 1
        if not page.get("has_more") or not rows:
            break
        url = f"https://api.resend.com/emails?limit=100&after={rows[-1]['id']}"
    return counts if counts["audience"] else None


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


def campaign_catalog(email, joined):
    rows = load(CAMPAIGNS, [])
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append({
            "id": str(row.get("id") or ""),
            "subject": str(row.get("subject") or ""),
            "cta_url": str(row.get("cta_url") or ""),
            "sent": bool(row.get("sent")),
            "clicked": int(email.get("clicked") or 0) if row.get("sent") else 0,
            "joined": int(joined or 0) if row.get("sent") else 0,
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
    if key:
        try:
            r = resend_stats(key)
            if r:
                data["email"] = {**data.get("email", {}), **r, "source": "Resend", "live": True}
        except Exception as e:
            print("Resend unavailable, keeping snapshot:", e)

    try:
        r = github_views(os.environ.get("GITHUB_TOKEN", "").strip())
        if r:
            data["board"] = r
    except Exception as e:
        print("GitHub traffic unavailable, keeping last board snapshot:", e)

    data["marketing"] = {
        "campaigns": campaign_catalog(data.get("email", {}), data.get("trampu", {}).get("joined", 0)),
        "funnel_definition": ["email audience", "delivered", "opened", "clicked", "joined"],
        "attribution": "UTM-tagged campaign links; website visits are intentionally not inferred from email clicks.",
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
            req = urllib.request.Request("https://trampu.online/static/logo.png", headers={"User-Agent": "trampu-board/1.1"})
            with urllib.request.urlopen(req, timeout=20) as r:
                LOGO.write_bytes(r.read())
        except Exception as e:
            print("logo download failed:", e)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
