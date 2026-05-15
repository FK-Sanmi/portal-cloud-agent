# Gemini Metadata Extraction — Implementation Prompt

## Your Task

Metadata fields that are **not available via XPath** (buried in body text or require interpretation) can be extracted using Gemini. There are **two approaches** depending on the source type:

| Approach                                              | When to use                                                 | Where Gemini config lives                                                      |
| ----------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **`need_prediction` in `fixed_metadata`**             | PDFs processed by the built-in `parse_pdf` method           | Inside the listing/detail BASIC config's `fixed_metadata` — **no custom code** |
| **`extract_metadata_from_text` in a `_final` METHOD** | HTML detail pages, or PDFs needing complex multi-step logic | Inside a custom `_final` function in the country crawler                       |

**Always prefer `need_prediction` for PDFs.** Only write a custom `_final` METHOD when the source is HTML or when `parse_pdf` alone cannot satisfy the extraction requirements.

The analyst will provide:

- The **list of metadata fields** to extract (names + descriptions).
- The **system prompt** to send to Gemini.
- The **word count** to pass to Gemini (how many words of body text to slice; default 400–500 for PDFs, 250 for HTML).
- Whether the source is **PDF** or **HTML**.

---

## Context: Where This Fits

```
Step 1 — Portal Instructions written by analyst
Step 2 — BASIC configs implemented (XPath extraction)
Step 3 — Gemini metadata added (need_prediction for PDFs, _final METHOD for HTML)
Step 4 — YOU ARE HERE: wire up the correct approach
Step 5 — Review, test, refine
```

For PDFs, Gemini extraction is triggered automatically inside `parse_pdf` when `need_prediction: True` is present in metadata. For HTML, it goes inside the `_final` METHOD **after** content has been obtained and **before** `format_metadata` + `content.update(metadata)`.

---

## Mandatory Rules (inherited from METHOD rules)

- **No `try/except`** — let exceptions propagate.
- **Random delays** — `time.sleep(random.randint(2, 4))`, never fixed values.
- **`clean_text` + `convert_to_markdown`** for HTML content (see method prompt Rule 3).
- **`skip_existing_file_with_timestamp_update`** for PDFs when `existing_file_data` is truthy.

---

## Pattern 0 — `need_prediction` in `fixed_metadata` (PREFERRED for PDFs)

When the final stage uses the built-in `parse_pdf` method, **no custom code is needed**. Add the Gemini configuration directly inside the listing/detail BASIC config's `fixed_metadata`. `parse_pdf` reads these keys automatically via `custom_crawler_service.py`.

### Required keys in `fixed_metadata`

| Key                 | Type                       | Description                                                                                                             |
| ------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `"need_prediction"` | `True`                     | Enables Gemini extraction                                                                                               |
| `"fields"`          | `dict`                     | Field names → type strings (use `"str"` for all)                                                                        |
| `"system_prompt"`   | `str`                      | Instruction sent to Gemini. **Must** specify the expected date format (e.g. DD/MM/YYYY) if any date field is requested. |
| `"page_no"`         | `int` or `tuple[int, int]` | _(optional)_ Page(s) to extract from; defaults to `1`. Use a tuple for a range, e.g. `(1, 3)`.                          |

### Example — listing config extracting `issuing_authority` from a PDF

```python
first = {
    "first_config": True,
    "agent": 5,
    "sleep": (2, 4),
    "urls": [
        "https://example.gov/opinions",  # Link 1: Opinions list
    ],
    "other_urls": None,
    "next_page": None,
    "type": CrawlerResponseTypeEnum.LIST,
    "kind": CrawlerKindEnum.BASIC,
    "allowed_domains": ["example.gov"],
    "conf": [
        {
            "xpath": '//table//tr[.//a[contains(@href, ".pdf")]]',
            "url": './/a/@href',
            "metadata_conf": {
                "title": ".//td[1]//text()",
                "date_of_publication": ".//td[2]//text()",
            },
            "fixed_metadata": {
                "type_of_law": "Opinion",
                "issuing_authority": "Example Courts",
                "lang": "en",
                "ocr": False,
                "date_order": "MDY",
                "need_prediction": True,
                "fields": {
                    "issuing_authority": "str",
                },
                "system_prompt": (
                    "From the first page of this court opinion PDF, extract the issuing authority "
                    "(the name of the court). Return it as issuing_authority."
                ),
            },
        }
    ],
    "metadata_conf": None,
    "regex": None,
    "process": None,
}

second = {
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "parse_pdf",   # ← built-in; reads need_prediction automatically
    "regex": None,
    "allowed_domains": ["example.gov"],
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "markdown_kind": None,
        "decompose_list": None,
        "metadata_processor": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
    "legal_classification": LegalClassificationEnum.COURT_CASES,
}
```

### How it works internally

`parse_pdf` (in `custom_crawler_service.py`) checks for `need_prediction` in `metadata`. When `True` it:

1. Pops `fields`, `optional_fields` (if any), and `system_prompt` from `metadata`.
2. Builds a dynamic Pydantic model from `fields`.
3. Calls `get_metadata_from_pdf_page(page_no=..., system_prompt=..., schema=...)`.
4. Merges the result into `metadata` before `format_metadata`.

You do **not** need to write any Python for this — everything is handled by the built-in method.

---

## `extract_metadata_from_text` Function Signature

_(Used only in custom `_final` METHOD functions — HTML sources or complex PDF cases.)_

`extract_metadata_from_text` is defined in `jimmy_v4/utils/helpers.py`:

```python
def extract_metadata_from_text(
    system_prompt: str,
    content: str,       # truncated text to send to Gemini
    url: str,           # used as cache key
    schema,             # Pydantic BaseModel class (NOT an instance)
) -> Union[dict, None]:
```

- Results are **cached** per `(portal_id, url, prompt, content)` in `MetadataCacheModelSQL`.
- The cache is bypassed only when `force_metadata_update=True` in `portal_info.json`.
- Returns a plain `dict` matching the schema fields (e.g. `{"date_of_publication": "01/01/2024"}`).
- Raises `TimeoutError` if Gemini exceeds 10 seconds.
- Uses `gemini-2.0-flash-lite` with `temperature=0.5` and structured JSON output.

---

## Pydantic Schema

Define the schema **inline** inside the METHOD function (not at module level). Every field must be `Optional[str]` unless it is always guaranteed to be present. Use snake_case names that match the metadata keys you want in the final document.

```python
from pydantic import BaseModel
from typing import Optional

class Metadata(BaseModel):
    date_of_publication: Optional[str]
    date_of_enactment: Optional[str]
    date_of_effective: Optional[str]
    document_number: Optional[str]
    issuing_body: Optional[str]
    # ... add only the fields the analyst requested
```

The field names become keys in the returned dict and are merged directly into `metadata`.

---

## Pattern 1 — `_final` METHOD with PDF source (complex cases only)

**Only use this pattern when `need_prediction` is insufficient** — for example, when the PDF requires custom logic beyond what `parse_pdf` provides (e.g. selective merging, chained extraction, post-processing before `format_metadata`).

```python
import random
import time
from pydantic import BaseModel
from typing import Optional
from scrapy.http import TextResponse
from selenium.webdriver.remote.webdriver import WebDriver
from jimmy_v4.utils.helpers import (
    clean_text,
    parse_pdf_file_by_downloading,
    extract_metadata_from_text,
    skip_existing_file_with_timestamp_update,
    format_metadata,
)


def country_portal_section_final(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> dict:
    class Metadata(BaseModel):
        # ← fill in fields provided by analyst
        date_of_publication: Optional[str]
        date_of_enactment: Optional[str]

    content = {}

    data = {
        "file_url": url,
        "ocr": False,   # set True only if the PDF is scanned / image-based
        "lang": "en",   # language code for OCR
    }
    page_content, content_markdown, existing_file_data = parse_pdf_file_by_downloading(
        webdriver=webdriver, data=data, portal=self.portal
    )
    if existing_file_data:
        return skip_existing_file_with_timestamp_update(url=url)

    content["content"] = page_content
    content["content_markdown"] = content_markdown

    # Truncate to first N words (analyst specifies; default 400–500 for PDFs)
    cleaned_content = " ".join(clean_text(page_content).split()[:500])
    extracted_metadata = extract_metadata_from_text(
        system_prompt=(
            # ← paste the system prompt provided by analyst
            "From the given content, extract the date of publication and date of enactment "
            "in DD/MM/YYYY format if they exist."
        ),
        content=cleaned_content,
        url=url,
        schema=Metadata,
    )
    if extracted_metadata:
        metadata.update(extracted_metadata)

    metadata = format_metadata(metadata)
    content.update(metadata)
    return content
```

---

## Pattern 2 — `_final` METHOD with HTML source

```python
import random
import time
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import Optional
from scrapy.http import TextResponse
from selenium.webdriver.remote.webdriver import WebDriver
from jimmy_v4.utils.helpers import (
    clean_text,
    convert_to_markdown,
    extract_metadata_from_text,
    format_metadata,
)
from jimmy_v4.utils.table_helpers import table_converter
from jimmy_v4.utils.list_helpers import list_converter


def country_portal_section_final(
    self, url: str, webdriver: WebDriver, metadata: dict = {}
) -> dict:
    class Metadata(BaseModel):
        # ← fill in fields provided by analyst
        date_of_publication: Optional[str]
        document_number: Optional[str]

    content = {}

    webdriver.get(url)
    time.sleep(random.randint(2, 4))

    soup = BeautifulSoup(webdriver.page_source, "html.parser")
    body = soup.find("body")
    for tag in body.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    page_content = clean_text(body.get_text(separator=" ", strip=True))
    content_markdown = convert_to_markdown(
        str(body),
        custom_converters={
            "table": table_converter,
            "ol": list_converter,
            "ul": list_converter,
        },
    ).strip()

    content["content"] = page_content
    content["content_markdown"] = content_markdown

    # Truncate to first N words (analyst specifies; default 250 for HTML)
    cleaned_content = " ".join(page_content.split()[:250])
    extracted_metadata = extract_metadata_from_text(
        system_prompt=(
            # ← paste the system prompt provided by analyst
            "From the given text, extract the date of publication and document number if they exist."
        ),
        content=cleaned_content,
        url=url,
        schema=Metadata,
    )
    if extracted_metadata:
        metadata.update(extracted_metadata)

    metadata = format_metadata(metadata)
    content.update(metadata)
    return content
```

---

## Config (final stage — Pattern 1 & 2 only)

The final stage config references the method by name. Only needed when using a custom `_final` METHOD (Patterns 1 or 2 above). When using `need_prediction` (Pattern 0), the `parse_pdf` built-in is referenced directly and no special flags are needed.

```python
config_number = { # for example, if the last config was second, this would be third
    "agent": 5,
    "sleep": (2, 4),
    "type": CrawlerResponseTypeEnum.DICT,
    "kind": CrawlerKindEnum.METHOD,
    "method_name": "reasonable_name_final", # reasonable name should match portal you're working on, e.g usa_utah_courts_opinions_final and should always end with _final
    "regex": None,
    "allowed_domains": ["utcourts.gov"],
    "return_from_method": True,
    "repealed_laws": None,
    "fields": {
        "conf": None,
        "extract": None,
        "date_order": None,
        "decompose_list": None,
        "metadata_processor": None,
        "markdown_kind": None,
        "keyword_matching_type": KeywordMatchingType.IN_CONTEXT,
    },
    "process": None,
}
```

Do **not** put `lang`, `ocr`, or Gemini-related options inside `fields` — those belong inside the METHOD body.

---

## Word Count Guidelines

| Source type                   | Recommended slice | Rationale                                      |
| ----------------------------- | ----------------- | ---------------------------------------------- |
| PDF — dense legal text        | 400–500 words     | Cover preamble/header where dates appear       |
| PDF — gazette/gazette-style   | 300–400 words     | First page usually has all metadata            |
| HTML detail page              | 200–300 words     | Metadata is typically in the page header/intro |
| Very short text (< 200 words) | pass full content | No need to truncate                            |

Always use `" ".join(clean_text(text).split()[:N])` — not character slicing — so multi-space/newline noise is removed first.

---

## Integration Notes

- `extracted_metadata` is a plain `dict`; always guard with `if extracted_metadata:` before calling `.update()`.
- Keys from `extracted_metadata` that collide with keys already in `metadata` (e.g. `title` passed down from the listing stage) will **overwrite** the listing-stage value. If this is undesired, use a selective merge:
    ```python
    for key, value in (extracted_metadata or {}).items():
        if value and not metadata.get(key):
            metadata[key] = value
    ```
- `format_metadata` normalises date strings and strips `None` values; always call it **after** merging `extracted_metadata`.
- The function is **not idempotent** across prompts — changing the system prompt invalidates the cache for that URL.

---

## Checklist before submitting

### If using Pattern 0 (`need_prediction` in `fixed_metadata`)

- [ ] `"need_prediction": True` is in `fixed_metadata` of the BASIC listing/detail config
- [ ] `"fields"` dict is present with all field names → `"str"`
- [ ] `"system_prompt"` is present and specifies expected date format if any date field is requested
- [ ] `"page_no"` added if extraction should come from a page other than page 1
- [ ] The FINAL stage uses `"method_name": "parse_pdf"` (built-in) — no custom code written
- [ ] No `_final` custom method created for this portal for this purpose

### If using Pattern 1 or 2 (custom `_final` METHOD)

- [ ] Schema fields are all `Optional[str]` (unless guaranteed present)
- [ ] Schema class is defined **inside** the function
- [ ] System prompt is a single clear instruction sentence or short paragraph; date format specified if needed
- [ ] Content is truncated to the agreed word count via `" ".join(...split()[:N])`
- [ ] `if extracted_metadata:` guard is present before `.update()`
- [ ] `format_metadata` called after merge
- [ ] No `try/except` around the Gemini call
- [ ] Imports: `extract_metadata_from_text` from `jimmy_v4.utils.helpers`
- [ ] Config `fields` does NOT contain `lang`, `ocr`, or prompt keys
