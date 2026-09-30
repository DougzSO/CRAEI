"""Diagnostic (temporary, not part of the production pipeline): discover the real
network request REN's frontend uses to populate the monthly "Indice de
produtibilidade hidroelectrica" (IPH) chart at

    https://datahub.ren.pt/pt/eletricidade/regimes/

Direct HTTP probing of servicebus.ren.pt (COMANDO 21 follow-up) timed out at the
TCP level from this machine while the main site loads fine -- consistent with a
WAF/CDN blocking non-browser clients, not a real outage. This script drives a
real headless browser instead, which sends the same requests a human visiting
the page would, and logs every request/response touching a candidate host or
keyword so the actual IPH endpoint can be identified without assuming it is one
of the documented generic servicebus.ren.pt/datahubapi endpoints (none of which
is explicitly named as the productivity index).

Usage:
    python scripts/debug_ren_iph_network.py
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGE_URL = "https://datahub.ren.pt/pt/eletricidade/regimes/"
MODULE_URL = (
    "https://datahub.ren.pt/pt/eletricidade/regimes/modules/mensal/"
    "hidrica-prod/indice-de-produtibilidade-hidroeletrica/"
)

CANDIDATE_HOSTS = ("servicebus.ren.pt", "datahub.ren.pt")
KEYWORDS = ("/api/", "regimes", "hidrica", "produtibilidade", "hydro")

TEST_DATES = ["2015-01-31", "2017-01-31", "2019-12-31", "2024-01-31", "2025-12-31"]

OUT_PATH = Path(__file__).resolve().parents[1] / "debug_ren_iph_network_log.json"


def _matches(url: str) -> bool:
    lowered = url.lower()
    return any(h in lowered for h in CANDIDATE_HOSTS) and (
        any(k in lowered for k in KEYWORDS) or "servicebus.ren.pt" in lowered
    )


def main() -> None:
    captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        )

        def on_request(request):
            if _matches(request.url):
                entry = {
                    "phase": "request",
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data,
                    "frame_url": request.frame.url if request.frame else None,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                captured.append(entry)
                print(f"[REQUEST] {request.method} {request.url}")

        def on_response(response):
            if _matches(response.url):
                entry = {
                    "phase": "response",
                    "url": response.url,
                    "status": response.status,
                    "content_type": response.headers.get("content-type"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "text" in content_type:
                    try:
                        entry["body"] = response.text()
                    except Exception as exc:  # noqa: BLE001 - diagnostic script only
                        entry["body_error"] = str(exc)
                captured.append(entry)
                print(f"[RESPONSE] {response.status} {response.url} ({content_type})")

        page = context.new_page()
        page.on("request", on_request)
        page.on("response", on_response)

        # Also instrument every frame (the module is embedded as an iframe).
        def on_frame_attached(frame):
            frame.on("request", on_request)
            frame.on("response", on_response)

        page.on("frameattached", on_frame_attached)

        print(f"Navigating to parent page: {PAGE_URL}")
        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        print(f"Navigating directly to embedded module: {MODULE_URL}")
        try:
            page.goto(MODULE_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
        except Exception as exc:  # noqa: BLE001
            print(f"  module navigation failed: {exc}")

        # Try to find date inputs/selectors and exercise the test dates, if any
        # such control exists on the page. Best-effort: log what's found.
        for test_date in TEST_DATES:
            print(f"Probing test date: {test_date}")
            try:
                date_inputs = page.locator("input[type='date'], input[type='text']")
                count = date_inputs.count()
                if count:
                    date_inputs.first.fill(test_date)
                    page.wait_for_timeout(2000)
                else:
                    print("  no date input control found on this page/module")
            except Exception as exc:  # noqa: BLE001
                print(f"  date probe failed for {test_date}: {exc}")

        browser.close()

    OUT_PATH.write_text(json.dumps(captured, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nCaptured {len(captured)} matching request/response entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
