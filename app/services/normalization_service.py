import re

from app.models.normalized_message import NormalizedMessage


ACTION_MAP = {
    "BUY": "BUY",
    "LONG": "BUY",
    "SELL": "SELL",
    "SHORT": "SELL",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = []

    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        line = re.sub(r"#\w+", "", line).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def first_content_line(clean_text: str) -> str:
    for line in clean_text.split("\n"):
        line = line.strip()

        if line:
            return line

    return ""


def clean_symbol(symbol: str | None) -> str | None:
    if not symbol:
        return None

    symbol = symbol.strip()
    symbol = symbol.strip(" -,:.$₹")
    symbol = re.sub(r"\s+", " ", symbol)

    symbol = re.sub(r"\b\d+\b", "", symbol)
    symbol = re.sub(r"\s+", " ", symbol).strip()

    if not symbol:
        return None

    return symbol.upper()


def detect_symbol(clean_text: str) -> str | None:
    line = first_content_line(clean_text)

    if not line:
        return None

    patterns = [
        r"^(.+?)\s*[-,]\s*[$₹]?\d",
        r"^(.+?)\s*[-,]\s*\d",
        r"^(.+?)\s+[-,]\s*[$₹]?\d",
    ]

    for pattern in patterns:
        match = re.search(pattern, line)

        if match:
            return clean_symbol(match.group(1))

    pair_match = re.search(
        r"^([A-Za-z0-9]+)\s*/\s*([A-Za-z0-9]+)",
        line
    )

    if pair_match:
        return clean_symbol(
            f"{pair_match.group(1)}/{pair_match.group(2)}"
        )

    return None


def detect_action(clean_text: str) -> str | None:
    upper = clean_text.upper()

    for keyword, action in ACTION_MAP.items():
        if re.search(rf"\b{keyword}\b", upper):
            return action

    if "INVESTMENT" in upper:
        return "BUY"

    return None


def detect_instrument(clean_text: str, symbol: str | None) -> str:
    upper = clean_text.upper()

    if not symbol:
        return "UNKNOWN"

    if (
        "/" in symbol
        or "USDT" in upper
        or "INR" in upper
        or "$" in clean_text
        or "CRYPTO" in upper
        or "BINANCE" in upper
        or "WAZIRX" in upper
        or "COIN" in upper
    ):
        return "CRYPTO"

    return "STOCK"


def normalize_message(db, message):
    clean_text = normalize_text(message.message_text)

    symbol = detect_symbol(clean_text)
    action = detect_action(clean_text)
    instrument = detect_instrument(clean_text, symbol)

    normalized = (
        db.query(NormalizedMessage)
        .filter(
            NormalizedMessage.message_id == message.id
        )
        .first()
    )

    if normalized is None:
        normalized = NormalizedMessage(
            message_id=message.id
        )
        db.add(normalized)

    normalized.clean_text = clean_text
    normalized.symbol = symbol
    normalized.action = action
    normalized.instrument_type = instrument
    normalized.parser_status = "SUCCESS"
    normalized.parser_version = "1.0"

    db.commit()
    db.refresh(normalized)

    return normalized