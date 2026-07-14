from decimal import Decimal

import pytest

from app.parsers.recommendation_parser import (
    STATUS_INFORMATIONAL,
    STATUS_SUCCESS,
    STATUS_UPDATE,
    TARGET_TYPE_MULTIPLIER,
    TARGET_TYPE_OPEN,
    parse_message,
)


@pytest.mark.parametrize(
    ("text", "tags", "symbol", "entry_low", "entry_high"),
    [
        (
            "#Freshview\nXtz/USDT - 3.9$\nCan add now or in dips also.\nTgt open.",
            ["Freshview", "Crypto"],
            "XTZ/USDT",
            Decimal("3.9"),
            Decimal("3.9"),
        ),
        (
            "#Freshview\nTomo/USDT - 2.19$\nCan add on dips near 1.8 to 2$.\nTgt open.",
            ["Freshview", "Crypto"],
            "TOMO/USDT",
            Decimal("1.8"),
            Decimal("2.19"),
        ),
        (
            "#Freshview\nENJ/INR - 45\nTgt open.",
            ["Freshview", "Crypto"],
            "ENJ/INR",
            Decimal("45"),
            Decimal("45"),
        ),
        (
            "#Freshview\nNew users can add TRX/INR now @ 6.5",
            ["Freshview"],
            "TRX/INR",
            Decimal("6.5"),
            Decimal("6.5"),
        ),
    ],
)
def test_buy_language_and_entry_formats(
    text,
    tags,
    symbol,
    entry_low,
    entry_high,
):
    result = parse_message(text, tags)
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.symbol == symbol
    assert result.recommendation.entry_low == entry_low
    assert result.recommendation.entry_high == entry_high


def test_open_target_metadata_is_always_populated():
    result = parse_message(
        "#Freshview\nICX/USDT - 2.83$\nTarget open",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.targets_json["target_type"] == TARGET_TYPE_OPEN
    assert result.recommendation.targets_json["targets"] == []


def test_double_target_becomes_absolute_price():
    result = parse_message(
        "#Freshview\nNavitas Semiconductor - 22$\n"
        "Can buy now and in dips near 18.\nTgt double.",
        ["Freshview", "NYSE"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.entry_low == Decimal("18")
    assert result.recommendation.entry_high == Decimal("22")
    assert result.recommendation.target1 == Decimal("36")
    assert result.recommendation.targets_json["target_type"] == TARGET_TYPE_MULTIPLIER
    assert result.recommendation.targets_json["multiplier"] == 2.0


def test_crypto_tag_overrides_stock_heuristic():
    result = parse_message(
        "#Freshview\nORDI - 42$\nCan add now.\nTgt open.",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.instrument_type == "CRYPTO"


def test_nyse_tag_classifies_stock():
    result = parse_message(
        "#Freshview #NYSE\nNVIDIA - 120$\nCan buy now.\nTgt 135",
        ["Freshview", "NYSE"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.instrument_type == "STOCK"


def test_symbol_cleanup():
    result = parse_message(
        "#Freshview\nInvestment Pick - CELR/USD - 0.083$\nCan add now.\nTgt open.",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.symbol == "CELR/USD"


def test_information_message_is_not_failure():
    result = parse_message(
        "This google sheet has all the recommended coin details.\n"
        "New calls will always be given with the tag of #Freshview",
        ["Freshview"],
    )
    assert result.parser_status == STATUS_INFORMATIONAL
    assert result.recommendation is None


def test_update_message_is_not_new_recommendation():
    result = parse_message(
        "#Update\nAAPL target achieved. Book full profit.",
        ["Update"],
    )
    assert result.parser_status == STATUS_UPDATE
    assert result.recommendation is None


def test_risk_and_pattern_extraction():
    result = parse_message(
        "#Freshview\nWTC/USDT - 1.90$\n"
        "Can add now or in dips near 1.70$\n"
        "Cup and handle pattern\nGo with small quantity\nTgt open",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.pattern == "CUP_AND_HANDLE"
    assert result.recommendation.risk == "HIGH"