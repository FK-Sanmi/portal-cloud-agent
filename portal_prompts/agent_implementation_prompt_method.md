# Step 3: Agent Implementation Prompt (Custom METHOD)

## Your Task

A portal has already been implemented with BASIC configs. You have been asked to replace one or more BASIC steps with a custom METHOD — typically because:

- A listing step requires **small crawl date filtering** (inject `?from=...&to=...` when `small_crawl=True`)
- A listing step requires **form submission** before results appear
- The page structure is too dynamic or conditional for static XPaths
- The final step needs **conditional PDF vs HTML** handling in one method

You will receive the existing config file(s), the portal URL, and a description of what the method needs to do. Your job is to write the method body in the correct country crawler file and update the config to reference it.

---

## Context: Where This Fits in the Workflow

```
Step 1 — Portal Instructions written by analyst
Step 2 — BASIC configs implemented (XPath extraction)
Step 3 — YOU ARE HERE: Selected steps converted to custom METHODs
Step 4 — Review, test, refine
```

The config file already exists. You are **adding or replacing** one step in it with `kind: CrawlerKindEnum.METHOD` and writing the corresponding method in `jimmy_v4/country_crawlers/<country>.py`.

---

## Mandatory Coding Rules

These rules are **non-negotiable**. PRs that violate them will not be approved.

---

### Rule 1 — No `try/except` blocks

**Never wrap a method body in `try/except`.** When a method silently swallows an exception, the crawler returns an empty result with no traceback, making failures impossible to diagnose in production.

```python
# ❌ WRONG — failure is invisible
def my_portal_first(self, url: str, webdriver: WebDriver, metadata: dict = {}) -> list:
    results = []
    try:
        webdriver.get(url)
        ...
    except Exception as e:
        write_log(f"Error: {str(e)}")
    return results

# ✅ CORRECT — exceptions propagate naturally with full traceback
def my_portal_first(self, url: str, webdriver: WebDriver, metadata: dict = {}) -> list:
    results = []
    webdriver.get(url)
    ...
    return results
```

---

### Rule 2 — Always use random delays

Fixed sleep values are a bot-detection fingerprint. Always draw from a range.

```python
# ❌ WRONG
time.sleep(2)

# ✅ CORRECT
time.sleep(random.randint(2, 4))
```

---

### Rule 3 — HTML extraction must use `clean_text` + `convert_to_markdown`

Never use `soup.get_text()` alone or set `content_markdown = content`. Always produce both fields correctly.

```python
# ❌ WRONG
content["content"] = body.get_text(separator="\n", strip=True)
content["content_markdown"] = content["content"]

# ✅ CORRECT
from jimmy_v4.utils.helpers import clean_text, convert_to_markdown
from jimmy_v4.utils.table_helpers import table_converter
from jimmy_v4.utils.list_helpers import list_converter

body = soup.find("body")
for tag in body.find_all(["script", "style", "nav", "header", "footer"]):
    tag.decompose()

content["content"] = clean_text(body.get_text(separator=" ", strip=True))
content["content_markdown"] = convert_to_markdown(
    str(body),
    custom_converters={
        "table": table_converter,
        "ol": list_converter,
        "ul": list_converter,
    },
).strip()
```

---

### Rule 4 — Don't write a custom final METHOD just to call `parse_pdf`

If your final METHOD only downloads a PDF, parses it, and calls `format_metadata`, **use the built-in `parse_pdf` method name instead**. Pass `date_order`, `lang`, and `ocr` via `fixed_metadata` in the earlier stage so `parse_pdf` picks them up:

```python
"fixed_metadata": {
    ...
    "lang": "en",
    "ocr": False,
    "date_order": "MDY",
},
```

Only write a custom final method when `parse_pdf` cannot handle the variation — e.g. conditional PDF vs HTML, title extraction from PDF content, multi-file download logic.

---

### Rule 5 — Always use `urljoin` to construct URLs

Never concatenate URL parts using f-strings or `+`. Use `urllib.parse.urljoin` (already imported in all crawler files).

```python
# ❌ WRONG — breaks with path edge cases and is hard to audit
download_url = f"{base_url}{path}"
download_url = base_url + path

# ✅ CORRECT
from urllib.parse import urljoin
download_url = urljoin(base_url, path)
```

---

## Method Signatures

### LIST method (returns `list`) — used for FIRST or intermediate stages

```python
def portal_name_stage_name(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> list:
    results = []
    webdriver.get(url)
    time.sleep(random.randint(2, 4))
    ...
    return results
```

### DICT method (returns `dict`) — used for FINAL stage

```python
def portal_name_final(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> dict:
    content = {}
    ...
    metadata = format_metadata(metadata, date_order="MDY")
    content.update(metadata)
    return content
```

---

## Metadata Pipeline — What Your Method Receives and Must Return

### What `metadata` contains when your method is called

The `metadata` dict passed to your method already contains **all metadata accumulated by every prior stage** — `fixed_metadata` from FIRST, any XPath-extracted values, and anything set by earlier METHOD stages. You do **not** need to re-establish prior metadata in your method.

### LIST methods — building result items

Each item your method appends to `results` must include a `"url"` key and a `"metadata"` dict:

```python
results.append({
    "url": full_url,
    "metadata": {
        "title": title,
        "date_of_publication": date,
        # Only include fields this stage introduces — prior metadata carries forward automatically
    },
})
```

Do **not** copy the entire incoming `metadata` dict into each result's metadata manually — the pipeline merges it automatically after the method returns.

### DICT methods — producing final content

Return a flat dict with `content`, `content_markdown`, plus any metadata fields this stage sets. Always call `format_metadata` before `content.update(metadata)`:

```python
metadata = format_metadata(metadata, date_order="MDY")
content.update(metadata)
return content
```

### Carry-forward rule

Once a metadata field is set by a prior non-final stage, it **cannot be changed** by a later non-final stage (the pipeline's `.update()` will overwrite the new value with the earlier one). A non-final method can only **add new fields**, not change existing ones. The final stage is the only place that can freely overwrite any field.

---

## Common Patterns

### Pattern A — Small Crawl Date Filter (FIRST step, LIST)

Use when the portal accepts `?from=...&to=...` query params and `small_crawl` should limit the window.

```python
def example_portal_news_first(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> list:
    from jimmy_v4.utils.helpers import get_date_range, fetch_pagination_data

    is_small_crawl = getattr(self.portal, "small_crawl", False)
    occurrence = getattr(self.portal, "crawling_occurrence", None)

    if is_small_crawl:
        date_range = get_date_range(occurrence)
        start = date_range["period_start"]
        end = date_range["current_date"]
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
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
                "ocr": False,
                "date_order": "MDY",
            },
        }
    ]

    results = fetch_pagination_data(
        url=url,
        webdriver=webdriver,
        conf=conf,
        next_page_xpath='//a[@rel="next"]/@href',
        delay_value=(2, 4),
    )
    return results
```

**Config:**

```python
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (2, 4),
    "urls": ["https://www.example.gov/news"],
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "example_portal_news_first",
    "allowed_domains": ["www.example.gov"],
    "regex": None,
    "process": None,
}
```

**Key points:**

- Always use `get_date_range(occurrence)` for small crawl date windows — **never** `get_previous_seven_days()`. The return dict has `"period_start"` and `"current_date"` keys, both `datetime` objects supporting `.strftime()`.
- Always get `occurrence = getattr(self.portal, "crawling_occurrence", None)` and pass it to `get_date_range(occurrence)` — the function uses it to determine the correct window size.
- Always check `getattr(self.portal, "small_crawl", False)` — never access `.small_crawl` directly.
- If `small_crawl` is `False`, crawl everything (no date filter added).
- Use `fetch_pagination_data` to handle multi-page results automatically.

---

### Pattern B — Pagination with Complex Link Collection (FIRST step, LIST)

Use when `fetch_pagination_data` is sufficient but you need some pre/post logic.

```python
def example_portal_list_first(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> list:
    from jimmy_v4.utils.helpers import fetch_pagination_data

    conf = [
        {
            "xpath": '//table[@id="results"]//tr[position()>1]',
            "url": ".//td[1]/a/@href",
            "metadata_conf": {
                "title": ".//td[1]/a/text()",
                "date_of_publication": ".//td[3]/text()",
            },
            "fixed_metadata": {
                "type_of_law": "Decision",
                "issuing_authority": "Example Court",
                "lang": "en",
                "ocr": False,
                "date_order": "DMY",
            },
            "pre_append_url": "https://www.example.gov",
        }
    ]

    return fetch_pagination_data(
        url=url,
        webdriver=webdriver,
        conf=conf,
        next_page_xpath='//a[contains(@class,"next")]/@href',
        delay_value=(2, 4),
    )
```

---

### Pattern C — Conditional PDF vs HTML Final (FINAL step, DICT)

Use when the URL may be either a PDF or an HTML page.

```python
def example_portal_final(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> dict:
    from jimmy_v4.utils.helpers import (
        parse_pdf_file_by_downloading,
        skip_existing_file_with_timestamp_update,
        clean_text,
        convert_to_markdown,
        format_metadata,
    )
    from jimmy_v4.utils.table_helpers import table_converter
    from jimmy_v4.utils.list_helpers import list_converter
    from bs4 import BeautifulSoup

    content = {}

    if url.lower().endswith(".pdf"):
        data = {"file_url": url, "ocr": False, "lang": "en"}
        page_content, content_markdown, existing_file_data = parse_pdf_file_by_downloading(
            webdriver=webdriver, data=data, portal=self.portal
        )
        if existing_file_data:
            return skip_existing_file_with_timestamp_update(url=url)
        content["content"] = page_content
        content["content_markdown"] = content_markdown
    else:
        webdriver.get(url)
        time.sleep(random.randint(2, 4))
        soup = BeautifulSoup(webdriver.page_source, "html.parser")
        body = soup.find("body")
        for tag in body.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        content["content"] = clean_text(body.get_text(separator=" ", strip=True))
        content["content_markdown"] = convert_to_markdown(
            str(body),
            custom_converters={
                "table": table_converter,
                "ol": list_converter,
                "ul": list_converter,
            },
        ).strip()

    metadata = format_metadata(metadata, date_order="MDY")
    content.update(metadata)
    return content
```

---

### Pattern D — Form Submission Before Listing (FIRST step, LIST)

Use when results are only available after submitting a search form.

```python
def example_portal_search_first(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> list:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from jimmy_v4.utils.helpers import fetch_pagination_data

    webdriver.get(url)
    time.sleep(random.randint(2, 4))

    # Fill and submit the search form
    search_input = webdriver.find_element(By.ID, "search-input")
    search_input.clear()
    search_input.send_keys("*")

    submit_btn = webdriver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    submit_btn.click()

    # Wait for results to load
    WebDriverWait(webdriver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".results-list"))
    )
    time.sleep(random.randint(1, 2))

    conf = [
        {
            "xpath": '//ul[@class="results-list"]/li',
            "url": ".//a/@href",
            "metadata_conf": {"title": ".//span[@class='title']/text()"},
            "fixed_metadata": {
                "type_of_law": "Decision",
                "issuing_authority": "Example Authority",
                "lang": "en",
                "ocr": False,
                "date_order": "DMY",
            },
        }
    ]

    current_url = webdriver.current_url
    return fetch_pagination_data(
        url=current_url,
        webdriver=webdriver,
        conf=conf,
        next_page_xpath='//a[@aria-label="Next page"]/@href',
        delay_value=(2, 4),
    )
```

---

## Where to Add the Method

Add the method to the correct `jimmy_v4/country_crawlers/<country>.py` file, grouped near other methods for the same portal. Method naming convention:

```
<portal_filename_prefix>_<stage_name>

Examples:
  usa_uscaaf_rules_first
  germany_bmg_laws_final
  netherlands_overheid_search_first
```

---

## Updating the Config

Change the affected step from `BASIC` to `METHOD`:

```python
# Before (BASIC)
first = {
    "first_config": True,
    "kind": CrawlerKindEnum.BASIC,
    "conf": [...],
    ...
}

# After (METHOD)
first = {
    "first_config": True,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "example_portal_first",  # must exist in country crawler
    "conf": None,
    ...
}
```

---

## Implementation Checklist

- [ ] No `try/except` anywhere in the method body
- [ ] All `time.sleep()` calls use `random.randint(min, max)` — no fixed values
- [ ] HTML content uses `clean_text` for `content` and `convert_to_markdown` for `content_markdown`
- [ ] Final methods call `format_metadata(metadata, date_order=...)` before `content.update(metadata)`
- [ ] Method does not manually copy prior pipeline metadata into each result (pipeline does this)
- [ ] Method name in config exactly matches the function name in the crawler file
- [ ] `getattr(self.portal, "small_crawl", False)` used — not `.small_crawl`
- [ ] `get_date_range(occurrence)` used for small crawl date windows — **not** `get_previous_seven_days()`; `occurrence = getattr(self.portal, "crawling_occurrence", None)`
- [ ] Method is a plain function on the class (no `try/except` wrapper, no nested helpers)
- [ ] `parse_pdf` built-in used for pure PDF-only finals instead of a custom method
