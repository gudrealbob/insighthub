from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

PARSER_VERSION = 2.1
OPEN_TARGET_VALUE = Decimal("999")

STATUS_SUCCESS = "SUCCESS"
STATUS_UPDATE = "UPDATE"
STATUS_INFORMATIONAL = "INFORMATIONAL"
STATUS_NO_RECOMMENDATION = "NO_RECOMMENDATION"
STATUS_UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"
STATUS_MULTIPLE_RECOMMENDATIONS = "MULTIPLE_RECOMMENDATIONS"
STATUS_REPOST = "REPOST"

ACTION_BUY = "BUY"
ACTION_SELL = "SELL"

INSTRUMENT_STOCK = "STOCK"
INSTRUMENT_CRYPTO = "CRYPTO"
INSTRUMENT_UNKNOWN = "UNKNOWN"

ENTRY_CURRENT_PRICE = "CURRENT_PRICE"
ENTRY_BUY_ON_DIPS = "BUY_ON_DIPS"
ENTRY_ADD = "ADD"
ENTRY_AVERAGE = "AVERAGE"
ENTRY_REENTRY = "REENTRY"
ENTRY_STAGED = "STAGED_ENTRY"
ENTRY_UNSPECIFIED = "UNSPECIFIED"

PRICE_SOURCE_MESSAGE = "MESSAGE"
PRICE_SOURCE_MARKET_LOOKUP_PENDING = "MARKET_LOOKUP_PENDING"

TARGET_TYPE_FIXED = "FIXED"
TARGET_TYPE_OPEN = "OPEN"
TARGET_TYPE_MULTIPLIER = "MULTIPLIER"
TARGET_TYPE_PERCENT = "PERCENT"
TARGET_TYPE_QUALITATIVE = "QUALITATIVE"
TARGET_TYPE_UNSPECIFIED = "UNSPECIFIED"

CRYPTO_SYMBOLS = {
    "1INCH", "AR", "ATOM", "BAKE", "BAT", "COW", "DASH", "ENJ", "EPT",
    "GALA", "HOT", "KLAY", "LINA", "LINK", "LTC", "METIS", "NANO",
    "PHB", "TWT", "WTC",
}

STOCK_NAMES = {
    "FRONTLINE PLC",
    "NEXTERA ENERGY",
    "STARBUCKS",
}

BUY_PHRASES = (
    r"\bbuy\b",
    r"\bgo\s+long\b",
    r"\bcan\s+add\b",
    r"\badd(?:ed|ing)?\b",
    r"\baccumulat(?:e|ing|ion)\b",
    r"\baverage\b",
    r"\bentry\b",
    r"\blooking\s+good\s+for\b",
    r"\blooks\s+good\s+for\b",
    r"\bcan\s+be\s+added\b",
    r"\btime\s+for\b",
    r"\blet'?s\s+(?:catch|drive|milk|bake)\b",
)

SELL_PHRASES = (
    r"\bsell\b",
    r"\bshort\b",
    r"\bgo\s+short\b",
)

UPDATE_PHRASES = (
    r"\bbook(?:ed)?\s+(?:full|partial|profit|profits)\b",
    r"\btarget\s+(?:achieved|hit|done)\b",
    r"\btgt\s+(?:achieved|hit|done)\b",
    r"\bstop\s*loss\s+(?:hit|triggered)\b",
    r"\bsl\s+(?:hit|triggered)\b",
    r"\bexit\b",
    r"\btrail(?:ing)?\s+(?:sl|stop)\b",
)

INFORMATIONAL_PHRASES = (
    r"new\s+calls\s+will\s+always",
    r"google\s+sheet\s+has\s+all",
    r"few\s+important\s+points",
    r"wait\s+for\s+new\s+calls",
)

PAIR_PATTERN = re.compile(
    r"(?P<base>[A-Za-z][A-Za-z0-9]{1,15})\s*/\s*"
    r"(?P<quote>USDT|USD|INR|BTC|ETH|BUSD|USDC)\b",
    re.IGNORECASE,
)

HEADER_WITH_SEPARATOR = re.compile(
    r"(?m)^\s*(?P<symbol>[A-Za-z0-9][A-Za-z0-9 .&()/'-]{0,60}?)"
    r"\s*(?:-|@|,|:)\s*[$₹]?\s*(?P<price>\d+(?:\.\d+)?)\s*[$₹]?",
    re.IGNORECASE,
)

HEADER_SIMPLE = re.compile(
    r"(?m)^\s*(?P<symbol>[A-Za-z0-9][A-Za-z0-9 .&()/'-]{0,50}?)"
    r"\s+[$₹]?(?P<price>\d+(?:\.\d+)?)\s*[$₹]\s*$",
    re.IGNORECASE,
)

INLINE_ENTRY_PATTERN = re.compile(
    r"\b(?:at|@|cmp|entry|now)\b[^0-9\n]{0,20}"
    r"[$₹]?\s*(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

DIP_RANGE_PATTERN = re.compile(
    r"\b(?:dips?|near|support|till)\b[^0-9\n]{0,25}"
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:to|-|/)\s*(?P<high>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

DIP_SINGLE_PATTERN = re.compile(
    r"\b(?:dips?|near|till)\b[^0-9\n]{0,25}(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

STOP_PATTERN = re.compile(
    r"\b(?:stop\s*loss|sl)\b(?:\s+of|\s+at|\s*[:=-])?\s*[$₹]?"
    r"(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

SUPPORT_PATTERN = re.compile(
    r"\bsupport\b(?:\s+at|\s+near|\s*[:=-])?\s*[$₹]?"
    r"(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

TRIGGER_PATTERN = re.compile(
    r"\b(?:closing|close|sustain(?:ing)?|cross(?:ing)?)\s+above\s+"
    r"[$₹]?(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

TARGET_LINE_PATTERN = re.compile(
    r"\b(?:targets?|tgts?|tgt)\b\s*(?:of|are|is|:|-)?\s*"
    r"(?P<values>[^\n]{1,160})",
    re.IGNORECASE,
)

LOOKING_GOOD_PATTERN = re.compile(
    r"\b(?:looking|looks)\s+good\s+for\s+(?P<values>[^\n.]{1,80})",
    re.IGNORECASE,
)

OPEN_TARGET_PATTERN = re.compile(
    r"\b(?:target|tgt)\s+(?:is\s+)?open\b",
    re.IGNORECASE,
)

MULTIPLIER_PATTERN = re.compile(
    r"\b(?:(?P<number>\d+(?:\.\d+)?)\s*[xX]|(?P<double>double)|"
    r"(?P<triple>triple))\s*(?:target|tgt|return)?\b",
    re.IGNORECASE,
)

THREE_DIGIT_PATTERN = re.compile(r"\b3\s*digit\s+(?:target|tgt)\b", re.IGNORECASE)
QUALITATIVE_TARGET_PATTERN = re.compile(
    r"\b(?:channel\s+top|big\s+move)\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])(\d+(?:\.\d+)?)")


@dataclass(slots=True)
class ParsedRecommendation:
    symbol: str
    action: str
    instrument_type: str
    entry_low: Decimal | None = None
    entry_high: Decimal | None = None
    entry_instruction: str = ENTRY_UNSPECIFIED
    entry_instruction_text: str | None = None
    entry_price_source: str = PRICE_SOURCE_MESSAGE
    stop_loss: Decimal | None = None
    support_level: Decimal | None = None
    trigger_level: Decimal | None = None
    target1: Decimal | None = None
    target2: Decimal | None = None
    target3: Decimal | None = None
    pattern: str | None = None
    risk: str | None = None
    targets_json: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "entry_low", "entry_high", "stop_loss", "support_level",
            "trigger_level", "target1", "target2", "target3",
        ):
            value = result[key]
            result[key] = float(value) if value is not None else None
        return result


@dataclass(slots=True)
class ParsedMessage:
    clean_text: str
    parser_status: str
    parser_version: float
    symbol: str | None = None
    instrument_type: str = INSTRUMENT_UNKNOWN
    action: str | None = None
    recommendation: ParsedRecommendation | None = None
    reason: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.recommendation is not None:
            result["recommendation"] = self.recommendation.to_dict()
        return result


def parse_recommendation(
    text: str,
    tags: Iterable[str] | str | None = None,
) -> dict[str, Any] | None:
    parsed = parse_message(text=text, tags=tags)
    return parsed.recommendation.to_dict() if parsed.recommendation else None


def parse_message(
    text: str,
    tags: Iterable[str] | str | None = None,
    known_content_hashes: set[str] | None = None,
) -> ParsedMessage:
    raw_text = text or ""
    clean_text = clean_message_text(raw_text)
    content_hash = normalized_content_hash(clean_text)
    normalized_tags = normalize_tags(tags)
    hashtags = {tag.casefold() for tag in re.findall(r"#([A-Za-z0-9.]+)", raw_text)}
    normalized_tags.update(hashtags)

    if not clean_text:
        return _message(
            clean_text, STATUS_VALIDATION_FAILED, content_hash,
            reason="Message text is blank.",
        )

    if known_content_hashes is not None and content_hash in known_content_hashes:
        return _message(
            clean_text, STATUS_REPOST, content_hash,
            reason="Exact normalized content was already processed.",
        )

    if _contains_any(clean_text, INFORMATIONAL_PHRASES):
        return _message(
            clean_text, STATUS_INFORMATIONAL, content_hash,
            reason="Informational message.",
        )

    # Hashtag is authoritative: UPDATE never creates a new recommendation.
    if "update" in normalized_tags or _contains_any(clean_text, UPDATE_PHRASES):
        return _message(
            clean_text, STATUS_UPDATE, content_hash,
            reason="Lifecycle update; does not create a new recommendation.",
        )

    is_freshview = "freshview" in normalized_tags
    symbols = extract_symbols(clean_text)
    action = extract_action(clean_text)

    # Business rule: every #Freshview is a new BUY recommendation.
    if is_freshview:
        action = ACTION_BUY

    if not symbols:
        return _message(
            clean_text,
            STATUS_UNSUPPORTED_FORMAT if is_freshview else STATUS_NO_RECOMMENDATION,
            content_hash,
            action=action,
            reason="No symbol could be extracted.",
        )

    if len(symbols) > 1 and not _same_asset_pairs(symbols):
        return _message(
            clean_text,
            STATUS_MULTIPLE_RECOMMENDATIONS,
            content_hash,
            symbol=symbols[0],
            action=action,
            reason="Message contains multiple distinct assets.",
        )

    if action is None:
        return _message(
            clean_text,
            STATUS_NO_RECOMMENDATION,
            content_hash,
            symbol=symbols[0],
            reason="Asset found but recommendation intent was not detected.",
        )

    symbol = choose_canonical_symbol(symbols)
    instrument_type = detect_instrument_type(symbol, normalized_tags, clean_text)
    entry_low, entry_high = extract_entry_range(clean_text)
    entry_instruction, instruction_text = extract_entry_instruction(clean_text)
    entry_price_source = (
        PRICE_SOURCE_MESSAGE
        if entry_low is not None or entry_high is not None
        else PRICE_SOURCE_MARKET_LOOKUP_PENDING
    )
    stop_loss = extract_level(STOP_PATTERN, clean_text)
    support_level = extract_level(SUPPORT_PATTERN, clean_text)
    trigger_level = extract_level(TRIGGER_PATTERN, clean_text)
    target_values, target_metadata = extract_targets(
        clean_text, entry_low or entry_high
    )

    recommendation = ParsedRecommendation(
        symbol=symbol,
        action=action,
        instrument_type=instrument_type,
        entry_low=entry_low,
        entry_high=entry_high,
        entry_instruction=entry_instruction,
        entry_instruction_text=instruction_text,
        entry_price_source=entry_price_source,
        stop_loss=stop_loss,
        support_level=support_level,
        trigger_level=trigger_level,
        target1=target_values[0] if len(target_values) > 0 else None,
        target2=target_values[1] if len(target_values) > 1 else None,
        target3=target_values[2] if len(target_values) > 2 else None,
        pattern=extract_pattern(clean_text),
        risk=extract_risk(clean_text),
        targets_json=target_metadata,
    )

    validation_error = validate_recommendation(recommendation)
    if validation_error:
        return _message(
            clean_text,
            STATUS_VALIDATION_FAILED,
            content_hash,
            symbol=symbol,
            instrument_type=instrument_type,
            action=action,
            recommendation=recommendation,
            reason=validation_error,
        )

    return _message(
        clean_text,
        STATUS_SUCCESS,
        content_hash,
        symbol=symbol,
        instrument_type=instrument_type,
        action=action,
        recommendation=recommendation,
    )


def clean_message_text(text: str | None) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in value.splitlines():
        line = re.sub(
            r"#(?:Freshview|Update|USstocks|NYSE|NASDAQ|Crypto3?\.?0?|Crypto|Takeoutcapital)\b",
            "",
            raw_line,
            flags=re.IGNORECASE,
        )
        line = re.sub(r"[^\x00-\x7F]+", " ", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def normalize_tags(tags: Iterable[str] | str | None) -> set[str]:
    if tags is None:
        return set()
    if isinstance(tags, str):
        candidate = tags.strip()
        if candidate.startswith("["):
            try:
                loaded = json.loads(candidate)
                if isinstance(loaded, list):
                    return {
                        str(item).strip().lstrip("#").casefold()
                        for item in loaded if str(item).strip()
                    }
            except json.JSONDecodeError:
                pass
        return {
            token.strip().lstrip("#").casefold()
            for token in re.split(r"[,;\s]+", candidate)
            if token.strip()
        }
    return {
        str(item).strip().lstrip("#").casefold()
        for item in tags if str(item).strip()
    }


def normalized_content_hash(text: str) -> str:
    canonical = re.sub(r"\s+", " ", text).strip().casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_action(text: str) -> str | None:
    if _contains_any(text, SELL_PHRASES):
        return ACTION_SELL
    if _contains_any(text, BUY_PHRASES):
        return ACTION_BUY
    return None


def extract_symbols(text: str) -> list[str]:
    symbols: list[str] = []

    for match in PAIR_PATTERN.finditer(text):
        symbols.append(
            f"{match.group('base').upper()}/{match.group('quote').upper()}"
        )

    for pattern in (HEADER_WITH_SEPARATOR, HEADER_SIMPLE):
        for match in pattern.finditer(text):
            candidate = canonicalize_symbol(match.group("symbol"))
            if candidate and not _looks_like_date_or_sentence(candidate):
                symbols.append(candidate)

    conversational_patterns = (
        r"\b(?:add|average)\s+(?P<symbol>[A-Za-z0-9]{2,15})\b",
        r"\btime\s+for\s+(?P<symbol>[A-Za-z0-9]{2,15})\b",
        r"\blet'?s\s+(?:catch|drive)\s+(?:some\s+)?(?P<symbol>[A-Za-z0-9]{2,15})\b",
        r"\blet'?s\s+milk\s+it\b[\s\S]{0,60}\b(?P<symbol>COW)\b",
        r"\blet'?s\s+['\"]?(?P<symbol>BAKE)['\"]?\b",
        r"\b(?P<symbol>[A-Za-z0-9]{2,15})\s*-\s*"
        r"(?:[A-Za-z][A-Za-z ]{2,40})\s+(?P<price>\d+(?:\.\d+)?)",
    )
    for pattern in conversational_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = canonicalize_symbol(match.group("symbol"))
            if candidate:
                symbols.append(candidate)

    # Last-resort lookup against known tickers appearing as standalone tokens.
    upper_text = text.upper()
    for ticker in sorted(CRYPTO_SYMBOLS, key=len, reverse=True):
        if re.search(rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])", upper_text):
            symbols.append(ticker)

    return _dedupe(symbols)


def canonicalize_symbol(raw_symbol: str) -> str:
    value = raw_symbol.strip()
    value = re.sub(
        r"^(?:freshview|crypto|investment\s+pick|round\s*\d+)\s*[-:,]*\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*\([^)]*\)\s*", "", value)
    value = re.sub(r"[\s.,;:!+\-]+$", "", value)
    value = re.sub(r"\s+", " ", value).strip().upper()

    aliases = {
        "NEXTERA ENERGY": "NEXTERA ENERGY",
        "FRONTLINE PLC": "FRONTLINE PLC",
        "STARBUCKS": "STARBUCKS",
    }
    return aliases.get(value, value)


def choose_canonical_symbol(symbols: list[str]) -> str:
    pair_symbols = [symbol for symbol in symbols if "/" in symbol]
    return pair_symbols[0] if pair_symbols else symbols[0]


def detect_instrument_type(symbol: str, tags: set[str], text: str) -> str:
    if tags.intersection({"crypto", "crypto3", "crypto3.0"}):
        return INSTRUMENT_CRYPTO
    if tags.intersection({"usstocks", "nyse", "nasdaq"}):
        return INSTRUMENT_STOCK

    base_symbol = symbol.split("/", 1)[0]
    if "/" in symbol or base_symbol in CRYPTO_SYMBOLS:
        return INSTRUMENT_CRYPTO
    if symbol in STOCK_NAMES:
        return INSTRUMENT_STOCK
    if re.search(r"\b(?:crypto|coin|token|usdt|wazirx|binance)\b", text, re.IGNORECASE):
        return INSTRUMENT_CRYPTO
    return INSTRUMENT_UNKNOWN


def extract_entry_range(text: str) -> tuple[Decimal | None, Decimal | None]:
    header_price = None
    for pattern in (HEADER_WITH_SEPARATOR, HEADER_SIMPLE):
        match = pattern.search(text)
        if match:
            header_price = _decimal(match.group("price"))
            break

    range_match = DIP_RANGE_PATTERN.search(text)
    if range_match:
        first = _decimal(range_match.group("low"))
        second = _decimal(range_match.group("high"))
        if first is not None and second is not None:
            low, high = sorted((first, second))
            if header_price is not None:
                high = max(high, header_price)
            return low, high

    single_dip = DIP_SINGLE_PATTERN.search(text)
    if single_dip:
        dip = _decimal(single_dip.group("price"))
        if dip is not None and header_price is not None:
            return min(dip, header_price), max(dip, header_price)
        if dip is not None:
            return dip, dip

    inline = INLINE_ENTRY_PATTERN.search(text)
    inline_price = _decimal(inline.group("price")) if inline else None
    price = header_price or inline_price
    return (price, price) if price is not None else (None, None)


def extract_entry_instruction(text: str) -> tuple[str, str | None]:
    rules = (
        (ENTRY_STAGED, r"\b\d+\s*%\s+now\b.*?\b\d+\s*%\s+(?:near|on\s+dips?)\b"),
        (ENTRY_AVERAGE, r"\baverage\b"),
        (ENTRY_REENTRY, r"\bre-?entry\b"),
        (ENTRY_BUY_ON_DIPS, r"\bbuy\s+on\s+dips?\b|\badd\s+on\s+dips?\b"),
        (ENTRY_ADD, r"\bcan\s+add\b|\badd\s+now\b|\bmissed\s+to\s+add\b"),
    )
    for instruction, pattern in rules:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            line = next(
                (line.strip() for line in text.splitlines()
                 if re.search(pattern, line, re.IGNORECASE)),
                match.group(0),
            )
            return instruction, line[:500]
    return ENTRY_CURRENT_PRICE, None


def extract_level(pattern: re.Pattern[str], text: str) -> Decimal | None:
    match = pattern.search(text)
    return _decimal(match.group("price")) if match else None


def extract_targets(
    text: str,
    reference_entry: Decimal | None,
) -> tuple[list[Decimal], dict[str, Any]]:
    if OPEN_TARGET_PATTERN.search(text):
        return [OPEN_TARGET_VALUE], {
            "target_type": TARGET_TYPE_OPEN,
            "targets": [float(OPEN_TARGET_VALUE)],
            "sentinel_value": float(OPEN_TARGET_VALUE),
            "source_text": "OPEN",
        }

    if THREE_DIGIT_PATTERN.search(text):
        return [], {
            "target_type": TARGET_TYPE_QUALITATIVE,
            "targets": [],
            "source_text": "THREE_DIGIT",
        }

    qualitative = QUALITATIVE_TARGET_PATTERN.search(text)
    if qualitative:
        return [], {
            "target_type": TARGET_TYPE_QUALITATIVE,
            "targets": [],
            "source_text": qualitative.group(0).upper(),
        }

    multiplier = MULTIPLIER_PATTERN.search(text)
    if multiplier:
        factor = (
            Decimal("2") if multiplier.group("double")
            else Decimal("3") if multiplier.group("triple")
            else _decimal(multiplier.group("number"))
        )
        absolute = (
            reference_entry * factor
            if reference_entry is not None and factor is not None
            else None
        )
        values = [absolute] if absolute is not None else []
        return values, {
            "target_type": TARGET_TYPE_MULTIPLIER,
            "multiplier": float(factor) if factor is not None else None,
            "targets": [float(value) for value in values],
        }

    for pattern in (TARGET_LINE_PATTERN, LOOKING_GOOD_PATTERN):
        match = pattern.search(text)
        if match:
            values = [
                value for value in (
                    _decimal(token)
                    for token in NUMBER_PATTERN.findall(match.group("values"))
                )
                if value is not None
            ][:3]
            if values:
                return values, {
                    "target_type": TARGET_TYPE_FIXED,
                    "targets": [float(value) for value in values],
                }

    return [], {
        "target_type": TARGET_TYPE_UNSPECIFIED,
        "targets": [],
    }


def extract_pattern(text: str) -> str | None:
    patterns = (
        ("CUP_AND_HANDLE", r"\bcup\s+and\s+handle\b"),
        ("FLAG", r"\bflag\b"),
        ("BREAKOUT", r"\bbreakout\b|\bcrossing\s+above\b|\bsustaining\s+above\b"),
        ("REVERSAL", r"\breversal\b|\bu\s*turn\b"),
        ("SUPPORT_ENTRY", r"\bnear\s+support\b"),
        ("ACCUMULATION", r"\baccumulat(?:e|ing|ion)\b|\baverage\b"),
    )
    for name, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return None


def extract_risk(text: str) -> str | None:
    if re.search(r"\bsmall\s+(?:qty|quantity|amount)\b|\bhigh\s+risk\b", text, re.IGNORECASE):
        return "HIGH"
    if re.search(r"\blow\s+risk\b|\bsafe\s+(?:pick|trade|entry)\b", text, re.IGNORECASE):
        return "LOW"
    if re.search(r"\bmedium\s+risk\b|\bmoderate\s+risk\b", text, re.IGNORECASE):
        return "MEDIUM"
    return None


def validate_recommendation(recommendation: ParsedRecommendation) -> str | None:
    if not recommendation.symbol:
        return "Symbol is required."
    if recommendation.action not in {ACTION_BUY, ACTION_SELL}:
        return "Action must be BUY or SELL."
    if recommendation.instrument_type not in {
        INSTRUMENT_STOCK, INSTRUMENT_CRYPTO, INSTRUMENT_UNKNOWN
    }:
        return "Invalid instrument type."
    if (
        recommendation.entry_low is not None
        and recommendation.entry_high is not None
        and recommendation.entry_low > recommendation.entry_high
    ):
        return "Entry low cannot exceed entry high."

    # Missing entry is valid and intentionally queued for market-price enrichment.
    if recommendation.entry_low is None and recommendation.entry_high is None:
        if recommendation.entry_price_source != PRICE_SOURCE_MARKET_LOOKUP_PENDING:
            return "Missing entry must be marked MARKET_LOOKUP_PENDING."
        return None

    if recommendation.action == ACTION_BUY:
        if (
            recommendation.stop_loss is not None
            and recommendation.entry_high is not None
            and recommendation.stop_loss >= recommendation.entry_high
        ):
            return "BUY stop loss must be below the entry range."
        for target in (
            recommendation.target1,
            recommendation.target2,
            recommendation.target3,
        ):
            if target is None or target == OPEN_TARGET_VALUE:
                continue
            if (
                recommendation.entry_low is not None
                and target <= recommendation.entry_low
            ):
                return "BUY numeric targets must be above the entry range."
    return None


def _message(
    clean_text: str,
    status: str,
    content_hash: str,
    *,
    symbol: str | None = None,
    instrument_type: str = INSTRUMENT_UNKNOWN,
    action: str | None = None,
    recommendation: ParsedRecommendation | None = None,
    reason: str | None = None,
) -> ParsedMessage:
    return ParsedMessage(
        clean_text=clean_text,
        parser_status=status,
        parser_version=PARSER_VERSION,
        symbol=symbol,
        instrument_type=instrument_type or INSTRUMENT_UNKNOWN,
        action=action,
        recommendation=recommendation,
        reason=reason,
        content_hash=content_hash,
    )


def _same_asset_pairs(symbols: list[str]) -> bool:
    bases = {symbol.split("/", 1)[0] for symbol in symbols}
    return len(bases) == 1


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(
        re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        for pattern in patterns
    )


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _looks_like_date_or_sentence(value: str) -> bool:
    blocked = {
        "CAN ADD NOW",
        "TARGET OPEN",
        "TGT OPEN",
        "SUPPORT",
        "NEW USERS",
        "OLD USERS",
    }
    if value in blocked:
        return True
    if re.search(r"\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", value):
        return True
    return len(value.split()) > 6