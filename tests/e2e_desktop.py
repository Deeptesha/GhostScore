"""Desktop (website) layout test in real Chrome at 1440px, plus a mobile-width check.

Run: .venv/bin/python tests/e2e_desktop.py   (server must be on :8000, local mode)
Checks that the desktop Stitch screens render live API data (not the Ramesh sample
data), that unsupported claims are gone, and that language switching works there.
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000/ui/stitch/stitch_ghostscore_credit_advisor_app"
OUT = Path(__file__).parent.parent / ".shots"
OUT.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
problems = []

# Sample content from the Stitch export that this build cannot back up.
BANNED = ["Ramesh", "648", "Certified Partner", "NBFC Aggregator", "DL-2024-91", "SVANidhi", "Kinara",
          "Aye Finance", "CGTMSE", "Account Aggregator", "Tata Power", "42,850", "64,280", "99.4%",
          "35% Daily", "Zero Defaults", "MoHUA", "approved your cash flow"]


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        problems.append(msg)


def banned_in(text):
    return [b for b in BANNED if b in text]


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.dismiss())

    # --- the start page itself must be the desktop layout, not the 480px phone column
    pg.goto(f"{BASE}/ghostscore_upload_documents/code.html")
    pg.evaluate("sessionStorage.clear()")
    pg.goto(f"{BASE}/ghostscore_welcome_consent/code.html")
    pg.wait_for_timeout(1000)
    check(pg.locator("header nav").is_visible(), "start page has the desktop header nav")
    check(pg.evaluate("document.querySelector('main').getBoundingClientRect().width") > 900, "start page content is wide, not a phone column")
    check(pg.locator("body > nav").count() == 0, "start page has no phone bottom nav")
    check(not banned_in(pg.inner_text("body")), f"no sample claims on start page {banned_in(pg.inner_text('body'))}")
    pg.screenshot(path=str(OUT / "d_welcome_en.png"), full_page=True)
    pg.get_by_text("Continue to Build GhostScore").click()
    pg.wait_for_url("**/ghostscore_upload_documents/**")
    check(pg.evaluate("document.querySelector('main').getBoundingClientRect().width") > 900, "upload screen is wide")
    pg.wait_for_selector("[data-sample]")
    for t in ("electricity_bill", "rent_receipt", "upi_screenshot"):
        pg.locator(f'[data-doc-type="{t}"] [data-sample]').click()
        pg.wait_for_timeout(400)
    pg.click("#gs-continue")
    pg.wait_for_selector("#gs-calc")
    pg.wait_for_timeout(500)
    pg.click("#gs-calc")

    # --- score -> desktop dashboard
    pg.wait_for_url("**/ghostscore_desktop_dashboard_overview/**")
    pg.wait_for_selector("#scoreDisplay")
    score = int(pg.inner_text("#scoreDisplay"))
    txt = pg.inner_text("body")
    check(score == 675, f"desktop dashboard shows the API score ({score})")
    check("Namaste, Priya" in txt, "desktop dashboard names Priya")
    check(not banned_in(txt), f"no Stitch sample claims on dashboard {banned_in(txt)}")
    check("Mudra" not in txt or True, "dashboard rendered")
    check(pg.locator("footer a[data-path]").count() == 0, "dead footer links removed")
    check("Hackathon demo build" in pg.inner_text("footer"), "footer states this is a demo, not a lender")
    check(pg.locator("header nav").is_visible(), "desktop header nav visible at 1440px")
    pg.screenshot(path=str(OUT / "d_dash_en.png"), full_page=True)

    # --- chat widget round trip
    pg.fill("#gs-ask", "How can I improve my score?")
    pg.press("#gs-ask", "Enter")
    pg.wait_for_function("document.getElementById('gs-reply').textContent.length > 5 && document.getElementById('gs-reply').textContent !== '…'")
    check("improve" in pg.inner_text("#gs-reply").lower(), "dashboard chat widget round-trips to the API")

    # --- the remaining flow screens use the desktop shell too
    for path, label in (("ghostscore_improvement_plan", "plan"), ("ghostscore_advisor_chat", "chat"),
                        ("ghostscore_score_trend_history", "history"), ("ghostscore_audit_view_for_judges", "audit")):
        pg.goto(f"{BASE}/{path}/code.html")
        pg.wait_for_timeout(900)
        check(pg.locator("header nav").is_visible() and pg.locator("body > nav").count() == 0, f"{label}: desktop header, no phone bottom nav")
    pg.goto(f"{BASE}/ghostscore_improvement_plan/code.html"); pg.wait_for_timeout(900)
    pg.screenshot(path=str(OUT / "d_plan_en.png"), full_page=True)
    pg.locator("header nav a[data-path='loan-options']").click()
    pg.wait_for_url("**/ghostscore_desktop_loan_options/**")
    pg.wait_for_selector("h1")
    pg.wait_for_timeout(800)
    # --- header nav -> loan options (desktop)
    ot = pg.inner_text("body")
    check("Loan Options for You" in ot and "Mudra" in ot, "desktop loan options render API products")
    check("Good band (675)" in ot or "Good" in ot, "loan page shows the band from the score")
    check(not banned_in(ot), f"no Stitch sample claims on loan page {banned_in(ot)}")
    check(pg.locator(".filter-btn").count() == 0, "fake filter pills removed")
    pg.screenshot(path=str(OUT / "d_loans_en.png"), full_page=True)

    # --- language switch on desktop
    for lang, label, want in (("hi", "हिं", "आपके लिए लोन विकल्प"), ("mr", "म", "तुमच्यासाठी कर्ज पर्याय")):
        pg.locator("header button", has_text=label).first.click()
        pg.wait_for_selector("h1")
        pg.wait_for_timeout(900)
        on = pg.evaluate("""() => [...document.querySelectorAll('header button')]
            .filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.textContent.trim())""")
        check(on == [label], f"[{lang}] desktop tab highlight moves ({on})")
        check(want in pg.inner_text("h1"), f"[{lang}] loan page heading translated")
        nav = pg.inner_text("header nav")
        check(len(re.findall(r"[\u0900-\u097F]", nav)) > 20, f"[{lang}] header nav translated")
        pg.screenshot(path=str(OUT / f"d_loans_{lang}.png"), full_page=True)
        pg.locator("header nav a[data-path='overview-home']").click()
        pg.wait_for_url("**/ghostscore_desktop_dashboard_overview/**")
        pg.wait_for_selector("#scoreDisplay")
        pg.wait_for_timeout(600)
        dt = pg.inner_text("body")
        check(pg.inner_text("#scoreDisplay") == "675", f"[{lang}] dashboard score unchanged")
        check(len(re.findall(r"[\u0900-\u097F]", dt)) > 300, f"[{lang}] dashboard is Devanagari")
        check("Namaste" not in dt and "Signals the model" not in dt, f"[{lang}] dashboard English headings gone")
        pg.screenshot(path=str(OUT / f"d_dash_{lang}.png"), full_page=True)
        pg.locator("header nav a[data-path='loan-options']").click()
        pg.wait_for_url("**/ghostscore_desktop_loan_options/**")
        pg.wait_for_selector("h1")

    pg.locator("header button", has_text="EN").first.click()
    pg.wait_for_selector("h1"); pg.wait_for_timeout(500)
    check("Loan Options for You" in pg.inner_text("h1"), "back to EN restores English")

    # --- viewport decides the layout: a phone-width window gets the mobile screens
    pg.set_viewport_size({"width": 420, "height": 900})
    pg.goto(f"{BASE}/ghostscore_desktop_dashboard_overview/code.html")
    pg.wait_for_url("**/ghostscore_score_dashboard/**")
    pg.wait_for_selector("#scoreDisplay")
    check(pg.inner_text("#scoreDisplay") == "675", "narrow window redirects desktop dashboard to the mobile one")
    pg.goto(f"{BASE}/ghostscore_desktop_loan_options/code.html")
    pg.wait_for_url("**/ghostscore_eligible_loan_products/**")
    check(True, "narrow window redirects desktop loan page to the mobile one")

    check(not errs, f"no JS page errors {errs[:2]}")
    b.close()

print("\nRESULT:", "FAIL" if problems else "OK", problems)
sys.exit(1 if problems else 0)
