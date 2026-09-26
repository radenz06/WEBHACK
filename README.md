# Denzyx Tools Suite v4.0.1

Toolkit pentest & recon komersial dengan sistem lisensi terproteksi.
Dua tool utama: `xweb.py` (web vulnerability scanner) dan `scan2.py` (terminal dorking engine).

Version: 4.0.1
Author: denzyx
License: Proprietary - Commercial

---

## Daftar Isi

1. [Fitur](#fitur)
2. [Struktur Project](#struktur-project)
3. [Instalasi](#instalasi)
4. [Setup Developer](#setup-developer)
5. [Cara Pakai Client](#cara-pakai-client)
6. [Konfigurasi](#konfigurasi)
7. [Build Distribusi](#build-distribusi)
8. [License Server (Opsional)](#license-server-opsional)光
9. [Keamanan](#keamanan)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)
12. [Kontak](#kontak)

---

## Fitur

### xweb.py - Web Vulnerability Scanner

22 phase pentest lengkap dalam satu tool:

| Phase | Nama | Deskripsi |
|-------|------|-----------|
| 1 | Recon | DNS, WHOIS, SSL/TLS info, tech fingerprint, security headers, robots.txt |
| 2 | Port Scan | 100+ common port + banner grabbing |
| 3 | Subdomain Enum | 100+ subdomain built-in wordlist |
| 4 | Directory Brute Force | Smart 404 baseline + recursive scan |
| 5 | SQL Injection | Error-based, boolean-based, time-based, union-based + WAF bypass |
| 6 | XSS | Reflected, DOM, stored |
| 7 | LFI | Local File Inclusion + PHP wrappers |
| 8 | SSRF | Cloud metadata + internal IP + file protocol |
| 9 | Open Redirect | 25+ payload variasi |
| 10 | Sensitive Files | 90+ file sensitif (config, backup, .git, .env, dll) |
| 11 | JWT Analyzer | Weak secret, kid path traversal, jku |
| 12 | Subdomain Takeover | 40+ service signature |
| 13 | CSRF Analyzer | Missing/weak token detection |
| 14 | HTTP Method Checker | Dangerous method detection |
| 15 | Cookie Analyzer | HttpOnly, Secure, SameSite flag check |
| 16 | CORS Misconfig | Wildcard, reflected origin, null origin |
| 17 | GraphQL Introspection | Auto endpoint discovery + schema leak |
| 18 | API Key Leak | 40+ regex pattern (AWS, GCP, Stripe, GitHub, dll) |
| 19 | XXE Detector | XML External Entity injection |
| 20 | SSTI | Server-Side Template Injection (11 test) |
| 21 | Command Injection | Shell command injection |
| 22 | Report Generator | JSON + HTML report |

Fitur tambahan:
- Auto-PoC pada temuan critical
- Prompt next/skip/cancel untuk critical finding
- Resource dumper (crawler + ZIP archive)
- Path preset (Termux, Android SD, Linux, custom)
- Custom filename report

### scan2.py - Terminal Dorking Engine

| Fitur | Detail |
|-------|--------|
| TLD Database | 84 ekstensi di 60+ negara |
| Objective | 24 kategori dork (135+ pattern unik) |
| Search Engine | 26 engine (DuckDuckGo, Bing, Yandex, Google, Baidu, Qwant, dll) |
| WAF Bypass | 8 user-agent rotation + 24 header spoofer + 11 encoder |
| Live Verification | Cek status HTTP + index of validator |
| Geo Enrichment | Resolve IP + geolocation (country, ISP, ASN) |
| Live Display | Split-screen progress bar + event stream realtime |
| Export | TXT, JSON, CSV, SQLite, HTML report |
| Cache | TTL cache untuk query yang sama |

---

## Struktur Project

```
WEBHACK/
├── __init__.py
├── _core/
│   ├── __init__.py
│   ├── guard.py             (module proteksi)
│   ├── payment.py           (payment guard + Telegram notify)
│   └── util.py              (helper umum)
├── _dev/
│   ├── __init__.py
│   ├── config_tool.py       (developer: bikin config)
│   ├── make_qr.py           (developer: convert QR Dana)
│   ├── license_issue.py     (developer: bikin license key)
│   └── build.sh             (developer: obfuscate)
├── _server/
│   ├── __init__.py
│   ├── server.py            (opsional: license server VPS)
│   └── requirements.txt
├── config.json              (terenkripsi, hasil dari config_tool)
├── dana_qr.txt              (hasil dari make_qr)
├── .license.key             (auto-saved license key)
├── .guard_state.json        (state HWID, last run)
├── xweb.py                  (tool 1, sudah diintegrasi guard)
├── scan2.py                 (tool 2, sudah diintegrasi guard)
└── README.md
```

---

## Instalasi

### Prasyarat

- Python 3.8+
- Termux (Android) atau Linux

```bash
# Install dependencies
pip install requests beautifulsoup4

# Klau mo scan QR
pip install pyzbar Pillow
```

### Clone / Extract

```bash
cd ~/WEBHACK
```

---

## Setup Developer

### 1. Generate License Key

```bash
cd ~/WEBHACK
python3 _dev/license_issue.py
```

Pilih `[1]` untuk generate license untuk device ini, atau `[2]` untuk HWID custom.

### 2. Buat Config

```bash
python3 _dev/config_tool.py
```

Pilih `[1]` → masukkan license key → set threads/timeout → config.json terenkripsi otomatis bikin.

### 3. Verify

```bash
python3 xweb.py
```

Harusnya masuk menu utama tanpa error "LICENSE REQUIRED".

---

## Cara Pakai Client

### xweb.py - Web Vulnerability Scanner

```bash
cd ~/WEBHACK
python3 xweb.py
```

Menu:
```
[1]  FULL SCAN (All 24 Phases + Auto-PoC)
[2]  Recon
[3]  Port Scan + Banner Grab
...
[24] Backup File Finder
[25] Dump Resources (Crawler + ZIP)
[26] About
[0]  Exit
```

### scan2.py - Terminal Dorking Engine

```bash
cd ~/WEBHACK
python3 scan2.py
```

Menu:
```
[1] Search (dork scan)
[2] Pilih Objective
[3] Pilih TLD
[4] Pilih Search Engine
[5] Custom Query
[6] Settings
[7] Export Results
[0] Exit
```

---

## Konfigurasi

Edit `config.json` (terenkripsi) via config_tool:

```bash
python3 _dev/config_tool.py
```

Pilih `[2]` untuk load config, `[3]` untuk generate license key baru.

---

## Build Distribusi

```bash
cd ~/WEBHACK/_dev
bash build.sh
```

Hasil: `webhack_dist_YYYYMMDD_HHMMSS.tar.gz` — semua file terenkripsi + di-obfuscate.

---

## License Server (Opsional)

Jalankan server VPS:

```bash
cd ~/WEBHACK/_server
pip install -r requirements.txt
python3 server.py
```

Default: `0.0.0.0:8443`

Endpoint:
- `GET /health` - Cek server hidup
- `GET /validate?key=W4-...&hwid=...` - Validasi license
- `POST /issue` - Issue license baru (body: `{"hwid":"...","note":"...","days":365}`)
- `GET /keys` - List semua license

---

## Keamanan

- HWID-based device fingerprint (SHA-256)
- XOR-encrypted config.json
- License key tied ke HWID device
- Guard check di setiap tool utama
- Obfuscation saat build distribusi

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `LICENSE REQUIRED` | Jalankan `_dev/license_issue.py` dulu |
| `ModuleNotFoundError` | `pip install requests beautifulsoup4` |
| Scan lambat | Turunin threads di config_tool |
| HWID berubah | Device berubah (reset?), re-issue license |
| config.json corrupt | Hapus config.json, bikin ulang via config_tool |

---

## FAQ

**Q: System pembayaran?**
A: Target run tool → QR Dana tampil → scan + bayar → notif Telegram → tool jalan.

**Q: Cara setting Telegram?**
A: Edit `~/WEBHACK/config.json` (terenkripsi) atau set env:
    export WEBHACK_BOT_TOKEN="xxx:YYY"
    export WEBHACK_CHAT_ID="123456789"

**Q: Cara setting QR Dana?**
A: Upload foto QR Dana ke catbox.moe → dapatkan URL → set di config.json:
    "telegram": { "catbox_url": "https://catbox.moe/xxxx.png" }

**Q: Cara setting nomor Dana?**
A: Set di config.json atau env:
    export WEBHACK_DANA_NUMBER="08xx"

**Q: Pembayaran di-check gimana?**
A: Polling otomatis tiap 5 detik (maks 10 menit). Kalau tidak ada server payment, target bisa ketik invoice ID manual untuk konfirmasi.

**Q: Bisa dipake di device lain?**
A: Tidak, license key terikat HWID device. Untuk pindah device, re-issue license.

**Q: Trial version ada gak?**
A: Tidak, ini proprietary commercial tool.

**Q: Bisa dijalankan di iOS?**
A: Tidak, hanya Termux/Linux.

---

## Kontak

Author: denzyx
Version: 4.0.1
License: Proprietary - Commercial