import re


def parse_recommendation(
    clean_text: str,
    symbol: str | None = None,
    action: str | None = None,
):
    """
    Sprint 3

    Recommendation parser.

    Input:
        - normalized message text
        - normalized symbol (optional)
        - normalized action (optional)

    Output:
        Recommendation fields only.
    """

    text = clean_text.upper()

    #
    # ENTRY
    #
    entry_match = re.search(r"ENTRY\s*([0-9]+)\s*-\s*([0-9]+)", text)

    if entry_match:
        entry_low = float(entry_match.group(1))
        entry_high = float(entry_match.group(2))
    else:
        entry_single = re.search(r"ENTRY\s*([0-9]+)", text)

        entry_low = (
            float(entry_single.group(1))
            if entry_single
            else None
        )

        entry_high = entry_low

    #
    # STOP LOSS
    #
    sl_match = re.search(
        r"(SL|STOP LOSS)\s*([0-9]+)",
        text,
    )

    stop_loss = (
        float(sl_match.group(2))
        if sl_match
        else None
    )

    #
    # TARGETS
    #
    targets = re.findall(
        r"TARGET\s*[0-9]*\s*([0-9]+)",
        text,
    )

    target1 = float(targets[0]) if len(targets) > 0 else None
    target2 = float(targets[1]) if len(targets) > 1 else None
    target3 = float(targets[2]) if len(targets) > 2 else None

    #
    # PATTERN
    #
    pattern_match = re.search(
        r"PATTERN\s*(.*)",
        text,
    )

    pattern = (
        pattern_match.group(1).strip()
        if pattern_match
        else None
    )

    #
    # RISK
    #
    risk_match = re.search(
        r"RISK\s*(LOW|MEDIUM|HIGH)",
        text,
    )

    risk = (
        risk_match.group(1)
        if risk_match
        else None
    )

    return {
        "symbol": symbol,
        "action": action,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop_loss": stop_loss,
        "target1": target1,
        "target2": target2,
        "target3": target3,
        "pattern": pattern,
        "risk": risk,
    }