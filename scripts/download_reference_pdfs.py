#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import socket
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request

try:
    from lxml import html as lxml_html
except ImportError:  # pragma: no cover - lxml is available in this environment
    lxml_html = None


USER_AGENT = "CodexReferencePdfDownloader/1.0 (+local)"
MIN_PDF_BYTES = 512
MAX_HTML_DEPTH = 2
CSV_FIELDS = [
    "key",
    "status",
    "filename",
    "title",
    "year",
    "entrytype",
    "doi",
    "url",
    "final_source_url",
    "method",
    "note",
]


@dataclass
class Entry:
    key: str
    entrytype: str
    title: str
    author: str
    year: str
    doi: str
    url: str
    eprint: str
    archiveprefix: str
    raw_fields: dict[str, str] = field(default_factory=dict)

    @property
    def clean_title(self) -> str:
        return bibtex_to_text(self.title)

    @property
    def clean_author(self) -> str:
        return bibtex_to_text(self.author)

    @property
    def first_author_surname(self) -> str:
        authors = [part.strip() for part in re.split(r"\band\b", self.clean_author, flags=re.I) if part.strip()]
        if not authors:
            return ""
        surname = authors[0].split(",")[0].strip()
        if "," not in authors[0]:
            pieces = authors[0].split()
            surname = pieces[-1] if pieces else authors[0]
        return normalize_text(surname)


@dataclass
class Attempt:
    method: str
    url: str
    outcome: str
    note: str


@dataclass
class DownloadResult:
    status: str
    filename: str
    final_source_url: str
    method: str
    note: str
    attempts: list[Attempt]
    resolved_doi: str = ""


class FetchError(RuntimeError):
    def __init__(self, url: str, status: int | None, reason: str):
        super().__init__(f"{url} -> {status or 'error'} {reason}")
        self.url = url
        self.status = status
        self.reason = reason


@dataclass
class HttpResponse:
    url: str
    status: int
    content_type: str
    data: bytes


class HttpClient:
    def __init__(self, retries: int, timeout: float):
        self.retries = retries
        self.timeout = timeout
        self.opener = request.build_opener()

    def fetch(self, url: str, *, accept: str = "*/*") -> HttpResponse:
        request_url = requote_url(url)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.7",
        }
        last_error: FetchError | None = None
        for attempt in range(self.retries + 1):
            try:
                req = request.Request(request_url, headers=headers)
                with self.opener.open(req, timeout=self.timeout) as response:
                    data = response.read()
                    content_type = response.headers.get_content_type() or response.headers.get("Content-Type", "")
                    return HttpResponse(
                        url=response.geturl(),
                        status=response.getcode(),
                        content_type=content_type,
                        data=data,
                    )
            except error.HTTPError as exc:
                body = b""
                try:
                    body = exc.read()
                except Exception:
                    body = b""
                reason = body[:120].decode("utf-8", errors="ignore").strip() or exc.reason
                last_error = FetchError(request_url, exc.code, str(reason))
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(min(2.0 * (attempt + 1), 6.0))
                    continue
                raise last_error
            except UnicodeEncodeError as exc:
                raise FetchError(request_url, None, f"URL encoding failed: {exc}") from exc
            except (TimeoutError, socket.timeout) as exc:
                last_error = FetchError(request_url, None, f"timeout: {exc}")
                if attempt < self.retries:
                    time.sleep(min(1.5 * (attempt + 1), 4.0))
                    continue
                raise last_error
            except error.URLError as exc:
                last_error = FetchError(request_url, None, str(exc.reason))
                if attempt < self.retries:
                    time.sleep(min(1.5 * (attempt + 1), 4.0))
                    continue
                raise last_error
        if last_error is not None:
            raise last_error
        raise FetchError(url, None, "unknown fetch error")

    def fetch_json(self, url: str) -> dict:
        response = self.fetch(url, accept="application/json,text/plain;q=0.9,*/*;q=0.8")
        try:
            return json.loads(response.data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise FetchError(url, response.status, f"invalid JSON: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public PDFs for all entries in a BibTeX file.")
    parser.add_argument("--bib", default="references.bib", help="BibTeX file to process.")
    parser.add_argument("--out", default="参考文献pdf", help="Output directory for PDFs and reports.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for HTTP requests.")
    parser.add_argument("--timeout", type=float, default=25.0, help="HTTP timeout in seconds.")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on number of entries to process.")
    return parser.parse_args()


def parse_bibtex(path: Path) -> list[Entry]:
    text = path.read_text(encoding="utf-8")
    entries: list[Entry] = []
    index = 0
    while True:
        start = text.find("@", index)
        if start == -1:
            break
        entrytype_start = start + 1
        while entrytype_start < len(text) and text[entrytype_start].isspace():
            entrytype_start += 1
        entrytype_end = entrytype_start
        while entrytype_end < len(text) and re.match(r"[\w-]", text[entrytype_end]):
            entrytype_end += 1
        entrytype = text[entrytype_start:entrytype_end].strip().lower()
        if not entrytype:
            index = start + 1
            continue
        cursor = entrytype_end
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] not in "{(":
            index = start + 1
            continue
        opening = text[cursor]
        closing = "}" if opening == "{" else ")"
        cursor += 1
        content_start = cursor
        depth = 1
        while cursor < len(text) and depth:
            char = text[cursor]
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
            cursor += 1
        content = text[content_start : cursor - 1]
        key, body = split_bib_key_body(content)
        fields = parse_bib_fields(body)
        entries.append(
            Entry(
                key=key,
                entrytype=entrytype,
                title=fields.get("title", ""),
                author=fields.get("author", ""),
                year=strip_non_year(fields.get("year", "")),
                doi=normalize_doi(fields.get("doi", "")),
                url=fields.get("url", "").strip(),
                eprint=fields.get("eprint", "").strip(),
                archiveprefix=fields.get("archiveprefix", "").strip(),
                raw_fields=fields,
            )
        )
        index = cursor
    return entries


def split_bib_key_body(content: str) -> tuple[str, str]:
    depth = 0
    in_quote = False
    for index, char in enumerate(content):
        if char == '"' and (index == 0 or content[index - 1] != "\\"):
            in_quote = not in_quote
        elif not in_quote:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == "," and depth == 0:
                key = content[:index].strip()
                body = content[index + 1 :]
                return key, body
    raise ValueError("BibTeX entry is missing its citation key separator")


def parse_bib_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    length = len(body)
    while index < length:
        while index < length and body[index] in " \t\r\n,":
            index += 1
        if index >= length:
            break
        name_start = index
        while index < length and re.match(r"[\w-]", body[index]):
            index += 1
        name = body[name_start:index].strip().lower()
        while index < length and body[index].isspace():
            index += 1
        if index >= length or body[index] != "=":
            while index < length and body[index] != ",":
                index += 1
            continue
        index += 1
        while index < length and body[index].isspace():
            index += 1
        value, index = parse_bib_value(body, index)
        fields[name] = collapse_ws(value)
    return fields


def parse_bib_value(body: str, index: int) -> tuple[str, int]:
    if index >= len(body):
        return "", index
    if body[index] == "{":
        depth = 1
        cursor = index + 1
        while cursor < len(body) and depth:
            if body[cursor] == "{":
                depth += 1
            elif body[cursor] == "}":
                depth -= 1
            cursor += 1
        return body[index + 1 : cursor - 1], cursor
    if body[index] == '"':
        cursor = index + 1
        while cursor < len(body):
            if body[cursor] == '"' and body[cursor - 1] != "\\":
                return body[index + 1 : cursor], cursor + 1
            cursor += 1
        return body[index + 1 :], len(body)
    cursor = index
    while cursor < len(body) and body[cursor] not in ",\r\n":
        cursor += 1
    return body[index:cursor], cursor


def strip_non_year(value: str) -> str:
    match = re.search(r"\d{4}", value)
    return match.group(0) if match else value.strip()


def collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def bibtex_to_text(value: str) -> str:
    text = value
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\_": "_",
        r"\#": "#",
        r"\$": "$",
        r"\L": "L",
        r"\l": "l",
        "~": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    patterns = [
        re.compile(r"\\[A-Za-z]+\*?\{([^{}]*)\}\{([^{}]*)\}"),
        re.compile(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}"),
        re.compile(r"\\[`'\"^~=\.uvHckbdtr]\s*\{?([A-Za-z])\}?"),
    ]
    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            new_text = pattern.sub(lambda match: match.group(match.lastindex or 0), text)
            if new_text != text:
                text = new_text
                changed = True
    text = re.sub(r"\\[A-Za-z]+", " ", text)
    text = text.replace("{", "").replace("}", "")
    return collapse_ws(text)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return collapse_ws(normalized)


def normalize_doi(value: str) -> str:
    doi = value.strip()
    if not doi:
        return ""
    doi = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.strip().strip("{}")


def infer_arxiv_pdf_url(entry: Entry) -> str:
    raw_candidates = [
        entry.url,
        entry.eprint,
        entry.raw_fields.get("journal", ""),
        entry.raw_fields.get("note", ""),
    ]
    for candidate in raw_candidates:
        if not candidate:
            continue
        candidate = candidate.strip()
        if "arxiv.org/abs/" in candidate.lower():
            return re.sub(r"/abs/", "/pdf/", candidate, flags=re.I).rstrip("/") + ".pdf"
        match = re.search(r"arxiv[:/ ](\d{4}\.\d{4,5}(?:v\d+)?)", candidate, flags=re.I)
        if match:
            return f"https://arxiv.org/pdf/{match.group(1)}.pdf"
        if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", candidate):
            return f"https://arxiv.org/pdf/{candidate}.pdf"
    return ""


def seed_urls(entry: Entry) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    if entry.url:
        urls.append((entry.url, "url"))
        urls.extend((candidate, "url_variant") for candidate in known_url_variants(entry.url))
    arxiv_pdf = infer_arxiv_pdf_url(entry)
    if arxiv_pdf:
        urls.append((arxiv_pdf, "arxiv"))
    return dedupe_pairs(urls)


def known_url_variants(url: str) -> list[str]:
    variants: list[str] = []
    lowered = url.lower().strip()
    if "aclanthology.org" in lowered and not lowered.endswith(".pdf"):
        variants.append(url.rstrip("/") + ".pdf")
    if "arxiv.org/abs/" in lowered:
        variants.append(re.sub(r"/abs/", "/pdf/", url, flags=re.I).rstrip("/") + ".pdf")
    return variants


def dedupe_pairs(items: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    output: list[tuple[str, str]] = []
    for url, method in items:
        normalized = normalize_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append((url, method))
    return output


def requote_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = parse.urlsplit(url.strip())
    except ValueError:
        return url.strip()
    if not parsed.scheme:
        return url.strip()
    path = parse.quote(parse.unquote(parsed.path), safe="/:@-._~!$&'()*+,;=")
    query = parse.quote(parse.unquote(parsed.query), safe="=&?/:@-._~!$&'()*+,;")
    fragment = parse.quote(parse.unquote(parsed.fragment), safe="=&?/:@-._~!$&'()*+,;")
    return parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, fragment))


def normalize_url(url: str) -> str:
    if not url:
        return ""
    requoted = requote_url(url)
    try:
        parsed = parse.urlsplit(requoted)
    except ValueError:
        return requoted
    path = parsed.path or "/"
    if not parsed.scheme:
        return requoted
    return parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def is_pdf_payload(data: bytes, content_type: str, url: str) -> bool:
    if data.lstrip().startswith(b"%PDF-"):
        return True
    lowered_type = (content_type or "").lower()
    lowered_url = url.lower()
    return "pdf" in lowered_type or lowered_url.endswith(".pdf")


def valid_pdf_bytes(data: bytes) -> bool:
    return len(data) >= MIN_PDF_BYTES and data.lstrip().startswith(b"%PDF-")


def valid_pdf_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_PDF_BYTES:
        return False
    with path.open("rb") as handle:
        header = handle.read(1024)
    return valid_pdf_bytes(header + (b"" if len(header) >= MIN_PDF_BYTES else b" " * MIN_PDF_BYTES))


def write_pdf(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".part")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def extract_pdf_links(base_url: str, html_bytes: bytes) -> list[str]:
    candidates: list[str] = []
    if lxml_html is None:
        pattern = rb"""https?://[^\s"'<>]+|/[^\s"'<>]+\.pdf[^\s"'<>]*"""
        for match in re.finditer(pattern, html_bytes, flags=re.I):
            raw = match.group(0).decode("utf-8", errors="ignore")
            if "pdf" in raw.lower():
                candidates.append(parse.urljoin(base_url, raw))
        return unique_urls(candidates)
    try:
        document = lxml_html.fromstring(html_bytes, base_url=base_url)
    except Exception:
        return []
    meta_names = {
        "citation_pdf_url",
        "eprints.document_url",
        "pdf_url",
    }
    for meta in document.xpath("//meta[@content]"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        if name in meta_names:
            candidates.append(parse.urljoin(base_url, meta.get("content", "")))
    for node in document.xpath("//link[@href] | //iframe[@src] | //embed[@src] | //object[@data]"):
        href = node.get("href") or node.get("src") or node.get("data") or ""
        if is_pdfish_href(href, ""):
            candidates.append(parse.urljoin(base_url, href))
    for anchor in document.xpath("//a[@href]"):
        href = anchor.get("href", "")
        label = collapse_ws(" ".join(anchor.itertext()))
        if is_pdfish_href(href, label):
            candidates.append(parse.urljoin(base_url, href))
    lowered = base_url.lower()
    if "aclanthology.org" in lowered and not lowered.endswith(".pdf"):
        candidates.insert(0, base_url.rstrip("/") + ".pdf")
    if "arxiv.org/abs/" in lowered:
        candidates.insert(0, re.sub(r"/abs/", "/pdf/", base_url, flags=re.I).rstrip("/") + ".pdf")
    return unique_urls(candidates)


def is_pdfish_href(href: str, label: str) -> bool:
    lowered_href = href.lower()
    lowered_label = label.lower()
    return (
        ".pdf" in lowered_href
        or "/pdf/" in lowered_href
        or "download" in lowered_href
        or "pdf" in lowered_label
    )


def unique_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for url in urls:
        normalized = normalize_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(url)
    return output


def crossref_work_url(doi: str) -> str:
    return f"https://api.crossref.org/works/{parse.quote(doi, safe='')}"


def openalex_doi_url(doi: str) -> str:
    doi_url = f"https://doi.org/{doi}"
    query = parse.urlencode({"filter": f"doi:{doi_url}", "per-page": 1})
    return f"https://api.openalex.org/works?{query}"


def crossref_title_search_url(title: str) -> str:
    query = parse.urlencode({"rows": 5, "query.title": title, "select": "DOI,title,author,published-print,published-online,issued"})
    return f"https://api.crossref.org/works?{query}"


def extract_crossref_year(item: dict) -> str:
    for key in ("published-print", "published-online", "issued"):
        part = item.get(key) or {}
        date_parts = part.get("date-parts") or []
        if date_parts and date_parts[0]:
            value = str(date_parts[0][0])
            if re.fullmatch(r"\d{4}", value):
                return value
    return ""


def crossref_best_match(entry: Entry, items: list[dict]) -> tuple[str, str, bool]:
    target_title = normalize_text(entry.clean_title)
    target_author = entry.first_author_surname
    scored: list[tuple[float, float, str, str, str]] = []
    for item in items:
        doi = normalize_doi(item.get("DOI", ""))
        title_values = item.get("title") or []
        candidate_title = " ".join(title_values).strip()
        normalized_candidate = normalize_text(candidate_title)
        if not doi or not normalized_candidate:
            continue
        similarity = difflib.SequenceMatcher(None, target_title, normalized_candidate).ratio()
        score = similarity
        candidate_year = extract_crossref_year(item)
        if entry.year and candidate_year:
            diff = abs(int(entry.year) - int(candidate_year))
            if diff == 0:
                score += 0.18
            elif diff == 1:
                score += 0.08
            elif diff > 2:
                score -= 0.15
        candidate_authors = item.get("author") or []
        if candidate_authors and target_author:
            family = normalize_text(candidate_authors[0].get("family", ""))
            if family and family == target_author:
                score += 0.08
        scored.append((score, similarity, doi, candidate_title, candidate_year))
    if not scored:
        return "", "Crossref title search returned no DOI candidates.", False
    scored.sort(reverse=True)
    best_score, best_similarity, best_doi, best_title, best_year = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1.0
    exact_title = normalize_text(best_title) == target_title
    if exact_title or best_score >= 0.83 or (best_similarity >= 0.72 and best_score - second_score >= 0.07):
        note = f"Matched DOI {best_doi} from title search (score={best_score:.2f}, year={best_year or 'n/a'})."
        return best_doi, note, False
    if best_score >= 0.72:
        note = f"Closest Crossref match looked plausible but ambiguous: {best_doi} ({best_title}, score={best_score:.2f})."
        return "", note, True
    note = f"Closest Crossref match was too weak: {best_doi} ({best_title}, score={best_score:.2f})."
    return "", note, False


def openalex_pdf_candidates(work: dict) -> list[str]:
    candidates: list[str] = []
    locations = []
    for key in ("best_oa_location", "primary_location"):
        value = work.get(key)
        if isinstance(value, dict):
            locations.append(value)
    locations.extend(location for location in (work.get("locations") or []) if isinstance(location, dict))
    for location in locations:
        pdf_url = location.get("pdf_url")
        landing = location.get("landing_page_url")
        if pdf_url:
            candidates.append(pdf_url)
        if landing:
            candidates.append(landing)
    oa_url = (work.get("open_access") or {}).get("oa_url")
    if oa_url:
        candidates.append(oa_url)
    return unique_urls(candidates)


def collect_manual_keywords(entry: Entry, resolved_doi: str) -> str:
    parts = [entry.clean_title]
    if entry.clean_author:
        parts.append(entry.clean_author.split(" and ")[0])
    if entry.year:
        parts.append(entry.year)
    if resolved_doi:
        parts.append(resolved_doi)
    return " | ".join(part for part in parts if part)


def file_name_for_key(key: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]+', "_", key).strip(" .")
    return f"{safe or 'reference'}.pdf"


def try_fetch_candidate(
    client: HttpClient,
    entry: Entry,
    url: str,
    method: str,
    destination: Path,
    attempts: list[Attempt],
    seen_urls: set[str],
    evidence: dict[str, bool],
    depth: int = 0,
) -> DownloadResult | None:
    normalized = normalize_url(url)
    if not normalized or normalized in seen_urls or depth > MAX_HTML_DEPTH:
        return None
    seen_urls.add(normalized)
    try:
        response = client.fetch(url, accept="application/pdf,text/html;q=0.9,*/*;q=0.8")
    except FetchError as exc:
        if exc.status in {401, 402, 403}:
            evidence["record_found"] = True
        attempts.append(Attempt(method, url, "fetch_error", f"{exc.status or 'network'} {exc.reason}"))
        return None
    if is_pdf_payload(response.data, response.content_type, response.url):
        if valid_pdf_bytes(response.data):
            write_pdf(destination, response.data)
            attempts.append(Attempt(method, response.url, "downloaded", f"{len(response.data)} bytes"))
            return DownloadResult(
                status="downloaded",
                filename=destination.name,
                final_source_url=response.url,
                method=method,
                note=f"Downloaded via {method}.",
                attempts=attempts,
            )
        evidence["invalid_pdf"] = True
        attempts.append(Attempt(method, response.url, "invalid_pdf", "Response looked like PDF but failed validation."))
        return None
    links = extract_pdf_links(response.url, response.data)
    if links:
        attempts.append(Attempt(method, response.url, "landing_page", f"Found {len(links)} PDF candidates."))
        for candidate in links:
            result = try_fetch_candidate(
                client,
                entry,
                candidate,
                f"{method}->landing",
                destination,
                attempts,
                seen_urls,
                evidence,
                depth + 1,
            )
            if result is not None:
                return result
    else:
        content = response.data[:200].decode("utf-8", errors="ignore").strip()
        note = "Landing page did not expose a PDF link." if content else "Response was not a PDF."
        attempts.append(Attempt(method, response.url, "not_pdf", note))
    return None


def try_doi_pipeline(
    client: HttpClient,
    entry: Entry,
    doi: str,
    destination: Path,
    attempts: list[Attempt],
    seen_urls: set[str],
    evidence: dict[str, bool],
    method_prefix: str,
) -> tuple[DownloadResult | None, bool]:
    record_found = False
    work_url = crossref_work_url(doi)
    try:
        payload = client.fetch_json(work_url)
        message = payload.get("message") or {}
        record_found = True
        evidence["record_found"] = True
        crossref_candidates: list[tuple[str, str]] = []
        for link in message.get("link") or []:
            candidate_url = link.get("URL") or link.get("url")
            if candidate_url:
                crossref_candidates.append((candidate_url, f"{method_prefix}:crossref_link"))
        landing_url = message.get("URL") or f"https://doi.org/{doi}"
        crossref_candidates.append((landing_url, f"{method_prefix}:crossref_landing"))
        for candidate_url, candidate_method in dedupe_pairs(crossref_candidates):
            result = try_fetch_candidate(
                client,
                entry,
                candidate_url,
                candidate_method,
                destination,
                attempts,
                seen_urls,
                evidence,
            )
            if result is not None:
                result.resolved_doi = doi
                return result, True
        attempts.append(Attempt(f"{method_prefix}:crossref_record", work_url, "checked", "Crossref record found but no downloadable PDF."))
    except FetchError as exc:
        attempts.append(Attempt(f"{method_prefix}:crossref_record", work_url, "fetch_error", f"{exc.status or 'network'} {exc.reason}"))
        landing_url = f"https://doi.org/{doi}"
        result = try_fetch_candidate(
            client,
            entry,
            landing_url,
            f"{method_prefix}:doi_landing",
            destination,
            attempts,
            seen_urls,
            evidence,
        )
        if result is not None:
            result.resolved_doi = doi
            return result, True
    openalex_url = openalex_doi_url(doi)
    try:
        payload = client.fetch_json(openalex_url)
        results = payload.get("results") or []
        if results:
            record_found = True
            evidence["record_found"] = True
            for candidate_url in openalex_pdf_candidates(results[0]):
                result = try_fetch_candidate(
                    client,
                    entry,
                    candidate_url,
                    f"{method_prefix}:openalex",
                    destination,
                    attempts,
                    seen_urls,
                    evidence,
                )
                if result is not None:
                    result.resolved_doi = doi
                    return result, True
            attempts.append(Attempt(f"{method_prefix}:openalex", openalex_url, "checked", "OpenAlex had no public PDF URL."))
        else:
            attempts.append(Attempt(f"{method_prefix}:openalex", openalex_url, "not_found", "OpenAlex returned no work record."))
    except FetchError as exc:
        attempts.append(Attempt(f"{method_prefix}:openalex", openalex_url, "fetch_error", f"{exc.status or 'network'} {exc.reason}"))
    return None, record_found


def process_entry(client: HttpClient, entry: Entry, output_dir: Path) -> DownloadResult:
    destination = output_dir / file_name_for_key(entry.key)
    attempts: list[Attempt] = []
    seen_urls: set[str] = set()
    evidence = {
        "record_found": False,
        "invalid_pdf": False,
        "manual_review": False,
    }
    resolved_doi = entry.doi
    if destination.exists() and valid_pdf_file(destination):
        return DownloadResult(
            status="skipped_existing",
            filename=destination.name,
            final_source_url="",
            method="existing",
            note="Existing PDF passed validation and was kept.",
            attempts=attempts,
            resolved_doi=resolved_doi,
        )
    if destination.exists():
        attempts.append(Attempt("existing", str(destination), "invalid_pdf", "Existing file failed validation and will be replaced if possible."))
        evidence["invalid_pdf"] = True
    for candidate_url, method in seed_urls(entry):
        result = try_fetch_candidate(
            client,
            entry,
            candidate_url,
            method,
            destination,
            attempts,
            seen_urls,
            evidence,
        )
        if result is not None:
            result.resolved_doi = resolved_doi
            return result
    if resolved_doi:
        result, record_found = try_doi_pipeline(
            client,
            entry,
            resolved_doi,
            destination,
            attempts,
            seen_urls,
            evidence,
            "doi",
        )
        evidence["record_found"] = evidence["record_found"] or record_found
        if result is not None:
            return result
    if entry.clean_title:
        search_url = crossref_title_search_url(entry.clean_title)
        try:
            payload = client.fetch_json(search_url)
            items = (payload.get("message") or {}).get("items") or []
            matched_doi, note, ambiguous = crossref_best_match(entry, items)
            if ambiguous:
                evidence["manual_review"] = True
            attempts.append(Attempt("crossref_title_search", search_url, "checked", note))
            if matched_doi:
                resolved_doi = matched_doi
                result, record_found = try_doi_pipeline(
                    client,
                    entry,
                    matched_doi,
                    destination,
                    attempts,
                    seen_urls,
                    evidence,
                    "crossref_title_search",
                )
                evidence["record_found"] = evidence["record_found"] or record_found
                if result is not None:
                    return result
        except FetchError as exc:
            attempts.append(Attempt("crossref_title_search", search_url, "fetch_error", f"{exc.status or 'network'} {exc.reason}"))
    status = "not_found"
    note = "No public PDF source was found."
    if evidence["invalid_pdf"]:
        status = "invalid_pdf"
        note = "Only invalid PDF payloads or corrupted existing files were found."
    elif evidence["manual_review"]:
        status = "manual_review"
        note = "Closest title-based match was ambiguous and needs human review."
    elif evidence["record_found"] or resolved_doi:
        status = "paywalled_or_no_public_pdf"
        note = "A bibliographic record was found, but no public PDF was reachable."
    return DownloadResult(
        status=status,
        filename=destination.name,
        final_source_url="",
        method="failed",
        note=note,
        attempts=attempts,
        resolved_doi=resolved_doi,
    )


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_missing_clues(path: Path, failures: list[tuple[Entry, dict[str, str], list[Attempt]]]) -> None:
    lines = ["# Missing or Manual-Review References", ""]
    if not failures:
        lines.extend(["All entries resolved to a valid PDF.", ""])
    for entry, manifest_row, attempts in failures:
        lines.append(f"## {entry.key}")
        lines.append(f"- Status: {manifest_row['status']}")
        lines.append(f"- Title: {entry.clean_title or entry.title or '(missing title)'}")
        lines.append(f"- Authors: {entry.clean_author or entry.author or '(missing authors)'}")
        lines.append(f"- Year: {entry.year or '(missing year)'}")
        lines.append(f"- Entry type: {entry.entrytype}")
        lines.append(f"- DOI: {manifest_row['doi'] or '(none)'}")
        lines.append(f"- URL: {entry.url or '(none)'}")
        attempted = ", ".join(f"{item.method}:{item.outcome}" for item in attempts) or "(none)"
        lines.append(f"- Attempted methods: {attempted}")
        lines.append(f"- Notes: {manifest_row['note']}")
        lines.append(f"- Suggested search keywords: {collect_manual_keywords(entry, manifest_row['doi']) or entry.key}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_summary(entries: list[Entry], manifest_rows: list[dict[str, str]]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for row in manifest_rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    distribution = {"doi_only": 0, "url_only": 0, "both": 0, "none": 0}
    for entry in entries:
        has_doi = bool(entry.doi)
        has_url = bool(entry.url)
        if has_doi and has_url:
            distribution["both"] += 1
        elif has_doi:
            distribution["doi_only"] += 1
        elif has_url:
            distribution["url_only"] += 1
        else:
            distribution["none"] += 1
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_entries": len(entries),
        "status_counts": counts,
        "metadata_distribution": distribution,
    }


def persist_reports(
    output_dir: Path,
    entries: list[Entry],
    manifest_rows: list[dict[str, str]],
    failures: list[tuple[Entry, dict[str, str], list[Attempt]]],
) -> None:
    write_manifest(output_dir / "manifest.csv", manifest_rows)
    write_missing_clues(output_dir / "missing_clues.md", failures)
    summary = build_summary(entries, manifest_rows)
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    args = parse_args()
    bib_path = Path(args.bib)
    output_dir = Path(args.out)
    if not bib_path.exists():
        print(f"BibTeX file not found: {bib_path}", file=sys.stderr)
        return 1
    entries = parse_bibtex(bib_path)
    if args.limit > 0:
        entries = entries[: args.limit]
    client = HttpClient(retries=max(args.retries, 0), timeout=max(args.timeout, 1.0))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []
    failures: list[tuple[Entry, dict[str, str], list[Attempt]]] = []
    for index, entry in enumerate(entries, start=1):
        print(f"[{index}/{len(entries)}] {entry.key}", flush=True)
        try:
            result = process_entry(client, entry, output_dir)
        except Exception as exc:
            result = DownloadResult(
                status="manual_review",
                filename=file_name_for_key(entry.key),
                final_source_url="",
                method="exception",
                note=f"Unhandled error: {type(exc).__name__}: {exc}",
                attempts=[],
                resolved_doi=entry.doi,
            )
        row = {
            "key": entry.key,
            "status": result.status,
            "filename": result.filename,
            "title": entry.clean_title,
            "year": entry.year,
            "entrytype": entry.entrytype,
            "doi": result.resolved_doi or entry.doi,
            "url": entry.url,
            "final_source_url": result.final_source_url,
            "method": result.method,
            "note": result.note,
        }
        manifest_rows.append(row)
        if result.status not in {"downloaded", "skipped_existing"}:
            failures.append((entry, row, list(result.attempts)))
        persist_reports(output_dir, entries, manifest_rows, failures)
    summary = build_summary(entries, manifest_rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
