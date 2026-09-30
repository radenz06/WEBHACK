#!/usr/bin/env python3
#depelongper_denzyx
import base64
import csv
import gzip
import io
import json
import os
import random
import re
import shutil
import signal
import socket
import sqlite3
import ssl
import sys
import textwrap
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from html import escape as html_escape, unescape
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import (
    parse_qs, parse_qsl, quote, quote_plus, unquote, urlencode, urljoin,
    urlparse, urlunparse,
)
from urllib.request import (
    HTTPCookieProcessor, Request, build_opener,
)

VERSION = "4.0.1"
AUTHOR = "denzyx"
CODENAME = "Terminal Dorking Engine Ultimate Hollywood"

THREADS = int(os.environ.get("DORK_THREADS", "15"))
TIMEOUT = int(os.environ.get("DORK_TIMEOUT", "20"))
RETRIES = int(os.environ.get("DORK_RETRIES", "2"))
RETRY_BACKOFF = float(os.environ.get("DORK_BACKOFF", "1.5"))
CACHE_ENABLED = os.environ.get("DORK_CACHE", "1").strip() in ("1", "true", "yes", "on")
CACHE_TTL = int(os.environ.get("DORK_CACHE_TTL", "600"))
CACHE_MAX = int(os.environ.get("DORK_CACHE_MAX", "2048"))
DEBUG = os.environ.get("DORK_DEBUG", "0").strip() in ("1", "true", "yes", "on")
WAF_BYPASS = os.environ.get("DORK_WAF", "1").strip() in ("1", "true", "yes", "on")
VERIFY_LIVE = os.environ.get("DORK_VERIFY", "1").strip() in ("1", "true", "yes", "on")
ENRICH_ENABLED = os.environ.get("DORK_ENRICH", "1").strip() in ("1", "true", "yes", "on")
CINEMATIC_MODE = os.environ.get("DORK_CINEMATIC", "1").strip() in ("1", "true", "yes", "on")

_BASE_UA = os.environ.get(
    "DORK_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36",
)

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"

SEVERITY_ORDER = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
    "other": 0,
}

SEVERITY_COLORS = {
    "critical": BRIGHT_RED,
    "high": BRIGHT_RED,
    "medium": BRIGHT_YELLOW,
    "low": BRIGHT_BLUE,
    "info": BRIGHT_CYAN,
    "other": DIM,
}

SEVERITY_LABELS = {
    "critical": "CRIT",
    "high": "HIGH",
    "medium": "MED",
    "low": "LOW",
    "info": "INFO",
    "other": "----",
}

BANNER_ART = [
    "   ____   ____    _    _   _ ",
    "  / ___| / ___|  / \\  | \\ | |",
    "  \\___ \\| |     / _ \\ |  \\| |",
    "   ___) | |___ / ___ \\| |\\  |",
    "  |____/ \\____/_/   \\_\\_| \\_|",
]

BANNER_SUB = [
    "  ============================================================",
    "        		     S C A N N E R",
    "  ============================================================",
]

def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


_COLOR = _color_enabled()


def c(code: str) -> str:
    return code if _COLOR else ""


PRINT_LOCK = threading.Lock()


def term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 100


def term_height() -> int:
    try:
        return os.get_terminal_size().lines
    except OSError:
        return 30


def visible_len(s: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def pad_visible(s: str, width: int) -> str:
    vl = visible_len(s)
    if vl >= width:
        return s
    return s + " " * (width - vl)


def truncate_visible(s: str, width: int) -> str:
    if visible_len(s) <= width:
        return s
    plain = re.sub(r"\033\[[0-9;]*m", "", s)
    return plain[: max(0, width - 3)] + "..."


def clear_screen() -> None:
    with PRINT_LOCK:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def info(msg: str) -> None:
    with PRINT_LOCK:
        print(f"{c(BRIGHT_CYAN)}[i]{c(RESET)} {msg}")


def success(msg: str) -> None:
    with PRINT_LOCK:
        print(f"{c(BRIGHT_GREEN)}[+]{c(RESET)} {msg}")


def warning(msg: str) -> None:
    with PRINT_LOCK:
        print(f"{c(BRIGHT_YELLOW)}[!]{c(RESET)} {msg}")


def error(msg: str) -> None:
    with PRINT_LOCK:
        print(f"{c(BRIGHT_RED)}[-]{c(RESET)} {msg}")


def ask(prompt: str) -> str:
    try:
        return input(f"{c(BRIGHT_MAGENTA)}[?]{c(RESET)} {prompt}").strip()
    except EOFError:
        return ""


def line_rule(label: str = "", char: str = "=") -> None:
    cols = term_width()
    if label:
        lead = f"{c(BRIGHT_CYAN)}{char * 3}{c(RESET)} "
        text = f"{c(BOLD)}{c(BRIGHT_WHITE)}{label}{c(RESET)}"
        tail_len = max(0, cols - visible_len(lead) - visible_len(text) - 1)
        print(f"{lead}{text} {c(BRIGHT_CYAN)}{char * tail_len}{c(RESET)}")
    else:
        print(f"{c(BRIGHT_CYAN)}{char * cols}{c(RESET)}")


def section_header(title: str, color: str = BRIGHT_CYAN) -> None:
    print()
    line_rule(title, "=")


def pill(text: str, bg: str, fg: str = BRIGHT_WHITE) -> str:
    return f"{c(bg)}{c(fg)} {text} {c(RESET)}"


def badge(sev: str) -> str:
    color = SEVERITY_COLORS.get(sev, DIM)
    label = SEVERITY_LABELS.get(sev, "----")
    return f"{c(color)}[{label}]{c(RESET)}"


def typewriter(text: str, delay: float = 0.012, color: str = "") -> None:
    if not _COLOR:
        print(text)
        return
    with PRINT_LOCK:
        if color:
            sys.stdout.write(c(color))
        for ch in text:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(delay)
        if color:
            sys.stdout.write(c(RESET))
        sys.stdout.write("\n")
        sys.stdout.flush()


def matrix_rain(duration: float = 1.2, density: int = 3) -> None:
    if not _COLOR:
        return
    cols = term_width()
    rows = min(term_height(), 20)
    chars = "01#%@$&*!?<>/\\|abcdefABCDEF"
    grid = [[random.choice(chars) for _ in range(cols)] for _ in range(rows)]
    end = time.time() + duration
    with PRINT_LOCK:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    try:
        while time.time() < end:
            with PRINT_LOCK:
                frame = []
                for r in range(rows):
                    line = ""
                    for col in range(cols):
                        ch = grid[r][col]
                        if random.random() < 0.02:
                            grid[r][col] = random.choice(chars)
                            line += f"{c(BRIGHT_GREEN)}{ch}{c(RESET)}"
                        elif random.random() < 0.1:
                            line += f"{c(DIM)}{ch}{c(RESET)}"
                        else:
                            line += f"{c(GREEN)}{ch}{c(RESET)}"
                    frame.append(line)
                sys.stdout.write("\033[H" + "\n".join(frame))
                sys.stdout.flush()
            time.sleep(0.06)
    finally:
        with PRINT_LOCK:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()


def cinematic_boot() -> None:
    if not CINEMATIC_MODE:
        return
    clear_screen()
    print()
    print()
    print()
    matrix_rain(duration=1.0)

    clear_screen()
    cols = term_width()
    width = min(cols, 60)
    for line in BANNER_ART:
        padded = line.center(width)
        with PRINT_LOCK:
            sys.stdout.write(f"{c(BRIGHT_CYAN)}{padded}{c(RESET)}\n")
            sys.stdout.flush()
        time.sleep(0.08)

    for line in BANNER_SUB:
        padded = line.center(width)
        with PRINT_LOCK:
            sys.stdout.write(f"{c(BRIGHT_MAGENTA)}{padded}{c(RESET)}\n")
            sys.stdout.flush()
        time.sleep(0.1)

    print()
    time.sleep(0.15)

    steps = [
        "menghubungkan ke terminal segelintir",
        "memuat database TLD",
        "memuat modul search engine",
        "menginisialisasi WAF bypass",
        "mengaktifkan cache layer",
        "menyiapkan live scanner",
        "terminal siap digunakan",
    ]
    for text in steps:
        with PRINT_LOCK:
            sys.stdout.write(f"{c(BRIGHT_CYAN)}  >{c(RESET)} {text} ")
            sys.stdout.flush()
        for _ in range(3):
            with PRINT_LOCK:
                sys.stdout.write(f"{c(BRIGHT_YELLOW)}.{c(RESET)}")
                sys.stdout.flush()
            time.sleep(0.06)
        with PRINT_LOCK:
            sys.stdout.write(f" {c(BRIGHT_GREEN)}[OK]{c(RESET)}\n")
            sys.stdout.flush()
        time.sleep(0.12)

    print()
    time.sleep(0.25)


_DEFAULT_PORTS = {"http": 80, "https": 443}
_SAFE_QUERY_CHARS = ":/?&=#%+@;,[]{}|\\^~`<>\"'"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return url
    try:
        p = urlparse(url)
    except ValueError:
        return url
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    if not host:
        return url
    port = p.port
    netloc = host
    if port and _DEFAULT_PORTS.get(scheme) != port:
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", p.path) if p.path else ""
    if not path:
        path = "/"
    try:
        query_pairs = parse_qsl(p.query, keep_blank_values=False)
        query_pairs.sort()
        query = urlencode(query_pairs, safe=_SAFE_QUERY_CHARS) if query_pairs else ""
    except (ValueError, TypeError):
        query = p.query
    return urlunparse((scheme, netloc, path, "", query, ""))


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 "
    "Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
]

WAF_BYPASS_HEADERS_POOL = [
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded-For": "10.0.0.1"},
    {"X-Forwarded-For": "192.168.1.1"},
    {"X-Real-IP": "127.0.0.1"},
    {"X-Originating-IP": "127.0.0.1"},
    {"X-Remote-IP": "127.0.0.1"},
    {"X-Remote-Addr": "127.0.0.1"},
    {"X-Client-IP": "127.0.0.1"},
    {"X-Host": "localhost"},
    {"X-Forwarded-Host": "localhost"},
    {"X-Forwarded-Server": "localhost"},
    {"X-Original-URL": "/"},
    {"X-Rewrite-URL": "/"},
    {"X-HTTP-Method-Override": "GET"},
    {"X-HTTP-Method": "GET"},
    {"X-Method-Override": "GET"},
    {"CF-Connecting-IP": "127.0.0.1"},
    {"True-Client-IP": "127.0.0.1"},
    {"Forwarded": "for=127.0.0.1;proto=https"},
    {"X-ProxyUser-Ip": "127.0.0.1"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
    {"X-Originating-URL": "/"},
    {"Referer": "https://www.google.com/"},
    {"Origin": "https://www.google.com"},
]

WAF_ENCODERS = [
    ("plain", lambda s: s),
    ("url", lambda s: quote(s, safe="")),
    ("double_url", lambda s: quote(quote(s, safe=""), safe="")),
    ("hex", lambda s: "".join(f"%{ord(ch):02x}" for ch in s)),
    ("html", lambda s: "".join(f"&#{ord(ch)};" for ch in s)),
    ("html_hex", lambda s: "".join(f"&#x{ord(ch):x};" for ch in s)),
    ("unicode", lambda s: "".join(f"\\u{ord(ch):04x}" for ch in s)),
    ("case", lambda s: "".join(
        ch.upper() if i % 2 else ch.lower() for i, ch in enumerate(s)
    )),
    ("space_plus", lambda s: s.replace(" ", "+")),
    ("space_tab", lambda s: s.replace(" ", "%09")),
    ("space_comment", lambda s: s.replace(" ", "/**/")),
]


class WafBypassEngine:
    def __init__(self) -> None:
        self._ua_index = 0
        self._header_index = 0
        self._lock = threading.Lock()
        self.detected_waf: Optional[str] = None
        self._rng = random.Random(int(time.time()))

    def next_ua(self) -> str:
        with self._lock:
            ua = UA_POOL[self._ua_index % len(UA_POOL)]
            self._ua_index += 1
            return ua

    def next_headers(self) -> Dict[str, str]:
        with self._lock:
            base = dict(
                WAF_BYPASS_HEADERS_POOL[
                    self._header_index % len(WAF_BYPASS_HEADERS_POOL)
                ]
            )
            self._header_index += 1
        extra_count = self._rng.randint(1, 3)
        for _ in range(extra_count):
            h = self._rng.choice(WAF_BYPASS_HEADERS_POOL)
            base.update(h)
        return base

    def encode_payload(self, payload: str, technique: str = "plain") -> str:
        for name, fn in WAF_ENCODERS:
            if name == technique:
                try:
                    return fn(payload)
                except Exception:
                    return payload
        return payload

    def random_technique(self) -> str:
        return self._rng.choice([n for n, _ in WAF_ENCODERS])

    def detect_waf_from_response(self, headers: Dict[str, str],
                                 body: str) -> Optional[str]:
        blob = (str(headers) + " " + body[:4000]).lower()
        signatures = {
            "Cloudflare": ["cloudflare", "cf-ray", "__cfduid", "cf-cache-status"],
            "Akamai": ["akamai", "akamaighost", "ak-bmsc"],
            "AWS WAF": ["awselb", "aws-waf", "x-amzn-requestid"],
            "Sucuri": ["sucuri", "x-sucuri-id", "cloudproxy"],
            "Incapsula": ["incap_ses", "visid_incap", "incapsula"],
            "Imperva": ["imperva", "x-iinfo"],
            "F5 BIG-IP": ["bigip", "big-ip", "ts01", "x-wa-info"],
            "Barracuda": ["barra", "barracuda"],
            "ModSecurity": ["mod_security", "modsecurity", "noyb"],
            "Wordfence": ["wordfence", "wfvt_"],
            "DDoS-Guard": ["ddos-guard", "ddosguard"],
            "Fastly": ["fastly", "x-fastly", "fastly-io"],
            "Cloudfront": ["cloudfront", "x-amz-cf-id"],
            "StackPath": ["stackpath", "netdna"],
            "Radware": ["radware", "x-sl-compstate"],
            "Citrix NetScaler": ["netscaler", "citrix", "ns_af"],
            "Fortinet FortiWeb": ["fortiweb", "fortinet"],
            "Wallarm": ["wallarm", "x-wallarm"],
            "Vercel": ["vercel", "x-vercel"],
            "Netlify": ["netlify"],
            "Reblaze": ["reblaze", "rbzid"],
            "Qrator": ["qrator"],
            "SafeLine": ["safeline", "chaitin"],
        }
        for name, sigs in signatures.items():
            for sig in sigs:
                if sig in blob:
                    self.detected_waf = name
                    return name
        return None

    def is_blocked_response(self, status: int, headers: Dict[str, str],
                            body: str) -> bool:
        if status in (403, 406, 429, 503):
            return True
        text = body[:2000].lower()
        block_phrases = [
            "access denied", "blocked", "forbidden",
            "request rejected", "security policy",
            "captcha", "challenge", "checking your browser",
            "attention required", "cloudflare ray id",
            "your request has been blocked",
            "the requested url was rejected",
            "not acceptable", "blocked by",
            "suspicious activity", "protection",
            "mod_security", "web application firewall",
            "ddos protection", "please wait",
            "verify you are human", "bot detected",
        ]
        return any(phrase in text for phrase in block_phrases)


WAF_ENGINE = WafBypassEngine()

_COOKIE_JAR = CookieJar()
_OPENER = build_opener(HTTPCookieProcessor(_COOKIE_JAR))


class HttpResult:
    __slots__ = ("status", "headers", "body", "final_url", "error",
                 "waf", "blocked", "elapsed")

    def __init__(self, status=0, headers=None, body=b"", final_url="",
                 error=None, waf=None, blocked=False, elapsed=0.0):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.final_url = final_url
        self.error = error
        self.waf = waf
        self.blocked = blocked
        self.elapsed = elapsed

    @property
    def text(self) -> str:
        return decode_body(self.body, self.headers)


def _decompress(data: bytes, headers: Dict[str, str]) -> bytes:
    enc = (headers.get("Content-Encoding") or "").lower()
    if not enc:
        return data
    try:
        if "gzip" in enc:
            return gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        if "deflate" in enc:
            try:
                return zlib.decompress(data)
            except zlib.error:
                return zlib.decompress(data, -zlib.MAX_WBITS)
    except (OSError, zlib.error, EOFError):
        return data
    return data


def decode_body(body: bytes, headers: Dict[str, str]) -> str:
    if not body:
        return ""
    ctype = headers.get("Content-Type", "")
    charset = None
    if "charset=" in ctype:
        charset = ctype.split("charset=", 1)[1].split(";")[0].strip().strip('"')
    for enc in (charset, "utf-8", "latin-1"):
        if not enc:
            continue
        try:
            return body.decode(enc, errors="strict")
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", errors="replace")


def _do_request(url: str, extra_headers: Dict[str, str],
                timeout: int, method: str = "GET") -> HttpResult:
    headers = {
        "User-Agent": _BASE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }
    if extra_headers:
        headers.update(extra_headers)

    start = time.time()
    req = Request(url, headers=headers, method=method)
    resp = _OPENER.open(req, timeout=timeout)
    raw = resp.read()
    elapsed = time.time() - start
    resp_headers = dict(resp.headers)
    body = _decompress(raw, resp_headers)
    return HttpResult(
        status=resp.getcode(),
        headers=resp_headers,
        body=body,
        final_url=resp.geturl(),
        elapsed=elapsed,
    )


def http_get(url: str, headers: Optional[Dict[str, str]] = None,
             timeout: Optional[int] = None,
             retries: Optional[int] = None,
             waf_bypass: bool = True,
             method: str = "GET",
             read_body: bool = True) -> HttpResult:
    timeout = timeout or TIMEOUT
    retries = RETRIES if retries is None else retries
    merged_base = dict(headers) if headers else {}

    last_error = None
    last_result: Optional[HttpResult] = None

    for attempt in range(retries + 1):
        attempt_headers = dict(merged_base)
        if waf_bypass and WAF_BYPASS:
            attempt_headers["User-Agent"] = WAF_ENGINE.next_ua()
            for k, v in WAF_ENGINE.next_headers().items():
                attempt_headers.setdefault(k, v)

        try:
            result = _do_request(url, attempt_headers, timeout, method)
            if not read_body:
                return result
            waf_name = WAF_ENGINE.detect_waf_from_response(
                result.headers, result.text[:4000]
            )
            blocked = WAF_ENGINE.is_blocked_response(
                result.status, result.headers, result.text
            )
            result.waf = waf_name
            result.blocked = blocked
            last_result = result
            if not blocked:
                return result
            if DEBUG:
                info(
                    f"WAF blocked attempt {attempt + 1}/{retries + 1} "
                    f"({waf_name or 'unknown'}) rotate"
                )
            last_error = f"waf_blocked_{result.status}"
        except HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except OSError:
                pass
            resp_headers = dict(e.headers) if e.headers else {}
            body = _decompress(raw, resp_headers)
            waf_name = WAF_ENGINE.detect_waf_from_response(
                resp_headers, decode_body(body, resp_headers)[:4000]
            )
            blocked = WAF_ENGINE.is_blocked_response(
                e.code, resp_headers, decode_body(body, resp_headers)
            )
            if 400 <= e.code < 500 and e.code != 429 and not blocked:
                return HttpResult(
                    status=e.code, headers=resp_headers,
                    body=body, final_url=url,
                )
            last_result = HttpResult(
                status=e.code, headers=resp_headers, body=body,
                final_url=url, waf=waf_name, blocked=blocked,
            )
            last_error = f"http_{e.code}"
        except URLError as e:
            last_error = f"urlerror_{e.reason}"
        except TimeoutError:
            last_error = "timeout"
        except OSError as e:
            last_error = f"oserror_{e}"
        except Exception as e:
            last_error = f"unexpected_{type(e).__name__}"

        if attempt < retries:
            time.sleep(RETRY_BACKOFF * (attempt + 1))

    if last_result is not None:
        return last_result
    return HttpResult(status=0, error=last_error or "unknown", final_url=url)


SKIP_HOSTS = (
    "google.", "bing.com", "duckduckgo.com", "yandex.",
    "mojeek.com", "marginalia", "searx", "startpage.",
    "brave.com", "ecosia.org", "w3.org", "schema.org",
    "gstatic", "googleapis", "yastatic", "bing.net",
    "msn.com", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "linkedin.com", "pinterest.com", "tiktok.com",
    "doubleclick", "googlesyndication", "googleadservices",
    "microsoft.com", "live.com", "windows.com",
    "creativecommons.org", "wikipedia.org", "wikimedia.org",
    "cloudflare.com", "cloudflareinsights.com",
    "gigablast", "yep.com", "presearch", "qwant",
    "baidu.com", "so.com", "sogou.com", "naver.com",
    "seznam.cz", "yahoo.com", "yahoosearch",
)

SKIP_EXT = (
    ".css", ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".webm",
)


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: List[Tuple[str, str]] = []
        self._current_href: Optional[str] = None
        self._current_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self._current_href = value
                    self._current_text = []
                    break

    def handle_data(self, data):
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href is not None:
            text = "".join(self._current_text).strip()
            self.anchors.append((self._current_href, text))
            self._current_href = None
            self._current_text = []


_URL_IN_TEXT = re.compile(r'https?://[^\s<>"\'\)\]\}]+', re.IGNORECASE)


def _decode_ddg(url: str) -> str:
    if "duckduckgo.com/l/" in url:
        qs = parse_qs(urlparse(url).query)
        if "uddg" in qs:
            return qs["uddg"][0]
    return url


def _decode_bing(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "u" in qs:
        val = qs["u"][0]
        if val.startswith("a1"):
            val = val[2:]
        padding = "=" * (-len(val) % 4)
        try:
            decoded = base64.urlsafe_b64decode(val + padding).decode(
                "utf-8", errors="replace"
            )
            if decoded.startswith(("http://", "https://")):
                return decoded
        except (ValueError, base64.binascii.Error):
            return url
    return url


def _decode_yandex(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "url" in qs:
        cand = qs["url"][0]
        if cand.startswith(("http://", "https://")):
            return cand
    return url


def _decode_google(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "q" in qs:
        cand = qs["q"][0]
        if cand.startswith(("http://", "https://")):
            return cand
    if "url" in qs:
        cand = qs["url"][0]
        if cand.startswith(("http://", "https://")):
            return cand
    return url


def _decode_qwant(url: str) -> str:
    if "qwant.com/r" in url:
        qs = parse_qs(urlparse(url).query)
        if "u" in qs:
            cand = unquote(qs["u"][0])
            if cand.startswith(("http://", "https://")):
                return cand
    return url


def _decode_startpage(url: str) -> str:
    if "startpage.com" in url and "/doproxy" in url or "startpage.com/do" in url:
        qs = parse_qs(urlparse(url).query)
        if "url" in qs:
            cand = qs["url"][0]
            if cand.startswith(("http://", "https://")):
                return cand
    return url


def _decode_yahoo(url: str) -> str:
    if "r.search.yahoo.com" in url:
        m = re.search(r"/RU=([^/]+)/", url)
        if m:
            cand = unquote(m.group(1))
            if cand.startswith(("http://", "https://")):
                return cand
    qs = parse_qs(urlparse(url).query)
    if "u" in qs:
        cand = unquote(qs["u"][0])
        if cand.startswith(("http://", "https://")):
            return cand
    return url


def _decode_baidu(url: str) -> str:
    if "baidu.com/link" in url:
        qs = parse_qs(urlparse(url).query)
        if "url" in qs:
            cand = unquote(qs["url"][0])
            if cand.startswith(("http://", "https://")):
                return cand
    return url


def _decode_ecosia(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "url" in qs:
        cand = unquote(qs["url"][0])
        if cand.startswith(("http://", "https://")):
            return cand
    return url


def _decode_brave(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "url" in qs:
        cand = unquote(qs["url"][0])
        if cand.startswith(("http://", "https://")):
            return cand
    return url


def _decode_gigablast(url: str) -> str:
    if "gigablast" in url or "yep.com" in url:
        qs = parse_qs(urlparse(url).query)
        if "u" in qs:
            cand = unquote(qs["u"][0])
            if cand.startswith(("http://", "https://")):
                return cand
    return url


def _decode_marginalia(url: str) -> str:
    qs = parse_qs(urlparse(url).query)
    if "url" in qs:
        cand = unquote(qs["url"][0])
        if cand.startswith(("http://", "https://")):
            return cand
    return url


_DECODERS = {
    "duckduckgo": _decode_ddg,
    "bing": _decode_bing,
    "yandex": _decode_yandex,
    "google": _decode_google,
    "qwant": _decode_qwant,
    "startpage": _decode_startpage,
    "yahoo": _decode_yahoo,
    "baidu": _decode_baidu,
    "ecosia": _decode_ecosia,
    "brave": _decode_brave,
    "gigablast": _decode_gigablast,
    "marginalia": _decode_marginalia,
    "mojeek": lambda u: u,
    "searx": lambda u: u,
    "presearch": lambda u: u,
    "yep": _decode_gigablast,
    "naver": lambda u: u,
    "seznam": lambda u: u,
    "swisscows": lambda u: u,
    "metager": lambda u: u,
    "onesearch": lambda u: u,
    "dogpile": lambda u: u,
    "ask": _decode_google,
    "lycos": lambda u: u,
    "sogou": lambda u: u,
    "so": lambda u: u,
    "yandexcom": _decode_yandex,
}


def _is_acceptable(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if not host:
        return False
    for skip in SKIP_HOSTS:
        if skip in host:
            return False
    lower_path = (p.path or "").lower()
    for ext in SKIP_EXT:
        if lower_path.endswith(ext):
            return False
    return True


def extract_urls_from_html(html_text: str, base_url: str,
                           engine_key: str) -> Set[str]:
    if not html_text:
        return set()
    decoder = _DECODERS.get(engine_key, lambda u: u)
    candidates: Set[str] = set()

    parser = AnchorParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        parser.anchors = []

    for href, _text in parser.anchors:
        if not href:
            continue
        href = unescape(href.strip())
        if href.startswith(("javascript:", "mailto:", "tel:", "data:")):
            continue
        try:
            absolute = urljoin(base_url, href)
        except ValueError:
            continue
        decoded = decoder(absolute)
        normalized = normalize_url(decoded)
        if normalized and _is_acceptable(normalized):
            candidates.add(normalized)

    if not candidates:
        for m in _URL_IN_TEXT.finditer(html_text):
            raw = unescape(m.group(0)).rstrip('.,;:!?)\\]\'"')
            decoded = decoder(raw)
            normalized = normalize_url(decoded)
            if normalized and _is_acceptable(normalized):
                candidates.add(normalized)

    return candidates


class TTLCache:
    def __init__(self, ttl: int = 600, max_entries: int = 2048) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._data: Dict[str, Tuple[float, Set[str]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Set[str]]:
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            ts, value = entry
            if time.time() - ts > self.ttl:
                del self._data[key]
                return None
            return set(value)

    def set(self, key: str, value: Set[str]) -> None:
        with self._lock:
            if len(self._data) >= self.max_entries:
                oldest_key = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest_key, None)
            self._data[key] = (time.time(), set(value))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


CACHE = TTLCache(ttl=CACHE_TTL, max_entries=CACHE_MAX)


@dataclass
class EngineResult:
    engine: str
    query: str
    urls: Set[str]
    status: str
    error: Optional[str] = None
    elapsed: float = 0.0
    waf: Optional[str] = None


@dataclass
class SearchEngine:
    key: str
    name: str
    url_template: str
    enabled: bool = True
    timeout: int = 20
    extra_headers: Dict[str, str] = field(default_factory=dict)

    def build_url(self, query: str) -> str:
        return self.url_template.format(query=quote_plus(query))

    def search(self, query: str, waf_bypass: bool = True) -> EngineResult:
        if not self.enabled:
            return EngineResult(self.key, query, set(), "disabled")

        cache_key = f"{self.key}|{query}|waf={waf_bypass}"
        if CACHE_ENABLED:
            hit = CACHE.get(cache_key)
            if hit is not None:
                return EngineResult(self.key, query, hit, "ok")

        start = time.time()
        url = self.build_url(query)
        resp = http_get(
            url, headers=self.extra_headers,
            timeout=self.timeout, waf_bypass=waf_bypass,
        )
        elapsed = time.time() - start

        if resp.error:
            status = "timeout" if "timeout" in resp.error else "http_error"
            return EngineResult(
                self.key, query, set(), status, resp.error, elapsed,
                waf=resp.waf,
            )
        if resp.status == 0:
            return EngineResult(
                self.key, query, set(), "http_error",
                "no_status", elapsed, waf=resp.waf,
            )
        if resp.status >= 400:
            return EngineResult(
                self.key, query, set(), "http_error",
                f"http_{resp.status}", elapsed, waf=resp.waf,
            )

        try:
            urls = extract_urls_from_html(
                resp.text, resp.final_url or url, self.key
            )
        except Exception as e:
            return EngineResult(
                self.key, query, set(), "parse_error",
                str(e), elapsed, waf=resp.waf,
            )

        if not urls:
            return EngineResult(
                self.key, query, set(), "empty", None, elapsed, waf=resp.waf,
            )

        if CACHE_ENABLED:
            CACHE.set(cache_key, urls)

        return EngineResult(
            self.key, query, urls, "ok", None, elapsed, waf=resp.waf,
        )


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: Dict[str, SearchEngine] = {}
        defaults = [
            SearchEngine(
                key="google", name="Google",
                url_template="https://www.google.com/search?q={query}&num=30",
                enabled=False,
                extra_headers={
                    "Referer": "https://www.google.com/",
                    "Accept": "text/html,application/xhtml+xml",
                },
            ),
            SearchEngine(
                key="duckduckgo", name="DuckDuckGo",
                url_template="https://html.duckduckgo.com/html/?q={query}",
                extra_headers={
                    "Referer": "https://duckduckgo.com/",
                    "Accept": "text/html,application/xhtml+xml",
                },
            ),
            SearchEngine(
                key="bing", name="Bing",
                url_template="https://www.bing.com/search?q={query}&count=30",
                extra_headers={
                    "Referer": "https://www.bing.com/",
                    "Accept": "text/html,application/xhtml+xml",
                },
            ),
            SearchEngine(
                key="yandex", name="Yandex",
                url_template="https://yandex.com/search/?text={query}",
                extra_headers={
                    "Referer": "https://yandex.com/",
                    "Accept": "text/html,application/xhtml+xml",
                },
            ),
            SearchEngine(
                key="yahoo", name="Yahoo",
                url_template="https://search.yahoo.com/search?p={query}",
                extra_headers={
                    "Referer": "https://search.yahoo.com/",
                },
            ),
            SearchEngine(
                key="baidu", name="Baidu",
                url_template="https://www.baidu.com/s?wd={query}",
                extra_headers={
                    "Referer": "https://www.baidu.com/",
                },
            ),
            SearchEngine(
                key="qwant", name="Qwant",
                url_template="https://www.qwant.com/?q={query}&t=web",
                extra_headers={
                    "Referer": "https://www.qwant.com/",
                },
            ),
            SearchEngine(
                key="mojeek", name="Mojeek",
                url_template="https://www.mojeek.com/search?q={query}",
            ),
            SearchEngine(
                key="marginalia", name="Marginalia",
                url_template="https://search.marginalia.nu/search?query={query}",
            ),
            SearchEngine(
                key="startpage", name="Startpage",
                url_template="https://www.startpage.com/sp/search?query={query}",
                enabled=False,
            ),
            SearchEngine(
                key="brave", name="Brave",
                url_template="https://search.brave.com/search?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="ecosia", name="Ecosia",
                url_template="https://www.ecosia.org/search?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="gigablast", name="Gigablast",
                url_template="https://www.gigablast.com/search?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="yep", name="Yep",
                url_template="https://yep.com/web?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="presearch", name="Presearch",
                url_template="https://presearch.com/search?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="searx", name="SearX",
                url_template="https://searx.be/search?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="swisscows", name="Swisscows",
                url_template="https://swisscows.com/en/web?query={query}",
                enabled=False,
            ),
            SearchEngine(
                key="metager", name="MetaGer",
                url_template="https://metager.org/meta/meta.ger3?eingabe={query}",
                enabled=False,
            ),
            SearchEngine(
                key="naver", name="Naver",
                url_template="https://search.naver.com/search.naver?query={query}",
                enabled=False,
            ),
            SearchEngine(
                key="seznam", name="Seznam",
                url_template="https://search.seznam.cz/?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="so", name="360 So",
                url_template="https://www.so.com/s?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="sogou", name="Sogou",
                url_template="https://www.sogou.com/web?query={query}",
                enabled=False,
            ),
            SearchEngine(
                key="dogpile", name="Dogpile",
                url_template="https://www.dogpile.com/serp?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="ask", name="Ask",
                url_template="https://www.ask.com/web?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="lycos", name="Lycos",
                url_template="https://www.lycos.com/?q={query}",
                enabled=False,
            ),
            SearchEngine(
                key="onesearch", name="OneSearch",
                url_template="https://www.onesearch.com/yhs/search?q={query}",
                enabled=False,
            ),
        ]
        for e in defaults:
            self._engines[e.key] = e

    def all(self) -> List[SearchEngine]:
        return list(self._engines.values())

    def enabled(self) -> List[SearchEngine]:
        return [e for e in self._engines.values() if e.enabled]


REGISTRY = EngineRegistry()

TLD_GROUPS: List[Tuple[str, List[Tuple[str, str]]]] = [
    ("Indonesia", [
        (".co.id", "Komersial"),
        (".id", "Umum"),
        (".my.id", "Personal"),
        (".web.id", "Website"),
        (".biz.id", "Bisnis"),
        (".net.id", "Network"),
        (".or.id", "Organisasi"),
        (".sch.id", "Sekolah"),
        (".ac.id", "Akademik"),
        (".go.id", "Pemerintah"),
        (".mil.id", "Militer"),
        (".desa.id", "Desa"),
    ]),
    ("Singapore", [
        (".sg", "Singapura"),
        (".com.sg", "Komersial SG"),
        (".edu.sg", "Edukasi SG"),
        (".gov.sg", "Pemerintah SG"),
        (".org.sg", "Organisasi SG"),
    ]),
    ("Malaysia", [
        (".my", "Malaysia"),
        (".com.my", "Komersial MY"),
        (".net.my", "Network MY"),
        (".org.my", "Organisasi MY"),
        (".edu.my", "Edukasi MY"),
        (".gov.my", "Pemerintah MY"),
    ]),
    ("Thailand", [
        (".th", "Thailand"),
        (".co.th", "Komersial TH"),
        (".ac.th", "Akademik TH"),
        (".go.th", "Pemerintah TH"),
        (".or.th", "Organisasi TH"),
    ]),
    ("Vietnam", [
        (".vn", "Vietnam"),
        (".com.vn", "Komersial VN"),
        (".net.vn", "Network VN"),
        (".org.vn", "Organisasi VN"),
        (".edu.vn", "Edukasi VN"),
        (".gov.vn", "Pemerintah VN"),
    ]),
    ("Filipina", [
        (".ph", "Filipina"),
        (".com.ph", "Komersial PH"),
        (".net.ph", "Network PH"),
        (".org.ph", "Organisasi PH"),
        (".gov.ph", "Pemerintah PH"),
    ]),
    ("China", [
        (".cn", "China"),
        (".com.cn", "Komersial CN"),
        (".net.cn", "Network CN"),
        (".org.cn", "Organisasi CN"),
        (".gov.cn", "Pemerintah CN"),
        (".edu.cn", "Edukasi CN"),
    ]),
    ("Hong Kong", [
        (".hk", "Hong Kong"),
        (".com.hk", "Komersial HK"),
        (".org.hk", "Organisasi HK"),
        (".edu.hk", "Edukasi HK"),
        (".gov.hk", "Pemerintah HK"),
    ]),
    ("Taiwan", [
        (".tw", "Taiwan"),
        (".com.tw", "Komersial TW"),
        (".org.tw", "Organisasi TW"),
        (".edu.tw", "Edukasi TW"),
        (".gov.tw", "Pemerintah TW"),
    ]),
    ("Jepang", [
        (".jp", "Jepang"),
        (".co.jp", "Komersial JP"),
        (".ne.jp", "Network JP"),
        (".or.jp", "Organisasi JP"),
        (".ac.jp", "Akademik JP"),
        (".go.jp", "Pemerintah JP"),
    ]),
    ("Korea", [
        (".kr", "Korea"),
        (".co.kr", "Komersial KR"),
        (".or.kr", "Organisasi KR"),
        (".ne.kr", "Network KR"),
        (".go.kr", "Pemerintah KR"),
        (".ac.kr", "Akademik KR"),
    ]),
    ("India", [
        (".in", "India"),
        (".co.in", "Komersial IN"),
        (".net.in", "Network IN"),
        (".org.in", "Organisasi IN"),
        (".gov.in", "Pemerintah IN"),
        (".ac.in", "Akademik IN"),
    ]),
    ("Pakistan", [
        (".pk", "Pakistan"),
        (".com.pk", "Komersial PK"),
        (".net.pk", "Network PK"),
        (".org.pk", "Organisasi PK"),
        (".gov.pk", "Pemerintah PK"),
    ]),
    ("Bangladesh", [
        (".bd", "Bangladesh"),
        (".com.bd", "Komersial BD"),
        (".org.bd", "Organisasi BD"),
        (".gov.bd", "Pemerintah BD"),
    ]),
    ("Sri Lanka", [
        (".lk", "Sri Lanka"),
        (".com.lk", "Komersial LK"),
        (".org.lk", "Organisasi LK"),
        (".gov.lk", "Pemerintah LK"),
    ]),
    ("Nepal", [
        (".np", "Nepal"),
        (".com.np", "Komersial NP"),
        (".org.np", "Organisasi NP"),
        (".gov.np", "Pemerintah NP"),
    ]),
    ("UAE", [
        (".ae", "UAE"),
        (".co.ae", "Komersial AE"),
        (".net.ae", "Network AE"),
        (".org.ae", "Organisasi AE"),
        (".gov.ae", "Pemerintah AE"),
    ]),
    ("Saudi", [
        (".sa", "Saudi"),
        (".com.sa", "Komersial SA"),
        (".org.sa", "Organisasi SA"),
        (".gov.sa", "Pemerintah SA"),
    ]),
    ("Qatar", [
        (".qa", "Qatar"),
        (".com.qa", "Komersial QA"),
        (".org.qa", "Organisasi QA"),
        (".gov.qa", "Pemerintah QA"),
    ]),
    ("Kuwait", [
        (".kw", "Kuwait"),
        (".com.kw", "Komersial KW"),
        (".org.kw", "Organisasi KW"),
        (".gov.kw", "Pemerintah KW"),
    ]),
    ("Turki", [
        (".tr", "Turki"),
        (".com.tr", "Komersial TR"),
        (".net.tr", "Network TR"),
        (".org.tr", "Organisasi TR"),
        (".gov.tr", "Pemerintah TR"),
    ]),
    ("Iran", [
        (".ir", "Iran"),
        (".co.ir", "Komersial IR"),
        (".org.ir", "Organisasi IR"),
        (".ac.ir", "Akademik IR"),
    ]),
    ("Kazakhstan", [
        (".kz", "Kazakhstan"),
        (".com.kz", "Komersial KZ"),
        (".org.kz", "Organisasi KZ"),
    ]),
    ("Inggris", [
        (".uk", "Inggris"),
        (".co.uk", "Komersial UK"),
        (".me.uk", "Personal UK"),
        (".org.uk", "Organisasi UK"),
        (".ac.uk", "Akademik UK"),
        (".gov.uk", "Pemerintah UK"),
    ]),
    ("Jerman", [
        (".de", "Jerman"),
        (".com.de", "Komersial DE"),
        (".co.de", "Komersial DE"),
    ]),
    ("Prancis", [
        (".fr", "Prancis"),
        (".com.fr", "Komersial FR"),
        (".gouv.fr", "Pemerintah FR"),
    ]),
    ("Italia", [
        (".it", "Italia"),
        (".com.it", "Komersial IT"),
        (".gov.it", "Pemerintah IT"),
    ]),
    ("Spanyol", [
        (".es", "Spanyol"),
        (".com.es", "Komersial ES"),
        (".gob.es", "Pemerintah ES"),
    ]),
    ("Belanda", [
        (".nl", "Belanda"),
        (".com.nl", "Komersial NL"),
    ]),
    ("Rusia", [
        (".ru", "Rusia"),
        (".com.ru", "Komersial RU"),
        (".net.ru", "Network RU"),
        (".org.ru", "Organisasi RU"),
        (".gov.ru", "Pemerintah RU"),
    ]),
    ("Polandia", [
        (".pl", "Polandia"),
        (".com.pl", "Komersial PL"),
        (".org.pl", "Organisasi PL"),
        (".gov.pl", "Pemerintah PL"),
    ]),
    ("Swedia", [
        (".se", "Swedia"),
        (".com.se", "Komersial SE"),
    ]),
    ("Swiss", [
        (".ch", "Swiss"),
        (".com.ch", "Komersial CH"),
    ]),
    ("Belgia", [
        (".be", "Belgia"),
        (".com.be", "Komersial BE"),
    ]),
    ("Austria", [
        (".at", "Austria"),
        (".co.at", "Komersial AT"),
    ]),
    ("Norwegia", [
        (".no", "Norwegia"),
        (".com.no", "Komersial NO"),
    ]),
    ("Denmark", [
        (".dk", "Denmark"),
        (".com.dk", "Komersial DK"),
    ]),
    ("Finlandia", [
        (".fi", "Finlandia"),
        (".com.fi", "Komersial FI"),
    ]),
    ("Ceko", [
        (".cz", "Ceko"),
        (".com.cz", "Komersial CZ"),
    ]),
    ("Rumania", [
        (".ro", "Rumania"),
        (".com.ro", "Komersial RO"),
    ]),
    ("Yunani", [
        (".gr", "Yunani"),
        (".com.gr", "Komersial GR"),
        (".gov.gr", "Pemerintah GR"),
    ]),
    ("Portugal", [
        (".pt", "Portugal"),
        (".com.pt", "Komersial PT"),
        (".gov.pt", "Pemerintah PT"),
    ]),
    ("Irlandia", [
        (".ie", "Irlandia"),
        (".gov.ie", "Pemerintah IE"),
    ]),
    ("Ukraina", [
        (".ua", "Ukraina"),
        (".com.ua", "Komersial UA"),
        (".org.ua", "Organisasi UA"),
        (".gov.ua", "Pemerintah UA"),
    ]),
    ("USA", [
        (".us", "USA"),
        (".gov", "Pemerintah US"),
        (".mil", "Militer US"),
        (".edu", "Edukasi US"),
    ]),
    ("Kanada", [
        (".ca", "Kanada"),
        (".gc.ca", "Pemerintah CA"),
    ]),
    ("Meksiko", [
        (".mx", "Meksiko"),
        (".com.mx", "Komersial MX"),
        (".org.mx", "Organisasi MX"),
        (".gob.mx", "Pemerintah MX"),
    ]),
    ("Brasil", [
        (".br", "Brasil"),
        (".com.br", "Komersial BR"),
        (".net.br", "Network BR"),
        (".org.br", "Organisasi BR"),
        (".gov.br", "Pemerintah BR"),
    ]),
    ("Argentina", [
        (".ar", "Argentina"),
        (".com.ar", "Komersial AR"),
        (".org.ar", "Organisasi AR"),
        (".gob.ar", "Pemerintah AR"),
    ]),
    ("Chile", [
        (".cl", "Chile"),
        (".com.cl", "Komersial CL"),
        (".gob.cl", "Pemerintah CL"),
    ]),
    ("Kolombia", [
        (".co", "Kolombia"),
        (".com.co", "Komersial CO"),
        (".gov.co", "Pemerintah CO"),
    ]),
    ("Peru", [
        (".pe", "Peru"),
        (".com.pe", "Komersial PE"),
        (".gob.pe", "Pemerintah PE"),
    ]),
    ("Venezuela", [
        (".ve", "Venezuela"),
        (".com.ve", "Komersial VE"),
        (".gob.ve", "Pemerintah VE"),
    ]),
    ("Ekuador", [
        (".ec", "Ekuador"),
        (".com.ec", "Komersial EC"),
        (".gob.ec", "Pemerintah EC"),
    ]),
    ("Afrika Selatan", [
        (".za", "Afrika Selatan"),
        (".co.za", "Komersial ZA"),
        (".org.za", "Organisasi ZA"),
        (".gov.za", "Pemerintah ZA"),
    ]),
    ("Mesir", [
        (".eg", "Mesir"),
        (".com.eg", "Komersial EG"),
        (".gov.eg", "Pemerintah EG"),
    ]),
    ("Nigeria", [
        (".ng", "Nigeria"),
        (".com.ng", "Komersial NG"),
        (".org.ng", "Organisasi NG"),
        (".gov.ng", "Pemerintah NG"),
    ]),
    ("Kenya", [
        (".ke", "Kenya"),
        (".co.ke", "Komersial KE"),
        (".go.ke", "Pemerintah KE"),
    ]),
    ("Maroko", [
        (".ma", "Maroko"),
        (".com.ma", "Komersial MA"),
        (".gov.ma", "Pemerintah MA"),
    ]),
    ("Australia", [
        (".au", "Australia"),
        (".com.au", "Komersial AU"),
        (".net.au", "Network AU"),
        (".org.au", "Organisasi AU"),
        (".gov.au", "Pemerintah AU"),
        (".edu.au", "Edukasi AU"),
    ]),
    ("Selandia Baru", [
        (".nz", "Selandia Baru"),
        (".co.nz", "Komersial NZ"),
        (".org.nz", "Organisasi NZ"),
        (".govt.nz", "Pemerintah NZ"),
    ]),
    ("Global", [
        (".com", "Komersial"),
        (".net", "Network"),
        (".org", "Organisasi"),
        (".info", "Informasi"),
        (".biz", "Bisnis"),
        (".io", "Startup"),
        (".me", "Personal"),
        (".tv", "Media"),
        (".xyz", "Generik"),
        (".online", "Online"),
        (".site", "Site"),
        (".tech", "Tech"),
        (".app", "App"),
        (".dev", "Dev"),
        (".cloud", "Cloud"),
        (".store", "Store"),
        (".shop", "Shop"),
        (".blog", "Blog"),
        (".news", "News"),
        (".live", "Live"),
        (".pro", "Profesional"),
        (".name", "Nama"),
        (".mobi", "Mobile"),
        (".asia", "Asia"),
        (".edu", "Edukasi"),
        (".gov", "Pemerintah"),
        (".mil", "Militer"),
        (".int", "Internasional"),
    ]),
]


def all_tlds() -> List[str]:
    result = []
    for _, tlds in TLD_GROUPS:
        for ext, _ in tlds:
            result.append(ext)
    return result


def tld_count() -> int:
    return sum(len(tlds) for _, tlds in TLD_GROUPS)


@dataclass(frozen=True)
class DorkObjective:
    key: str
    name: str
    patterns: List[str]


OBJECTIVES: Dict[str, DorkObjective] = {}


def _reg(key, name, patterns):
    OBJECTIVES[key] = DorkObjective(key=key, name=name, patterns=patterns)


_reg("1", "index of / generic", [
    "index of /", "intitle:index of /",
    '"index of /" "parent directory"',
    '"parent directory" "index of"',
    'intitle:"index of" "parent directory"',
])
_reg("2", "upload & uploads", [
    "index of /upload", "index of /uploads",
    'intitle:"index of /upload"', 'intitle:"index of /uploads"',
    "inurl:/upload/", "inurl:/uploads/",
    "inurl:upload.php", "inurl:uploader",
    '"index of" "/uploads"',
])
_reg("3", "files & file", [
    "index of /files", "index of /file",
    'intitle:"index of /files"',
    "inurl:/files/", "inurl:/file/",
    '"index of" "/files"',
])
_reg("4", "backup & backups", [
    "index of /backup", "index of /backups",
    'intitle:"index of /backup"', 'intitle:"index of /backups"',
    "inurl:/backup/", "inurl:/backups/",
    "filetype:sql inurl:backup", "filetype:zip inurl:backup",
    "filetype:tar inurl:backup", "filetype:tar.gz inurl:backup",
    "filetype:bak inurl:backup", "filetype:old inurl:backup",
    "filetype:rar inurl:backup", "filetype:7z inurl:backup",
])
_reg("5", "config & env", [
    "index of /config", "index of /conf", "index of /configuration",
    "inurl:/config/", "inurl:/conf/",
    "filetype:env", "filetype:env inurl:config",
    "filetype:json inurl:config", "filetype:yml inurl:config",
    "filetype:yaml inurl:config", "filetype:xml inurl:config",
    "filetype:ini inurl:config", "filetype:cfg inurl:config",
    "filetype:conf inurl:config", "filetype:toml inurl:config",
])
_reg("6", "admin panel", [
    "index of /admin", "index of /administrator",
    'intitle:"admin login"', 'intitle:"admin panel"',
    'intitle:"administrator"',
    "inurl:/admin/", "inurl:/administrator/",
    "inurl:/adminpanel", "inurl:/admin/login",
])
_reg("7", "database & sql", [
    "index of /database", "index of /databases",
    "index of /db", "index of /sql",
    "inurl:/database/", "inurl:/db/",
    "filetype:sql", "filetype:sqlite", "filetype:db",
    "filetype:mdb", "filetype:dbf",
    "filetype:sql inurl:backup",
    'intitle:"index of" sql', 'intitle:"index of" database',
])
_reg("8", "log & logs", [
    "index of /log", "index of /logs",
    "inurl:/log/", "inurl:/logs/",
    "filetype:log", "filetype:log inurl:log",
    'intitle:"index of" log', 'intitle:"index of" logs',
])
_reg("9", "private & secret", [
    "index of /private", "index of /secret",
    "index of /hidden", "index of /personal",
    "inurl:/private/", "inurl:/secret/", "inurl:/hidden/",
    'intitle:"index of /private"', 'intitle:"index of /secret"',
])
_reg("10", "documents & pdf", [
    "index of /doc", "index of /docs",
    "index of /document", "index of /documents",
    "inurl:/documents/", "inurl:/docs/",
    "filetype:pdf inurl:download", "filetype:doc inurl:download",
    "filetype:docx inurl:download", "filetype:xls inurl:download",
    "filetype:xlsx inurl:download", "filetype:ppt inurl:download",
    "filetype:pptx inurl:download", "filetype:csv inurl:download",
])
_reg("11", "images & media", [
    "index of /img", "index of /images", "index of /image",
    "index of /media", "index of /video", "index of /videos",
    "inurl:/images/", "inurl:/img/", "inurl:/media/",
    "filetype:png inurl:download", "filetype:jpg inurl:download",
    "filetype:jpeg inurl:download", "filetype:gif inurl:download",
    "filetype:mp4 inurl:download",
])
_reg("12", "archive & compressed", [
    "index of /archive", "index of /archives",
    "inurl:/archive/",
    "filetype:zip", "filetype:rar", "filetype:tar",
    "filetype:tar.gz", "filetype:tgz", "filetype:7z",
    "filetype:bz2", "filetype:gz",
])
_reg("13", "web shell indicators", [
    "inurl:shell", "inurl:cmd", "inurl:exec",
    "inurl:c99", "inurl:r57", "inurl:b374k",
    "inurl:webshell", 'intitle:"shell" inurl:.php',
    "filetype:php inurl:shell", "inurl:uploadshell",
    "inurl:backdoor",
])
_reg("14", "panel & login", [
    'intitle:"cpanel"', 'intitle:"phpmyadmin"',
    'intitle:"webmail"', 'intitle:"plesk"',
    'intitle:"directadmin"',
    "inurl:/cpanel", "inurl:/phpmyadmin", "inurl:/pma",
    "inurl:/webmail", "inurl:/plesk", "inurl:/directadmin",
    "inurl:/roundcube", "inurl:/horde",
])
_reg("15", "source code & git", [
    "index of /.git", "index of /.svn",
    'intitle:"index of" .git', 'intitle:"index of" .svn',
    "inurl:/.git/", "inurl:/.svn/",
    "filetype:gitignore", "inurl:/.env", "inurl:.git/config",
])
_reg("16", "API & endpoint", [
    "inurl:/api/v1", "inurl:/api/v2", "inurl:/api/v3",
    "inurl:/api/", "inurl:/graphql", "inurl:/rest/",
    'intitle:"api documentation"', 'intitle:"swagger ui"',
    "inurl:/swagger", "inurl:/openapi",
])
_reg("17", "keys & credentials", [
    "filetype:pem", "filetype:key", "filetype:crt",
    "filetype:ppk", "filetype:rdp", "filetype:ovpn",
    "inurl:id_rsa", "inurl:.ssh", "inurl:credentials", "inurl:apikey",
])
_reg("18", "temp & cache", [
    "index of /tmp", "index of /temp", "index of /cache",
    "index of /var", "inurl:/tmp/", "inurl:/temp/", "inurl:/cache/",
])
_reg("19", "full stack", [
    "index of /", "index of /upload", "index of /uploads",
    "index of /files", "index of /file", "index of /backup",
    "index of /backups", "index of /config", "index of /conf",
    "index of /admin", "index of /administrator",
    "index of /database", "index of /db", "index of /log",
    "index of /logs", "index of /private", "index of /secret",
    "index of /documents", "index of /docs", "index of /images",
    "index of /img", "index of /media", "index of /archive",
    "filetype:sql", "filetype:env", "filetype:log",
    "filetype:bak", "filetype:zip", "filetype:tar.gz",
    "filetype:json inurl:config", 'intitle:"index of"',
])
_reg("20", "admin & dashboard", [
    'intitle:"dashboard"', 'intitle:"admin dashboard"',
    "inurl:/dashboard/", "inurl:/panel/",
    "inurl:/controlpanel/", "inurl:/manage/",
    "inurl:/management/", 'intitle:"control panel"',
])
_reg("21", "CMS specific", [
    "inurl:/wp-content/", "inurl:/wp-includes/",
    "inurl:/wp-admin/", "inurl:/wp-json/",
    "inurl:/xmlrpc.php", "inurl:/joomla/", "inurl:/drupal/",
    'intitle:"index of /wp-content"',
    'intitle:"index of /wp-includes"',
])
_reg("22", "financial & invoice", [
    "inurl:/invoice/", "inurl:/invoices/",
    "inurl:/payment/", "inurl:/billing/", "inurl:/finance/",
    "filetype:pdf inurl:invoice", "filetype:xls inurl:invoice",
])
_reg("23", "network & internal", [
    "inurl:/internal/", "inurl:/intranet/", "inurl:/vpn/",
    "inurl:/proxy/", "inurl:/firewall/", 'intitle:"internal server"',
])
_reg("24", "email & webmail", [
    "inurl:/mail/", "inurl:/webmail/", "inurl:/smtp/",
    "inurl:/imap/", "inurl:/pop3/",
    'intitle:"webmail login"', 'intitle:"roundcube"',
])


def all_patterns() -> List[str]:
    seen = set()
    result = []
    for obj in OBJECTIVES.values():
        for p in obj.patterns:
            if p not in seen:
                seen.add(p)
                result.append(p)
    return result


def build_queries(tlds: List[str], patterns: List[str]) -> List[str]:
    return [f"site:{tld} {pat}" for tld in tlds for pat in patterns]


@dataclass
class Result:
    url: str
    host: str
    engines: Set[str] = field(default_factory=set)
    queries: Set[str] = field(default_factory=set)
    first_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    category: str = "other"
    severity: str = "other"
    live_status: int = 0
    live_error: Optional[str] = None
    is_index_of: bool = False
    content_type: str = ""
    server: str = ""
    powered_by: str = ""
    title: str = ""
    preview: str = ""
    elapsed: float = 0.0
    ip: Optional[str] = None
    country: Optional[str] = None
    isp: Optional[str] = None
    asn: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "host": self.host,
            "engines": sorted(self.engines),
            "queries": sorted(self.queries),
            "category": self.category,
            "severity": self.severity,
            "first_seen": self.first_seen,
            "live_status": self.live_status,
            "live_error": self.live_error,
            "is_index_of": self.is_index_of,
            "content_type": self.content_type,
            "server": self.server,
            "powered_by": self.powered_by,
            "title": self.title,
            "preview": self.preview[:300],
            "elapsed": self.elapsed,
            "ip": self.ip,
            "country": self.country,
            "isp": self.isp,
            "asn": self.asn,
        }


CATEGORY_KEYWORDS = {
    "config": ["/config", "/conf", "/.env", "/settings", "/secrets"],
    "backup": ["/backup", "/backups", "/.bak", "/.old", ".sql", ".zip", ".tar"],
    "admin": ["/admin", "/administrator", "/dashboard", "/panel"],
    "database": ["/database", "/db", "/mysql", "/postgres", "/mongo"],
    "upload": ["/upload", "/uploads", "/file", "/files"],
    "log": ["/log", "/logs", ".log"],
    "shell-indicator": ["shell", "/cmd", "/exec", "c99", "r57", "b374k", "webshell"],
    "panel": ["/cpanel", "/phpmyadmin", "/pma", "/webmail", "/plesk"],
    "document": ["/doc", "/docs", "/documents", ".pdf", ".doc", ".xls", ".ppt", ".csv"],
    "media": ["/image", "/img", "/media", ".png", ".jpg", ".jpeg", ".gif", ".mp4"],
    "archive": [".zip", ".rar", ".tar", ".tar.gz", ".tgz", ".7z", ".gz"],
}

SEVERITY_KEYWORDS = {
    "critical": [".env", "/.git/", "id_rsa", ".aws/credentials",
                 "wp-config.php", ".bash_history", "shadow", "private_key",
                 "credentials", "passwd", "dump.sql", "backup.sql"],
    "high": ["/backup", "/database", "/config", ".sql", ".pem",
             ".key", ".ppk", "/admin", "/phpmyadmin", "/cpanel",
             "/webshell", ".ovpn"],
    "medium": ["/upload", "/uploads", "/files", "/logs", "/log",
               "/private", "/secret", "/tmp", "/internal"],
    "low": ["/images", "/img", "/media", "/docs", "/docs"],
}


def categorize(url: str) -> str:
    lower = url.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in lower:
                return cat
    if lower.endswith("/") or "/index of/" in lower:
        return "index-of"
    return "other"


def score_severity(url: str) -> str:
    lower = url.lower()
    for sev, keys in SEVERITY_KEYWORDS.items():
        for k in keys:
            if k in lower:
                return sev
    return "info"


class ResultStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._map: Dict[str, Result] = {}

    def add(self, url: str, engine: str, query: str) -> Optional[Result]:
        normalized = normalize_url(url)
        if not normalized:
            return None
        host = host_of(normalized)
        if not host:
            return None
        with self._lock:
            existing = self._map.get(normalized)
            if existing:
                existing.engines.add(engine)
                existing.queries.add(query)
                return None
            res = Result(
                url=normalized, host=host,
                engines={engine}, queries={query},
                category=categorize(normalized),
                severity=score_severity(normalized),
            )
            self._map[normalized] = res
            return res

    def update_live(self, url: str, status: int, error: Optional[str],
                    is_index: bool, content_type: str, server: str,
                    powered_by: str, title: str, preview: str,
                    elapsed: float) -> None:
        with self._lock:
            res = self._map.get(url)
            if not res:
                return
            res.live_status = status
            res.live_error = error
            res.is_index_of = is_index
            res.content_type = content_type
            res.server = server
            res.powered_by = powered_by
            res.title = title
            res.preview = preview
            res.elapsed = elapsed

    def update_enrich(self, url: str, ip: Optional[str], country: Optional[str],
                      isp: Optional[str], asn: Optional[str]) -> None:
        with self._lock:
            res = self._map.get(url)
            if not res:
                return
            res.ip = ip
            res.country = country
            res.isp = isp
            res.asn = asn

    def all(self) -> List[Result]:
        with self._lock:
            return list(self._map.values())

    def size(self) -> int:
        with self._lock:
            return len(self._map)

    def by_category(self) -> Dict[str, List[Result]]:
        with self._lock:
            buckets: Dict[str, List[Result]] = {}
            for r in self._map.values():
                buckets.setdefault(r.category, []).append(r)
            for k in buckets:
                buckets[k].sort(
                    key=lambda x: (-SEVERITY_ORDER.get(x.severity, 0), x.url)
                )
            return buckets

    def by_severity(self) -> Dict[str, List[Result]]:
        with self._lock:
            buckets: Dict[str, List[Result]] = {}
            for r in self._map.values():
                buckets.setdefault(r.severity, []).append(r)
            return buckets

    def unique_hosts(self) -> List[str]:
        with self._lock:
            hosts = sorted({r.host for r in self._map.values() if r.host})
            return hosts


def analyze_index_of(html_text: str) -> bool:
    if not html_text:
        return False
    lower = html_text[:20000].lower()
    indicators = [
        "<title>index of",
        "<h1>index of",
        "parent directory</a>",
        "parent directory</h1>",
        "[to parent directory]",
        "directory listing for",
    ]
    hits = sum(1 for ind in indicators if ind in lower)
    return hits >= 1


def analyze_title(html_text: str) -> str:
    if not html_text:
        return ""
    m = re.search(r"<title[^>]*>(.*?)</title>",
                  html_text[:20000], re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return unescape(m.group(1)).strip()[:200]


def analyze_preview(html_text: str, length: int = 200) -> str:
    if not html_text:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text,
                  flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text,
                  flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:length]


class SplitScreenDisplay:
    def __init__(self, total: int, label: str = "scanning",
                 enabled: bool = True) -> None:
        self.total = max(1, total)
        self.label = label
        self.enabled = enabled and _COLOR and hasattr(sys.stdout, "isatty")
        self.current = 0
        self.ok = 0
        self.err = 0
        self.found = 0
        self.waf_set: Set[str] = set()
        self.log_lines: List[str] = []
        self.event_lines: List[str] = []
        self._lock = threading.Lock()
        self._last_render = 0.0
        self._started = False
        self._phase_label = label
        self._start_time = time.time()

    def start(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            sys.stdout.write("\033[?1049h")
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
            self._started = True
        self._render(force=True)

    def stop(self) -> None:
        if not self.enabled or not self._started:
            return
        with self._lock:
            sys.stdout.write("\033[?25h")
            sys.stdout.write("\033[?1049l")
            sys.stdout.flush()
            self._started = False

    def set_label(self, label: str) -> None:
        with self._lock:
            self._phase_label = label
        self._render(force=True)

    def set_total(self, total: int) -> None:
        with self._lock:
            self.total = max(1, total)
            self.current = 0
            self.ok = 0
            self.err = 0
        self._render(force=True)

    def update_status(self, status: str, suffix: str = "") -> None:
        with self._lock:
            self.current += 1
            if status == "ok":
                self.ok += 1
            elif status in ("timeout", "http_error", "parse_error"):
                self.err += 1
            self._push_event(suffix, status)
        self._render(force=False, suffix=suffix)

    def _push_event(self, suffix: str, status: str) -> None:
        if not suffix:
            return
        icons = {
            "ok": f"{c(BRIGHT_GREEN)}·{c(RESET)}",
            "empty": f"{c(DIM)}·{c(RESET)}",
            "timeout": f"{c(BRIGHT_YELLOW)}!{c(RESET)}",
            "http_error": f"{c(BRIGHT_RED)}x{c(RESET)}",
            "parse_error": f"{c(BRIGHT_RED)}x{c(RESET)}",
            "disabled": f"{c(DIM)}-{c(RESET)}",
        }
        icon = icons.get(status, "·")
        short = truncate_visible(suffix, max(20, term_width() // 2 - 4))
        line = f"  {icon} {c(DIM)}{short}{c(RESET)}"
        self.event_lines.append(line)
        if len(self.event_lines) > 100:
            self.event_lines = self.event_lines[-100:]

    def log(self, line: str) -> None:
        with self._lock:
            self.log_lines.append(line)
            if len(self.log_lines) > 200:
                self.log_lines = self.log_lines[-200:]
        self._render(force=False)

    def new_finding(self, url: str, engine: str,
                    severity: str = "other") -> None:
        with self._lock:
            self.found += 1
            short = url if len(url) <= 90 else url[:87] + "..."
            sev_badge = badge(severity)
            self.log_lines.append(
                f"{sev_badge} {c(BRIGHT_GREEN)}[+]{c(RESET)} {short} "
                f"{c(DIM)}({engine}){c(RESET)}"
            )
            if len(self.log_lines) > 200:
                self.log_lines = self.log_lines[-200:]
        self._render(force=True)

    def add_waf(self, name: str) -> None:
        with self._lock:
            self.waf_set.add(name)

    def _render(self, force: bool = False, suffix: str = "") -> None:
        if not self.enabled:
            return
        now = time.time()
        if not force and (now - self._last_render) < 0.08:
            return
        self._last_render = now

        with self._lock:
            current = self.current
            ok = self.ok
            err = self.err
            found = self.found
            waf_list = sorted(self.waf_set)
            logs = self.log_lines[-12:]
            events = self.event_lines[-8:]
            label = self._phase_label
            total = self.total

        cols = term_width()
        rows = term_height()
        elapsed = now - self._start_time

        left_width = max(30, int(cols * 0.55))
        right_width = max(20, cols - left_width - 3)

        left_lines: List[str] = []
        right_lines: List[str] = []

        bar_width = max(15, min(35, left_width - 10))
        pct = current / total if total else 0
        filled = int(bar_width * pct)
        if filled < bar_width:
            bar = "=" * max(0, filled - 1) + ">" + " " * (bar_width - filled)
        else:
            bar = "=" * bar_width

        left_lines.append(
            f"{c(BOLD)}{c(BRIGHT_CYAN)}denzyx-dork{c(RESET)} "
            f"{c(BRIGHT_MAGENTA)}v{VERSION}{c(RESET)}"
        )
        left_lines.append(
            f"{c(DIM)}phase:{c(RESET)} {c(BRIGHT_WHITE)}{label}{c(RESET)}"
        )
        left_lines.append(
            f"{c(DIM)}threads:{c(RESET)} {THREADS}  "
            f"{c(DIM)}waf:{c(RESET)}"
            f"{c(BRIGHT_GREEN) if WAF_BYPASS else c(BRIGHT_RED)}"
            f"{'ON' if WAF_BYPASS else 'OFF'}{c(RESET)}"
        )
        left_lines.append("")
        left_lines.append(
            f"{c(BRIGHT_CYAN)}[{current}/{total}]{c(RESET)}"
        )
        left_lines.append(f"{c(BRIGHT_GREEN)}{bar}{c(RESET)}")
        left_lines.append(
            f"{c(BRIGHT_YELLOW)}[{int(pct*100):>3}%]{c(RESET)} "
            f"{c(DIM)}elapsed {elapsed:.0f}s{c(RESET)}"
        )
        left_lines.append("")
        left_lines.append(
            f"{pill('ok ' + str(ok), BG_GREEN)}  "
            f"{pill('err ' + str(err), BG_RED)}  "
            f"{pill('hit ' + str(found), BG_MAGENTA)}"
        )
        if waf_list:
            left_lines.append("")
            left_lines.append(
                f"{c(BRIGHT_RED)}WAF:{c(RESET)} "
                f"{', '.join(waf_list[:3])}"
            )
        if suffix:
            left_lines.append("")
            left_lines.append(
                f"{c(DIM)}> {truncate_visible(suffix, left_width - 4)}{c(RESET)}"
            )

        right_lines.append(f"{c(BOLD)}{c(BRIGHT_CYAN)}EVENT STREAM{c(RESET)}")
        right_lines.append(f"{c(DIM)}{'-' * (right_width - 2)}{c(RESET)}")
        for e in events:
            right_lines.append(truncate_visible(e, right_width))

        out: List[str] = []
        out.append("\033[H")
        out.append("\033[2J")

        max_rows = max(len(left_lines), len(right_lines))
        sep = f"{c(BRIGHT_CYAN)}|{c(RESET)}"
        for i in range(max_rows):
            l = left_lines[i] if i < len(left_lines) else ""
            r = right_lines[i] if i < len(right_lines) else ""
            out.append(
                pad_visible(l, left_width)
                + "  " + sep + "  "
                + truncate_visible(r, right_width)
                + "\n"
            )

        remaining = rows - max_rows - 4
        if remaining > 0:
            out.append(f"{c(BRIGHT_CYAN)}{'-' * cols}{c(RESET)}\n")
            out.append(f"{c(BOLD)}{c(BRIGHT_CYAN)}FINDING LOG{c(RESET)}\n")
            shown = logs[-remaining:] if remaining > 0 else []
            for line in shown:
                out.append(truncate_visible(line, cols - 2) + "\n")

        with PRINT_LOCK:
            sys.stdout.write("".join(out))
            sys.stdout.flush()

    def finish(self) -> None:
        self._render(force=True)
        time.sleep(0.3)
        self.stop()


STOP_EVENT = threading.Event()


def request_stop() -> None:
    STOP_EVENT.set()


def reset_stop() -> None:
    STOP_EVENT.clear()


def is_stopped() -> bool:
    return STOP_EVENT.is_set()


class ScanSummary:
    def __init__(self) -> None:
        self.total_queries = 0
        self.total_engine_calls = 0
        self.ok = 0
        self.empty = 0
        self.timeout = 0
        self.http_error = 0
        self.parse_error = 0
        self.disabled = 0
        self.unique_urls = 0
        self.elapsed = 0.0
        self.waf_seen: Set[str] = set()

    def add(self, res: EngineResult) -> None:
        self.total_engine_calls += 1
        if res.status == "ok":
            self.ok += 1
        elif res.status == "empty":
            self.empty += 1
        elif res.status == "timeout":
            self.timeout += 1
        elif res.status == "http_error":
            self.http_error += 1
        elif res.status == "parse_error":
            self.parse_error += 1
        elif res.status == "disabled":
            self.disabled += 1
        if res.waf:
            self.waf_seen.add(res.waf)

    def render(self) -> None:
        print()
        print(f"  {c(BRIGHT_CYAN)}engine calls:{c(RESET)} {self.total_engine_calls}")
        print(f"  {c(BRIGHT_GREEN)}ok           :{c(RESET)} {self.ok}")
        print(f"  {c(DIM)}empty        :{c(RESET)} {self.empty}")
        print(f"  {c(BRIGHT_YELLOW)}timeout      :{c(RESET)} {self.timeout}")
        print(f"  {c(BRIGHT_RED)}http_error   :{c(RESET)} {self.http_error}")
        print(f"  {c(BRIGHT_RED)}parse_error  :{c(RESET)} {self.parse_error}")
        print(f"  {c(DIM)}disabled     :{c(RESET)} {self.disabled}")
        if self.waf_seen:
            print(f"  {c(BRIGHT_RED)}WAF          :{c(RESET)} "
                  f"{', '.join(sorted(self.waf_seen))}")
        print(f"  {c(BRIGHT_GREEN)}unique urls  :{c(RESET)} {self.unique_urls}")
        print(f"  {c(DIM)}elapsed      :{c(RESET)} {self.elapsed:.2f}s")


def scan(
    queries: List[str],
    engines: List[SearchEngine],
    store: ResultStore,
    show_progress: bool = True,
    waf_bypass: bool = True,
    live_label: str = "scanning",
) -> ScanSummary:
    reset_stop()
    summary = ScanSummary()
    summary.total_queries = len(queries)

    jobs = [(eng, q) for q in queries for eng in engines]
    total_jobs = len(jobs)

    display: Optional[SplitScreenDisplay] = None
    if show_progress:
        display = SplitScreenDisplay(total=total_jobs, label=live_label)
        display.start()

    start = time.time()

    def worker(eng: SearchEngine, query: str) -> EngineResult:
        if is_stopped():
            return EngineResult(eng.key, query, set(), "disabled")
        return eng.search(query, waf_bypass=waf_bypass)

    try:
        with ThreadPoolExecutor(max_workers=THREADS) as ex:
            futures = {ex.submit(worker, e, q): (e, q) for e, q in jobs}
            for fut in as_completed(futures):
                if is_stopped():
                    for f in futures:
                        f.cancel()
                    break
                eng, query = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = EngineResult(
                        eng.key, query, set(), "parse_error", str(e),
                    )
                summary.add(res)

                if display:
                    if res.waf:
                        display.add_waf(res.waf)

                for u in res.urls:
                    new_res = store.add(u, res.engine, res.query)
                    if new_res and display:
                        display.new_finding(u, res.engine, new_res.severity)

                if display:
                    suffix = f"{eng.name}: {query[:60]}"
                    display.update_status(res.status, suffix=suffix)
    finally:
        if display:
            display.finish()

    summary.unique_urls = store.size()
    summary.elapsed = time.time() - start
    return summary


def verify_live_urls(store: ResultStore,
                     display: Optional[SplitScreenDisplay] = None) -> int:
    results = store.all()
    if not results:
        return 0

    if display:
        display.set_label("verifying-live")
        display.set_total(len(results))

    def worker(res: Result) -> Tuple[str, int, Optional[str], bool, str, str,
                                     str, str, str, float]:
        try:
            resp = http_get(res.url, waf_bypass=WAF_BYPASS, method="GET",
                            timeout=TIMEOUT, retries=0)
            body = resp.text[:50000]
            is_idx = analyze_index_of(body) if resp.status == 200 else False
            title = analyze_title(body)
            preview = analyze_preview(body, 200)
            ctype = resp.headers.get("Content-Type", "")
            server = resp.headers.get("Server", "")
            powered = resp.headers.get("X-Powered-By", "")
            return (
                res.url, resp.status,
                resp.error if resp.error else None,
                is_idx, ctype, server, powered, title, preview,
                resp.elapsed,
            )
        except Exception as e:
            return (res.url, 0, str(e), False, "", "", "", "", "", 0.0)

    count_live = 0
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(worker, r): r for r in results}
        for fut in as_completed(futures):
            if is_stopped():
                for f in futures:
                    f.cancel()
                break
            try:
                (url, status, err, is_idx, ctype, server, powered,
                 title, preview, elapsed) = fut.result()
            except Exception:
                continue
            store.update_live(
                url, status, err, is_idx, ctype, server, powered,
                title, preview, elapsed,
            )
            if status == 200:
                count_live += 1
            if display:
                tag = "ok" if status == 200 else "err"
                suffix = f"[{status}] {url[:70]}"
                display.update_status(tag, suffix=suffix)
    return count_live


def enrich_geo(store: ResultStore,
               display: Optional[SplitScreenDisplay] = None) -> int:
    hosts = store.unique_hosts()
    if not hosts:
        return 0

    if display:
        display.set_label("enrich-geo")
        display.set_total(len(hosts))

    def resolve_host(host: str) -> Tuple[str, Optional[str]]:
        try:
            ip = socket.gethostbyname(host)
            return host, ip
        except Exception:
            return host, None

    host_ip: Dict[str, Optional[str]] = {}
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(resolve_host, h): h for h in hosts}
        for fut in as_completed(futures):
            if is_stopped():
                for f in futures:
                    f.cancel()
                break
            try:
                h, ip = fut.result()
                host_ip[h] = ip
            except Exception:
                continue
            if display:
                display.update_status("ok", suffix=f"resolve {h}")

    unique_ips = sorted({ip for ip in host_ip.values() if ip})
    if not unique_ips:
        return 0

    if display:
        display.set_label("enrich-ip")
        display.set_total(len(unique_ips))

    ip_info: Dict[str, Dict[str, Optional[str]]] = {}

    def geo_lookup(ip: str) -> Tuple[str, Dict[str, Optional[str]]]:
        info = {"country": None, "isp": None, "asn": None}
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,country,isp,as"
            resp = http_get(url, waf_bypass=False, timeout=8, retries=0)
            if resp.status == 200:
                data = json.loads(resp.text)
                if data.get("status") == "success":
                    info["country"] = data.get("country")
                    info["isp"] = data.get("isp")
                    info["asn"] = data.get("as")
        except Exception:
            pass
        return ip, info

    with ThreadPoolExecutor(max_workers=min(THREADS, 5)) as ex:
        futures = {ex.submit(geo_lookup, ip): ip for ip in unique_ips[:50]}
        for fut in as_completed(futures):
            if is_stopped():
                for f in futures:
                    f.cancel()
                break
            try:
                ip, info = fut.result()
                ip_info[ip] = info
            except Exception:
                continue
            if display:
                display.update_status("ok", suffix=f"geo {ip}")

    for res in store.all():
        ip = host_ip.get(res.host)
        if not ip or ip not in ip_info:
            continue
        info = ip_info[ip]
        store.update_enrich(
            res.url, ip,
            info.get("country"), info.get("isp"), info.get("asn"),
        )

    return len(ip_info)


def export_txt(results: List[Result], out_path: str) -> str:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# denzyx-dork export {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"# total: {len(results)}\n")
        f.write("=" * 72 + "\n\n")
        results_sorted = sorted(
            results,
            key=lambda r: (-SEVERITY_ORDER.get(r.severity, 0), r.url),
        )
        for r in results_sorted:
            f.write(f"[{r.severity.upper():>8}] {r.url}\n")
            f.write(f"           host     : {r.host}\n")
            f.write(f"           category : {r.category}\n")
            f.write(f"           engines  : {', '.join(sorted(r.engines))}\n")
            f.write(f"           live     : {r.live_status}\n")
            if r.is_index_of:
                f.write("           index-of : yes\n")
            if r.title:
                f.write(f"           title    : {r.title}\n")
            if r.server:
                f.write(f"           server   : {r.server}\n")
            if r.ip:
                f.write(f"           ip       : {r.ip}\n")
            if r.country:
                f.write(f"           country  : {r.country}\n")
            if r.isp:
                f.write(f"           isp      : {r.isp}\n")
            f.write(f"           seen     : {r.first_seen}\n\n")
    return str(path)


def export_json(results: List[Result], out_path: str) -> str:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "total": len(results),
        "results": [r.to_dict() for r in results],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(path)


def export_csv(results: List[Result], out_path: str) -> str:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "url", "host", "severity", "category", "live_status",
            "is_index_of", "content_type", "server", "powered_by",
            "title", "ip", "country", "isp", "asn",
            "engines", "queries", "first_seen",
        ])
        for r in sorted(results, key=lambda x: x.url):
            writer.writerow([
                r.url, r.host, r.severity, r.category, r.live_status,
                "yes" if r.is_index_of else "no",
                r.content_type, r.server, r.powered_by,
                r.title, r.ip or "", r.country or "", r.isp or "", r.asn or "",
                "|".join(sorted(r.engines)),
                "|".join(sorted(r.queries)),
                r.first_seen,
            ])
    return str(path)


def export_sqlite(results: List[Result], out_path: str) -> str:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE results (
            url TEXT PRIMARY KEY,
            host TEXT,
            severity TEXT,
            category TEXT,
            live_status INTEGER,
            is_index_of INTEGER,
            content_type TEXT,
            server TEXT,
            powered_by TEXT,
            title TEXT,
            preview TEXT,
            ip TEXT,
            country TEXT,
            isp TEXT,
            asn TEXT,
            engines TEXT,
            queries TEXT,
            elapsed REAL,
            first_seen TEXT
        )
    """)
    for r in results:
        cur.execute(
            "INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.url, r.host, r.severity, r.category, r.live_status,
                1 if r.is_index_of else 0,
                r.content_type, r.server, r.powered_by,
                r.title, r.preview[:500],
                r.ip, r.country, r.isp, r.asn,
                "|".join(sorted(r.engines)),
                "|".join(sorted(r.queries)),
                r.elapsed, r.first_seen,
            ),
        )
    conn.commit()
    conn.close()
    return str(path)


def export_html(results: List[Result], out_path: str) -> str:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    total = len(results)
    sev_count = {k: 0 for k in ("critical", "high", "medium", "low", "info", "other")}
    for r in results:
        sev_count[r.severity] = sev_count.get(r.severity, 0) + 1

    rows = []
    for r in sorted(results, key=lambda x: (-SEVERITY_ORDER.get(x.severity, 0), x.url)):
        sev = r.severity
        sev_color = {
            "critical": "#ff2e2e",
            "high": "#ff6b2e",
            "medium": "#ffb300",
            "low": "#4da3ff",
            "info": "#00d4d4",
            "other": "#888888",
        }.get(sev, "#888888")

        tag = ""
        if r.is_index_of:
            tag = '<span class="tag idx">INDEX</span>'
        if r.live_status == 200:
            tag += '<span class="tag live">LIVE</span>'

        geo = []
        if r.country:
            geo.append(r.country)
        if r.isp:
            geo.append(r.isp)
        if r.asn:
            geo.append(r.asn)
        geo_str = " / ".join(geo) if geo else ""

        rows.append(f"""
        <tr>
          <td><span class="sev" style="background:{sev_color}">{sev.upper()}</span></td>
          <td class="cat">{html_escape(r.category)}</td>
          <td class="url"><a href="{html_escape(r.url)}" target="_blank">{html_escape(r.url)}</a>{tag}</td>
          <td class="stat">{r.live_status}</td>
          <td class="srv">{html_escape(r.server or "-")}</td>
          <td class="ip">{html_escape(r.ip or "-")}</td>
          <td class="geo">{html_escape(geo_str)}</td>
          <td class="title">{html_escape(r.title or "-")}</td>
          <td class="eng">{html_escape(", ".join(sorted(r.engines)))}</td>
        </tr>""")

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>denzyx-dork report {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    background: #0a0e14;
    color: #c9d1d9;
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    font-size: 13px;
  }}
  h1 {{ color: #00ffcc; margin: 0 0 4px; font-size: 22px; }}
  h1 small {{ color: #6e7681; font-weight: 400; }}
  .meta {{ color: #6e7681; margin-bottom: 20px; }}
  .summary {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0 24px; }}
  .card {{
    background: #11161d; border-radius: 8px; padding: 14px 20px;
    min-width: 90px; text-align: center; border-left: 4px solid #30363d;
  }}
  .card .n {{ font-size: 24px; font-weight: 700; }}
  .card .l {{ color: #6e7681; font-size: 11px; letter-spacing: 1px; }}
  .card.crit {{ border-color: #ff2e2e; }} .card.crit .n {{ color: #ff2e2e; }}
  .card.high {{ border-color: #ff6b2e; }} .card.high .n {{ color: #ff6b2e; }}
  .card.med {{ border-color: #ffb300; }} .card.med .n {{ color: #ffb300; }}
  .card.low {{ border-color: #4da3ff; }} .card.low .n {{ color: #4da3ff; }}
  .card.info {{ border-color: #00d4d4; }} .card.info .n {{ color: #00d4d4; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th, td {{
    text-align: left; padding: 8px 10px;
    border-bottom: 1px solid #1c2128; vertical-align: top;
  }}
  th {{ background: #11161d; color: #00ffcc; font-size: 11px;
       letter-spacing: 1px; position: sticky; top: 0; }}
  tr:hover {{ background: #11161d; }}
  .sev {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
         color: #000; font-weight: 700; font-size: 10px; }}
  .tag {{ display: inline-block; margin-left: 8px; padding: 1px 6px;
         border-radius: 3px; font-size: 10px; font-weight: 700; }}
  .tag.idx {{ background: #00ffcc; color: #000; }}
  .tag.live {{ background: #2ea043; color: #fff; }}
  .url a {{ color: #58a6ff; text-decoration: none; word-break: break-all; }}
  .url a:hover {{ text-decoration: underline; }}
  .stat {{ color: #7ee787; font-weight: 600; }}
  .srv, .ip, .geo, .title, .eng {{ color: #8b949e; font-size: 12px; }}
  .title {{ max-width: 220px; overflow: hidden; text-overflow: ellipsis;
           white-space: nowrap; }}
</style>
</head>
<body>
<h1>denzyx-dork report</h1>
<small>v{VERSION} — {CODENAME}</small>
<div class="meta">
  Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
  &middot; {total} unique URL
</div>
<div class="summary">
  <div class="card crit"><div class="n">{sev_count['critical']}</div><div class="l">CRITICAL</div></div>
  <div class="card high"><div class="n">{sev_count['high']}</div><div class="l">HIGH</div></div>
  <div class="card med"><div class="n">{sev_count['medium']}</div><div class="l">MEDIUM</div></div>
  <div class="card low"><div class="n">{sev_count['low']}</div><div class="l">LOW</div></div>
  <div class="card info"><div class="n">{sev_count['info']}</div><div class="l">INFO</div></div>
</div>
<table>
  <thead>
    <tr>
      <th>SEV</th><th>CATEGORY</th><th>URL</th><th>STATUS</th>
      <th>SERVER</th><th>IP</th><th>GEO</th><th>TITLE</th><th>ENGINES</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
</body>
</html>"""
    with path.open("w", encoding="utf-8") as f:
        f.write(html)
    return str(path)


_LAST_STORE: Optional[ResultStore] = None
_LAST_SUMMARY: Optional[ScanSummary] = None


def print_banner() -> None:
    clear_screen()
    cols = term_width()
    banner_width = max(len(line) for line in BANNER_ART)
    width = min(cols, banner_width + 4)
    print()
    for line in BANNER_ART:
        print(f"{c(BRIGHT_CYAN)}{line.center(width)}{c(RESET)}")
    for line in BANNER_SUB:
        print(f"{c(BRIGHT_MAGENTA)}{line.center(width)}{c(RESET)}")
    print()
    print(f"  {c(BOLD)}{c(BRIGHT_CYAN)}denzyx-dork{c(RESET)} "
          f"{c(BRIGHT_MAGENTA)}v{VERSION}{c(RESET)} "
          f"{c(DIM)}{CODENAME}{c(RESET)}")
    print(f"  {c(DIM)}by {AUTHOR}{c(RESET)}")
    line_rule("", "=")
    print(f"  {c(BRIGHT_WHITE)}TLD       :{c(RESET)} {tld_count()} ekstensi")
    print(f"  {c(BRIGHT_WHITE)}Objective :{c(RESET)} {len(OBJECTIVES)} kategori")
    print(f"  {c(BRIGHT_WHITE)}Engine    :{c(RESET)} "
          f"{c(BRIGHT_GREEN)}{sum(1 for e in REGISTRY.all() if e.enabled)} aktif{c(RESET)} "
          f"{c(DIM)}/ {len(REGISTRY.all())} total{c(RESET)}")
    print(f"  {c(BRIGHT_WHITE)}Threads   :{c(RESET)} {THREADS}   "
          f"{c(BRIGHT_WHITE)}Timeout:{c(RESET)} {TIMEOUT}s")
    print(f"  {c(BRIGHT_WHITE)}WAF bypass:{c(RESET)} "
          f"{c(BRIGHT_GREEN) if WAF_BYPASS else c(BRIGHT_RED)}"
          f"{'ON' if WAF_BYPASS else 'OFF'}{c(RESET)}   "
          f"{c(BRIGHT_WHITE)}Cache:{c(RESET)} "
          f"{c(BRIGHT_GREEN) if CACHE_ENABLED else c(BRIGHT_RED)}"
          f"{'ON' if CACHE_ENABLED else 'OFF'}{c(RESET)}   "
          f"{c(BRIGHT_WHITE)}Verify:{c(RESET)} "
          f"{c(BRIGHT_GREEN) if VERIFY_LIVE else c(BRIGHT_RED)}"
          f"{'ON' if VERIFY_LIVE else 'OFF'}{c(RESET)}   "
          f"{c(BRIGHT_WHITE)}Enrich:{c(RESET)} "
          f"{c(BRIGHT_GREEN) if ENRICH_ENABLED else c(BRIGHT_RED)}"
          f"{'ON' if ENRICH_ENABLED else 'OFF'}{c(RESET)}")
    line_rule("", "=")
    print()


def _build_tld_columns(columns: int, col_width: int) -> List[str]:
    cell_width = max(col_width, 22)
    chunks: List[List[Tuple[str, List[Tuple[str, str]]]]] = []
    for i in range(0, len(TLD_GROUPS), columns):
        chunks.append(TLD_GROUPS[i:i + columns])

    lines: List[str] = []

    for chunk in chunks:
        header_line = ""
        for group_name, _ in chunk:
            cell = f"{c(BOLD)}{c(BRIGHT_YELLOW)}{group_name}{c(RESET)}"
            header_line += pad_visible(cell, cell_width)
        lines.append("  " + header_line.rstrip())

        body_rows = max(len(tlds) for _, tlds in chunk)
        for r in range(body_rows):
            row_line = ""
            for _, tlds in chunk:
                if r < len(tlds):
                    ext, desc = tlds[r]
                    cell = (f"{c(BRIGHT_GREEN)}{ext}{c(RESET)} "
                            f"{c(DIM)}{desc}{c(RESET)}")
                else:
                    cell = ""
                row_line += pad_visible(cell, cell_width)
            lines.append("  " + row_line.rstrip())

        lines.append("")

    return lines


def show_tld_menu() -> Dict[str, str]:
    section_header("DAFTAR TLD TERSEDIA")
    index_map: Dict[str, str] = {}
    counter = 1

    for _, tlds in TLD_GROUPS:
        for ext, _ in tlds:
            index_map[str(counter)] = ext
            counter += 1

    cols = term_width()
    if cols >= 150:
        num_cols = 6
        col_width = (cols - 2) // num_cols
    elif cols >= 120:
        num_cols = 5
        col_width = (cols - 2) // num_cols
    elif cols >= 90:
        num_cols = 4
        col_width = (cols - 2) // num_cols
    elif cols >= 60:
        num_cols = 3
        col_width = (cols - 2) // num_cols
    elif cols >= 40:
        num_cols = 2
        col_width = (cols - 2) // num_cols
    else:
        num_cols = 1
        col_width = cols - 2

    print()
    for line in _build_tld_columns(num_cols, col_width):
        print(line)

    line_rule("", "-")
    print(f"  {c(BRIGHT_YELLOW)}[99]{c(RESET)} Pilih SEMUA TLD ({counter - 1} ekstensi)")
    print(f"  {c(BRIGHT_YELLOW)}[0] {c(RESET)} Input TLD manual")
    print(f"  {c(BRIGHT_YELLOW)}[q] {c(RESET)} Batal")
    print(f"  {c(DIM)}Catatan: masukkan nomor urut global (contoh: 1, 40, 85){c(RESET)}")
    print()
    return index_map


def parse_index_list(raw: str) -> List[str]:
    return [p for p in re.split(r"[\s,]+", raw) if p]


def select_tlds() -> Optional[List[str]]:
    index_map = show_tld_menu()
    valid_set = set(all_tlds())
    while True:
        raw = ask("Masukan input TLD (contoh: 1,2,3 / 99 / 0): ").strip().lower()
        if raw in ("q", "quit", "exit"):
            return None
        if raw == "99":
            tlds = all_tlds()
            success(f"Dipilih: {len(tlds)} TLD (semua)")
            return tlds
        if raw == "0":
            manual = ask("Masukan TLD manual (pisah koma): ").strip()
            if not manual:
                warning("Kosong, coba lagi")
                continue
            tlds = []
            for t in manual.split(","):
                t = t.strip()
                if not t:
                    continue
                if not t.startswith("."):
                    t = "." + t
                if t not in valid_set:
                    warning(f"TLD tidak dikenal: {t}")
                    continue
                tlds.append(t)
            if tlds:
                success(f"Dipilih: {', '.join(tlds)}")
                return tlds
            continue
        selected, invalid = [], []
        for p in parse_index_list(raw):
            if p in index_map:
                ext = index_map[p]
                if ext not in selected:
                    selected.append(ext)
            else:
                invalid.append(p)
        if invalid:
            warning(f"Nomor tidak valid: {', '.join(invalid)}")
            continue
        if selected:
            success(f"Dipilih: {', '.join(selected)}")
            return selected


def show_objective_menu() -> None:
    section_header(f"DAFTAR TUJUAN DORK ({len(OBJECTIVES)} kategori)")
    cols = term_width()
    if cols >= 110:
        num_cols = 2
    else:
        num_cols = 1

    entries = []
    for key, obj in OBJECTIVES.items():
        entries.append((key, obj.name, len(obj.patterns)))

    if num_cols == 1:
        for key, name, plen in entries:
            print(f"  {c(BRIGHT_GREEN)}[{key:>2}]{c(RESET)} "
                  f"{name:<28} {c(DIM)}({plen} pattern){c(RESET)}")
    else:
        cell_width = max(42, (cols - 2) // num_cols)
        for i in range(0, len(entries), num_cols):
            row = entries[i:i + num_cols]
            line = "  "
            for key, name, plen in row:
                cell = (f"{c(BRIGHT_GREEN)}[{key:>2}]{c(RESET)} "
                        f"{name:<28} {c(DIM)}({plen}p){c(RESET)}")
                line += pad_visible(cell, cell_width)
            print(line.rstrip())

    line_rule("", "-")
    print(f"  {c(BRIGHT_YELLOW)}[99]{c(RESET)} FULL semua tujuan digabung")
    print(f"  {c(BRIGHT_YELLOW)}[0] {c(RESET)} Input pattern manual")
    print(f"  {c(BRIGHT_YELLOW)}[q] {c(RESET)} Batal")
    print()


def select_objectives() -> Optional[List[str]]:
    show_objective_menu()
    while True:
        raw = ask("Masukan input tujuan (contoh: 1,2,3 / 99 / 0): ").strip().lower()
        if raw in ("q", "quit", "exit"):
            return None
        if raw == "99":
            patterns = all_patterns()
            success(f"Dipilih FULL: {len(patterns)} pattern unik")
            return patterns
        if raw == "0":
            manual = ask("Masukan pattern manual (pisah dengan | ): ").strip()
            if not manual:
                warning("Kosong, coba lagi")
                continue
            patterns = [p.strip() for p in manual.split("|") if p.strip()]
            if patterns:
                success(f"Dipilih: {len(patterns)} pattern manual")
                return patterns
            continue
        selected, invalid = [], []
        for p in parse_index_list(raw):
            if p in OBJECTIVES:
                for pat in OBJECTIVES[p].patterns:
                    if pat not in selected:
                        selected.append(pat)
            else:
                invalid.append(p)
        if invalid:
            warning(f"Nomor tidak valid: {', '.join(invalid)}")
            continue
        if selected:
            success(f"Dipilih: {len(selected)} pattern")
            return selected


def select_engines() -> None:
    while True:
        section_header(f"DAFTAR SEARCH ENGINE ({len(REGISTRY.all())} total)")
        engines = REGISTRY.all()
        cols = term_width()
        if cols >= 110:
            num_cols = 2
        else:
            num_cols = 1

        entries = []
        for i, e in enumerate(engines, 1):
            entries.append((i, e.name, e.enabled))

        if num_cols == 1:
            for i, name, en in entries:
                status = (f"{c(BRIGHT_GREEN)}AKTIF{c(RESET)}"
                          if en else f"{c(BRIGHT_RED)}NONAKTIF{c(RESET)}")
                print(f"  {c(BRIGHT_YELLOW)}[{i:>2}]{c(RESET)} {name:<14} {status}")
        else:
            cell_width = max(34, (cols - 2) // num_cols)
            for i in range(0, len(entries), num_cols):
                row = entries[i:i + num_cols]
                line = "  "
                for num, name, en in row:
                    status = (f"{c(BRIGHT_GREEN)}ON{c(RESET)}"
                              if en else f"{c(BRIGHT_RED)}OFF{c(RESET)}")
                    cell = (f"{c(BRIGHT_YELLOW)}[{num:>2}]{c(RESET)} "
                            f"{name:<12} {status}")
                    line += pad_visible(cell, cell_width)
                print(line.rstrip())

        line_rule("", "-")
        print(f"  {c(BRIGHT_YELLOW)}[a]{c(RESET)} Aktifkan SEMUA engine")
        print(f"  {c(BRIGHT_YELLOW)}[n]{c(RESET)} Nonaktifkan SEMUA engine")
        print(f"  {c(BRIGHT_YELLOW)}[r]{c(RESET)} Reset ke default")
        print(f"  {c(BRIGHT_YELLOW)}[q]{c(RESET)} Kembali")
        print()
        raw = ask("Toggle engine (contoh: 1,3,5 / a / n / r / q): ").strip().lower()
        if raw in ("q", "quit", "exit"):
            return
        if raw == "a":
            for e in engines:
                e.enabled = True
            success(f"Semua engine diaktifkan ({len(engines)})")
            continue
        if raw == "n":
            for e in engines:
                e.enabled = False
            success("Semua engine dinonaktifkan")
            continue
        if raw == "r":
            defaults = {"duckduckgo", "bing", "yandex", "mojeek", "marginalia"}
            for e in engines:
                e.enabled = e.key in defaults
            success("Reset ke default (5 engine aktif)")
            continue
        if not raw:
            return
        changed = 0
        for p in parse_index_list(raw):
            try:
                idx = int(p) - 1
            except ValueError:
                warning(f"Nomor tidak valid: {p}")
                continue
            if 0 <= idx < len(engines):
                e = engines[idx]
                e.enabled = not e.enabled
                changed += 1
                success(f"{e.name} -> {'AKTIF' if e.enabled else 'NONAKTIF'}")
            else:
                warning(f"Diluar range: {p}")
        if changed == 0:
            time.sleep(0.4)


def print_grouped_results(store: ResultStore) -> None:
    buckets = store.by_category()
    titles = {
        "config": ("CONFIG FILES", BRIGHT_RED),
        "backup": ("BACKUP FILES", BRIGHT_RED),
        "admin": ("ADMIN PANEL", BRIGHT_YELLOW),
        "database": ("DATABASE", BRIGHT_RED),
        "upload": ("UPLOAD DIRECTORY", BRIGHT_MAGENTA),
        "log": ("LOG FILES", BRIGHT_BLUE),
        "shell-indicator": ("SHELL INDICATORS", BRIGHT_RED),
        "panel": ("PANEL & LOGIN", BRIGHT_YELLOW),
        "document": ("DOCUMENTS", BRIGHT_CYAN),
        "media": ("IMAGES & MEDIA", BRIGHT_MAGENTA),
        "archive": ("ARCHIVES", BRIGHT_RED),
        "index-of": ("INDEX OF /", BRIGHT_GREEN),
        "other": ("LAINNYA", BRIGHT_CYAN),
    }
    for cat, (title, color) in titles.items():
        items = buckets.get(cat, [])
        if not items:
            continue
        section_header(f"{title} ({len(items)} URL)", color)
        for r in items:
            sev_tag = badge(r.severity)
            live_tag = ""
            if r.live_status == 200:
                live_tag = f" {c(BRIGHT_GREEN)}[LIVE]{c(RESET)}"
            elif r.live_status in (301, 302):
                live_tag = f" {c(BRIGHT_YELLOW)}[{r.live_status}]{c(RESET)}"
            elif r.live_status >= 400:
                live_tag = f" {c(BRIGHT_RED)}[{r.live_status}]{c(RESET)}"
            idx_tag = ""
            if r.is_index_of:
                idx_tag = f" {c(BRIGHT_CYAN)}[IDX]{c(RESET)}"
            print(f"{sev_tag}{live_tag}{idx_tag} {r.url}")
            if r.title:
                print(f"      {c(DIM)}title : {r.title[:80]}{c(RESET)}")
            if r.server or r.powered_by:
                parts = []
                if r.server:
                    parts.append(f"server={r.server}")
                if r.powered_by:
                    parts.append(f"powered={r.powered_by}")
                print(f"      {c(DIM)}{' '.join(parts)}{c(RESET)}")
            if r.ip:
                geo = []
                if r.country:
                    geo.append(r.country)
                if r.isp:
                    geo.append(r.isp)
                geo_str = f" ({', '.join(geo)})" if geo else ""
                print(f"      {c(DIM)}ip={r.ip}{geo_str}{c(RESET)}")


def print_summary_dashboard(summary: ScanSummary, store: ResultStore,
                            verified: int, geo_count: int) -> None:
    section_header("SUMMARY DASHBOARD")
    sev = store.by_severity()

    cards = [
        ("CRITICAL", sev.get("critical", []), BRIGHT_RED, BG_RED),
        ("HIGH", sev.get("high", []), BRIGHT_RED, BG_RED),
        ("MEDIUM", sev.get("medium", []), BRIGHT_YELLOW, BG_YELLOW),
        ("LOW", sev.get("low", []), BRIGHT_BLUE, BG_BLUE),
        ("INFO", sev.get("info", []), BRIGHT_CYAN, BG_CYAN),
    ]

    print()
    for label, items, fg, bg in cards:
        count = len(items)
        if count == 0:
            continue
        bar_len = min(40, count)
        bar = "█" * bar_len
        print(f"  {pill(label.ljust(8), bg)} "
              f"{c(fg)}{bar}{c(RESET)} {c(BOLD)}{count}{c(RESET)}")

    print()
    line_rule("", "-")
    print(f"  {c(BRIGHT_CYAN)}query total     :{c(RESET)} {summary.total_queries}")
    print(f"  {c(BRIGHT_CYAN)}engine calls    :{c(RESET)} {summary.total_engine_calls}")
    print(f"  {c(BRIGHT_GREEN)}unique urls     :{c(RESET)} {store.size()}")
    print(f"  {c(BRIGHT_GREEN)}live 200 ok     :{c(RESET)} {verified}")
    print(f"  {c(BRIGHT_CYAN)}geolocated      :{c(RESET)} {geo_count}")
    print(f"  {c(BRIGHT_CYAN)}unique hosts    :{c(RESET)} {len(store.unique_hosts())}")
    if summary.waf_seen:
        print(f"  {c(BRIGHT_RED)}waf detected    :{c(RESET)} "
              f"{', '.join(sorted(summary.waf_seen))}")
    print(f"  {c(DIM)}elapsed         :{c(RESET)} {summary.elapsed:.2f}s")


def run_scan_flow() -> None:
    global _LAST_STORE, _LAST_SUMMARY
    tlds = select_tlds()
    if not tlds:
        return
    patterns = select_objectives()
    if not patterns:
        return

    queries = build_queries(tlds, patterns)
    engines = REGISTRY.enabled()
    if not engines:
        error("Tidak ada engine aktif.")
        return

    section_header("KONFIGURASI SCAN")
    print(f"  {c(BRIGHT_WHITE)}TLD             :{c(RESET)} {len(tlds)}")
    print(f"  {c(BRIGHT_WHITE)}Pattern         :{c(RESET)} {len(patterns)}")
    print(f"  {c(BRIGHT_WHITE)}Total query     :{c(RESET)} {len(queries)}")
    print(f"  {c(BRIGHT_WHITE)}Engine aktif    :{c(RESET)} "
          f"{', '.join(e.name for e in engines)}")
    print(f"  {c(BRIGHT_WHITE)}Total job       :{c(RESET)} "
          f"{len(queries) * len(engines)}")
    print(f"  {c(BRIGHT_WHITE)}Threads         :{c(RESET)} {THREADS}")
    print(f"  {c(BRIGHT_WHITE)}WAF bypass      :{c(RESET)} "
          f"{'ON' if WAF_BYPASS else 'OFF'}")
    print(f"  {c(BRIGHT_WHITE)}Verify live     :{c(RESET)} "
          f"{'ON' if VERIFY_LIVE else 'OFF'}")
    print(f"  {c(BRIGHT_WHITE)}Geo enrich      :{c(RESET)} "
          f"{'ON' if ENRICH_ENABLED else 'OFF'}")
    print()

    if ask("Mulai scan? [y/N]: ").lower() != "y":
        return

    store = ResultStore()
    _LAST_STORE = store

    print()
    print(f"{c(BRIGHT_YELLOW)}memulai live scan (split-screen mode)...{c(RESET)}")
    time.sleep(0.6)

    summary = scan(
        queries=queries, engines=engines, store=store,
        show_progress=True, waf_bypass=WAF_BYPASS,
        live_label="dork-scan",
    )
    _LAST_SUMMARY = summary

    verified = 0
    geo_count = 0

    if VERIFY_LIVE and store.size() > 0:
        print()
        print(f"{c(BRIGHT_YELLOW)}verifikasi live status...{c(RESET)}")
        time.sleep(0.4)
        display = SplitScreenDisplay(total=store.size(), label="verifying-live")
        display.start()
        try:
            verified = verify_live_urls(store, display)
        finally:
            display.finish()

    if ENRICH_ENABLED and store.size() > 0:
        print()
        print(f"{c(BRIGHT_YELLOW)}enrichment ip & geo...{c(RESET)}")
        time.sleep(0.4)
        display = SplitScreenDisplay(total=store.size(), label="enrich")
        display.start()
        try:
            geo_count = enrich_geo(store, display)
        finally:
            display.finish()

    print()
    print_summary_dashboard(summary, store, verified, geo_count)
    print()
    print_grouped_results(store)


def custom_query_flow() -> None:
    global _LAST_STORE, _LAST_SUMMARY
    q = ask("Masukan query (contoh: site:.co.id index of /): ").strip()
    if not q:
        return
    engines = REGISTRY.enabled()
    if not engines:
        error("aktifin dulu engine di opsi 4.")
        return
    store = ResultStore()
    _LAST_STORE = store
    print()
    print(f"{c(BRIGHT_YELLOW)}memulai live scan...{c(RESET)}")
    time.sleep(0.6)
    summary = scan([q], engines, store, show_progress=True,
                   waf_bypass=WAF_BYPASS, live_label="custom-query")
    _LAST_SUMMARY = summary

    verified = 0
    geo_count = 0

    if VERIFY_LIVE and store.size() > 0:
        print()
        print(f"{c(BRIGHT_YELLOW)}verifikasi live status...{c(RESET)}")
        display = SplitScreenDisplay(total=store.size(), label="verifying-live")
        display.start()
        try:
            verified = verify_live_urls(store, display)
        finally:
            display.finish()

    if ENRICH_ENABLED and store.size() > 0:
        print()
        print(f"{c(BRIGHT_YELLOW)}enrichment ip & geo...{c(RESET)}")
        display = SplitScreenDisplay(total=store.size(), label="enrich")
        display.start()
        try:
            geo_count = enrich_geo(store, display)
        finally:
            display.finish()

    print()
    print_summary_dashboard(summary, store, verified, geo_count)
    print()
    print_grouped_results(store)


def export_flow() -> None:
    global _LAST_STORE
    if _LAST_STORE is None or _LAST_STORE.size() == 0:
        warning("belum ada hasil untuk diexport.")
        return

    section_header("EXPORT HASIL")
    print(f"  {c(BRIGHT_YELLOW)}[1]{c(RESET)} TXT report")
    print(f"  {c(BRIGHT_YELLOW)}[2]{c(RESET)} JSON")
    print(f"  {c(BRIGHT_YELLOW)}[3]{c(RESET)} CSV")
    print(f"  {c(BRIGHT_YELLOW)}[4]{c(RESET)} SQLite database")
    print(f"  {c(BRIGHT_YELLOW)}[5]{c(RESET)} HTML report (recommended)")
    print(f"  {c(BRIGHT_YELLOW)}[6]{c(RESET)} Semua format")
    print(f"  {c(BRIGHT_YELLOW)}[0]{c(RESET)} Kembali")
    print()
    choice = ask("Pilih format: ").strip()
    if choice == "0" or choice not in ("1", "2", "3", "4", "5", "6"):
        return
    name = ask("Nama file (tanpa ekstensi, ENTER=timestamp): ").strip()
    if not name:
        name = "denzyx_dork_" + time.strftime("%Y%m%d_%H%M%S")
    results = _LAST_STORE.all()
    out_dir = "resultscan"
    os.makedirs(out_dir, exist_ok=True)
    try:
        if choice in ("1", "6"):
            success(f"TXT    : {export_txt(results, f'{out_dir}/{name}.txt')}")
        if choice in ("2", "6"):
            success(f"JSON   : {export_json(results, f'{out_dir}/{name}.json')}")
        if choice in ("3", "6"):
            success(f"CSV    : {export_csv(results, f'{out_dir}/{name}.csv')}")
        if choice in ("4", "6"):
            success(f"SQLite : {export_sqlite(results, f'{out_dir}/{name}.db')}")
        if choice in ("5", "6"):
            success(f"HTML   : {export_html(results, f'{out_dir}/{name}.html')}")
    except OSError as e:
        error(f"gagal export: {e}")


def settings_flow() -> None:
    global THREADS, TIMEOUT, RETRIES, CACHE_ENABLED, DEBUG, WAF_BYPASS
    global VERIFY_LIVE, ENRICH_ENABLED, CINEMATIC_MODE
    while True:
        print_banner()
        section_header("SETTINGS")
        print(f"  {c(BRIGHT_YELLOW)}[1]{c(RESET)} Threads         : {THREADS}")
        print(f"  {c(BRIGHT_YELLOW)}[2]{c(RESET)} Timeout         : {TIMEOUT}s")
        print(f"  {c(BRIGHT_YELLOW)}[3]{c(RESET)} Retries         : {RETRIES}")
        print(f"  {c(BRIGHT_YELLOW)}[4]{c(RESET)} Cache           : "
              f"{'ON' if CACHE_ENABLED else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[5]{c(RESET)} WAF bypass      : "
              f"{'ON' if WAF_BYPASS else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[6]{c(RESET)} Debug           : "
              f"{'ON' if DEBUG else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[7]{c(RESET)} Verify live     : "
              f"{'ON' if VERIFY_LIVE else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[8]{c(RESET)} Enrich geo/ip   : "
              f"{'ON' if ENRICH_ENABLED else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[9]{c(RESET)} Cinematic boot  : "
              f"{'ON' if CINEMATIC_MODE else 'OFF'}")
        print(f"  {c(BRIGHT_YELLOW)}[0]{c(RESET)} Kembali")
        print()
        c_in = ask("Pilih setting: ").strip()
        if c_in == "0":
            return
        try:
            if c_in == "1":
                THREADS = max(1, int(ask("Threads baru: ")))
                success(f"Threads = {THREADS}")
            elif c_in == "2":
                TIMEOUT = max(5, int(ask("Timeout baru (detik): ")))
                success(f"Timeout = {TIMEOUT}")
            elif c_in == "3":
                RETRIES = max(0, int(ask("Retries baru: ")))
                success(f"Retries = {RETRIES}")
            elif c_in == "4":
                CACHE_ENABLED = not CACHE_ENABLED
                success(f"Cache = {'ON' if CACHE_ENABLED else 'OFF'}")
            elif c_in == "5":
                WAF_BYPASS = not WAF_BYPASS
                success(f"WAF bypass = {'ON' if WAF_BYPASS else 'OFF'}")
            elif c_in == "6":
                DEBUG = not DEBUG
                success(f"Debug = {'ON' if DEBUG else 'OFF'}")
            elif c_in == "7":
                VERIFY_LIVE = not VERIFY_LIVE
                success(f"Verify live = {'ON' if VERIFY_LIVE else 'OFF'}")
            elif c_in == "8":
                ENRICH_ENABLED = not ENRICH_ENABLED
                success(f"Enrich = {'ON' if ENRICH_ENABLED else 'OFF'}")
            elif c_in == "9":
                CINEMATIC_MODE = not CINEMATIC_MODE
                success(f"Cinematic = {'ON' if CINEMATIC_MODE else 'OFF'}")
            else:
                warning("pilihan tidak valid")
        except ValueError:
            warning("input harus angka")


def install_signal_handler() -> None:
    def _handler(signum, frame):
        request_stop()
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.write("\033[?1049l")
            sys.stdout.flush()
        except OSError:
            pass
        warning("dihentikan oleh user (Ctrl+C)")
    try:
        signal.signal(signal.SIGINT, _handler)
    except (ValueError, OSError):
        pass


def main() -> None:
    install_signal_handler()
    cinematic_boot()
    while True:
        try:
            print_banner()
            print(f"  {c(BRIGHT_YELLOW)}[1]{c(RESET)} Search (dork scan)")
            print(f"  {c(BRIGHT_YELLOW)}[2]{c(RESET)} Pilih Objective")
            print(f"  {c(BRIGHT_YELLOW)}[3]{c(RESET)} Pilih TLD")
            print(f"  {c(BRIGHT_YELLOW)}[4]{c(RESET)} Pilih Search Engine")
            print(f"  {c(BRIGHT_YELLOW)}[5]{c(RESET)} Custom Query")
            print(f"  {c(BRIGHT_YELLOW)}[6]{c(RESET)} Settings")
            print(f"  {c(BRIGHT_YELLOW)}[7]{c(RESET)} Export Results")
            print(f"  {c(BRIGHT_YELLOW)}[8]{c(RESET)} Cinematic Boot (replay)")
            print(f"  {c(BRIGHT_YELLOW)}[0]{c(RESET)} Exit")
            print()
            choice = ask("dork > ").strip()
            if choice == "0":
                print()
                typewriter("  terminal shutting down ...", 0.02, BRIGHT_YELLOW)
                time.sleep(0.4)
                info("keluar...")
                sys.exit(0)
            elif choice == "1":
                run_scan_flow()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "2":
                show_objective_menu()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "3":
                show_tld_menu()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "4":
                select_engines()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "5":
                custom_query_flow()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "6":
                settings_flow()
            elif choice == "7":
                export_flow()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            elif choice == "8":
                cinematic_boot()
                ask(f"\n{c(BRIGHT_CYAN)}ENTER untuk kembali...{c(RESET)}")
            else:
                warning("pilihan tidak valid")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()
            warning("interrupted, kembali ke menu.")
            continue
        except Exception as e:
            error(f"error: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{c(BRIGHT_YELLOW)}exit{c(RESET)}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{c(BRIGHT_RED)}fatal: {e}{c(RESET)}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)
