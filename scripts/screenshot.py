"""Drive the running app end to end and save docs/screenshot.png.

Start the app first (streamlit run app.py), then:
    pip install playwright
    python scripts/screenshot.py [sample-name] [url] [viewport-height]

Uses the locally installed Microsoft Edge, so no browser download is needed.
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = sys.argv[1] if len(sys.argv) > 1 else "02_concrete_invoice.pdf"
URL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8501"
HEIGHT = int(sys.argv[3]) if len(sys.argv) > 3 else 1500

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1440, "height": HEIGHT}, device_scale_factor=2)
    page.goto(URL)
    page.locator("[data-testid=stSelectbox]").click()
    page.get_by_role("option", name=SAMPLE).click()
    page.get_by_test_id("stMain").get_by_text(SAMPLE, exact=True).wait_for()
    page.get_by_role("button", name=re.compile("^(Extract|Load saved result)$")).click()
    page.get_by_text("Checks before approving").wait_for(timeout=180_000)
    page.wait_for_timeout(1500)  # let the data editor finish drawing
    page.screenshot(path=ROOT / "docs" / "screenshot.png")

    page.get_by_role("button", name="Approve & save").click()
    page.get_by_text("Approved records").wait_for()
    print(page.get_by_text("Approved and saved to").inner_text())
    browser.close()
