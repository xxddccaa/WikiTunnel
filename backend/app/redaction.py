from __future__ import annotations

import re


PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
    re.DOTALL,
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passphrase|secret|token|authorization|api[_-]?key)\b"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))" )


def redact_text(value: str, limit: int = 4000) -> str:
    text = ANSI_RE.sub("", value.replace("\x00", ""))
    text = PRIVATE_KEY_RE.sub("[PRIVATE KEY REDACTED]", text)
    text = BEARER_RE.sub("Bearer <redacted>", text)
    text = SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def redact_lines(lines: list[str]) -> list[str]:
    return [redact_text(line.rstrip("\n")) for line in lines]

