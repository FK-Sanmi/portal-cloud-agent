# Step 2: Agent Implementation Prompt (v2)

## Your Task

You are implementing a new portal crawler based on plain English instructions describing a government/regulatory portal. You will receive human-readable extraction instructions and must translate them into working crawler configurations.

**IMPORTANT**: Prefer **BASIC** (XPath-based) configs for listing and detail extraction. Use **METHOD** only when absolutely necessary (see "BASIC vs METHOD" below). Your goal is to provide a working starting point that can be manually refined later.

## What You'll Receive

You'll receive plain English instructions in this format:

```markdown
# Portal Implementation Instructions: [Portal Name]

## General Configuration

- **Issuing Authority (Local Language):** [Authority name in native language]
- **Issuing Authority (EN):** [Authority name in English]
- **Base Domain:** [domain.com]
- **Global Extraction Rule:** [Any rules that apply to all links]
- **Data Guardrail:** [Things to ignore/avoid]

## Link 1: [Section Name]

- **Primary URL:** [URL to crawl]
- **Type of Law:** [Category/type of content]
- **Number of Crawl Stages:** [2, 3, or 4+]
- **Pagination:** [Yes/No - describe if applicable]

### Stage 1 — [HUB/LISTING]

- **Stage URL:** [URL or "Derived from Link 1"]
- **Page description:** [What this page contains]
- **What to collect:**
    - [Specific links/items to pick]
    - [Pick 1/Pick 2 patterns if multiple categories]
- **What to skip:** [Items to ignore]

### Stage 2 — [INTERMEDIATE/TOPIC]

...

### Stage N — DETAIL

- **Content type:** [HTML only / PDF only / Both HTML and PDFs]
- **What to extract:**
    - For HTML content: [Title, Full Text extraction]
    - For PDF content: [How to find PDFs, extraction method]

## Link 2: [Another Section]

...
```

---

## ⚠️ CRITICAL: Input Format Variations

The human-provided instructions may NOT match the template above exactly. Common variations include:

1. **"Number of Steps" vs "Number of Crawl Stages"** — treat these as equivalent
2. **"3 (Hub → Sub-hub → Detail)"** — describes the actual flow, map to your config steps
3. **"Both HTML and PDFs"** at final stage — handle by extracting both types (see Mixed Content Patterns below)
4. **"Pick 1, Pick 2, etc."** — each "Pick" becomes a separate XPath config entry in that stage
5. **Missing fields** — some instructions may omit optional fields; use sensible defaults

---

## Your Translation Process

When you receive these instructions, you must:

1. **Identify the portal** - Extract name, base URL, and jurisdiction
2. **Use the provided Portal ID** - You will be given the Portal ID to use
3. **Count the sections** - Each "Link X:" becomes a separate configuration file
4. **Get HTML via browser (Playwright)** - Do not use curl. Use the Playwright MCP (or equivalent browser tool) to navigate to each Stage URL, perform any required interaction (e.g. form submit), then get the page HTML and derive XPaths. See "Navigation and HTML for XPath Extraction" below.
5. **Use the Number of Steps** from the instructions to determine configs:
    - **2 steps** = FIRST → FINAL (HTML content extraction)
    - **3 steps** = FIRST → SECOND → FINAL (PDF or DOCX content extraction)
6. **Prefer BASIC kind** for listing and detail steps; use **METHOD only when necessary** (see "BASIC vs METHOD" below).
7. **⚠️ ALWAYS add the link number as a comment on EVERY URL** in the FIRST config's `urls` list — e.g. `"https://example.com/list",  # Link 1: Section Name`. This is mandatory for every config file, every portal, no exceptions.
8. **For PDFs, use the built-in `parse_pdf` method** - This is a generic handler, no custom code required (METHOD kind for FINAL step).
9. **For DOCX/DOC files, use the built-in `parse_doc` method** - Works the same way as `parse_pdf`.
10. **For small crawl with date filters, use METHOD kind for the FIRST step** - See the Small Crawl section below.
11. **Extract XPaths from HTML** - Inspect the HTML you captured after navigating (see below) to find correct selectors.
12. **Map metadata fields** from the instructions to config fields.

---

## BASIC vs METHOD: When to Use Which

- **Prefer BASIC** for any step that can be done with static URLs and XPath extraction (listing pages, detail pages, collecting links or content). Use `kind: CrawlerKindEnum.BASIC` and a `conf` with XPaths.
- **Use METHOD only when necessary**, for example:
    - **FINAL step for PDFs/DOCX:** Use `method_name: "parse_pdf"` or `"parse_doc"` (built-in; no custom code).
    - **Small crawl with date filtering:** The FIRST step must build date-filtered URLs dynamically → use a METHOD that reads `small_crawl` and injects query params (see Small Crawl section).
    - **API-backed listing/pagination:** If Playwright network inspection reveals a stable same-domain API/XHR endpoint that returns listing rows, pagination data, or metadata more reliably than DOM scraping, use a METHOD to call that API. Confirm the endpoint in the browser first; do not guess API URLs.
    - **Form submission before listing:** When the listing URL requires submitting a form (e.g. search form, date range) and the results are only available after submit → use a METHOD that drives the browser, fills the form, submits, then extracts from the resulting page.
    - **Custom extraction:** When the page structure cannot be reliably expressed with XPaths alone (e.g. complex layout, conditional sections, need to run JS on the page) → use a custom method in the country crawler and reference it with `method_name`.
- Do **not** use METHOD for straightforward list → detail or hub → sub-hub → detail flows when BASIC XPaths would work.

### API-first when it is clearly available

- During Playwright inspection, check network activity when a listing loads, paginates, filters, or opens details. If the page uses a clear same-domain JSON/API endpoint, prefer that endpoint when it is more stable than scraping rendered DOM.
- Use APIs for listing/pagination only after confirming the request URL, method, query parameters, response shape, and required headers from browser/network inspection.
- Do not use random/private-looking endpoints if they require fragile session state, cookies, or one-off tokens unless there is no reliable DOM alternative.
- If implementing an API-backed METHOD with `requests`, follow `agent_implementation_prompt_method.md`: include headers with a `user-agent`, proxies, `verify=False`, and raise on failed requests.
- BASIC is still preferred when static HTML/XPath extraction is reliable and pagination URLs are real links.

---

## ⚠️ CRITICAL: Rules for Writing Custom Methods

When a custom METHOD is genuinely required (see section above), **read** and follow all mandatory rules in **`agent_implementation_prompt_method.md`** before writing the method — that file contains coding rules, full examples, and a checklist for every type of custom method.

Before writing a custom METHOD, check whether one of these simpler options works:

- BASIC config with real links and stable XPaths.
- Built-in `parse_pdf`, `parse_doc`, or `parse_pdf_or_doc`.
- `parse_pdf` with `need_prediction` for PDF-body metadata.
- API-backed listing/pagination METHOD discovered through Playwright network inspection.

---

## ⚠️ CRITICAL: Navigation and HTML for XPath Extraction

**DO NOT use curl.** **DO NOT guess XPaths.** You must use the **browser (Playwright MCP or equivalent)** to navigate to each stage, confirm the page is correct, get the live HTML, then derive XPaths. This ensures the DOM you inspect is the same as what the crawler will see and that navigation (including forms) works.

### Why navigation first

- The instructions describe **stages** (e.g. Stage 1 listing, Stage 2 detail). You must **reach each stage** in the browser so the HTML you capture matches what the config will crawl.
- Many portals need **interaction** to reach the listing (e.g. submit a search form, pick a date range). Only the browser can do that; static fetch cannot.
- XPaths derived from the **post-navigation, post-interaction** DOM are the ones that will work in production.

### Required workflow (per link / per stage)

For **each** link in the instructions, and for **each** stage of that link:

1. **Navigate** to the Stage URL from the instructions (e.g. `browser_navigate` with that URL).
2. **If the instructions say this stage requires interaction** (e.g. "submit the search form", "select date range then click Zoeken"):
    - Use the browser to **fill the form, click the submit button**, and wait for the results page to load (e.g. URL change or a results container to appear).
    - Then treat the **current page** as the HTML for this stage.
3. **Confirm you're on the right page** — e.g. accessibility snapshot or a quick check that the page shows a list vs a detail article, as described in the instructions.
4. **Get the full page HTML** for the current page. To avoid response size limits, **write HTML to a file** from the browser (e.g. with Playwright MCP: `browser_run_code` that runs `page.content()` and writes it to a path under `browser_dev/portal_html_inspection/` or `/tmp/portal_html_inspection/`), then **read that file** to inspect the DOM.
5. **Derive XPaths** from the HTML you captured: list item containers, link selectors, title/date/metadata, pagination, PDF links, content containers — as required by the instructions for this stage.
6. **Record the XPaths** (and any interaction steps) in your config. If this stage needs form submission to reach it, use a METHOD for that step; otherwise use BASIC with the XPaths you found.

Repeat for every stage (Stage 1 listing, Stage 2 detail, etc.) and for every link. Then assemble the configs (FIRST, SECOND, FINAL) from the XPaths and patterns you derived.

### Getting HTML without hitting size limits

- Page HTML can be very large. Prefer **writing to a file** in the workspace or `/tmp/portal_html_inspection/` and then reading it:
    - **Playwright MCP:** e.g. `browser_run_code` with code that gets `await page.content()`, writes it to `browser_dev/portal_html_inspection/stage1_listing.html` (using Node `fs` or similar if available in the runtime), and returns the file path. Then use the Read tool on that path.
    - If the tool cannot write files, request a **truncated** segment (e.g. first 15–20k characters) that includes the main content area and list/detail structure, and derive XPaths from that; note in the config that full page was not inspected if relevant.
- Create the directory if needed: `mkdir -p browser_dev/portal_html_inspection` or `mkdir -p /tmp/portal_html_inspection`.

### Tips for XPath extraction (from the HTML you captured)

- **Use class names** when available: `//div[@class="item"]`
- **Use contains() for partial matches**: `//div[contains(@class, "news-item")]`
- **Relative XPaths start with `.`**: `.//h3/text()` (relative to parent)
- **Absolute XPaths start with `//`**: `//div[@class="container"]` (from document root)
- **Use `/@href` for links**: `.//a/@href`
- **Use `/text()` for text content**: `.//h3/text()`
- **Use `//text()` to get all text**: `.//div//text()`
- **Check pagination**: Look for "next", "›", "→" buttons at page bottom
- **For PDFs**: Look for `//a[contains(@href, ".pdf")]`
- **Form fields:** Note `name` and `id` on inputs/buttons (e.g. for METHOD steps that submit forms).

### If you do not have a browser/Playwright tool

If no browser tool is available, ask the human to open each Stage URL (and perform any required interaction), then paste the HTML for that stage so you can derive XPaths. Do not guess XPaths without real HTML.

---

## Small Crawl: Date Filtering in BASIC Configs

When `small_crawl = True` is set on a portal, the crawler should restrict its crawl to a recent window (approximately the last 7–9 days) instead of crawling all historical pages.

### When Does a Portal Support Small Crawl?

The instructions will indicate when date filtering is available — typically phrased as:

- "The portal supports date filtering via URL query parameters"
- "Date range can be passed as `?from=YYYY-MM-DD&to=YYYY-MM-DD`"

### How to Implement It

Because the BASIC engine uses seed `urls` verbatim, **date filtering cannot be done declaratively in a BASIC config**. Instead, use a **METHOD kind for the FIRST step** to dynamically inject the date params when `small_crawl` is active.

#### Pattern: METHOD FIRST + BASIC SECOND (optional) + FINAL

```
FIRST (METHOD, LIST):  Builds date-filtered URLs → returns list items
                              ↓
[SECOND (BASIC, LIST): Collects document URLs from detail pages]  ← optional
                              ↓
FINAL (BASIC or METHOD, DICT): Extracts content
```

#### Example: Portal with date-filter query params

**Config file:**

```python
# STEP 1 (FIRST): METHOD to inject date filter when small_crawl is active
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (3, 5),
    "urls": [
        "https://www.example.gov/news",
    ],
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "example_portal_news_first",  # implement in the country crawler file
    "allowed_domains": ["www.example.gov"],
    "regex": None,
    "process": None,
}
```

**Country crawler method** (add to the relevant `country_crawlers/<country>.py`):

```python
def example_portal_news_first(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> list:
    from datetime import datetime
    from jimmy_v4.utils.helpers import get_previous_seven_days, fetch_pagination_data

    is_small_crawl = getattr(self.portal, "small_crawl", False)

    if is_small_crawl:
        week_res = get_previous_seven_days()
        start = week_res["seven_days_ago"]
        end = week_res["current_date"]
        start_str = f"{start.year}-{start.month:02d}-{start.day:02d}"
        end_str   = f"{end.year}-{end.month:02d}-{end.day:02d}"
        url = f"{url}?from={start_str}&to={end_str}"

    conf = [
        {
            "xpath": '//ul[@class="news-list"]/li',
            "url": ".//a/@href",
            "metadata_conf": {
                "title": ".//h3/text()",
                "date_of_publication": ".//time/@datetime",
            },
            "fixed_metadata": {
                "type_of_law": "News",
                "issuing_authority": "Example Authority",
                "lang": "en",
            },
        }
    ]

    results = fetch_pagination_data(
        url=url,
        webdriver=webdriver,
        conf=conf,
        next_page_xpath='//a[@rel="next"]/@href',
        delay_value=(3, 5),
    )
    return results
```

**Also add to `seed.py`** (the portal entry):

```python
{
    "id": PortalIDEnum.EXAMPLE_PORTAL,
    "name": "Example Portal",
    "base_url": "www.example.gov",
    "jurisdiction": ...,
    "occurrence": PortalModelSQL.WEEKLY,
    "small_crawl": True,
},
```

### Key Points

- `get_previous_seven_days()` returns a dict with keys `"current_date"` and `"seven_days_ago"`, each a `DateObject` with `.year`, `.month`, `.day` attributes. The window is actually ~9 days to handle month-boundary overlap.
- The date format depends on the portal — check what the portal expects (`YYYY-MM-DD`, `MM/DD/YYYY`, etc.).
- If `small_crawl` is `False`, the method should crawl everything (no date filter on the URL).
- Always check `getattr(self.portal, "small_crawl", False)` — never access `.small_crawl` directly.

---

## Reference Example: Australia Food Regulations (3-Step PDF Pattern)

This is the pattern to follow for 3-step PDF extraction:

```python
from jimmy_v4.constants import (
    CrawlerKindEnum,
    CrawlerResponseTypeEnum,
    KeywordMatchingType,
    MarkdownKindEnum,
)
from jimmy_v4.constants import PortalIDEnum

# STEP 1 (FIRST): Collect detail page URLs from listing page
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (2, 4),
    "urls": [
        "https://www.foodregulation.gov.au/resources/collections/ministerial-policy-guidelines",  # Link 1: Ministerial Policy Guidelines
    ],
    "next_page": None,  # Add pagination XPath if needed
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.foodregulation.gov.au"],
    "conf": [
        {
            "xpath": '//ul[contains(@class, "health-listing")]/li/div[@class="au-callout"]',
            "url": "./p/a/@href",
            "metadata_conf": {
                "title": "./p/a//text()",
                "date_of_publication": './/div[@class="health-field__item"]/time/text()',
            },
            "fixed_metadata": {
                "type_of_law": "Guideline",
                "issuing_authority": "Australia and New Zealand Ministerial Forum on Food Regulation (Food Ministers' Meeting)",
                "lang": "en",
                "ocr": False,
                "date_order": "DMY",
            },
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

# STEP 2 (SECOND): Collect PDF URLs from each detail page
second = {
    "agent": 5,
    "sleep": (2, 4),
    "next_page": None,
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.foodregulation.gov.au"],
    "conf": [
        {
            # Find PDF links on the detail page
            "xpath": '(//div[@class="au-callout"])[1]/div[@class="health-file"]//a[contains(@href, ".pdf") or contains(@href, ".PDF")]',
            "url": "./@href",
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

# STEP 3 (FINAL): Extract text from PDFs using built-in parse_pdf method
third = {
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_pdf",  # Built-in method - no custom code needed!
    "regex": None,
    "allowed_domains": ["www.foodregulation.gov.au"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}

australia_foodregulation_configurations = {
    "portal_id": PortalIDEnum.AUSTRALIA_FOODREGULATIONS,
    "config": [third, second, first],  # Reverse order: FINAL, SECOND, FIRST
    "_config_module": __name__.split(".")[-1],
}
```

### Key Points from Example:

1. **FIRST config**: Uses `BASIC` kind with XPaths to collect detail page URLs
2. **SECOND config**: Uses `BASIC` kind with XPaths to collect PDF URLs from detail pages
3. **FINAL config**: Uses `METHOD` kind with `method_name: "parse_pdf"` - this is a **built-in generic method**, no custom code required
4. **Fixed metadata**: Includes `lang`, `ocr`, and `date_order` for PDF processing

---

## Pattern 1: 3-Step PDF Extraction (FIRST → SECOND → FINAL)

Use this when instructions say "pick all PDFs" or "extract PDF content":

```
FIRST (BASIC, LIST):  Listing page → collects detail page URLs
                              ↓
SECOND (BASIC, LIST): Detail pages → collects PDF download URLs
                              ↓
FINAL (METHOD):       PDF URLs → extracts text using built-in parse_pdf
```

### FINAL Config for PDFs (always use this structure):

```python
final = {
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_pdf",  # Built-in - no custom code!
    "regex": None,
    "allowed_domains": ["domain.com"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

**⚠️ IMPORTANT**: For PDF extraction, include these in FIRST config's `fixed_metadata`:

```python
"fixed_metadata": {
    "type_of_law": "...",
    "issuing_authority": "...",
    "lang": "en",      # Language code for OCR
    "ocr": False,      # Set True if scanned PDFs
    "date_order": "DMY",  # Date format: DMY, MDY, or YMD
},
```

### PDF + Gemini metadata extraction (`need_prediction`)

If metadata fields (e.g. `title`, `issuing_authority`, `date_of_publication`) cannot be extracted via XPath and must be read from the PDF body text, add these keys to the **same `fixed_metadata`** block — no custom code required:

```python
"fixed_metadata": {
    "type_of_law": "...",
    "issuing_authority": "...",
    "lang": "en",
    "ocr": False,
    "date_order": "MDY",
    # Gemini extraction — parsed automatically by the built-in parse_pdf
    "need_prediction": True,
    "fields": {
        "title": "str",                 # field name → type "str"
        "date_of_publication": "str",   # add only the fields you need
    },
    "page_no": 1,   # optional: page(s) to extract from; omit to default to 1; use tuple (1,3) for a range
    "system_prompt": (
        "From the first page of this PDF, extract the title and date of publication "
        "in DD/MM/YYYY format. Return title and date_of_publication."
        # ↑ Always specify expected date format when any date field is present
    ),
},
```

The built-in `parse_pdf` reads `need_prediction`, `fields`, `system_prompt`, and `page_no` automatically and calls `get_metadata_from_pdf_page` (Gemini). No `_final` METHOD or custom code is needed. See `agent_implementation_prompt_gemini_metadata.md` for full details.

### Example: annotated court order PDF metadata

Use this pattern when the portal instructions say that metadata is visible **inside the PDF itself** rather than on the listing/detail HTML page. This commonly appears in annotated screenshots where labels point to PDF text such as issuing authority, title, source identifiers, source keywords, type of law, and full text.

Do **not** write a custom final METHOD for this. Put `need_prediction` on the stage that collects the PDF URL, then use the built-in `parse_pdf` final config.

```python
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (2, 4),
    "urls": [
        "https://www.examplecourt.gov/orders",  # Link 2: Disciplinary Orders
    ],
    "next_page": None,
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.examplecourt.gov"],
    "conf": [
        {
            "xpath": '//table//tr[.//a[contains(@href, ".pdf")]]',
            "url": './/a[contains(@href, ".pdf")]/@href',
            "metadata_conf": {
                # Only include metadata that is available on the HTML page here.
                "date_of_publication": ".//td[contains(@class, 'date')]//text()",
            },
            "fixed_metadata": {
                "lang": "en",
                "ocr": False,
                "date_order": "MDY",
                "need_prediction": True,
                "fields": {
                    "title": "str",
                    "issuing_authority": "str",
                    "type_of_law": "str",
                    "source_identifier": "str",
                    "source_secondary_identifier": "str",
                    "source_keywords": "str",
                },
                "page_no": 1,
                "system_prompt": (
                    "From the first page of this court order PDF, extract these fields: "
                    "title from the party/matter caption on the left; "
                    "issuing_authority from the court name centered at the top; "
                    "type_of_law from the document heading such as ORDER; "
                    "source_identifier from the docket/board number line such as No. 120 DB 2025; "
                    "source_secondary_identifier from the secondary docket line such as No. 3135 Disciplinary Docket No. 3; "
                    "source_keywords from the county or parenthetical keyword such as Allegheny County. "
                    "Return only the requested field names."
                ),
            },
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

final = {
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_pdf",
    "regex": None,
    "allowed_domains": ["www.examplecourt.gov"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

Key rules for PDF-body metadata:

- Use canonical metadata keys such as `type_of_law`, `issuing_authority`, `source_identifier`, `source_secondary_identifier`, and `source_keywords`.
- Include only fields that the instructions say are visible in or inferable from the PDF.
- Include `page_no` when the annotated metadata is on a known page, usually page 1.
- If any date field is requested, the `system_prompt` must specify the expected date format.
- Keep HTML XPath metadata in `metadata_conf`; keep PDF-body metadata in `fixed_metadata["fields"]` with `need_prediction: True`.

---

## Pattern 1b: 3-Step DOCX Extraction (FIRST → SECOND → FINAL)

Use this when the portal serves `.doc` or `.docx` files instead of PDFs.

```
FIRST (BASIC, LIST):  Listing page → collects detail page URLs
                              ↓
SECOND (BASIC, LIST): Detail pages → collects .doc/.docx download URLs
                              ↓
FINAL (METHOD):       DOCX URLs → extracts text using built-in parse_doc
```

### SECOND Config — collecting `.doc`/`.docx` links:

```python
second = {
    "agent": 5,
    "sleep": (2, 4),
    "next_page": None,
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["domain.com"],
    "conf": [
        {
            # Match .doc and .docx links (case-insensitive via both variants)
            "xpath": '//a[contains(@href, ".doc") or contains(@href, ".docx") or contains(@href, ".DOC") or contains(@href, ".DOCX")]',
            "url": "./@href",
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}
```

### FINAL Config for DOCX (always use this structure):

```python
final = {
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_doc",  # Built-in - no custom code!
    "regex": None,
    "allowed_domains": ["domain.com"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

**⚠️ IMPORTANT**: Just like PDFs, include these in FIRST config's `fixed_metadata` when dealing with DOCX:

```python
"fixed_metadata": {
    "type_of_law": "...",
    "issuing_authority": "...",
    "lang": "en",
    "ocr": False,
    "date_order": "DMY",
},
```

### How `parse_doc` Works

`parse_doc` is a built-in method on `CustomCrawlerServices`. It:

1. Uses the browser to trigger the file download to the local download directory
2. Waits for the `.crdownload` temp file to disappear (up to 180 s)
3. POSTs the downloaded `.doc`/`.docx` file to the `DOC_PARSER_URL` microservice
4. Receives HTML back, strips non-content tags, and returns plain text + markdown

No custom code is needed — it works the same way as `parse_pdf`.

---

## Pattern 2: 2-Step HTML Extraction (FIRST → FINAL)

Use this when instructions say "extract full text" from HTML pages:

```
FIRST (BASIC, LIST):  Listing page → collects article page URLs
                              ↓
FINAL (BASIC, DICT):  Article pages → extracts HTML content
```

### FINAL Config for HTML Content:

```python
final = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.BASIC,
    "regex": None,
    "allowed_domains": ["domain.com"],
    "repealed_laws": None,
    "fields": {
        "conf": {
            "title": '//h1[@class="article-title"]/text()',
            "content": ['//div[@class="article-content"]'],  # List of content containers
        },
        "extract": {"title": "extract_first"},
        "markdown_kind": MarkdownKindEnum.BASIC,
        "decompose_list": [".cookie-banner", ".navigation", ".footer"],  # CSS selectors to remove
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

---

## Pattern 3: 4+ Stage Deep Crawls (FIRST → SECOND → THIRD → FOURTH → FINAL)

Use this when instructions describe 4 or more stages (e.g., Hub → Sub-hub → Topic → Detail).

```
Stage 1 (BASIC, LIST): Hub page → collects category/section URLs
                              ↓
Stage 2 (BASIC, LIST): Category page → collects sub-category URLs
                              ↓
Stage 3 (BASIC, LIST): Sub-category page → collects detail page URLs
                              ↓
[Stage 4 if needed]
                              ↓
FINAL (BASIC or METHOD): Detail pages → extracts content (HTML/PDF)
```

### Example: Mapping 4-Stage Instructions to Config

If instructions describe:

- Stage 1: Hub (main sections)
- Stage 2: Sub-hub (topics)
- Stage 3: Topic (individual items)
- Stage 4: Detail (content)

Map to config:

- FIRST = Stage 1
- SECOND = Stage 2
- THIRD = Stage 3
- FINAL = Stage 4

```python
# STAGE 1 (FIRST): Hub → collects section/category links
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (3, 6),
    "urls": ["https://www.example.gov/main-hub"],
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.example.gov"],
    "conf": [
        {
            "xpath": '//nav[@class="main-menu"]//a',
            "url": "./@href",
            "metadata_conf": {},
            "fixed_metadata": {},
        }
    ],
    ...
}

# STAGE 2 (SECOND): Sub-hub → collects topic links
second = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.example.gov"],
    "conf": [{"xpath": '//div[@class="topic-list"]//a', "url": "./@href"}],
    ...
}

# STAGE 3 (THIRD): Topic → collects detail page links
third = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.example.gov"],
    "conf": [{"xpath": '//ul[@class="items"]/li/a', "url": "./@href"}],
    ...
}

# STAGE 4 (FINAL): Detail → extracts content
final = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.BASIC,
    ...
}

portal_config = {
    "portal_id": PortalIDEnum.EXAMPLE,
    "config": [final, third, second, first],
    "_config_module": __name__.split(".")[-1],
}
```

---

## Pattern 4: Mixed Content (Both HTML and PDFs at Final Stage)

Use this when the final stage can contain BOTH HTML content AND PDF links.

### Option A: Extract Both in Final Config

```python
final = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.BASIC,
    "regex": None,
    "allowed_domains": ["www.example.gov"],
    "repealed_laws": None,
    "fields": {
        "conf": {
            "title": '//h1[@class="article-title"]/text()',
            "content": ['//div[@class="article-content"]'],
        },
        "extract": {"title": "extract_first"},
        "markdown_kind": MarkdownKindEnum.BASIC,
        "decompose_list": [".sidebar", ".advertisement"],
        "pdf_urls": {
            "xpath": '//a[contains(@href, ".pdf") or contains(@href, ".PDF")]/@href',
            "extract": "extract_all",
        },
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

### Option B: Two-Phase (if PDFs need separate processing)

```
FIRST (BASIC, LIST):  Listing → collects detail page URLs
                            ↓
SECOND (BASIC, LIST): Detail pages → collects PDF URLs + content
                            ↓
FINAL (METHOD): Parses PDFs
```

---

## Pattern 5: Hub → Sub-hub → Listing → Detail (4-Stage with Mixed Final)

Use for complex portals where final stage has mixed content:

```python
# Map 4-stage to config:
# Stage 1 → FIRST
# Stage 2 → SECOND
# Stage 3 → THIRD
# Stage 4 → FINAL (handle both HTML and PDF)

portal_config = {
    "portal_id": PortalIDEnum.EXAMPLE,
    "config": [final, third, second, first],
    "_config_module": __name__.split(".")[-1],
}
```

---

## Complete Translation Example

### Input Instructions:

```markdown
# Portal Implementation Instructions: Bundesministerium für Gesundheit

## General Configuration

- **Issuing Authority (DE):** Bundesministerium für Gesundheit
- **Issuing Authority (EN):** Federal Ministry of Health
- **Global Extraction Rule:** Pick all results visible in the lists.
- **Data Guardrail:** Ignore any links that redirect to bundestag.de.

## Link 1: Gesetze und Verordnungen (Laws and Regulations)

- **Primary URL:** https://www.bundesgesundheitsministerium.de/service/gesetze-und-verordnungen.html
- **Type of Law:** Gesetzen und Verordnungen
- **Number of Steps:** 3
- **Step Breakdown:**
    - **Step 1:** Collect all law entry URLs from the listing page
    - **Step 2:** On each law detail page, collect all PDF download links
    - **Step 3:** Extract text content from each PDF file
- **Extraction Logic:**
    - Navigate to each search result's detail page.
    - Pick all PDFs found on the detail page.
    - Metadata: Extract "Date of Publication".

## Link 2: Pressemitteilungen (Press Releases)

- **Primary URL:** https://www.bundesgesundheitsministerium.de/presse/pressemitteilungen.html
- **Type of Law:** Pressemitteilung
- **Number of Steps:** 2
- **Step Breakdown:**
    - **Step 1:** Collect all press release URLs from the listing page
    - **Step 2:** Extract the HTML text content from each press release page
- **Extraction Logic:**
    - Pick all entries from the list.
    - Title: Extract from the main heading.
    - Full Text: Extract the complete text body.
```

### Output Implementation:

#### Step 1: constants.py

**Note**: You will be provided with the Portal ID to use.

**IMPORTANT**: Always add new IDs at the END of `PortalIDEnum`, never insert them in the middle.

```python
class PortalIDEnum(int, Enum):
    # ... all existing portal IDs ...
    EXISTING_PORTAL_LAST = 449
    # Add new portal at the END
    GERMANY_BMG = 450  # Provided by instructions
```

#### Step 2: seed.py

```python
{
    "id": PortalIDEnum.GERMANY_BMG,
    "name": "Bundesministerium für Gesundheit",
    "base_url": "www.bundesgesundheitsministerium.de",
    "jurisdiction": germany_german_j,
},
```

#### Step 3: Navigate, capture HTML, and extract XPaths

Use the browser (Playwright MCP or equivalent): navigate to the listing Stage URL, capture page HTML (write to file if large, e.g. `browser_dev/portal_html_inspection/bmg_laws_list.html`), then navigate to a detail page example and capture its HTML. Read the captured files and extract XPaths based on the actual DOM structure.

#### Step 4: Configuration File for Laws (3-step PDF)

**File: `jimmy_v4/portal_configurations/germany/germany_bmg_laws.py`**

```python
from jimmy_v4.constants import (
    CrawlerKindEnum,
    CrawlerResponseTypeEnum,
    KeywordMatchingType,
)
from jimmy_v4.constants import PortalIDEnum

# STEP 1 (FIRST): Collect law entry URLs from the listing page
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (3, 6),
    "urls": [
        "https://www.bundesgesundheitsministerium.de/service/gesetze-und-verordnungen.html",  # Link 1: Gesetze und Verordnungen
    ],
    "next_page": '//nav[@class="c-pagination"]//a[contains(@class, "next")]/@href',
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.bundesgesundheitsministerium.de"],
    "conf": [
        {
            "xpath": '//article[@class="c-teaser"]',
            "url": ".//h3[@class='c-teaser__headline']/a/@href",
            "metadata_conf": {
                "title": ".//h3[@class='c-teaser__headline']/a/text()",
                "date_of_publication": ".//time/@datetime",
            },
            "fixed_metadata": {
                "type_of_law": "Gesetzen und Verordnungen",
                "issuing_authority": "Bundesministerium für Gesundheit",
                "lang": "de",
                "ocr": False,
                "date_order": "DMY",
            },
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

# STEP 2 (SECOND): Collect PDF URLs from each detail page
second = {
    "agent": 5,
    "sleep": (3, 6),
    "next_page": None,
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.bundesgesundheitsministerium.de"],
    "conf": [
        {
            "xpath": '//a[contains(@href, ".pdf") or contains(@href, ".PDF")]',
            "url": "./@href",
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

# STEP 3 (FINAL): Extract text from PDFs using built-in parse_pdf
third = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_pdf",  # Built-in - no custom code!
    "regex": None,
    "allowed_domains": ["www.bundesgesundheitsministerium.de"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}

germany_bmg_laws_configurations = {
    "portal_id": PortalIDEnum.GERMANY_BMG,
    "config": [third, second, first],
    "_config_module": __name__.split(".")[-1],
}
```

#### Step 5: Configuration File for Press (2-step HTML)

**File: `jimmy_v4/portal_configurations/germany/germany_bmg_press.py`**

```python
from jimmy_v4.constants import (
    CrawlerKindEnum,
    CrawlerResponseTypeEnum,
    KeywordMatchingType,
    MarkdownKindEnum,
)
from jimmy_v4.constants import PortalIDEnum

# STEP 1 (FIRST): Collect press release URLs from listing page
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (3, 6),
    "urls": [
        "https://www.bundesgesundheitsministerium.de/presse/pressemitteilungen.html",  # Link 2: Pressemitteilungen
    ],
    "next_page": '//a[contains(@class, "next")]/@href',
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["www.bundesgesundheitsministerium.de"],
    "conf": [
        {
            "xpath": '//article[contains(@class, "press-release")]',
            "url": ".//a/@href",
            "metadata_conf": {
                "title": ".//h2/text()",
                "date_of_publication": ".//time/@datetime",
            },
            "fixed_metadata": {
                "type_of_law": "Pressemitteilung",
                "issuing_authority": "Bundesministerium für Gesundheit",
            },
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

# STEP 2 (FINAL): Extract HTML content from each press release page
second = {
    "agent": 5,
    "sleep": (3, 6),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.BASIC,
    "regex": None,
    "allowed_domains": ["www.bundesgesundheitsministerium.de"],
    "repealed_laws": None,
    "fields": {
        "conf": {
            "title": '//h1[@class="c-headline"]/text()',
            "content": ['//div[@class="c-article__content"]'],
        },
        "extract": {"title": "extract_first"},
        "markdown_kind": MarkdownKindEnum.BASIC,
        "decompose_list": [".cookie-banner", ".share-buttons", ".c-breadcrumb"],
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}

germany_bmg_press_configurations = {
    "portal_id": PortalIDEnum.GERMANY_BMG,
    "config": [second, first],
    "_config_module": __name__.split(".")[-1],
}
```

---

## Implementation Checklist

### ✅ Step 1: Update constants.py

1. Use the Portal ID provided in the instructions (if new portal)
2. Add portal ID to the END of `PortalIDEnum` (if new portal)

### ✅ Step 2: Add Portal to seed.py (if new portal)

1. Find the appropriate jurisdiction variable
2. Add portal entry to `portal_list`

### ✅ Step 3: Navigate and capture HTML per stage

1. Create directory: `mkdir -p browser_dev/portal_html_inspection` (or `/tmp/portal_html_inspection`)
2. For each Stage URL: navigate with the browser, perform any required interaction (e.g. form submit), then capture page HTML (write to file to avoid size limits) and read it
3. Derive XPaths from the captured HTML for listing, detail, pagination, and content/PDFs as needed

### ✅ Step 4: Create Configuration Files

1. One file per section in `portal_configurations/[country]/`
2. Name pattern: `[country]_[portal]_[section].py`
3. Follow the appropriate pattern (2-step or 3-step)
4. **⚠️ ALWAYS add the link number as a comment on every URL** in the FIRST config's `urls` list (e.g. `"https://example.com",  # Link 1: Section Name`). This is mandatory — never leave a URL without a link number comment.

---

## Key Rules Summary

| Content Type     | Stages | Pattern                                                          |
| ---------------- | ------ | ---------------------------------------------------------------- |
| HTML content     | 2      | FIRST (BASIC) → FINAL (BASIC)                                    |
| PDF content      | 3      | FIRST (BASIC) → SECOND (BASIC) → FINAL (METHOD with `parse_pdf`) |
| DOCX content     | 3      | FIRST (BASIC) → SECOND (BASIC) → FINAL (METHOD with `parse_doc`) |
| Mixed (HTML+PDF) | 3+     | FIRST → [SECOND →] FINAL (handle both types)                     |
| 4+ deep levels   | 4+     | FIRST → SECOND → THIRD → [FOURTH →] FINAL                        |
| Date-filtered    | any    | FIRST (METHOD) → [SECOND (BASIC)] → FINAL (BASIC or METHOD)      |

### Fixed Metadata for PDFs:

Always include in FIRST config when dealing with PDFs:

```python
"fixed_metadata": {
    "type_of_law": "...",
    "issuing_authority": "...",
    "lang": "en",       # or "de", "fr", etc.
    "ocr": False,       # True for scanned PDFs
    "date_order": "DMY",  # or "MDY", "YMD"
},
```

### Config Order in Export:

Always reverse order - FINAL first, FIRST last. Always include `"_config_module"` as the **last key**:

```python
portal_configurations = {
    "portal_id": PortalIDEnum.PORTAL_NAME,
    "config": [third, second, first],           # 2-step: [second, first]
    "config": [fourth, third, second, first],   # 4-step example
    "_config_module": __name__.split(".")[-1],
}
```

---

## What You're Providing

You are providing a **starting point configuration**. The XPaths may need manual adjustment after testing. The goal is to:

1. ✅ Create the correct file structure
2. ✅ Add portal ID to `PortalIDEnum` and seed entry
3. ✅ Provide reasonable XPaths based on **actual HTML** from **browser navigation** (Playwright or equivalent) — never guess; if no browser tool, ask human to paste HTML per stage
4. ✅ Use the correct patterns (2-step, 3-step, 4+ step, or mixed content)
5. ✅ **Prefer BASIC** for listing and detail; use **METHOD only when necessary** (parse_pdf/parse_doc, small_crawl date filter, form submission, or custom extraction)
6. ✅ Handle PDFs with built-in `parse_pdf` method (METHOD for FINAL step)
7. ✅ Handle DOCX/DOC files with built-in `parse_doc` method
8. ✅ Handle mixed content (both HTML and PDFs) at final stage
9. ✅ Get HTML by **navigating** to each Stage URL (and interacting if needed), then capturing page HTML; write to file when large and read it to derive XPaths — do not use curl; do not guess XPaths
10. ✅ When `small_crawl` is available, use a METHOD kind FIRST step to inject date filters
11. ✅ Include `"_config_module": __name__.split(".")[-1]` as the last key in the bottom configurations dict
12. ✅ **⚠️ ALWAYS add the link number as a comment on every URL** in the FIRST config's `urls` list (e.g. `"https://example.com",  # Link 1: Section Name`) — mandatory for every config file without exception

The human will then test and refine the XPaths as needed.
