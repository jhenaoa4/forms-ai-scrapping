# 🤖 AI Forms Scraper
### Playwright + Crawl4AI + Gemini API

An AI-powered browser automation proof of concept. Instead of writing brittle CSS selectors by hand, you describe what you want in plain English — and Gemini figures out how to do it. Crawl4AI fetches and cleans the page, Gemini plans the actions, Playwright executes them in a real visible browser.

---

## How It Works

```
┌─────────────┐     ┌───────────────┐     ┌──────────────────────┐     ┌────────────────┐
│  Target URL │────▶│   Crawl4AI    │────▶│     Gemini API       │────▶│   Playwright   │
│             │     │               │     │                      │     │                │
│ Any webpage │     │ Cleans HTML   │     │ Reads HTML + intent  │     │ Opens browser  │
│             │     │ into markdown │     │ Returns JSON actions │     │ Fills form     │
│             │     │ + clean HTML  │     │                      │     │ Clicks submit  │
└─────────────┘     └───────────────┘     └──────────────────────┘     └────────────────┘
```

**Step 1 — Crawl4AI** fetches the page and strips it down to clean markdown and HTML that an LLM can easily understand, removing ads, overlays, and noise.

**Step 2 — Gemini** receives the cleaned page content plus your plain-English intent and returns a structured JSON action plan like:
```json
[
  { "action": "fill",   "selector": "input[name='custname']", "value": "John Doe" },
  { "action": "fill",   "selector": "input[name='custtel']",  "value": "+1-555-0123" },
  { "action": "select", "selector": "select[name='size']",    "value": "medium" },
  { "action": "click",  "selector": "button[type='submit']" }
]
```

**Step 3 — Playwright** opens a real Chromium browser window and executes each action with a visible delay, so you can watch it happen in real time.

---

## Requirements

- Python 3.9+
- A [Gemini API key](https://aistudio.google.com/apikey) (free, no credit card needed)

---

## Installation

**1. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**2. Install the Playwright browser**
```bash
playwright install chromium
```

**3. Set your Gemini API key**

On Windows (PowerShell):
```powershell
$env:GEMINI_API_KEY = "AIza..."
```

On macOS / Linux:
```bash
export GEMINI_API_KEY="AIza..."
```

To set it permanently on Windows:
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza...", "User")
```

---

## Usage

```bash
python main.py
```

A browser window will open and you'll see the form being filled field by field in real time. The console logs each action as it happens. When done, a screenshot is saved to `/tmp/result_screenshot.png`.

**Example console output:**
```
============================================================
  AI Web Scraper POC: Playwright + Crawl4AI + Gemini
============================================================

[1/3] 🕷️  Crawling https://httpbin.org/forms/post with Crawl4AI...
   ✅ Page crawled. Markdown length: 843 chars
   ✅ Raw HTML length: 2847 chars

[2/3] 🤖 Asking Gemini to analyze the page and plan actions...
   ✅ Gemini responded with 312 chars
   ✅ Parsed 5 actions from Gemini

[3/3] 🎭 Playwright executing 5 actions on https://httpbin.org/forms/post...
   ✅ Page loaded
   [1] ✍️  fill('input[name="custname"]', 'John Doe')
   [2] ✍️  fill('input[name="custtel"]', '+1-555-0123')
   [3] ✍️  fill('input[name="custemail"]', 'john.doe@example.com')
   [4] 🔽 select('select[name="size"]', 'medium')
   [5] 🖱️  click('button[type="submit"]')

   ✅ Final URL  : https://httpbin.org/post
   ✅ Page title : httpbin.org
   ✅ Screenshot : /tmp/result_screenshot.png

============================================================
  ✅ DEMO COMPLETE
============================================================
```

---

## Customization

Open `main.py` and change these two variables at the top:

```python
# The page you want to automate
TARGET_URL = "https://your-target-site.com/contact"

# What you want the AI to do, in plain English
FORM_INTENT = """
Fill the contact form with:
- Name: Jane Smith
- Email: jane@example.com
- Subject: Partnership inquiry
- Message: Hello, I'd like to discuss a potential collaboration.
Then click the Submit button.
"""
```

No selectors. No XPath. No inspecting the DOM manually. Just describe it.

---

## Configuration Options

### Gemini Model

Choose based on your free tier needs:

| Model | RPM | Req/Day | Best for |
|---|---|---|---|
| `gemini-2.5-flash-lite` | 15 | 1,000 | High volume, POC testing |
| `gemini-2.5-flash` *(default)* | 10 | 250 | Balanced quality & quota |
| `gemini-2.5-pro` | 5 | 100 | Complex pages, best reasoning |

Change it in `main.py`:
```python
GEMINI_MODEL = "gemini-2.5-flash-lite"  # most free quota
```

### Browser Visibility & Speed

```python
# In execute_actions():
browser = await p.chromium.launch(
    headless=False,  # True = invisible background, False = visible window
    slow_mo=800      # milliseconds between each action (0 = instant)
)
```

| `slow_mo` value | Effect |
|---|---|
| `0` | Instant, no visible delay |
| `500` | Fast but followable |
| `800` *(default)* | Comfortable demo speed |
| `1500` | Slow, great for presentations |

---

## Project Structure

```
ai_scraper_demo/
├── main.py           # Main script — all logic lives here
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

`main.py` is organized into three clean sections:

| Function | Role |
|---|---|
| `crawl_page(url)` | Fetches page with Crawl4AI, returns markdown + HTML |
| `analyze_with_gemini(page_data, intent)` | Sends page to Gemini, returns list of actions |
| `execute_actions(url, actions)` | Opens Playwright browser, runs each action |
| `run_demo()` | Orchestrates the three steps end to end |

---

## Extending This POC

**Handle login flows**
Add fill + click actions for the login form before navigating to your target page.

**Multi-page flows**
Call `execute_actions()` in sequence with different URLs and intents for each step.

**Extract data after acting**
Call `crawl_page()` again after Playwright finishes to scrape the result page.

**Run headless in production**
Set `headless=True` and `slow_mo=0` for unattended server execution.

**Use a different LLM**
The `analyze_with_gemini()` function is self-contained — swap it for any other LLM client (OpenAI, Anthropic, Ollama, etc.) as long as it returns the same JSON action format.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `google-genai` | ≥ 1.0.0 | Gemini API client (new SDK) |
| `crawl4ai` | ≥ 0.4.0 | Intelligent page fetching & HTML cleaning |
| `playwright` | ≥ 1.44.0 | Browser automation |

---

## Troubleshooting

**`404 NOT_FOUND` on model name**
Make sure you're using the correct model string: `gemini-2.5-flash`, not `gemini-2.0-flash` (deprecated March 2026).

**`AttributeError: module 'google.genai' has no attribute 'configure'`**
You're mixing the old and new SDK. Uninstall the old one:
```bash
pip uninstall google-generativeai -y
pip install google-genai
```

**`'export' is not recognized`** (Windows)
Use PowerShell syntax instead:
```powershell
$env:GEMINI_API_KEY = "AIza..."
```

**`generate_content_free_tier_input_token_limit is 0`**
Your model is deprecated. Update `GEMINI_MODEL` to `"gemini-2.5-flash"` in `main.py`.

**Playwright can't find elements**
Gemini occasionally generates a wrong CSS selector. Try switching to `gemini-2.5-pro` for better accuracy on complex pages, or add a retry loop around `execute_actions`.
