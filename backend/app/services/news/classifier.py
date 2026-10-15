"""
Rule-based categorisation. Categories are assigned by this service from the headline, excerpt
and the source's own tags -- not by the publisher -- and the UI says so. No AI call is made,
so categorising never costs money, adds latency or invents anything.
"""

from __future__ import annotations

import re

from app.schemas.news import NewsCategory

# Checked in order; the first rule with a match wins, so list narrower topics first.
_RULES: tuple[tuple[NewsCategory, re.Pattern[str]], ...] = (
    (NewsCategory.CAREERS, re.compile(r"\b(careers?|hiring|workforce|skills? (gap|shortage)|apprenticeship|internships?|job market|certifications?|training programme|cyber ?first|graduates?)\b", re.I)),
    (NewsCategory.BUG_BOUNTY, re.compile(r"\b(bug bount(y|ies)|hackerone|bugcrowd|responsible disclosure|coordinated disclosure|pentest(ing|ers?)?|penetration test(ing|ers?)?|red team(ing)?|ethical hack(ing|ers?)?|capture the flag|\bctf\b|pwn2own)\b", re.I)),
    (NewsCategory.AI_SECURITY, re.compile(r"\b(llms?|large language models?|prompt injection|jailbreak(s|ing)?|generative ai|genai|ai agents?|agentic|machine learning|chatgpt|copilot|gemini|claude|\bai\b|artificial intelligence|mcp servers?)\b", re.I)),
    (NewsCategory.MALWARE, re.compile(r"\b(ransomware|malware|botnet|trojan|infostealers?|stealers?|spyware|backdoor|rootkit|wiper|loader|apt\d*|threat actors?|extortion|lockbit|cl0p|shinyhunters|worm)\b", re.I)),
    (NewsCategory.BREACHES, re.compile(r"\b(data breach(es)?|breach(ed)?|leak(ed|s)?|exposed (data|records)|stolen data|compromis(e|ed) of|hacked|cyber ?attack|incident|data theft|stole)\b", re.I)),
    (NewsCategory.VULNERABILITIES, re.compile(r"\b(CVE-\d{4}-\d{4,7}|vulnerabilit(y|ies)|zero-?days?|patch(es|ed)?|patch tuesday|rce|remote code execution|privilege escalation|security (update|advisory|bulletin)|exploit(ed|s|ation)?|known exploited|kev|advisory|advisories)\b", re.I)),
    (NewsCategory.CLOUD_NETWORK, re.compile(r"\b(cloud|aws|azure|kubernetes|container(s)?|firewall|vpn|dns|ddos|network|router|identity|iam|active directory|entra|okta|sso|mfa|zero trust|ics|scada|ot security)\b", re.I)),
    (NewsCategory.APPSEC, re.compile(r"\b(web app(lication)?|appsec|api security|xss|sql injection|sqli|csrf|ssrf|supply chain|npm|pypi|open[- ]source|dependency|dependencies|browser|javascript|owasp|sdk|ci/cd|github)\b", re.I)),
    (NewsCategory.TOOLS_RESEARCH, re.compile(r"\b(research(ers?)?|paper|whitepaper|study|tool|framework|open-?source tool|technique|analysis|reverse engineering|fuzz(ing|er)?|cryptograph(y|ic)|encryption|post-quantum)\b", re.I)),
)


def classify(title: str, summary: str | None, tags: list[str], default: NewsCategory) -> NewsCategory:
    headline_and_tags = " ".join([title, *tags])
    # Headline and tags are the strongest signal; the excerpt is only consulted if they say nothing.
    for text in (headline_and_tags, f"{headline_and_tags} {summary or ''}"):
        for category, pattern in _RULES:
            if pattern.search(text):
                return category
    return default
