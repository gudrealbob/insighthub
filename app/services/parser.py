import re


NUMBER_PATTERN = r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"


def parse_number(value: str | None):
    if value is None:
        return None

    return float(value.replace(",", ""))


def first_content_line(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()

        if line:
            return line

    return ""


def parse_header_price(text: str):
    line = first_content_line(text)

    match = re.search(
        rf"[-,]\s*[$₹]?{NUMBER_PATTERN}\s*[$₹]?",
        line,
    )

    if match:
        return parse_number(match.group(1))

    return None


def parse_entry(text: str):
    header_price = parse_header_price(text)

    range_patterns = [
        rf"\bENTRY\s*[:\-]?\s*[$₹]?{NUMBER_PATTERN}\s*[$₹]?\s*(?:\-|TO)\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+NOW\s+AND\s+IN\s+DIPS\s+TILL\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bCAN\s+BUY\s+NOW\s+AND\s+IN\s+DIPS\s+TILL\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+ON\s+DIPS\s+TILL\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bIN\s+DIPS\s+TILL\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bDIPS\s+TILL\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bNEAR\s*[$₹]?{NUMBER_PATTERN}",
    ]

    for pattern in range_patterns:
        match = re.search(pattern, text)

        if match:
            price = parse_number(match.group(1))

            if header_price is not None:
                return min(header_price, price), max(header_price, price)

            return price, price

    single_patterns = [
        rf"\bENTRY\s*[:\-]?\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+ABOVE\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bCROSSING\s+ABOVE\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bABOVE\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+AT\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+NEAR\s*[$₹]?{NUMBER_PATTERN}",
        rf"\bBUY\s+AROUND\s*[$₹]?{NUMBER_PATTERN}",
    ]

    for pattern in single_patterns:
        match = re.search(pattern, text)

        if match:
            price = parse_number(match.group(1))
            return price, price

    if header_price is not None:
        return header_price, header_price

    return None, None


def parse_stop_loss(text: str):
    patterns = [
        rf"\b(?:SL|STOP LOSS|STOPLOSS)\s*(?:OF|AT|:|-)?\s*[$₹]?{NUMBER_PATTERN}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return parse_number(match.group(1))

    return None


def parse_targets(text: str):
    targets = []

    target_phrases = re.findall(
        rf"\b(?:TGT|TARGET)\s*(?:OF|:|-)?\s*((?:[$₹]?[0-9]+(?:,[0-9]{{3}})*(?:\.[0-9]+)?(?:\+\+)?\s*,?\s*)+)",
        text,
    )

    for phrase in target_phrases:
        values = re.findall(NUMBER_PATTERN, phrase)

        for value in values:
            targets.append(parse_number(value))

    expect_phrases = re.findall(
        rf"\b(?:CAN\s+EXPECT|EXPECT)\s*((?:[$₹]?[0-9]+(?:,[0-9]{{3}})*(?:\.[0-9]+)?(?:\+\+)?\s*,?\s*)+)",
        text,
    )

    for phrase in expect_phrases:
        values = re.findall(NUMBER_PATTERN, phrase)

        for value in values:
            targets.append(parse_number(value))

    term_targets = re.findall(
        rf"\b(?:SHORT\s+TERM\s+TGT|LONG\s+TERM\s+TGT)\s*[$₹]?{NUMBER_PATTERN}",
        text,
    )

    for value in term_targets:
        targets.append(parse_number(value))

    multiply_targets = re.findall(
        r"\b([0-9]+(?:\.[0-9]+)?)\s*X\b",
        text,
    )

    for value in multiply_targets:
        targets.append(float(value))

    if "DOUBLE" in text and not targets:
        targets.append(2.0)

    deduped = []

    for target in targets:
        if target is not None and target not in deduped:
            deduped.append(target)

    return deduped


def parse_pattern(text: str):
    pattern_match = re.search(
        r"\b(BREAKOUT|DIVERGENCE|FALLING WEDGE|POLE AND PENNANT|WEDGE|PENNANT)\b.*",
        text,
    )

    if pattern_match:
        return pattern_match.group(0).strip()

    return None


def parse_risk(text: str):
    risk_match = re.search(
        r"\bRISK\s*[:\-]?\s*(LOW|MEDIUM|HIGH)",
        text,
    )

    if risk_match:
        return risk_match.group(1)

    return None


def parse_recommendation(
    clean_text: str,
    symbol: str | None = None,
    action: str | None = None,
):
    text = clean_text.upper()

    entry_low, entry_high = parse_entry(text)
    stop_loss = parse_stop_loss(text)
    targets = parse_targets(text)

    target1 = targets[0] if len(targets) > 0 else None
    target2 = targets[1] if len(targets) > 1 else None
    target3 = targets[2] if len(targets) > 2 else None

    pattern = parse_pattern(text)
    risk = parse_risk(text)

    return {
        "symbol": symbol,
        "action": action,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop_loss": stop_loss,
        "target1": target1,
        "target2": target2,
        "target3": target3,
        "targets_json": targets,
        "pattern": pattern,
        "risk": risk,
    }