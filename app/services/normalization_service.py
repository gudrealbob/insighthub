import re

from app.models.normalized_message import NormalizedMessage


CRYPTO_SYMBOLS = {
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
}


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

        if line:
            lines.append(line)

    return "\n".join(lines)


def detect_action(clean_text: str) -> str | None:
    upper = clean_text.upper()

    for keyword, action in ACTION_MAP.items():
        if re.search(rf"\b{keyword}\b", upper):
            return action

    return None


def detect_symbol(clean_text: str) -> str | None:
    upper = clean_text.upper()

    action_words = "|".join(ACTION_MAP.keys())

    match = re.search(
        rf"\b(?:{action_words})\b\s+([A-Z0-9]{2,15})\b",
        upper,
    )

    if match:
        return match.group(1)

    return None


def detect_instrument(symbol: str | None) -> str:
    if not symbol:
        return "UNKNOWN"

    if symbol.upper() in CRYPTO_SYMBOLS:
        return "CRYPTO"

    return "STOCK"


def normalize_message(db, message):
    clean_text = normalize_text(message.message_text)

    symbol = detect_symbol(clean_text)

    action = detect_action(clean_text)

    instrument = detect_instrument(symbol)

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