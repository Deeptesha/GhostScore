"""Click through the Priya flow in real Chrome and save screenshots.
Run: .venv/bin/python tests/e2e_ui.py   (server must be on :8000)"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000/ui/stitch/stitch_ghostscore_credit_advisor_app"
OUT = Path(__file__).parent.parent / ".shots"
OUT.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
problems = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        problems.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 420, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # Tailwind CDN and fonts need internet; don't fail on those
    pg.goto(f"{BASE}/ghostscore_welcome_consent/code.html")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "1_welcome.png"))
    pg.get_by_text("Continue to Build GhostScore").click()
    pg.wait_for_url("**/ghostscore_upload_documents/**")
    check(True, "welcome -> upload navigation")

    for t in ("electricity_bill", "rent_receipt", "upi_screenshot"):
        pg.locator(f'[data-doc-type="{t}"] [data-sample]').click()
        pg.wait_for_timeout(500)
    check("3 document(s) added" in pg.inner_text("#gs-count"), "3 documents uploaded via UI")
    pg.screenshot(path=str(OUT / "2_upload.png"))
    pg.click("#gs-continue")
    pg.wait_for_url("**/ghostscore_document_check_results/**")
    pg.wait_for_selector("#gs-calc")
    pg.wait_for_timeout(800)
    check("MSEDCL" in pg.inner_text("main"), "review shows API-extracted biller (not Stitch sample)")
    check("Ramesh" not in pg.inner_text("main"), "no leftover 'Ramesh' sample on review")
    pg.screenshot(path=str(OUT / "3_review.png"), full_page=True)
    pg.click("#gs-calc")
    pg.wait_for_url("**/ghostscore_score_dashboard/**")
    pg.wait_for_selector("#scoreDisplay")
    score = int(pg.inner_text("#scoreDisplay"))
    txt = pg.inner_text("main")
    check(300 <= score <= 850 and score != 648, f"dashboard shows API score {score}")
    check("Ramesh" not in txt and "Namaste, Priya" in txt, "dashboard shows Priya, not Ramesh")
    check("F6" not in txt and "F8" not in txt, "no placeholder factor labels")
    pg.screenshot(path=str(OUT / "4_score.png"), full_page=True)
    pg.get_by_text("See my improvement plan").click()
    pg.wait_for_url("**/ghostscore_improvement_plan/**")
    pg.wait_for_selector("text=Best single step")
    check("+" in pg.inner_text("main"), "plan shows what-if point estimates")
    pg.screenshot(path=str(OUT / "5_plan.png"), full_page=True)
    pg.go_back(); pg.wait_for_selector("#scoreDisplay")
    pg.get_by_text("Loan options for me").click()
    pg.wait_for_url("**/ghostscore_eligible_loan_products/**")
    pg.wait_for_timeout(1000)
    ot = pg.inner_text("main")
    check("Loan Options for You" in ot and "PM SVANidhi" not in ot, "options rendered from API")
    pg.screenshot(path=str(OUT / "6_options.png"), full_page=True)
    pg.go_back(); pg.wait_for_selector("#scoreDisplay")
    pg.get_by_text("Ask the advisor").click()
    pg.wait_for_url("**/ghostscore_advisor_chat/**")
    pg.fill("#userInput", "How can I improve my score?")
    pg.press("#userInput", "Enter")
    pg.wait_for_timeout(1500)
    ct = pg.inner_text("#chatStream")
    check("improve" in ct.lower() and "Ramesh" not in ct, "chat round-trips to API")
    pg.screenshot(path=str(OUT / "7_chat.png"), full_page=True)
    for key in ("score_trend_history", "audit_view_for_judges"):
        pg.goto(f"{BASE}/ghostscore_{key}/code.html")
        pg.wait_for_timeout(1200)
        pg.screenshot(path=str(OUT / f"8_{key}.png"), full_page=True)
    check("Priya" in pg.inner_text("main") or "Audit" in pg.inner_text("main"), "audit page renders")
    check(not errs, f"no JS page errors {errs[:2]}")
    b.close()
print("\nRESULT:", "FAIL" if problems else "OK", problems)
sys.exit(1 if problems else 0)
