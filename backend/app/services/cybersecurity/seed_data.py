"""
Starter cybersecurity topics dataset.

A reasonable, hand-curated set of topics spanning all supported categories —
not an exhaustive content library. `learning_service.ensure_seeded()` loads
these into MongoDB idempotently (upsert by slug) so re-running it or
restarting the app never creates duplicates.
"""

from __future__ import annotations

STARTER_TOPICS: list[dict] = [
    # --- Cybersecurity Fundamentals ---
    {
        "slug": "cia-triad",
        "title": "The CIA Triad",
        "category": "Cybersecurity Fundamentals",
        "difficulty": "beginner",
        "description": "The three core properties — Confidentiality, Integrity, and Availability — that most security decisions are weighed against.",
        "learning_objectives": [
            "Define confidentiality, integrity, and availability",
            "Give a real-world example of each being violated",
            "Explain why security controls usually trade off between them",
        ],
        "content": (
            "The CIA triad is a simple model for thinking about what security is protecting.\n\n"
            "- **Confidentiality** — only authorized people can read the data (e.g. encryption, access control).\n"
            "- **Integrity** — data hasn't been tampered with (e.g. checksums, digital signatures).\n"
            "- **Availability** — the system is up and usable when needed (e.g. redundancy, DDoS protection).\n\n"
            "Most attacks target one leg of the triad: a data breach hits confidentiality, "
            "a ransomware attack hits availability, and tampering with logs hits integrity."
        ),
        "examples": [
            "A leaked customer database is a confidentiality failure.",
            "A website defacement that alters page content is an integrity failure.",
            "A DDoS attack that takes a site offline is an availability failure.",
        ],
        "key_points": [
            "Confidentiality, Integrity, Availability are often in tension with each other",
            "Every security control usually maps back to protecting one of these",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "authentication-vs-authorization",
        "title": "Authentication vs Authorization",
        "category": "Cybersecurity Fundamentals",
        "difficulty": "beginner",
        "description": "Two frequently confused concepts: proving who you are, versus what you're allowed to do.",
        "learning_objectives": [
            "Distinguish authentication from authorization",
            "Identify common authentication factors",
            "Explain why authorization failures (like IDOR) still matter even with strong authentication",
        ],
        "content": (
            "**Authentication** answers \"who are you?\" — logging in with a password, a fingerprint, "
            "or a hardware key are all authentication.\n\n"
            "**Authorization** answers \"what are you allowed to do?\" — once you're logged in, "
            "authorization decides whether you can view another user's data, access an admin panel, "
            "or just your own account.\n\n"
            "A system can authenticate you perfectly and still have broken authorization — "
            "for example, a logged-in regular user who can access another user's private records "
            "just by changing an ID in the URL."
        ),
        "examples": [
            "Entering a password: authentication.",
            "A regular user being blocked from an admin-only page: authorization.",
        ],
        "key_points": [
            "AuthN = identity, AuthZ = permissions",
            "Broken authorization is a leading cause of real-world data exposure",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "hashing-vs-encryption",
        "title": "Hashing vs Encryption",
        "category": "Cybersecurity Fundamentals",
        "difficulty": "beginner",
        "description": "Two different cryptographic tools that get confused constantly: one is reversible, the other isn't supposed to be.",
        "learning_objectives": [
            "Explain the key difference between hashing and encryption",
            "Identify when to use each",
            "Explain why passwords are hashed, not encrypted",
        ],
        "content": (
            "**Encryption** is reversible: data is transformed with a key, and the same (or a paired) "
            "key can transform it back to the original. Used when you need to get the original data back.\n\n"
            "**Hashing** is one-way: it produces a fixed-size fingerprint of data, and there's no key "
            "to reverse it. Used to verify data hasn't changed, or to store passwords without "
            "keeping the original value at all.\n\n"
            "This is why passwords are hashed (with a slow, salted algorithm like Argon2 or bcrypt) "
            "rather than encrypted — the application never needs the original password back, "
            "only a way to check a guess against it."
        ),
        "examples": [
            "TLS encrypts traffic between your browser and a website — it needs to be decrypted at the other end.",
            "A password hash stored in a database can't be turned back into the original password.",
        ],
        "key_points": [
            "Encryption is reversible with a key; hashing is one-way by design",
            "Never 'encrypt' passwords — hash them with a slow, salted algorithm",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "least-privilege",
        "title": "Principle of Least Privilege",
        "category": "Cybersecurity Fundamentals",
        "difficulty": "beginner",
        "description": "Give every user, process, and system only the access it actually needs — nothing more.",
        "learning_objectives": [
            "State the principle of least privilege",
            "Explain why it limits the blast radius of a compromise",
        ],
        "content": (
            "Least privilege means every account, service, and process should have the minimum "
            "level of access required to do its job — no more.\n\n"
            "It doesn't prevent every compromise, but it limits how far an attacker can go once "
            "they get in. A compromised low-privilege web server account should not, for example, "
            "be able to read the entire company's HR database."
        ),
        "examples": [
            "A web application's database account should only be able to read/write its own tables, not drop the whole database.",
            "An employee in marketing shouldn't have access to the finance system by default.",
        ],
        "key_points": [
            "Limits blast radius when (not if) something is compromised",
            "Applies to users, service accounts, and processes alike",
        ],
        "practice_enabled": True,
    },
    # --- Networking ---
    {
        "slug": "osi-model",
        "title": "The OSI Model",
        "category": "Networking",
        "difficulty": "beginner",
        "description": "The seven-layer conceptual model used to describe how network communication works.",
        "learning_objectives": [
            "List the seven OSI layers in order",
            "Map common protocols/devices to their layer",
        ],
        "content": (
            "The OSI model splits networking into seven layers, from physical cabling up to the "
            "application a user interacts with:\n\n"
            "1. Physical — cables, radio signals, voltages\n"
            "2. Data Link — MAC addresses, switches\n"
            "3. Network — IP addresses, routers\n"
            "4. Transport — TCP/UDP, ports\n"
            "5. Session — session establishment/teardown\n"
            "6. Presentation — encoding, encryption formatting\n"
            "7. Application — HTTP, DNS, the protocols apps actually use\n\n"
            "It's a mental model more than something you'll implement directly, but it's the "
            "shared vocabulary the whole networking and security field uses (\"that's a layer 3 issue\")."
        ),
        "examples": [
            "A switch operates at layer 2 (MAC addresses); a router operates at layer 3 (IP addresses).",
            "TCP and UDP live at layer 4.",
        ],
        "key_points": [
            "Physical, Data Link, Network, Transport, Session, Presentation, Application",
            "Mostly a shared vocabulary for describing where a problem or protocol sits",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "tcp-vs-udp",
        "title": "TCP vs UDP",
        "category": "Networking",
        "difficulty": "beginner",
        "description": "The two core transport-layer protocols, and the reliability-vs-speed trade-off between them.",
        "learning_objectives": [
            "Explain the core difference between TCP and UDP",
            "Give an example use case for each",
        ],
        "content": (
            "**TCP** is connection-oriented: it establishes a connection (via the three-way handshake), "
            "guarantees delivery and ordering, and retransmits lost packets. This makes it reliable "
            "but adds overhead.\n\n"
            "**UDP** is connectionless: it just sends packets with no guarantee they arrive or arrive "
            "in order. This makes it fast and lightweight, at the cost of reliability.\n\n"
            "Applications pick whichever trade-off suits them: a file download needs every byte "
            "(TCP), while a live video call would rather drop a frame than stall waiting for a "
            "retransmit (UDP)."
        ),
        "examples": [
            "HTTP/HTTPS, SSH, and email all run over TCP.",
            "DNS lookups, video streaming, and VoIP commonly use UDP.",
        ],
        "key_points": [
            "TCP = reliable, ordered, connection-oriented",
            "UDP = fast, unordered, connectionless",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "tcp-three-way-handshake",
        "title": "TCP Three-Way Handshake",
        "category": "Networking",
        "difficulty": "beginner",
        "description": "How two devices establish a reliable TCP connection before any data is exchanged.",
        "learning_objectives": [
            "Describe the SYN, SYN-ACK, ACK sequence",
            "Explain what each step confirms",
        ],
        "content": (
            "Before any data flows over TCP, the client and server perform a three-step handshake:\n\n"
            "1. **SYN** — the client sends a SYN packet to request a connection and proposes an "
            "initial sequence number.\n"
            "2. **SYN-ACK** — the server acknowledges the client's SYN and sends its own SYN with "
            "its own sequence number.\n"
            "3. **ACK** — the client acknowledges the server's SYN.\n\n"
            "After this exchange, both sides have confirmed they can send and receive, and the "
            "connection is considered established."
        ),
        "examples": [
            "A half-open connection (SYN sent, no SYN-ACK reply) is the basis of a SYN flood attack.",
            "`nmap` uses handshake behavior to determine whether a port is open, closed, or filtered.",
        ],
        "key_points": [
            "SYN -> SYN-ACK -> ACK",
            "Confirms both directions of communication work before data is sent",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "dns-basics",
        "title": "DNS Basics",
        "category": "Networking",
        "difficulty": "beginner",
        "description": "How human-readable domain names get turned into IP addresses.",
        "learning_objectives": [
            "Explain what DNS resolution does",
            "Name a few common DNS record types",
        ],
        "content": (
            "DNS (Domain Name System) translates domain names like `example.com` into IP addresses "
            "computers actually use to route traffic. A resolver queries a chain of DNS servers "
            "(root, TLD, authoritative) until it gets an answer.\n\n"
            "Common record types include A (IPv4 address), AAAA (IPv6 address), MX (mail server), "
            "TXT (arbitrary text, often used for verification/SPF), and CNAME (alias to another name)."
        ),
        "examples": [
            "DNS spoofing/cache poisoning tricks a resolver into returning a malicious IP address.",
            "`dig example.com` shows the DNS resolution chain for a domain.",
        ],
        "key_points": [
            "DNS maps names to IP addresses",
            "A, AAAA, MX, TXT, CNAME are common record types",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "common-ports",
        "title": "Common Network Ports",
        "category": "Networking",
        "difficulty": "beginner",
        "description": "The handful of well-known ports that come up constantly in networking and security work.",
        "learning_objectives": [
            "Recall the port numbers for common services",
            "Explain why knowing common ports helps during enumeration",
        ],
        "content": (
            "Ports let a single IP address run many services at once. A few come up constantly:\n\n"
            "- 22 — SSH\n- 25 — SMTP (email)\n- 53 — DNS\n- 80 — HTTP\n- 443 — HTTPS\n"
            "- 445 — SMB\n- 3306 — MySQL\n- 3389 — RDP\n\n"
            "During reconnaissance, an open port map (e.g. from an `nmap` scan) tells you which "
            "services are worth investigating further."
        ),
        "examples": ["`nmap -p 22,80,443 target` checks specifically for SSH, HTTP, and HTTPS."],
        "key_points": ["22=SSH, 53=DNS, 80=HTTP, 443=HTTPS, 3389=RDP among the most common"],
        "practice_enabled": True,
    },
    # --- Linux ---
    {
        "slug": "linux-file-permissions",
        "title": "Linux File Permissions",
        "category": "Linux",
        "difficulty": "beginner",
        "description": "How Linux controls who can read, write, and execute a file, and how to read/change permission bits.",
        "learning_objectives": [
            "Read a permission string like `-rwxr-xr--`",
            "Explain owner/group/other and read/write/execute",
            "Use `chmod` to change permissions",
        ],
        "content": (
            "Every Linux file has permissions for three groups: the **owner**, the file's **group**, "
            "and **others**. Each group can have **r**ead, **w**rite, and e**x**ecute permission.\n\n"
            "`-rwxr-xr--` breaks down as: owner has rwx, group has r-x, others have r--.\n\n"
            "`chmod 750 file` sets exactly that: 7 (rwx) for owner, 5 (r-x) for group, 0 (---) for others."
        ),
        "examples": [
            "`chmod +x script.sh` makes a script executable.",
            "`ls -l` shows the permission string for each file.",
        ],
        "key_points": [
            "Owner / Group / Other, each with Read / Write / Execute",
            "chmod uses either symbolic (`+x`) or numeric (`750`) notation",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "linux-processes-services",
        "title": "Linux Processes and Services",
        "category": "Linux",
        "difficulty": "intermediate",
        "description": "How Linux tracks running programs, and how services are managed with systemd.",
        "learning_objectives": [
            "Use `ps`/`top` to inspect running processes",
            "Explain what a systemd service unit is",
        ],
        "content": (
            "Every running program on Linux is a **process**, with a PID (process ID), an owner, "
            "and resource usage you can inspect with `ps aux` or `top`.\n\n"
            "**Services** are long-running background processes (web servers, databases, SSH). "
            "Most modern distros manage them with `systemd`: `systemctl status nginx`, "
            "`systemctl restart nginx`, `journalctl -u nginx` for its logs."
        ),
        "examples": [
            "`ps aux | grep sshd` shows the SSH daemon's process.",
            "`systemctl status ssh` shows whether the SSH service is running.",
        ],
        "key_points": [
            "ps/top inspect running processes",
            "systemctl starts/stops/inspects services managed by systemd",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "ssh-basics",
        "title": "SSH Basics",
        "category": "Linux",
        "difficulty": "beginner",
        "description": "Secure remote shell access, and the difference between password and key-based authentication.",
        "learning_objectives": [
            "Explain what SSH is used for",
            "Describe the difference between password and public-key authentication",
        ],
        "content": (
            "SSH (Secure Shell) provides an encrypted remote terminal session (and secure file "
            "transfer, via `scp`/`sftp`) over an untrusted network.\n\n"
            "You can authenticate with a password, or (much more securely) with a key pair: a "
            "private key you keep secret, and a public key placed on the server in "
            "`~/.ssh/authorized_keys`. Password auth is often disabled entirely on hardened servers."
        ),
        "examples": [
            "`ssh user@10.10.10.10` opens a remote shell.",
            "`ssh-keygen` generates a new key pair for key-based login.",
        ],
        "key_points": [
            "SSH encrypts remote shell/file-transfer traffic",
            "Key-based auth is generally preferred over passwords",
        ],
        "practice_enabled": True,
    },
    # --- Windows ---
    {
        "slug": "windows-event-logs",
        "title": "Windows Event Logs",
        "category": "Windows",
        "difficulty": "intermediate",
        "description": "Where Windows records security-relevant activity, and the event IDs worth knowing.",
        "learning_objectives": [
            "Name the main Windows event log categories",
            "Recognize a couple of high-value security event IDs",
        ],
        "content": (
            "Windows records activity in several logs viewable with Event Viewer or `wevtutil`: "
            "**Application**, **System**, and **Security** are the main ones.\n\n"
            "The Security log is especially valuable for defenders — Event ID 4624 (successful "
            "logon), 4625 (failed logon), and 4688 (new process created) are commonly used during "
            "investigations to reconstruct what happened on a host."
        ),
        "examples": ["A spike in 4625 events can indicate a brute-force login attempt."],
        "key_points": [
            "Security log tracks logons, process creation, and other sensitive events",
            "4624 = successful logon, 4625 = failed logon, 4688 = process creation",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "powershell-basics",
        "title": "PowerShell Basics",
        "category": "Windows",
        "difficulty": "beginner",
        "description": "Windows' object-oriented shell and scripting language, used constantly in both administration and attacks.",
        "learning_objectives": [
            "Explain what makes PowerShell different from a traditional shell",
            "Run a basic PowerShell cmdlet",
        ],
        "content": (
            "PowerShell is Windows' scripting shell — but unlike Bash, its pipeline passes structured "
            ".NET objects between commands (cmdlets), not just plain text.\n\n"
            "Cmdlets follow a Verb-Noun pattern: `Get-Process`, `Get-Service`, `Set-ExecutionPolicy`. "
            "Because it's so powerful, PowerShell is also heavily used by attackers for "
            "post-exploitation — which is why execution policies, logging, and AMSI matter."
        ),
        "examples": ["`Get-Process | Where-Object {$_.CPU -gt 100}` lists high-CPU processes."],
        "key_points": [
            "Cmdlets use a Verb-Noun naming pattern and pass structured objects",
            "Powerful for admins and attackers alike — logging/AMSI help detect misuse",
        ],
        "practice_enabled": True,
    },
    # --- Web Security ---
    {
        "slug": "xss",
        "title": "Cross-Site Scripting (XSS)",
        "category": "Web Security",
        "difficulty": "intermediate",
        "description": "Injecting attacker-controlled script into a page that runs in another user's browser.",
        "learning_objectives": [
            "Explain how XSS lets an attacker run script in a victim's browser",
            "Distinguish stored, reflected, and DOM-based XSS",
            "Name a basic mitigation",
        ],
        "content": (
            "XSS happens when an application includes untrusted input in a page without properly "
            "encoding it, letting an attacker's script run in another user's browser session.\n\n"
            "- **Stored XSS** — the payload is saved (e.g. in a comment) and served to every visitor.\n"
            "- **Reflected XSS** — the payload comes from the request (e.g. a URL parameter) and is "
            "immediately reflected back in the response.\n"
            "- **DOM-based XSS** — the vulnerability is entirely in client-side JavaScript that "
            "unsafely handles data.\n\n"
            "The core fix is output encoding: render user-supplied data as text, not as HTML/script, "
            "and use a Content-Security-Policy as defense in depth."
        ),
        "examples": [
            "A comment field that stores `<script>...</script>` and later renders it unescaped for every visitor.",
        ],
        "key_points": [
            "Stored, reflected, and DOM-based are the three main types",
            "Fix: encode output properly, add a Content-Security-Policy",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "sql-injection",
        "title": "SQL Injection",
        "category": "Web Security",
        "difficulty": "intermediate",
        "description": "Manipulating a database query by injecting SQL through untrusted input.",
        "learning_objectives": [
            "Explain how untrusted input can alter a SQL query's logic",
            "Explain why parameterized queries prevent it",
        ],
        "content": (
            "SQL injection happens when user input is concatenated directly into a SQL query "
            "instead of being treated as pure data. An attacker can craft input that changes the "
            "query's logic entirely.\n\n"
            "For example, a login check like:\n"
            "`SELECT * FROM users WHERE username = '<input>' AND password = '<input>'`\n"
            "can be broken by entering `' OR '1'='1` as the username, turning the WHERE clause "
            "into something always true.\n\n"
            "The fix is parameterized queries (prepared statements), which keep user input as "
            "data and never let it change the query structure."
        ),
        "examples": ["`' OR '1'='1' --` is a classic authentication-bypass payload."],
        "key_points": [
            "Happens when input is concatenated into SQL instead of parameterized",
            "Fix: parameterized queries / prepared statements, not string concatenation",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "csrf",
        "title": "Cross-Site Request Forgery (CSRF)",
        "category": "Web Security",
        "difficulty": "intermediate",
        "description": "Tricking a logged-in user's browser into making an unwanted request on their behalf.",
        "learning_objectives": [
            "Explain how CSRF abuses a victim's existing session",
            "Name a common CSRF defense",
        ],
        "content": (
            "CSRF tricks a victim's browser into submitting a request to a site they're already "
            "authenticated on, without their intent — the browser automatically attaches cookies, "
            "so the request looks legitimate to the server.\n\n"
            "For example, a malicious page could auto-submit a hidden form to "
            "`bank.com/transfer?to=attacker&amount=1000` — if the victim is logged into their bank "
            "in another tab, the browser sends their session cookie along with it.\n\n"
            "Common defenses: CSRF tokens (a random value the server checks on state-changing "
            "requests) and the `SameSite` cookie attribute."
        ),
        "examples": ["A hidden auto-submitting form on a malicious page targeting a bank transfer endpoint."],
        "key_points": [
            "Exploits the browser automatically attaching cookies to requests",
            "Defenses: CSRF tokens, SameSite cookies",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "idor",
        "title": "Insecure Direct Object Reference (IDOR)",
        "category": "Web Security",
        "difficulty": "intermediate",
        "description": "When an application lets you access another user's data just by changing an ID.",
        "learning_objectives": [
            "Explain what IDOR is",
            "Explain why it's an authorization bug, not an authentication bug",
        ],
        "content": (
            "IDOR happens when an application exposes a direct reference to an internal object "
            "(like a database ID) and doesn't verify the requesting user is actually allowed to "
            "access that specific object.\n\n"
            "For example, `GET /api/invoices/1042` might return invoice 1042 for whoever's logged "
            "in — even if it belongs to a different account — if the server only checks that "
            "*someone* is logged in, not that *this* user owns invoice 1042.\n\n"
            "The fix is an authorization check on every object access: confirm the resource "
            "belongs to (or is otherwise accessible to) the current user before returning it."
        ),
        "examples": ["Changing `?invoice_id=1042` to `1043` in the URL and getting someone else's invoice."],
        "key_points": [
            "An authorization failure, not an authentication failure",
            "Fix: check object ownership/access on every request, not just that the user is logged in",
        ],
        "practice_enabled": True,
    },
    {
        "slug": "security-headers",
        "title": "HTTP Security Headers",
        "category": "Web Security",
        "difficulty": "beginner",
        "description": "A handful of response headers that meaningfully reduce a web app's attack surface.",
        "learning_objectives": [
            "Name a few common security headers and what they do",
        ],
        "content": (
            "A few HTTP response headers add meaningful defense-in-depth for very little effort:\n\n"
            "- `Content-Security-Policy` — restricts what scripts/resources a page can load, "
            "mitigating XSS impact.\n"
            "- `Strict-Transport-Security` — forces browsers to only use HTTPS for the site.\n"
            "- `X-Content-Type-Options: nosniff` — stops browsers from guessing content types.\n"
            "- `X-Frame-Options` — prevents the page from being embedded in a clickjacking iframe."
        ),
        "examples": ["`Strict-Transport-Security: max-age=63072000` forces HTTPS for about two years."],
        "key_points": [
            "CSP, HSTS, X-Content-Type-Options, X-Frame-Options are common baseline headers",
        ],
        "practice_enabled": True,
    },
    # --- SOC ---
    {
        "slug": "what-is-soc",
        "title": "What Is a SOC?",
        "category": "SOC",
        "difficulty": "beginner",
        "description": "The team and function responsible for monitoring and responding to security events around the clock.",
        "learning_objectives": [
            "Explain the purpose of a Security Operations Center",
            "Describe the general flow from alert to resolution",
        ],
        "content": (
            "A Security Operations Center (SOC) is the team (and the tooling/process around it) "
            "responsible for continuously monitoring an organization's systems for security "
            "threats and responding when something looks wrong.\n\n"
            "A typical flow: a detection tool raises an **alert** -> a SOC analyst **triages** it "
            "(is it a false positive, low, or high severity?) -> if real, it becomes an "
            "**incident** that gets investigated and remediated."
        ),
        "examples": ["An analyst investigating an alert for unusual login activity from a new country."],
        "key_points": ["Alert -> Triage -> Investigation -> Remediation is the general SOC workflow"],
        "practice_enabled": True,
    },
    {
        "slug": "incident-triage",
        "title": "Incident Triage",
        "category": "SOC",
        "difficulty": "intermediate",
        "description": "How a SOC analyst quickly decides how serious an alert is and what to do next.",
        "learning_objectives": [
            "Explain the goal of triage",
            "List questions an analyst asks when triaging an alert",
        ],
        "content": (
            "Triage is the first pass over an alert to decide: is this a false positive, and if "
            "not, how urgent is it? Analysts typically ask:\n\n"
            "- What triggered the alert, exactly?\n"
            "- What asset/user is involved, and how sensitive is it?\n"
            "- Is there supporting evidence elsewhere (other logs, other alerts)?\n"
            "- Has this happened before and been explained (known-benign)?\n\n"
            "Good triage keeps analysts from drowning in noise and gets real incidents escalated fast."
        ),
        "examples": ["A login alert from an employee's usual laptop and city is likely benign; the same alert from an unfamiliar country at 3am is not."],
        "key_points": ["Goal: separate real incidents from noise, fast, using context"],
        "practice_enabled": True,
    },
    # --- SIEM ---
    {
        "slug": "what-is-siem",
        "title": "What Is a SIEM?",
        "category": "SIEM",
        "difficulty": "beginner",
        "description": "The platform that aggregates logs from across an environment and helps detect suspicious patterns.",
        "learning_objectives": [
            "Explain what a SIEM does",
            "Explain the difference between a log and an alert",
        ],
        "content": (
            "A SIEM (Security Information and Event Management) system collects logs from many "
            "sources — firewalls, servers, endpoints, applications — into one place, correlates "
            "them, and raises alerts when patterns match known-bad or suspicious behavior.\n\n"
            "A **log** is just a raw event record. An **alert** is the SIEM (or an analyst) "
            "deciding a log, or combination of logs, is worth investigating."
        ),
        "examples": ["A SIEM rule that fires when the same account fails to log in 20 times in a minute."],
        "key_points": ["Aggregates + correlates logs from many sources; turns patterns into alerts"],
        "practice_enabled": True,
    },
    {
        "slug": "log-analysis-basics",
        "title": "Log Analysis Basics",
        "category": "SIEM",
        "difficulty": "intermediate",
        "description": "Core techniques for finding what matters in a sea of log data.",
        "learning_objectives": [
            "Explain what to look for when reviewing logs",
            "Explain the value of baselining normal behavior",
        ],
        "content": (
            "Effective log analysis usually starts with knowing what \"normal\" looks like — a "
            "baseline — so anomalies actually stand out. From there, analysts look for things like:\n\n"
            "- Unusual times or locations for legitimate accounts\n"
            "- Spikes in failed authentication\n"
            "- Unexpected privilege escalation or new admin accounts\n"
            "- Traffic to known-bad IPs/domains (threat intel matches)"
        ),
        "examples": ["A service account that normally never logs in interactively suddenly does."],
        "key_points": ["Baseline normal first, then hunt for deviations from it"],
        "practice_enabled": True,
    },
    # --- Incident Response ---
    {
        "slug": "incident-response-lifecycle",
        "title": "Incident Response Lifecycle",
        "category": "Incident Response",
        "difficulty": "intermediate",
        "description": "The standard phases organizations follow when responding to a security incident.",
        "learning_objectives": [
            "List the phases of the incident response lifecycle",
            "Explain what happens in each phase",
        ],
        "content": (
            "A commonly used incident response lifecycle (based on NIST) has these phases:\n\n"
            "1. **Preparation** — policies, tooling, and training in place before anything happens.\n"
            "2. **Detection & Analysis** — identifying and confirming an incident occurred.\n"
            "3. **Containment, Eradication & Recovery** — stopping the spread, removing the cause, "
            "restoring systems.\n"
            "4. **Post-Incident Activity** — lessons learned, updating processes.\n\n"
            "The cycle feeds back into itself: lessons learned improve preparation for next time."
        ),
        "examples": ["Isolating an infected host from the network is a containment action."],
        "key_points": ["Preparation -> Detection/Analysis -> Containment/Eradication/Recovery -> Lessons Learned"],
        "practice_enabled": True,
    },
    # --- Digital Forensics ---
    {
        "slug": "chain-of-custody",
        "title": "Chain of Custody",
        "category": "Digital Forensics",
        "difficulty": "beginner",
        "description": "The documented trail proving evidence hasn't been tampered with from collection to presentation.",
        "learning_objectives": [
            "Explain what chain of custody is and why it matters",
        ],
        "content": (
            "Chain of custody is the documented history of who collected a piece of evidence, "
            "when, how it was stored, and who accessed it afterward. If any link in that chain is "
            "broken or undocumented, the evidence's integrity — and its usefulness, especially "
            "legally — can be challenged.\n\n"
            "In digital forensics this usually means hashing evidence (e.g. a disk image) at "
            "collection time so any later alteration can be detected."
        ),
        "examples": ["Recording a SHA-256 hash of a disk image immediately after acquisition, and re-verifying it before analysis."],
        "key_points": ["Documents who handled evidence and when; hashing detects tampering"],
        "practice_enabled": True,
    },
    {
        "slug": "disk-vs-memory-forensics",
        "title": "Disk Forensics vs Memory Forensics",
        "category": "Digital Forensics",
        "difficulty": "intermediate",
        "description": "Two complementary sources of evidence: what's persisted to disk, and what only lives in RAM.",
        "learning_objectives": [
            "Explain the difference between disk and memory forensics",
            "Give an example of something only found in memory",
        ],
        "content": (
            "**Disk forensics** examines persistent storage: files, deleted-but-recoverable data, "
            "file system metadata, timestamps.\n\n"
            "**Memory forensics** examines a snapshot of RAM, capturing things that may never touch "
            "disk: running processes, open network connections, decrypted data, and in-memory-only "
            "malware.\n\n"
            "Because memory is volatile, it must be captured while the system is still running — "
            "once powered off, that evidence is gone."
        ),
        "examples": ["Fileless malware that only ever exists in memory is invisible to pure disk forensics."],
        "key_points": ["Disk = persistent evidence; Memory = volatile, must be captured live"],
        "practice_enabled": True,
    },
    # --- Penetration Testing ---
    {
        "slug": "recon-and-enumeration",
        "title": "Reconnaissance and Enumeration",
        "category": "Penetration Testing",
        "difficulty": "beginner",
        "description": "The early information-gathering phases of a penetration test.",
        "learning_objectives": [
            "Distinguish reconnaissance from enumeration",
            "Give an example tool/technique for each",
        ],
        "content": (
            "**Reconnaissance** gathers information about a target with minimal or no direct "
            "interaction — public records, DNS records, social media, job postings that reveal "
            "the tech stack.\n\n"
            "**Enumeration** actively probes the target to extract concrete details — open ports, "
            "running services and versions, valid usernames, shared folders — usually the step "
            "right after an initial port scan."
        ),
        "examples": [
            "Passive: searching for employee names on LinkedIn (recon).",
            "Active: `nmap -sV` to identify service versions on open ports (enumeration).",
        ],
        "key_points": ["Recon = passive/indirect information gathering; Enumeration = active probing"],
        "practice_enabled": True,
    },
    {
        "slug": "privilege-escalation-concepts",
        "title": "Privilege Escalation Concepts",
        "category": "Penetration Testing",
        "difficulty": "intermediate",
        "description": "How an attacker with limited access tries to gain higher-level permissions.",
        "learning_objectives": [
            "Distinguish vertical from horizontal privilege escalation",
            "Give a common cause of privilege escalation vulnerabilities",
        ],
        "content": (
            "**Vertical privilege escalation** means going from a lower privilege level to a higher "
            "one (regular user -> admin/root). **Horizontal privilege escalation** means accessing "
            "another account at the *same* privilege level (user A accessing user B's data).\n\n"
            "Common causes include misconfigured file/service permissions, unpatched "
            "vulnerabilities, weak credential storage, and (on the web side) authorization bugs "
            "like IDOR."
        ),
        "examples": ["A world-writable script that runs as root is a classic Linux privilege-escalation path."],
        "key_points": ["Vertical = higher privilege level; Horizontal = same level, different account"],
        "practice_enabled": True,
    },
    # --- Cryptography ---
    {
        "slug": "hash-functions",
        "title": "Cryptographic Hash Functions",
        "category": "Cryptography",
        "difficulty": "beginner",
        "description": "One-way functions that turn arbitrary data into a fixed-size fingerprint.",
        "learning_objectives": [
            "List the key properties of a good cryptographic hash function",
            "Name a hash algorithm still considered secure today",
        ],
        "content": (
            "A cryptographic hash function takes input of any size and produces a fixed-size "
            "output (a digest), with a few important properties:\n\n"
            "- **Deterministic** — same input always gives the same output.\n"
            "- **One-way** — infeasible to reverse the digest back to the input.\n"
            "- **Collision-resistant** — infeasible to find two different inputs with the same digest.\n\n"
            "MD5 and SHA-1 are broken for security purposes (collisions are practical). SHA-256 "
            "and SHA-3 are current, secure general-purpose choices — though for *passwords* "
            "specifically, a slow, salted algorithm like Argon2 or bcrypt is used instead."
        ),
        "examples": ["Verifying a downloaded file's SHA-256 checksum matches the one published by the vendor."],
        "key_points": ["Deterministic, one-way, collision-resistant; MD5/SHA-1 are broken, SHA-256/SHA-3 are current"],
        "practice_enabled": True,
    },
    {
        "slug": "symmetric-vs-asymmetric-encryption",
        "title": "Symmetric vs Asymmetric Encryption",
        "category": "Cryptography",
        "difficulty": "intermediate",
        "description": "The two families of encryption, and why real systems (like TLS) use both together.",
        "learning_objectives": [
            "Explain the core difference between symmetric and asymmetric encryption",
            "Explain why TLS uses both",
        ],
        "content": (
            "**Symmetric encryption** uses the same key to encrypt and decrypt (e.g. AES). It's "
            "fast, but both sides need to already share that secret key.\n\n"
            "**Asymmetric encryption** uses a key pair: a public key anyone can use to encrypt, and "
            "a private key only the owner holds to decrypt (e.g. RSA). It solves the key-sharing "
            "problem but is much slower.\n\n"
            "TLS uses both: asymmetric encryption to securely agree on a shared secret, then fast "
            "symmetric encryption for the actual data using that secret."
        ),
        "examples": ["AES is symmetric; RSA is asymmetric."],
        "key_points": ["Symmetric = one shared key, fast; Asymmetric = key pair, slower, solves key exchange"],
        "practice_enabled": True,
    },
    {
        "slug": "base64-encoding",
        "title": "Base64 Encoding (Not Encryption)",
        "category": "Cryptography",
        "difficulty": "beginner",
        "description": "A common encoding scheme that is frequently — and dangerously — mistaken for security.",
        "learning_objectives": [
            "Explain what Base64 actually does",
            "Explain why Base64 is not a security control",
        ],
        "content": (
            "Base64 encodes binary data as printable ASCII text, so it can safely travel through "
            "systems that only handle text (like embedding an image in a JSON payload).\n\n"
            "It is **not** encryption — there's no key, and anyone can decode it instantly. Seeing "
            "Base64-looking text in a config file or a URL is a strong hint the underlying value "
            "is not actually protected, just encoded."
        ),
        "examples": ["`echo -n 'password123' | base64` produces `cGFzc3dvcmQxMjM=`, trivially reversible with `base64 -d`."],
        "key_points": ["Encoding, not encryption — reversible by anyone, no key required"],
        "practice_enabled": True,
    },
    # --- Threat Intelligence ---
    {
        "slug": "indicators-of-compromise",
        "title": "Indicators of Compromise (IOCs)",
        "category": "Threat Intelligence",
        "difficulty": "beginner",
        "description": "The observable artifacts that suggest a system has been compromised.",
        "learning_objectives": [
            "Define IOC",
            "Give a few examples of common IOC types",
        ],
        "content": (
            "An Indicator of Compromise (IOC) is a piece of forensic evidence suggesting malicious "
            "activity has occurred — a known-bad IP address, a malware file hash, a suspicious "
            "domain, or an unusual registry key.\n\n"
            "Threat intelligence feeds distribute IOCs so defenders can search their own "
            "environment (and configure detections) for the same indicators seen in other attacks."
        ),
        "examples": ["A file hash matching a known ransomware sample; a domain associated with a known phishing campaign."],
        "key_points": ["Observable artifacts (hashes, IPs, domains) associated with malicious activity"],
        "practice_enabled": True,
    },
    # --- Cloud Security ---
    {
        "slug": "shared-responsibility-model",
        "title": "Cloud Shared Responsibility Model",
        "category": "Cloud Security",
        "difficulty": "beginner",
        "description": "Where the cloud provider's security responsibility ends and the customer's begins.",
        "learning_objectives": [
            "Explain the shared responsibility model",
            "Give an example of a customer-side responsibility",
        ],
        "content": (
            "Cloud providers secure the underlying infrastructure — physical data centers, the "
            "hypervisor, the network backbone (\"security **of** the cloud\"). Customers remain "
            "responsible for how they configure and use it — access controls, data encryption, "
            "network rules, patching their own instances (\"security **in** the cloud\").\n\n"
            "A huge share of real cloud breaches come from customer-side misconfiguration — like a "
            "storage bucket accidentally left publicly readable — not from the provider being hacked."
        ),
        "examples": ["A publicly readable S3 bucket exposing customer data is a customer misconfiguration, not a provider failure."],
        "key_points": ["Provider secures the cloud; customer secures what they put in it and how they configure it"],
        "practice_enabled": True,
    },
    # --- Active Directory ---
    {
        "slug": "active-directory-basics",
        "title": "Active Directory Basics",
        "category": "Active Directory",
        "difficulty": "intermediate",
        "description": "The directory service most enterprise Windows networks use for identity and access management.",
        "learning_objectives": [
            "Explain what Active Directory manages",
            "Define a domain, a domain controller, and an OU",
        ],
        "content": (
            "Active Directory (AD) is Microsoft's directory service for managing users, computers, "
            "groups, and permissions across a Windows network from a central place.\n\n"
            "A **domain** is the administrative boundary; a **Domain Controller (DC)** is the server "
            "that holds the AD database and handles authentication; an **Organizational Unit (OU)** "
            "groups objects (like users or computers) for applying policy consistently.\n\n"
            "Because a compromised DC effectively means a compromised network, AD security "
            "(patching, tiered admin access, monitoring) is a major focus in enterprise defense."
        ),
        "examples": ["Group Policy applied to an OU can enforce a password policy for every user in it."],
        "key_points": ["Domain = boundary, DC = authentication server, OU = grouping for policy"],
        "practice_enabled": True,
    },
    # --- Malware Basics ---
    {
        "slug": "malware-types",
        "title": "Common Malware Types",
        "category": "Malware Basics",
        "difficulty": "beginner",
        "description": "A quick tour of the vocabulary used to categorize malicious software.",
        "learning_objectives": [
            "Distinguish a virus, worm, trojan, and ransomware",
        ],
        "content": (
            "- **Virus** — attaches itself to a legitimate file/program and spreads when that file runs.\n"
            "- **Worm** — spreads on its own across a network, without needing a host file or user action.\n"
            "- **Trojan** — disguises itself as legitimate software to trick a user into running it.\n"
            "- **Ransomware** — encrypts a victim's files and demands payment for the decryption key.\n\n"
            "These categories describe *behavior*, and real malware often combines several of them."
        ),
        "examples": ["WannaCry combined ransomware with worm-like self-propagation."],
        "key_points": ["Virus needs a host file, worm self-propagates, trojan relies on deception, ransomware extorts via encryption"],
        "practice_enabled": True,
    },
    # --- Security Tools ---
    {
        "slug": "nmap-basics",
        "title": "Nmap Basics",
        "category": "Security Tools",
        "difficulty": "beginner",
        "description": "The de facto standard tool for network discovery and port scanning.",
        "learning_objectives": [
            "Explain what Nmap is used for",
            "Read a basic Nmap scan result",
        ],
        "content": (
            "Nmap scans hosts to discover what's alive on a network and what services are running "
            "on them. A basic scan reports each port's state — **open**, **closed**, or "
            "**filtered** — and with `-sV` can also try to identify the service and version behind "
            "an open port.\n\n"
            "It's an essential reconnaissance/enumeration tool, and understanding its output is a "
            "foundational skill for both offense and defense."
        ),
        "examples": ["`nmap -sV -p- 10.10.10.10` scans all 65535 ports and tries to identify service versions."],
        "key_points": ["Reports port state (open/closed/filtered); -sV attempts service/version detection"],
        "practice_enabled": True,
    },
]
