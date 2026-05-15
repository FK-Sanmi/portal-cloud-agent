---
applyTo: "**"
---

# Portal Review Instructions

DO NOT DEPEND ON THE EDITOR OPENED FILES ONLY. MUST USE GREP SEARCH TO FIND ALL RELEVANT FILES.

You may be given a portal ID enum such as `BELGIUM_VLAAMS_PARLEMENT`, a plain-English name such as `Belgium Vlaams Parliament`, or a numeric portal ID such as `329`. Resolve the portal through `jimmy_v4/constants.py` and `jimmy_v4/management/seed.py`, then review every related configuration file.

## Review Mode

Use one of these modes inside the same workflow instead of separate prompts:

- `critical`: Only report violations of the critical checklists below and hard runtime bugs such as missing methods, invalid references, or invalid config structure that will break execution. Ignore style, refactoring, and non-critical performance comments.
- `full`: Report all correctness issues covered by this prompt, including broader review findings and suggested fixes.

Default to `full` unless the request explicitly asks for a critical-only review.

## Discovery Procedure

Follow this order strictly:

1. Resolve the portal from `jimmy_v4/constants.py` and `jimmy_v4/management/seed.py`.
2. Ensure `jimmy_v4/management/seed.py` contains an entry for the resolved portal enum with at least `id`, `name`, `base_url`, and `jurisdiction`. Other keys may exist. If `small_crawl` is present, the line must be commented out.
3. Convert the resolved portal enum to lowercase.
4. Grep `jimmy_v4/portal_configurations/` for all configuration files whose names start with that lowercase value. Review all of them.
5. Read `jimmy_v4/schemas.py` as the schema reference for configuration shape.
6. For every configuration with `"kind": CrawlerKindEnum.METHOD`, identify the helper methods in `jimmy_v4/country_crawlers/<country_or_state>.py`, unless the method is `parse_pdf`, `parse_doc`, or `parse_pdf_or_doc`.
7. Review configuration files first, then custom methods.

## Files To Review

1. Portal configuration files in `jimmy_v4/portal_configurations/` whose filename starts with the resolved lowercase portal enum.
2. The matching country crawler file in `jimmy_v4/country_crawlers/` if any config uses `CrawlerKindEnum.METHOD`.
3. `jimmy_v4/schemas.py` for schema constraints.

## Configuration Rules

### Config List Ordering

- The `..._configurations["config"]` list must be in reverse pipeline order: `[final_config, ..., first_config]`.
- The first executed config must have `"first_config": True`.

### ID Assignment

- Config entries must not have a manually assigned `id`.
- IDs are auto-assigned via `"_config_module": __name__.split(".")[-1]`.

### Type Rules

- Only the last config in execution order may have `"type": CrawlerResponseTypeEnum.DICT`.
- All earlier configs must have `"type": CrawlerResponseTypeEnum.LIST`.

### Allowed Domains

- `"allowed_domains"` must be a list of URL substrings, not full URLs.

### Pagination

- If pagination is present and `next_page` is not `None`, `max_pagination` must be present and must be set in a way that respects `is_small_crawl`.

### Method Names

- If `"kind": CrawlerKindEnum.METHOD`, `"method_name"` must be present.
- That method must exist in the correct `jimmy_v4/country_crawlers/<country_or_state>.py` file.

### Process Methods

- If `"process"` is not `None`, each name must match a method in `AfterCrawlingProcessServices` in `jimmy_v4/data_processor_service.py`.
- These are distinct from `method_name` and `process_name`.

### Fixed Metadata vs XPath Metadata

- `"fixed_metadata"` may contain only literal values.
- `"metadata_conf"` may contain only XPath expressions.
- The only accepted law-type key is `type_of_law`.

### XPath Rules In `conf`

- Inside config `"conf"`, `xpath` may be absolute.
- Inside config `"conf"`, `url` must be relative such as `.//a/@href` or `./@href`.
- Inside config `"conf"`, every `metadata_conf` XPath must be relative and start with `./` or `.//`.
- Exception: if a `metadata_conf` expression starts with an XPath function such as `concat()`, `substring()`, or `normalize-space()`, it is valid only when its node references are relative.
- `pre_append_url` is a top-level config key, not a key inside a `conf` item.

### XPath Rules Outside `conf`

- `metadata_conf` XPaths defined outside config `"conf"` are expected to be absolute, not relative.

### Metadata Requirements

- `issuing_authority`, `title`, and `type_of_law` must be guaranteed by the end of the pipeline.
- If metadata is extracted in the final config and a metadata XPath ends with `//text`, the corresponding extract mode must be `extract`, not `extract_first`.

### Language

- If the portal has non-English PDFs, the correct `lang` must be provided in `fixed_metadata` or otherwise guaranteed before PDF parsing.
- Any `lang` value must match the real portal language and a supported PaddleOCR language.
- If `lang` is passed through `fixed_metadata` and is not in `METADATA_TO_KEEP`, it must be removed in the final METHOD via `metadata.pop("lang", None)` or not carried in metadata at all.

### URL Lists And Labels

- Every item in a `urls` list must include a label comment such as `# Link 2`.
- If there is more than one `urls` entry and more than one dict in `conf`, each `conf` item must be labeled to indicate which URL it belongs to.

### Prediction And Extraction Fields

- If `"need_prediction": True` is present, `"system_prompt"` must also be present.
- If `"need_prediction": True` is present, at least one of `"fields"` or `"optional_fields"` must also be present.
- Any prediction or LLM prompt that returns dates must specify the expected date format explicitly, for example `DD/MM/YYYY`.
- For pipelines ending with `"method_name": "parse_pdf"`, fields such as `ocr`, `lang`, `need_prediction`, `system_prompt`, and `fields` must be established before the final parse step.

### Other Config Validations

- No invalid expression may appear in `decompose_list`.
- The last dict in the config list must not contain `"disabled": True`.
- The last dict in the config list must not contain `"is_import": False`.
- Shared fields such as `lang` or `is_authority` should be assigned in a loop rather than repeated on every dict when multiple entries share the same value.

## Custom Method Rules

Apply these to every custom method in `jimmy_v4/country_crawlers/<country_or_state>.py`.

### Exceptions And Control Flow

- No `try/except` blocks anywhere in custom methods, including around API calls.

### Timing And Browser Actions

- Do not use fixed `time.sleep()` values. All sleeps must use `random.randint(...)`.
- Every `webdriver.get()` call should be followed by a random sleep.
- Do not use `.click()` to simulate clicks. Use `webdriver.execute_script("arguments[0].click();", element)`.

### HTML And Final Content Extraction

- HTML extraction must use `clean_text` together with `convert_to_markdown`, not raw `get_text()` alone.
- In `_final` methods that handle HTML pages, locate the main content element with `webdriver.find_element(By.XPATH, ...)`, not `scrapy_res.xpath(...).get()`.
- If a `_final` method extracts a PDF link from the webpage, it must update `content["url"]` to the PDF URL.

### Small Crawl Behavior

- Small crawl logic must use `get_date_range(occurence)`, not `get_previous_seven_days()`.

### Requests Usage

- Every `requests` call must include a `headers` parameter containing a `user-agent` key.
- Every `requests` call must include `proxies={"http": PROXY_URL, "https": PROXY_URL}` and `verify=False`.
- Failed `requests` calls must raise an exception.

### URL Construction

- Do not use f-strings or `+` to concatenate URLs.
- Always use `urljoin(base, path)`.

### METHOD Justification

- Do not use a custom final METHOD that only wraps `parse_pdf_file_by_downloading` plus `format_metadata`; use `"method_name": "parse_pdf"` instead.
- Do not use METHOD when a BASIC config with static URLs and XPath extraction would work.
- Do not add a separate intermediate step solely to collect a single PDF link from a page when the first step can point directly to that PDF URL.
- If paginated results are capped, do not rely on plain page-counter pagination without date or filter chunking.

### Method Hygiene

- Remove dead methods that are no longer referenced by any config.
- Do not define nested helper functions inside method bodies.

## XPath Validation Inside METHOD Bodies

When a METHOD builds internal `confs` for helpers like `extract_page_data_with_xpath()` or `fetch_pagination_data()`:

- `url` must still be relative, using `.//`, `./`, or `@` form.
- `metadata_conf` XPaths must remain relative to the container element.
- `pre_append_url` may appear inside these internal method confs.

## Metadata Pipeline Behavior

After each non-final stage, accumulated scanner metadata is merged into every result via:

```python
result["metadata"].update({k: v for k, v in scanner.metadata.items() if v is not None})
```

This means earlier non-`None` metadata wins in non-final stages. A later non-final stage can add new keys, but it cannot reliably override an already-established metadata value.

A METHOD receives `metadata = scanner.metadata.copy()`, so do not flag a method only because it does not manually merge inherited metadata back into each result.

The final-stage METHOD is exempt from metadata locking. It may normalize, replace, or clean metadata before producing the saved document.

Check `format_metadata(metadata)` before claiming metadata loss is a bug; it removes non-string values and normalizes string fields.

## Review Strategy

1. Read the config list in execution order by starting from the last listed config.
2. Trace metadata introduced at each stage through `fixed_metadata`, `metadata_conf`, and custom METHOD logic.
3. Verify canonical metadata fields are present by the end of the pipeline.
4. Verify non-final stages do not appear to change already-locked metadata fields.
5. Read helper methods when a METHOD is responsible for metadata or content extraction.

## Output Contract

### Critical Mode Output

- Report only critical checklist violations and hard runtime bugs.
- Provide a numbered list.
- Use this exact format for each issue:

```text
[Issue <number>] : <relative_file_path>:<line_number> or <line_start>-<line_end> : <brief explanation>, violates <checklist item number>
```

### Full Mode Output

- Present findings first.
- Keep summaries brief.
- If issues are found, include corrected code snippets only for the affected files.
- If no issues are found, respond with `No issues found.`

## Final Checklist

- All config entries are listed in reverse pipeline order and the first executed entry has `first_config: True`
- No manual `id` field exists and `_config_module` is present
- Only the final config returns `DICT`; earlier ones return `LIST`
- `allowed_domains` contains substrings, not full URLs
- `max_pagination` is present when pagination is used
- All `method_name` and `process` references resolve correctly
- `fixed_metadata` contains literals only and `metadata_conf` contains XPath only
- `type_of_law` is used instead of aliases such as `type_of_document`
- `url` and relative `metadata_conf` XPaths inside `conf` are correctly scoped
- Required metadata fields exist by the end of the pipeline
- `lang` usage is correct for non-English PDF flows
- Prediction prompts include companion fields and explicit date formats
- `decompose_list` contains only valid expressions
- Final config does not use `disabled=True` or `is_import=False`
- Custom methods avoid `try/except`, fixed sleeps, direct `.click()`, raw HTML extraction, and URL concatenation
- Requests use `headers`, `user-agent`, proxies, `verify=False`, and raise on failure
- METHOD usage is justified and no dead or nested helper methods remain

Use grep search extensively. Read all relevant files before concluding.
