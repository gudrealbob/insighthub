from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

PARSER_VERSION = 2.0

STATUS_SUCCESS = "SUCCESS"
STATUS_UPDATE = "UPDATE"
STATUS_INFORMATIONAL = "INFORMATIONAL"
STATUS_NO_RECOMMENDATION = "NO_RECOMMENDATION"
STATUS_UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"
STATUS_MULTIPLE_RECOMMENDATIONS = "MULTIPLE_RECS"
STATUS_REPOST = "REPOST"

TARGET_TYPE_FIXED = "FIXED"
TARGET_TYPE_OPEN = "OPEN"
TARGET_TYPE_MULTIPLIER = "MULTIPLIER"
TARGET_TYPE_PERCENT = "PERCENT"
TARGET_TYPE_UNSPECIFIED = "UNSPECIFIED"

ACTION_BUY = "BUY"
ACTION_SELL = "SELL"

INSTRUMENT_STOCK = "STOCK"
INSTRUMENT_CRYPTO = "CRYPTO"
INSTRUMENT_UNKNOWN = "UNKNOWN"

BUY_PHRASES = (
    r"\bbuy\b",
    r"\bcan\s+buy\b",
    r"\bgo\s+long\b",
    r"\bcan\s+go\s+long\b",
    r"\badd\b",
    r"\bcan\s+add\b",
    r"\baccumulat(?:e|ing|ion)\b",
    r"\bmake\s+(?:an?\s+)?entry\b",
    r"\bentry\s+here\b",
    r"\bnew\s+(?:users|friends).*?\badd\b",
    r"\bthose\s+who\s+missed.*?\badd\b",
    r"\bpeople\s+who.*?\bbuy\b",
    r"\bwhoever.*?\badd\b",
    r"\blooking\s+good\s+for\b",
    r"\blooks\s+good\s+for\b",
    r"\bready\s+for\b",
    r"\binvestment\s+pick\b",
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
    r"\bhold\b",
    r"\btrail(?:ing)?\s+(?:sl|stop)\b",
    r"\bupdate\b",
)

INFORMATIONAL_PHRASES = (
    r"new\s+calls\s+will\s+always",
    r"google\s+sheet\s+has\s+all",
    r"few\s+important\s+points",
    r"there\s+are\s+more\s+than\s+\d+\s+crypto",
    r"don't\s+invest\s+more\s+than",
    r"wait\s+for\s+new\s+calls",
    r"small\s+players\s+can\s+avoid",
)

RISK_PATTERNS = (
    ("HIGH", r"\b(?:very\s+)?risky\b|\bhigh\s+risk\b|\bsmall\s+(?:qty|quantity|amount)\b"),
    ("LOW", r"\blow\s+risk\b|\bsafe\s+(?:pick|trade|entry)\b"),
    ("MEDIUM", r"\bmedium\s+risk\b|\bmoderate\s+risk\b"),
)

PATTERN_PATTERNS = (
    ("CUP_AND_HANDLE", r"\bcup\s+and\s+handle\b"),
    ("FLAG", r"\bflag\b"),
    ("POLE_AND_PENNANT", r"\bpole\s+and\s+pennant\b"),
    ("BREAKOUT", r"\bbreakout\b|\bcrossing\s+above\b|\bsustaining\s+above\b"),
    ("REVERSAL", r"\breversal\b|\bu\s*turn\b"),
    ("SUPPORT_ENTRY", r"\bnear\s+support\b|\bsupport\b"),
    ("ACCUMULATION", r"\baccumulat(?:e|ing|ion)\b"),
    ("MULTIBAGGER", r"\bmultibagger\b|\bmulti\s+bagger\b"),
)

PAIR_PATTERN = re.compile(
    r"(?P<base>[A-Za-z][A-Za-z0-9]{1,15})\s*/\s*"
    r"(?P<quote>USDT|USD|INR|BTC|ETH|BUSD|USDC)\b",
    re.IGNORECASE,
)

HEADER_PATTERN = re.compile(
    r"(?m)^\s*(?:investment\s+pick\s*[-:]\s*)?"
    r"(?P<symbol>[A-Za-z][A-Za-z0-9 .&()/-]{0,60}?)"
    r"\s*(?:-|@|:)\s*[$₹]?\s*(?P<price>\d+(?:\.\d+)?)\s*[$₹]?",
    re.IGNORECASE,
)

INLINE_ENTRY_PATTERN = re.compile(
    r"\b(?:add|buy|entry|here|now)\b[^@\n]{0,50}@?\s*[$₹]?\s*"
    r"(?P<price>\d+(?:\.\d+)?)\s*[$₹]?",
    re.IGNORECASE,
)

DIP_RANGE_PATTERN = re.compile(
    r"\b(?:dips?|near|support)\b[^0-9\n]{0,25}"
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:to|-|/)\s*(?P<high>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

DIP_SINGLE_PATTERN = re.compile(
    r"\b(?:dips?|near|support|till)\b[^0-9\n]{0,25}"
    r"(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

STOP_PATTERN = re.compile(
    r"\b(?:stop\s*loss|sl)\b(?:\s+of|\s+at|\s*[:=-])?\s*[$₹]?"
    r"(?P<price>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

TARGET_LINE_PATTERN = re.compile(
    r"\b(?:targets?|tgts?|tgt)\b\s*(?:of|are|is|:|-)?\s*"
    r"(?P<values>[^\n.]{1,120})",
    re.IGNORECASE,
)

PERCENT_PATTERN = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*%\s*(?:to|-)?\s*"
    r"(?P<high>\d+(?:\.\d+)?)?\s*%\s*(?:upside|upmove|return)?",
    re.IGNORECASE,
)

MULTIPLIER_PATTERN = re.compile(
    r"\b(?:(?P<number>\d+(?:\.\d+)?)\s*[xX]|(?P<double>double)|(?P<triple>triple))"
    r"\s*(?:target|tgt|return)?\b",
    re.IGNORECASE,
)

OPEN_TARGET_PATTERN = re.compile(
    r"\b(?:target|tgt)\s+(?:is\s+)?(?:open|as\s+usual)\b",
    re.IGNORECASE,
)

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])(\d+(?:\.\d+)?)")

TRAILING_SYMBOL_NOISE = re.compile(r"[\s.,;:!+\-]+$")
LEADING_SYMBOL_NOISE = re.compile(
    r"^(?:freshview|crypto|investment\s+pick|round\s*\d+|new\s+friends?)\s*[-:,]*\s*",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ParsedRecommendation:
    symbol: str
    action: str
    instrument_type: str
    entry_low: Decimal | None = None
    entry_high: Decimal | None = None
    stop_loss: Decimal | None = None
    target1: Decimal | None = None
    target2: Decimal | None = None
    target3: Decimal | None = None
    pattern: str | None = None
    risk: str | None = None
    targets_json: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "entry_low",
            "entry_high",
            "stop_loss",
            "target1",
            "target2",
            "target3",
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
    instrument_type: str | None = None
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
    """Backward-compatible parser entry point used by earlier services."""
    parsed = parse_message(text=text, tags=tags)
    if parsed.recommendation is None:
        return None
    return parsed.recommendation.to_dict()


def parse_message(
    text: str,
    tags: Iterable[str] | str | None = None,
    known_content_hashes: set[str] | None = None,
) -> ParsedMessage:
    clean_text = clean_message_text(text)
    content_hash = normalized_content_hash(clean_text)

    if not clean_text:
        return ParsedMessage(
            clean_text="",
            parser_status=STATUS_VALIDATION_FAILED,
            parser_version=PARSER_VERSION,
            reason="Message text is blank.",
            content_hash=content_hash,
        )

    if known_content_hashes is not None and content_hash in known_content_hashes:
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_REPOST,
            parser_version=PARSER_VERSION,
            reason="Exact normalized content was already processed.",
            content_hash=content_hash,
        )

    normalized_tags = normalize_tags(tags)
    if _contains_any(clean_text, INFORMATIONAL_PHRASES):
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_INFORMATIONAL,
            parser_version=PARSER_VERSION,
            reason="Informational, disclaimer, or navigation message.",
            content_hash=content_hash,
        )

    if "update" in normalized_tags or _contains_any(clean_text, UPDATE_PHRASES):
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_UPDATE,
            parser_version=PARSER_VERSION,
            reason="Lifecycle update; does not create a new recommendation.",
            content_hash=content_hash,
        )

    symbols = extract_symbols(clean_text)
    action = extract_action(clean_text)
    has_recommendation_tag = bool(
        normalized_tags.intersection({"freshview", "nyse", "crypto", "crypto3", "crypto3.0"})
    )
    has_entry_language = action is not None
    has_price_structure = bool(HEADER_PATTERN.search(clean_text) or INLINE_ENTRY_PATTERN.search(clean_text))

    if not symbols:
        status = STATUS_UNSUPPORTED_FORMAT if has_recommendation_tag else STATUS_NO_RECOMMENDATION
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=status,
            parser_version=PARSER_VERSION,
            action=action,
            reason="No canonical symbol or trading pair could be extracted.",
            content_hash=content_hash,
        )

    if len(symbols) > 1 and not _same_asset_pairs(symbols):
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_MULTIPLE_RECOMMENDATIONS,
            parser_version=PARSER_VERSION,
            symbol=symbols[0],
            action=action,
            reason="Message contains multiple distinct assets and requires TD-004 support.",
            content_hash=content_hash,
        )

    if action is None and not (has_recommendation_tag and has_price_structure):
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_NO_RECOMMENDATION,
            parser_version=PARSER_VERSION,
            symbol=symbols[0],
            reason="Asset was found but no recommendation intent was detected.",
            content_hash=content_hash,
        )

    action = action or ACTION_BUY
    symbol = choose_canonical_symbol(symbols)
    instrument_type = detect_instrument_type(symbol, normalized_tags, clean_text)
    entry_low, entry_high = extract_entry_range(clean_text)
    stop_loss = extract_stop_loss(clean_text)
    target_values, target_metadata = extract_targets(
        clean_text=clean_text,
        reference_entry=entry_low or entry_high,
    )
    pattern = extract_pattern(clean_text)
    risk = extract_risk(clean_text)

    if entry_low is None and entry_high is None:
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_VALIDATION_FAILED,
            parser_version=PARSER_VERSION,
            symbol=symbol,
            instrument_type=instrument_type,
            action=action,
            reason="Recommendation intent found, but entry price could not be extracted.",
            content_hash=content_hash,
        )

    recommendation = ParsedRecommendation(
        symbol=symbol,
        action=action,
        instrument_type=instrument_type,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        target1=target_values[0] if len(target_values) > 0 else None,
        target2=target_values[1] if len(target_values) > 1 else None,
        target3=target_values[2] if len(target_values) > 2 else None,
        pattern=pattern,
        risk=risk,
        targets_json=target_metadata,
    )

    validation_error = validate_recommendation(recommendation)
    if validation_error:
        return ParsedMessage(
            clean_text=clean_text,
            parser_status=STATUS_VALIDATION_FAILED,
            parser_version=PARSER_VERSION,
            symbol=symbol,
            instrument_type=instrument_type,
            action=action,
            recommendation=recommendation,
            reason=validation_error,
            content_hash=content_hash,
        )

    return ParsedMessage(
        clean_text=clean_text,
        parser_status=STATUS_SUCCESS,
        parser_version=PARSER_VERSION,
        symbol=symbol,
        instrument_type=instrument_type,
        action=action,
        recommendation=recommendation,
        content_hash=content_hash,
    )


def clean_message_text(text: str | None) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in value.splitlines():
        line = re.sub(r"#(?:Freshview|Update|NYSE|Crypto3?\.?0?|Takeoutcapital)\b", "", raw_line, flags=re.IGNORECASE)
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
                    return {str(item).strip().casefold() for item in loaded if str(item).strip()}
            except json.JSONDecodeError:
                pass
        return {
            token.strip().lstrip("#").casefold()
            for token in re.split(r"[,;\s]+", candidate)
            if token.strip()
        }
    return {str(item).strip().lstrip("#").casefold() for item in tags if str(item).strip()}


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
    pair_symbols = [
        f"{match.group('base').upper()}/{match.group('quote').upper()}"
        for match in PAIR_PATTERN.finditer(text)
    ]

    # A trading pair is more reliable than a loose header match. Returning
    # pairs immediately prevents date/header lines such as
    # "1st April, 2021" from being interpreted as a second asset.
    if pair_symbols:
        return _dedupe(pair_symbols)

    symbols: list[str] = []
    for match in HEADER_PATTERN.finditer(text):
        candidate = canonicalize_symbol(match.group("symbol"))
        if candidate and candidate not in symbols and not _looks_like_date_or_sentence(candidate):
            symbols.append(candidate)

    if not symbols:
        inline_patterns = (
            r"\badd\s+(?P<symbol>[A-Za-z][A-Za-z0-9]{1,14}(?:\s*/\s*(?:USDT|USD|INR))?)\s+(?:here|now|again)\b",
            r"\b(?P<symbol>[A-Za-z][A-Za-z0-9]{1,14}(?:\s*/\s*(?:USDT|USD|INR))?)\s+here\s+@\s*",
            r"\b(?P<symbol>[A-Za-z][A-Za-z0-9]{1,14})\s+ready\s+for\b",
        )
        for pattern in inline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = canonicalize_symbol(match.group("symbol"))
                if candidate:
                    symbols.append(candidate)
                    break

    return _dedupe(symbols)


def canonicalize_symbol(raw_symbol: str) -> str:
    value = raw_symbol.strip()
    value = LEADING_SYMBOL_NOISE.sub("", value)
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*\([^)]*\)\s*", "", value)
    value = TRAILING_SYMBOL_NOISE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip()

    if "/" in value:
        parts = value.split("/", 1)
        return f"{parts[0].upper()}/{parts[1].upper()}"

    aliases = {
        "NVIDIA CORPORATION": "NVIDIA",
        "INTEL CORPORATION": "INTEL",
        "NAVITAS SEMICONDUCTOR CORPORATION": "NAVITAS SEMICONDUCTOR",
        "VET VECHAIN": "VET",
    }
    normalized = value.upper()
    return aliases.get(normalized, normalized)


def choose_canonical_symbol(symbols: list[str]) -> str:
    pair_symbols = [symbol for symbol in symbols if "/" in symbol]
    if pair_symbols:
        preferred_quotes = ("USDT", "USD", "INR", "USDC", "BUSD", "BTC", "ETH")
        for quote in preferred_quotes:
            for symbol in pair_symbols:
                if symbol.endswith(f"/{quote}"):
                    return symbol
    return symbols[0]


def detect_instrument_type(symbol: str, tags: set[str], text: str) -> str:
    if tags.intersection({"crypto", "crypto3", "crypto3.0"}):
        return INSTRUMENT_CRYPTO
    if "nyse" in tags:
        return INSTRUMENT_STOCK

    if "/" in symbol:
        quote = symbol.rsplit("/", 1)[1]
        if quote in {"USDT", "BTC", "ETH", "BUSD", "USDC", "INR", "USD"}:
            return INSTRUMENT_CRYPTO

    stock_names = (
        "NVIDIA",
        "INTEL",
        "EVERQUOTE",
        "REDDIT",
        "NAVITAS SEMICONDUCTOR",
        "WALMART",
        "VISA",
    )
    if symbol in stock_names:
        return INSTRUMENT_STOCK

    if re.search(r"\b(?:crypto|coin|token|binance|usdt|wazirx)\b", text, re.IGNORECASE):
        return INSTRUMENT_CRYPTO

    return INSTRUMENT_STOCK


def extract_entry_range(text: str) -> tuple[Decimal | None, Decimal | None]:
    header = HEADER_PATTERN.search(text)
    header_price = _decimal(header.group("price")) if header else None

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


def extract_stop_loss(text: str) -> Decimal | None:
    match = STOP_PATTERN.search(text)
    return _decimal(match.group("price")) if match else None


def extract_targets(
    clean_text: str,
    reference_entry: Decimal | None,
) -> tuple[list[Decimal], dict[str, Any]]:
    if OPEN_TARGET_PATTERN.search(clean_text):
        return [], {
            "target_type": TARGET_TYPE_OPEN,
            "targets": [],
            "source_text": "OPEN",
        }

    multiplier_match = MULTIPLIER_PATTERN.search(clean_text)
    if multiplier_match:
        if multiplier_match.group("double"):
            multiplier = Decimal("2")
        elif multiplier_match.group("triple"):
            multiplier = Decimal("3")
        else:
            multiplier = _decimal(multiplier_match.group("number"))
        absolute = reference_entry * multiplier if reference_entry is not None and multiplier is not None else None
        targets = [absolute] if absolute is not None else []
        return targets, {
            "target_type": TARGET_TYPE_MULTIPLIER,
            "multiplier": float(multiplier) if multiplier is not None else None,
            "reference_entry": float(reference_entry) if reference_entry is not None else None,
            "targets": [float(value) for value in targets],
        }

    percent_match = PERCENT_PATTERN.search(clean_text)
    if percent_match:
        low_pct = _decimal(percent_match.group("low"))
        high_pct = _decimal(percent_match.group("high")) or low_pct
        targets: list[Decimal] = []
        if reference_entry is not None and low_pct is not None:
            targets.append(reference_entry * (Decimal("1") + low_pct / Decimal("100")))
        if reference_entry is not None and high_pct is not None and high_pct != low_pct:
            targets.append(reference_entry * (Decimal("1") + high_pct / Decimal("100")))
        return targets, {
            "target_type": TARGET_TYPE_PERCENT,
            "percent_low": float(low_pct) if low_pct is not None else None,
            "percent_high": float(high_pct) if high_pct is not None else None,
            "reference_entry": float(reference_entry) if reference_entry is not None else None,
            "targets": [float(value) for value in targets],
        }

    target_match = TARGET_LINE_PATTERN.search(clean_text)
    if target_match:
        values = [
            value
            for value in (_decimal(token) for token in NUMBER_PATTERN.findall(target_match.group("values")))
            if value is not None
        ][:3]
        return values, {
            "target_type": TARGET_TYPE_FIXED,
            "targets": [float(value) for value in values],
        }

    looking_good_match = re.search(
        r"\b(?:looking|looks)\s+good\s+for\s+(?P<values>[^\n.]{1,80})",
        clean_text,
        re.IGNORECASE,
    )
    if looking_good_match:
        values = [
            value
            for value in (_decimal(token) for token in NUMBER_PATTERN.findall(looking_good_match.group("values")))
            if value is not None
        ][:3]
        if values and not any("%" in token for token in looking_good_match.group("values").split()):
            return values, {
                "target_type": TARGET_TYPE_FIXED,
                "targets": [float(value) for value in values],
            }

    return [], {
        "target_type": TARGET_TYPE_UNSPECIFIED,
        "targets": [],
    }


def extract_pattern(text: str) -> str | None:
    for name, pattern in PATTERN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return None


def extract_risk(text: str) -> str | None:
    for name, pattern in RISK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    if re.search(r"\b(?:5|10)\s*%\s+(?:only|of\s+(?:your|ur)\s+capital)\b", text, re.IGNORECASE):
        return "HIGH"
    return None


def validate_recommendation(recommendation: ParsedRecommendation) -> str | None:
    if not recommendation.symbol:
        return "Symbol is required."
    if recommendation.action not in {ACTION_BUY, ACTION_SELL}:
        return "Action must be BUY or SELL."
    if recommendation.entry_low is None or recommendation.entry_high is None:
        return "Entry low and entry high are required."
    if recommendation.entry_low > recommendation.entry_high:
        return "Entry low cannot exceed entry high."
    if recommendation.action == ACTION_BUY:
        if recommendation.stop_loss is not None and recommendation.stop_loss >= recommendation.entry_high:
            return "BUY stop loss must be below the entry range."
        for target in (
            recommendation.target1,
            recommendation.target2,
            recommendation.target3,
        ):
            if target is not None and target <= recommendation.entry_low:
                return "BUY targets must be above the entry range."
    return None


def _same_asset_pairs(symbols: list[str]) -> bool:
    bases = {symbol.split("/", 1)[0] for symbol in symbols}
    return len(bases) == 1


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in patterns)


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
        if value not in seen:
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
    return value in blocked or bool(re.fullmatch(r"\d{1,2}(?:ST|ND|RD|TH)?\s+[A-Z]+", value))