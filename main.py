"""
AI Web Scraper Demo
Stack: Playwright + Crawl4AI + Gemini API

POC: Navigates to a page, extracts content with Crawl4AI,
     uses Gemini to analyze the HTML and decide what actions to take,
     then Playwright executes those actions (e.g., fill forms, click buttons).
"""

import asyncio
import json
import re
import os
from google import genai
from google.genai import types
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from playwright.async_api import async_playwright


# ─── CONFIG ──────────────────────────────────────────────────────────────────

TARGET_URL = "https://httpbin.org/forms/post"  # Public form for safe testing

GEMINI_MODEL = "gemini-2.5-flash"  # Free tier: 10 RPM, 250 req/day
# Other free options:
# "gemini-2.5-flash-lite"  — 15 RPM, 1000 req/day (fastest, most quota)
# "gemini-2.5-pro"         — 5 RPM,  100 req/day  (best quality, slowest)

# Form data we want to fill (you'd customize this per use case)
FORM_INTENT = """
Fill out the form with the following details:
- Customer name: John Doe
- Telephone: +1-555-0123
- Email: john.doe@example.com
- Any size/option fields: pick the first available option
- Comments or message field: "This is an automated test submission."
Then click the submit button.
"""

# ─── STEP 1: CRAWL THE PAGE WITH CRAWL4AI ────────────────────────────────────

async def crawl_page(url: str) -> dict:
    """Use Crawl4AI to fetch and extract page content."""
    print(f"\n[1/3] 🕷️  Crawling {url} with Crawl4AI...")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,   # Always fetch fresh
        word_count_threshold=5,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

    if not result.success:
        raise RuntimeError(f"Crawl4AI failed: {result.error_message}")

    print(f"   ✅ Page crawled. Markdown length: {len(result.markdown)} chars")
    print(f"   ✅ Raw HTML length: {len(result.html)} chars")

    return {
        "url": url,
        "markdown": result.markdown,        # Clean text/markdown version
        "html": result.html,                # Full raw HTML
        "cleaned_html": result.cleaned_html # Crawl4AI cleaned HTML
    }


# ─── STEP 2: GEMINI ANALYZES THE PAGE AND RETURNS ACTIONS ────────────────────

def analyze_with_gemini(page_data: dict, intent: str) -> list[dict]:
    """
    Send the page HTML/markdown to Gemini.
    Gemini returns a structured list of actions to perform.
    """
    print("\n[2/3] 🤖 Asking Gemini to analyze the page and plan actions...")

    # Instantiate client with API key from environment
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    system_prompt = """You are an expert web automation agent. 
You receive the HTML and markdown content of a webpage, plus a user intent.
Your job is to return a JSON array of browser actions to fulfill the intent.

Each action must be one of:
  { "action": "fill",   "selector": "<css_selector>", "value": "<text>" }
  { "action": "select", "selector": "<css_selector>", "value": "<option_value>" }
  { "action": "click",  "selector": "<css_selector>" }
  { "action": "wait",   "ms": <milliseconds> }

Rules:
- Use ONLY CSS selectors (not XPath).
- Prefer name, id, or type selectors (e.g. input[name='custname'], button[type='submit']).
- Order actions logically: fill fields first, then click submit.
- Return ONLY a raw JSON array. No markdown, no explanation, no code fences."""

    user_message = f"""
PAGE URL: {page_data['url']}

--- PAGE MARKDOWN (clean text) ---
{page_data['markdown'][:3000]}

--- CLEANED HTML (structure) ---
{page_data['cleaned_html'][:4000]}

--- INTENT ---
{intent}

Return the JSON action array now:
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )

    raw = response.text.strip()

    print(f"   ✅ Gemini responded with {len(raw)} chars")
    print(f"\n   📋 Raw Gemini response:\n{raw}\n")

    # Strip markdown fences if Gemini wrapped in ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    actions = json.loads(raw)
    print(f"   ✅ Parsed {len(actions)} actions from Gemini")
    return actions


# ─── STEP 3: PLAYWRIGHT EXECUTES THE ACTIONS ─────────────────────────────────

async def execute_actions(url: str, actions: list[dict]):
    """Use Playwright to open the browser and execute Gemini's action plan."""
    print(f"\n[3/3] 🎭 Playwright executing {len(actions)} actions on {url}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=800)  # slow_mo = ms delay between each action
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        print(f"   ✅ Page loaded")

        for i, action in enumerate(actions, 1):
            act = action.get("action")
            selector = action.get("selector", "")

            try:
                if act == "fill":
                    await page.fill(selector, action["value"])
                    print(f"   [{i}] ✍️  fill({selector!r}, {action['value']!r})")

                elif act == "select":
                    await page.select_option(selector, action["value"])
                    print(f"   [{i}] 🔽 select({selector!r}, {action['value']!r})")

                elif act == "click":
                    await page.click(selector)
                    print(f"   [{i}] 🖱️  click({selector!r})")

                elif act == "wait":
                    ms = action.get("ms", 1000)
                    await page.wait_for_timeout(ms)
                    print(f"   [{i}] ⏳ wait({ms}ms)")

                else:
                    print(f"   [{i}] ⚠️  Unknown action: {act}")

                await page.wait_for_timeout(400)  # Small delay between actions

            except Exception as e:
                print(f"   [{i}] ❌ Error on action {action}: {e}")

        # Capture result page
        await page.wait_for_timeout(2000)
        final_url = page.url
        title = await page.title()
        screenshot_path = "/tmp/result_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)

        print(f"\n   ✅ Final URL  : {final_url}")
        print(f"   ✅ Page title : {title}")
        print(f"   ✅ Screenshot : {screenshot_path}")

        await browser.close()
        return {"final_url": final_url, "title": title, "screenshot": screenshot_path}


# ─── MAIN ORCHESTRATOR ────────────────────────────────────────────────────────

async def run_demo():
    print("=" * 60)
    print("  AI Web Scraper POC: Playwright + Crawl4AI + Gemini")
    print("=" * 60)

    # Step 1: Crawl
    page_data = await crawl_page(TARGET_URL)

    # Step 2: Gemini plans the actions
    actions = analyze_with_gemini(page_data, FORM_INTENT)

    # Step 3: Playwright executes
    result = await execute_actions(TARGET_URL, actions)

    print("\n" + "=" * 60)
    print("  ✅ DEMO COMPLETE")
    print(f"  Final URL : {result['final_url']}")
    print(f"  Title     : {result['title']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_demo())