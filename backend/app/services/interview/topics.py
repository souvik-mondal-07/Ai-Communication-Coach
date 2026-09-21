"""
Interview taxonomy.

Two related but distinct ideas live here:

* **Interview type** — what the user selects (`hr`, `technical`,
  `cybersecurity`, `scenario_based`, `mixed`). It decides which topic areas
  the interview draws questions from.
* **Topic** — the subject area of one question (`network_security`,
  `linux`, `soc_blue_team`, ...). Topics also drive the interview-level
  weak-topic detection. Each topic has *focus areas*: concrete subjects
  (e.g. "IDS vs IPS") that the planner spreads across the interview so
  questions don't repeat.

Everything is data, so adding a topic or focus area is a one-line change.
"""

from __future__ import annotations

from dataclasses import dataclass

INTERVIEW_TYPES = ("hr", "technical", "cybersecurity", "scenario_based", "mixed")
DIFFICULTIES = ("beginner", "intermediate", "advanced")
INPUT_MODES = ("text", "voice")

# Interview lengths the setup screen offers. One constant, easy to extend.
ALLOWED_QUESTION_COUNTS = (5, 10, 15, 20)

# The first HR question is always the classic opener.
HR_OPENER_FOCUS = "self-introduction (\"Tell me about yourself\")"


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    kind: str  # "behavioral" | "technical" | "scenario"
    focus_areas: tuple[str, ...]
    # Step 5 learning-topic categories that cover this topic (used to ground
    # "Recommended Practice" in content that actually exists in the app).
    learning_categories: tuple[str, ...] = ()


TOPICS: dict[str, Topic] = {
    t.id: t
    for t in (
        Topic(
            "hr",
            "HR / Behavioral",
            "behavioral",
            (
                HR_OPENER_FOCUS,
                "why cybersecurity",
                "why we should hire you",
                "your strengths",
                "your weaknesses",
                "where you see yourself in five years",
                "why you want this internship or role",
                "a project you worked on",
                "a time you made a mistake or faced a setback",
                "working in a team",
                "how you keep learning new skills",
                "disagreeing with a colleague or a decision",
                "handling pressure and tight deadlines",
                "prioritising when everything seems urgent",
                "explaining a technical issue to a non-technical person",
                "receiving and acting on critical feedback",
                "ethics and responsible disclosure",
                "taking initiative or leading something",
                "a lab, CTF or certification you are proud of",
                "what you would do in your first 90 days",
                "why you want to join this particular team",
            ),
        ),
        Topic(
            "fundamentals",
            "Cybersecurity Fundamentals",
            "technical",
            (
                "the CIA triad",
                "authentication vs authorization",
                "encryption vs hashing",
                "least privilege and defense in depth",
                "vulnerability vs threat vs risk",
                "common security principles",
            ),
            ("Cybersecurity Fundamentals",),
        ),
        Topic(
            "network_security",
            "Network Security",
            "technical",
            (
                "TCP vs UDP",
                "the TCP three-way handshake",
                "DNS",
                "HTTP vs HTTPS",
                "firewalls",
                "IDS vs IPS",
                "network segmentation",
                "VPNs",
                "common network attacks",
            ),
            ("Networking",),
        ),
        Topic(
            "linux",
            "Linux",
            "technical",
            (
                "file permissions and chmod",
                "processes and services",
                "networking commands",
                "logs and where to find them",
                "SSH",
                "privilege concepts such as sudo and SUID",
            ),
            ("Linux",),
        ),
        Topic(
            "web_security",
            "Web Security",
            "technical",
            (
                "cross-site scripting (XSS)",
                "SQL injection",
                "CSRF",
                "SSRF",
                "authentication vulnerabilities",
                "OWASP Top 10 concepts",
                "session management",
            ),
            ("Web Security",),
        ),
        Topic(
            "soc_blue_team",
            "SOC / Blue Team",
            "technical",
            (
                "SIEM",
                "alert triage and false positives",
                "log analysis",
                "incident response",
                "indicators of compromise (IOCs)",
                "threat detection",
                "escalating an incident to senior staff",
            ),
            ("SOC", "SIEM", "Incident Response"),
        ),
        Topic(
            "digital_forensics",
            "Digital Forensics",
            "technical",
            (
                "evidence acquisition",
                "chain of custody",
                "disk imaging",
                "file systems",
                "file metadata",
                "forensic tools",
            ),
            ("Digital Forensics",),
        ),
        Topic(
            "penetration_testing",
            "Penetration Testing",
            "technical",
            (
                "reconnaissance",
                "enumeration",
                "vulnerability assessment",
                "exploitation concepts",
                "privilege escalation",
                "reporting",
                "scope and authorization",
            ),
            ("Penetration Testing",),
        ),
        Topic(
            "cryptography",
            "Cryptography",
            "technical",
            (
                "symmetric encryption",
                "asymmetric encryption",
                "hash functions and collision resistance",
                "digital signatures",
                "certificates and PKI",
                "key exchange",
            ),
            ("Cryptography",),
        ),
        Topic(
            "scenario_based",
            "Scenario-Based Security",
            "scenario",
            (
                "a suspicious login was detected",
                "a ransomware incident",
                "a phishing attack",
                "a compromised endpoint",
                "suspicious PowerShell activity",
                "data exfiltration",
                "a web server compromise",
                "an insider threat",
                "a misconfigured cloud storage bucket",
                "a denial-of-service attack",
                "a business email compromise",
                "a lost or stolen laptop",
                "a malware outbreak on the network",
                "credential stuffing against a login page",
                "a supply-chain or third-party compromise",
                "repeated SSH brute-force attempts",
                "unusual outbound DNS traffic",
                "a vulnerable public-facing API",
                "an unpatched critical vulnerability being exploited",
                "an employee reporting a suspicious USB drive",
            ),
            ("Incident Response", "SOC"),
        ),
    )
}

# Which topics each interview type draws from.
TYPE_TOPICS: dict[str, tuple[str, ...]] = {
    "hr": ("hr",),
    # Core security knowledge across the fundamentals.
    "technical": ("fundamentals", "network_security", "linux", "web_security", "cryptography"),
    # The full specialty spread: everything above plus blue team, forensics and pentesting.
    "cybersecurity": (
        "fundamentals",
        "network_security",
        "linux",
        "web_security",
        "soc_blue_team",
        "digital_forensics",
        "penetration_testing",
        "cryptography",
    ),
    "scenario_based": ("scenario_based",),
}

# "Mixed" = HR + technical + scenarios, in these proportions.
MIXED_HR_SHARE = 0.25
MIXED_SCENARIO_SHARE = 0.25

INTERVIEW_TYPE_LABELS = {
    "hr": "HR",
    "technical": "Technical",
    "cybersecurity": "Cybersecurity",
    "scenario_based": "Scenario-Based",
    "mixed": "Mixed",
}


def topic_label(topic_id: str) -> str:
    topic = TOPICS.get(topic_id)
    return topic.label if topic else topic_id
