"""Cybersecurity and automation coding exercises. Pure functions over sample strings: no network, no subprocess, no real files."""

from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import re
from collections import Counter
from urllib.parse import urlparse

from app.services.python_practice.content.build import code_q as C


def _st(entry: str, args: str, doc: str) -> str:
    return f'def {entry}({args}):\n    """{doc}"""\n    # your code here\n    pass'


def failed_login_users(lines, threshold):
    counts = Counter()
    for line in lines:
        m = re.search(r"auth failed user=(\w+)", line)
        if m:
            counts[m.group(1)] += 1
    return sorted(u for u, n in counts.items() if n >= threshold)


def _fl_alt(lines, threshold):
    seen = {}
    for line in lines:
        marker = "auth failed user="
        if marker in line:
            rest = line.split(marker, 1)[1]
            user = ""
            for ch in rest:
                if ch.isalnum() or ch == "_":
                    user += ch
                else:
                    break
            seen[user] = seen.get(user, 0) + 1
    return sorted(u for u in seen if seen[u] >= threshold)


def extract_valid_ips(text):
    out = []
    for cand in re.findall(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?!\.?\d)", text):
        try:
            ipaddress.IPv4Address(cand)
        except ValueError:
            continue
        if cand not in out:
            out.append(cand)
    return out


def _ev_alt(text):
    found, token = [], ""
    for ch in text + " ":
        if ch.isdigit() or ch == ".":
            token += ch
            continue
        core = token[:-1] if token.endswith(".") else token
        parts = core.split(".")
        if len(parts) == 4 and all(p.isdigit() and len(p) <= 3 and int(p) <= 255 and (len(p) == 1 or p[0] != "0") for p in parts) and core not in found:
            found.append(core)
        token = ""
    return found


def classify_ip(value):
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return "invalid"
    if ip.is_loopback:
        return "loopback"
    if ip.is_private:
        return "private"
    return "public"


def _ci_alt(value):
    v = value
    parts = v.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts) and all(int(p) < 256 for p in parts) and all(len(p) == 1 or p[0] != "0" for p in parts):
        a, b = int(parts[0]), int(parts[1])
        if a == 127:
            return "loopback"
        if a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or (a == 169 and b == 254) or a == 0 or (a == 100 and 64 <= b <= 127) or (a == 192 and b == 0 and int(parts[2]) in (0, 2)) or (a == 198 and b in (18, 19)) or (a == 198 and b == 51 and int(parts[2]) == 100) or (a == 203 and b == 0 and int(parts[2]) == 113) or a >= 240:
            return "private"
        return "public"
    if v == "::1":
        return "loopback"
    if ":" in v:
        try:
            ip = ipaddress.ip_address(v)
        except ValueError:
            return "invalid"
        return "private" if ip.is_private else "public"
    return "invalid"


def sha256_chunks(chunks):
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.encode("utf-8"))
    return h.hexdigest()


def _sc_alt(chunks):
    return hashlib.sha256("".join(chunks).encode("utf-8")).hexdigest()


def safe_filename(name):
    base = re.split(r"[\\/]", name)[-1]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")
    return (base or "unnamed")[:50]


def _sf_alt(name):
    cut = max(name.rfind("/"), name.rfind("\\"))
    base = name[cut + 1:]
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    chars = [c if c in allowed else "_" for c in base]
    while chars and chars[0] == ".":
        chars.pop(0)
    result = "".join(chars)
    if not result:
        return "unnamed"
    return result[:50]


def csv_row_safe(fields):
    cleaned = ["'" + f if f[:1] in ("=", "+", "-", "@") else f for f in fields]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(cleaned)
    return buf.getvalue()


def _cr_alt(fields):
    out = []
    for f in fields:
        if f[:1] in ("=", "+", "-", "@"):
            f = "'" + f
        if any(ch in f for ch in ',"\n\r'):
            f = '"' + f.replace('"', '""') + '"'
        out.append(f)
    return ",".join(out) + "\n"


def url_host_allowed(url, allowed):
    u = urlparse(url)
    return u.scheme == "https" and (u.hostname or "").lower() in {a.lower() for a in allowed}


def _uh_alt(url, allowed):
    if not url.lower().startswith("https://"):
        return False
    rest = url[8:]
    for sep in "/?#":
        rest = rest.split(sep, 1)[0]
    rest = rest.rsplit("@", 1)[-1]
    if ":" in rest:
        host, _, port = rest.rpartition(":")
        if port.isdigit():
            rest = host
    return rest.lower() in [a.lower() for a in allowed] and rest != ""


def mask_secrets(line):
    return re.sub(r"(?i)\b(password|token|secret|api_key)=\S+", lambda m: m.group(1) + "=***", line)


def _ms_alt(line):
    out = []
    for tok in line.split(" "):
        key, eq, _ = tok.partition("=")
        out.append(key + "=***" if eq and key.lower() in ("password", "token", "secret", "api_key") else tok)
    return " ".join(out)


LOG = ["2024-05-01 10:00:01 WARN auth failed user=alice ip=203.0.113.9", "2024-05-01 10:00:05 INFO login ok user=bob ip=198.51.100.2",
       "2024-05-01 10:00:09 WARN auth failed user=alice ip=203.0.113.9", "2024-05-01 10:00:12 WARN auth failed user=mallory ip=192.0.2.44",
       "2024-05-01 10:00:15 WARN auth failed user=alice ip=203.0.113.9", "garbage line", "2024-05-01 10:00:19 WARN auth failed user=mallory ip=192.0.2.44"]


def questions() -> list[dict]:
    return [
        C("event-analysis", "medium", "coding", "Flag Repeated Failed Logins", "Each log line looks like `2024-05-01 10:00:01 WARN auth failed user=alice ip=203.0.113.9`. Return a sorted list of usernames that have at least `threshold` lines containing `auth failed user=NAME`. Ignore every other line (including malformed ones).",
          "failed_login_users", "def failed_login_users(lines, threshold):", _st("failed_login_users", "lines, threshold", "Return sorted users with >= threshold failed logins."), failed_login_users, _fl_alt,
          [(LOG, 3), (LOG, 2), (LOG, 4), ([], 1), (["auth failed user=x"], 1), (["INFO login ok user=a", "auth failed user=a_1"], 1), (LOG + LOG, 6)], constraints=("Usernames are letters, digits or underscore", "Offline sample data only"), time_c="O(n)", space_c="O(u)",
          expl="Use a regular expression to pull the username from matching lines, count with Counter, and keep users at or above the threshold. Malformed lines simply do not match. Real detection would also bucket by time window and source IP.", hints=("re.search(r'auth failed user=(\\w+)', line)",), imports=("import re", "from collections import Counter")),
        C("regex-extraction", "medium", "coding", "Extract Valid IPv4 Addresses", "Return the unique valid IPv4 addresses found in `text`, in order of first appearance. A dotted-number pattern is only a candidate: reject out-of-range values such as `999.1.1.1`. Use the `ipaddress` module for validation.",
          "extract_valid_ips", "def extract_valid_ips(text):", _st("extract_valid_ips", "text", "Return unique valid IPv4 addresses in order."), extract_valid_ips, _ev_alt,
          [("from 10.0.0.1 and 192.168.1.5", ), ("bad 999.1.1.1 good 8.8.8.8 8.8.8.8", ), ("", ), ("no ips here 1.2.3", ), ("a 1.1.1.1, b 2.2.2.2; c 1.1.1.1.", ), ("256.0.0.1 255.255.255.255 0.0.0.0", ), ("v 1.2.3.4.5 w", )], constraints=("Offline text only",), time_c="O(n)", space_c="O(k)",
          expl="Find candidates with a regex, then validate each with ipaddress.IPv4Address, which rejects octets above 255. Keep a first-seen list for uniqueness. Regex finds, the standard library decides.", hints=("re.findall(r'(?<![\\d.])\\d{1,3}(?:\\.\\d{1,3}){3}(?!\\.?\\d)', text)",), imports=("import re", "import ipaddress")),
        C("ip-validation", "medium", "coding", "Classify an IP Address", "Return `'invalid'` if the text is not a valid IPv4/IPv6 address, `'loopback'` for loopback addresses, `'private'` for private (non-global) addresses, and `'public'` otherwise. Use the `ipaddress` module.",
          "classify_ip", "def classify_ip(value):", _st("classify_ip", "value", "Return 'invalid', 'loopback', 'private' or 'public'."), classify_ip, _ci_alt,
          [("127.0.0.1",), ("10.2.3.4",), ("8.8.8.8",), ("999.0.0.1",), ("::1",), ("192.168.0.1",), ("172.32.0.1",), ("172.16.5.5",), ("not an ip",), ("1.2.3",)], constraints=("Examples use documentation and sample ranges only",), time_c="O(1)", space_c="O(1)",
          expl="ipaddress.ip_address parses both families and raises ValueError for invalid input; its is_loopback and is_private properties do the classification. Checking loopback first matters because loopback addresses are also reported as private.", hints=("Catch ValueError for invalid text.", "Test is_loopback before is_private.",), imports=("import ipaddress",)),
        C("file-hashing", "easy", "coding", "Hash Data in Chunks", "Given a list of text chunks (as if read from a large file piece by piece), return the SHA-256 hex digest of all chunks joined together, encoded as UTF-8. Do not join them into one big string first: feed the hash object chunk by chunk.",
          "sha256_chunks", "def sha256_chunks(chunks):", _st("sha256_chunks", "chunks", "Return the SHA-256 hex digest of all chunks."), sha256_chunks, _sc_alt,
          [(["abc"],), (["a", "bc"],), ([],), ([""],), (["héllo", " wörld"],), (["x"] * 50,)], constraints=("Chunks are strings; encode as UTF-8",), time_c="O(total bytes)", space_c="O(1) per chunk",
          expl="hashlib objects accept data incrementally through update(), so memory stays constant however large the file is. The digest is identical to hashing the concatenation.", hints=("h = hashlib.sha256(); h.update(piece.encode())",), imports=("import hashlib",)),
        C("untrusted-input", "medium", "coding", "Sanitise an Uploaded Filename", "Turn an untrusted filename into a safe one: (1) keep only the part after the last `/` or `\\\\`; (2) replace every character other than letters, digits, `.`, `_`, `-` with `_`; (3) strip leading dots; (4) if nothing is left return `'unnamed'`; (5) truncate to 50 characters.",
          "safe_filename", "def safe_filename(name):", _st("safe_filename", "name", "Return a safe filename."), safe_filename, _sf_alt,
          [("report.pdf",), ("../../etc/passwd",), ("..\\..\\win\\system.ini",), ("my file (1).txt",), ("...hidden",), ("",), ("a" * 80,), ("/",), ("naïve.txt",)], constraints=("Path traversal must be impossible in the result",), time_c="O(n)", space_c="O(n)",
          expl="Reduce the name to its final path component so `../` sequences cannot climb directories, whitelist characters instead of blacklisting bad ones, strip leading dots to avoid hidden files, and cap the length. Also store uploads under a server-generated name where possible.", hints=("re.split(r'[\\\\/]', name)[-1]",), imports=("import re",)),
        C("csv-reports", "medium", "coding", "Write a CSV Row Safely", "Return one CSV line (ending in a single newline) for the list of string `fields`. Neutralise spreadsheet formula injection: if a field starts with `=`, `+`, `-` or `@`, prefix it with a single quote `'`. Quote fields containing commas, quotes or newlines (double any embedded quote) as the csv module does.",
          "csv_row_safe", "def csv_row_safe(fields):", _st("csv_row_safe", "fields", "Return a safe CSV line ending in a newline."), csv_row_safe, _cr_alt,
          [(["amy", "5"],), (["=SUM(A1:A9)", "ok"],), (["said \"hi\"", "a,b"],), (["", "x"],), (["-5", "+x", "@y"],), (["line1\nline2", "z"],), (["plain"],)], compare_mode="text", constraints=("Use \\n line endings",), time_c="O(total length)", space_c="O(total length)",
          expl="Untrusted cells that begin with = + - @ may execute as formulas when the CSV is opened in a spreadsheet, so they are defused with a leading quote; csv.writer then handles quoting. Use lineterminator='\\n' for predictable output.", hints=("csv.writer(io.StringIO(), lineterminator='\\n')",), imports=("import csv", "import io")),
        C("url-parsing", "medium", "coding", "Allow-list a URL by Host", "Return True only if `url` uses the `https` scheme AND its hostname (not just its start) exactly equals one of the `allowed` hostnames, ignoring case. Tricks such as `https://example.com@evil.test/` or `https://example.com.evil.test/` must be rejected.",
          "url_host_allowed", "def url_host_allowed(url, allowed):", _st("url_host_allowed", "url, allowed", "Return True if url is https and its host is allow-listed."), url_host_allowed, _uh_alt,
          [("https://example.com/path", ["example.com"]), ("http://example.com/", ["example.com"]), ("https://example.com@evil.test/", ["example.com"]), ("https://example.com.evil.test/", ["example.com"]), ("https://EXAMPLE.com:8443/a?b=1", ["example.com"]), ("https://other.org", ["example.com", "other.org"]), ("ftp://example.com", ["example.com"]), ("https:///nohost", ["example.com"])], constraints=("Parse the URL; never test with startswith",), time_c="O(len(url))", space_c="O(1)",
          expl="Parse with urllib.parse and compare urlparse(url).hostname, which excludes userinfo and port, against an allow-list. Substring or prefix checks are bypassed by lookalike hosts and `user@host` tricks.", hints=("urlparse(url).hostname", "Compare the whole hostname, lower-cased.",), imports=("from urllib.parse import urlparse",)),
        C("secret-management", "medium", "coding", "Mask Secrets in a Log Line", "Replace the value of any `password=`, `token=`, `secret=` or `api_key=` pair (case-insensitive key) in a space-separated log line with `***`, keeping the key. Everything else must stay unchanged.",
          "mask_secrets", "def mask_secrets(line):", _st("mask_secrets", "line", "Redact secret values in a log line."), mask_secrets, _ms_alt,
          [("login user=amy password=hunter2 ok",), ("TOKEN=abc123 path=/x",), ("no secrets here",), ("api_key=k1 secret=s2 password=p3",), ("user=bob passwordless=yes",), ("",), ("Password=A token=B user=C",)], compare_mode="text", constraints=("Keys are separated from values by '=' with no spaces",), time_c="O(n)", space_c="O(n)",
          expl="Redact before logging, never after. A regex with a case-insensitive key group replaces just the value; `\\b` keeps `passwordless` from matching. Better still: do not put secrets into log messages at all.", hints=("re.sub with a function or a \\1 group reference.", "Use \\b so longer words are not matched."), imports=("import re",)),
    ]
