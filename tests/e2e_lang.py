"""Language-switch test: EN -> हिं -> म across every screen, in real Chrome.

Asserts the tab highlight moves, text becomes Devanagari, results re-localise
after a switch, and lists any remaining English words per screen.
Run: .venv/bin/python tests/e2e_lang.py   (server must be on :8000, local mode)
Translations are AI-drafted and NOT native-reviewed; this test only checks that
they are applied, not that they are good Hindi/Marathi.
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000/ui/stitch/stitch_ghostscore_credit_advisor_app"
OUT = Path(__file__).parent.parent / ".shots"
OUT.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENS = ["welcome_consent", "upload_documents", "document_check_results", "score_dashboard",
           "improvement_plan", "eligible_loan_products", "advisor_chat", "score_trend_history"]
# Words that are legitimately Latin in a Hindi/Marathi UI (brand, units, acronyms, IDs).
ALLOWED = {"ghostscore", "upi", "qr", "ai", "id", "inr", "msedcl", "priya", "sharma", "pm", "svanidhi", "mudra",
           "shishu", "kcc", "mfi", "rbi", "sidbi", "vertex", "search", "gst", "emi", "kyc", "ml", "stub",
           "sample", "pdf", "tcs", "a", "p", "s", "x", "mitra"}
problems, leftovers = [], {}


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        problems.append(msg)


def english_words(text):
    # ignore material-symbol icon names (snake_case words rendered as ligature text)
    words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    return sorted({w for w in words if w.lower() not in ALLOWED and len(w) > 2})


def devanagari(text):
    return len(re.findall(r"[\u0900-\u097F]", text))


def body_text(pg):
    # visible text only: innerText skips display:none; icon ligatures are removed below
    return pg.evaluate("""() => {
        const c = document.body.cloneNode(true);
        c.querySelectorAll('.material-symbols-outlined, script, style').forEach(e => e.remove());
        document.body.appendChild(c); c.style.position='absolute'; c.style.left='-9999px';
        const t = c.innerText; c.remove(); return t; }""")


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 420, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.dismiss())

    # --- build the Priya flow in English first
    pg.goto(f"{BASE}/ghostscore_upload_documents/code.html")
    pg.evaluate("sessionStorage.clear()")
    pg.reload()
    pg.wait_for_selector("[data-sample]")
    for t in ("electricity_bill", "rent_receipt", "upi_screenshot"):
        pg.locator(f'[data-doc-type="{t}"] [data-sample]').click()
        pg.wait_for_timeout(400)
    pg.click("#gs-continue")
    pg.wait_for_selector("#gs-calc")
    pg.wait_for_timeout(600)
    pg.click("#gs-calc")
    pg.wait_for_selector("#scoreDisplay")
    en_score = pg.inner_text("#scoreDisplay")
    en_headline = pg.inner_text("main")
    check("Namaste, Priya" in en_headline, "English score screen renders")

    # --- active tab highlight moves, language persists (header buttons)
    for lang, label in (("hi", "हिं"), ("mr", "म")):
        pg.locator("button", has_text=label).first.click()
        pg.wait_for_selector("#scoreDisplay")
        pg.wait_for_timeout(500)
        on = pg.evaluate("""() => [...document.querySelectorAll('button')]
              .filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.textContent.trim())""")
        check(on == [label], f"[{lang}] only the {label} tab is active, got {on}")
        check(pg.evaluate("document.documentElement.lang") == lang, f"[{lang}] <html lang> set")
        txt = pg.inner_text("main")
        check(devanagari(txt) > 100, f"[{lang}] score screen is mostly Devanagari ({devanagari(txt)} chars)")
        check(pg.inner_text("#scoreDisplay") == en_score, f"[{lang}] score number unchanged ({en_score})")
        check("Namaste" not in txt and "Credit Readiness" not in txt, f"[{lang}] English headings gone")
        want = "अच्छा" if lang == "hi" else "चांगला"
        check(want in txt and "Good" not in txt and "Fair" not in txt, f"[{lang}] band labels localised incl. range grid")
        pg.screenshot(path=str(OUT / f"lang_{lang}_score.png"), full_page=True)

        # walk every screen
        for s in SCREENS:
            pg.goto(f"{BASE}/ghostscore_{s}/code.html")
            pg.wait_for_timeout(1300)
            t = body_text(pg)
            if s == "advisor_chat":
                pg.fill("#userInput", "How can I improve my score?")
                pg.press("#userInput", "Enter")
                pg.wait_for_timeout(1200)
                t = body_text(pg)
            eng = english_words(t)
            leftovers[f"{lang}/{s}"] = eng
            check(devanagari(t) > 30, f"[{lang}] {s}: Devanagari present ({devanagari(t)} chars)")
            pg.screenshot(path=str(OUT / f"lang_{lang}_{s}.png"), full_page=True)

        # plan + options actually re-localised from the API (not the English cache)
        pg.goto(f"{BASE}/ghostscore_improvement_plan/code.html"); pg.wait_for_timeout(1200)
        pt = pg.inner_text("main")
        check("Add proof of rent" not in pt and "Step 1" not in pt, f"[{lang}] plan text re-localised")
        pg.goto(f"{BASE}/ghostscore_eligible_loan_products/code.html"); pg.wait_for_timeout(1200)
        check("May be eligible" not in pg.inner_text("main"), f"[{lang}] options re-localised")

        pg.goto(f"{BASE}/ghostscore_score_dashboard/code.html"); pg.wait_for_selector("#scoreDisplay")

    # --- welcome screen pill (different markup) highlights the active language
    pg.goto(f"{BASE}/ghostscore_welcome_consent/code.html"); pg.wait_for_timeout(800)
    on = pg.evaluate("""() => [...document.querySelectorAll('button')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.textContent.trim())""")
    check(on == ["म"], f"welcome pill highlights active language (म), got {on}")
    pg.locator("button", has_text="हिं").first.click(); pg.wait_for_timeout(800)
    check("आपके भुगतान" in pg.inner_text("main"), "welcome pill click switches to Hindi")
    pg.screenshot(path=str(OUT / "lang_hi_welcome_after_click.png"))
    pg.goto(f"{BASE}/ghostscore_score_dashboard/code.html"); pg.wait_for_selector("#scoreDisplay")

    # --- back to English restores English
    pg.locator("button", has_text="EN").first.click()
    pg.wait_for_selector("#scoreDisplay"); pg.wait_for_timeout(500)
    check("Namaste, Priya" in pg.inner_text("main"), "switching back to EN restores English")

    # --- chat screen compact badge cycles EN -> हिं
    pg.goto(f"{BASE}/ghostscore_advisor_chat/code.html"); pg.wait_for_timeout(800)
    pg.locator("button[aria-label='हिंदी']").first.click()
    pg.wait_for_timeout(1200)
    check(pg.evaluate("document.documentElement.lang") == "hi", "chat badge switches language to Hindi")

    check(not errs, f"no JS page errors {errs[:2]}")
    b.close()

print("\n--- Remaining English words (excluding brand/acronyms) ---")
for k, v in leftovers.items():
    print(f"{k}: {v}")
print("\nRESULT:", "FAIL" if problems else "OK", problems)
sys.exit(1 if problems else 0)
