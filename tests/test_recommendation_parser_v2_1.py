from decimal import Decimal

import pytest

from app.parsers.recommendation_parser import (
    ENTRY_ADD,
    ENTRY_AVERAGE,
    ENTRY_BUY_ON_DIPS,
    ENTRY_STAGED,
    INSTRUMENT_CRYPTO,
    INSTRUMENT_STOCK,
    OPEN_TARGET_VALUE,
    PRICE_SOURCE_MARKET_LOOKUP_PENDING,
    STATUS_SUCCESS,
    STATUS_UPDATE,
    parse_message,
)


@pytest.mark.parametrize(
    ("text", "tags", "symbol", "instrument"),
    [
        (
            "#Freshview\nStarbucks, 106.50 - 31st Dec, 2020\n"
            "Buy on dips till 100. Tgt open.",
            ["Freshview", "USstocks"],
            "STARBUCKS",
            INSTRUMENT_STOCK,
        ),
        (
            "#Freshview - Link/USD @ 14.4\nLooking good for 16, 17, 19++",
            ["Freshview", "Crypto"],
            "LINK/USD",
            INSTRUMENT_CRYPTO,
        ),
        (
            "Lets catch some BAT\n#Freshview, BAT\nGo with small qty.",
            ["Freshview", "Crypto"],
            "BAT",
            INSTRUMENT_CRYPTO,
        ),
        (
            "#Freshview, Crypto.\nLet's drive some NANO - 4.25$\n"
            "Can add on dips also near 3$ if comes.\nTgt open.",
            ["Freshview", "Crypto"],
            "NANO",
            INSTRUMENT_CRYPTO,
        ),
        (
            "#Freshview\nTime for PHB now\nPHB 0.892$",
            ["Freshview", "Crypto"],
            "PHB",
            INSTRUMENT_CRYPTO,
        ),
        (
            "#Freshview\nLet's milk it\nCOW 0.99$\nTgt 1.4",
            ["Freshview", "Crypto"],
            "COW",
            INSTRUMENT_CRYPTO,
        ),
    ],
)
def test_freshview_examples_are_new_buy_recommendations(
    text,
    tags,
    symbol,
    instrument,
):
    result = parse_message(text, tags)
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.action == "BUY"
    assert result.recommendation.symbol == symbol
    assert result.recommendation.instrument_type == instrument


def test_klay_decimal_target():
    result = parse_message(
        """
#Freshview

Klay - 0.164$

Let's do bottom Coining for an immediate tgt of 0.36$++
""",
        ["Freshview", "Crypto"],
    )

    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.symbol == "KLAY"
    assert result.recommendation.instrument_type == INSTRUMENT_CRYPTO
    assert result.recommendation.action == "BUY"
    assert result.recommendation.entry_low == Decimal("0.164")
    assert result.recommendation.entry_high == Decimal("0.164")
    assert result.recommendation.target1 == Decimal("0.36")


def test_idex_short_and_long_term_decimal_targets():
    result = parse_message(
        """
#Freshview

Idex - 0.068$, 25th Feb, 2024.

Breakout above 0.071 and short term tgt 0.137 and long term 0.50$++

Available in Wazirx also.
""",
        ["Freshview", "Crypto"],
    )

    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.symbol == "IDEX"
    assert result.recommendation.instrument_type == INSTRUMENT_CRYPTO
    assert result.recommendation.action == "BUY"
    assert result.recommendation.entry_low == Decimal("0.068")
    assert result.recommendation.entry_high == Decimal("0.068")
    assert result.recommendation.trigger_level == Decimal("0.071")
    assert result.recommendation.target1 == Decimal("0.137")
    assert result.recommendation.target2 == Decimal("0.50")

def test_open_target_is_numeric_999():
    result = parse_message(
        "#Freshview\nDASH 243$\nBuy on dips till 200\nTgt open",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.target1 == OPEN_TARGET_VALUE
    assert result.recommendation.targets_json["target_type"] == "OPEN"


def test_missing_entry_is_success_and_queued_for_market_lookup():
    result = parse_message(
        "Lets catch some BAT\n#Freshview, BAT\nGo with small qty.",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation is not None
    assert result.recommendation.entry_low is None
    assert result.recommendation.entry_high is None
    assert (
        result.recommendation.entry_price_source
        == PRICE_SOURCE_MARKET_LOOKUP_PENDING
    )


def test_entry_instruction_values():
    dips = parse_message(
        "#Freshview\nStarbucks, 106.50\nBuy on dips till 100",
        ["Freshview", "USstocks"],
    )
    add = parse_message(
        "#Freshview\nHOT 0.0204$\nThose who missed to add HOT can add now",
        ["Freshview", "Crypto"],
    )
    average = parse_message(
        "#Freshview\nHOT 0.011259$\nAverage HOT here",
        ["Freshview", "Crypto"],
    )
    staged = parse_message(
        "#Freshview\nTWT - Trust Wallet Token 1.36\n"
        "Add 50% now and remaining 50% near 1",
        ["Freshview", "Crypto"],
    )

    assert dips.recommendation.entry_instruction == ENTRY_BUY_ON_DIPS
    assert add.recommendation.entry_instruction == ENTRY_ADD
    assert average.recommendation.entry_instruction == ENTRY_AVERAGE
    assert staged.recommendation.entry_instruction == ENTRY_STAGED


def test_support_trigger_and_stop_loss_are_separate():
    result = parse_message(
        "#Freshview\nEPT - 0.00476$\n"
        "Support 0.004\nU turn on closing above 0.0056\nSL 0.0035",
        ["Freshview", "Crypto"],
    )
    assert result.parser_status == STATUS_SUCCESS
    assert result.recommendation.support_level == Decimal("0.004")
    assert result.recommendation.trigger_level == Decimal("0.0056")
    assert result.recommendation.stop_loss == Decimal("0.0035")


def test_update_never_creates_new_recommendation():
    result = parse_message(
        "#Update\nLINK target achieved. Book full profit.",
        ["Update"],
    )
    assert result.parser_status == STATUS_UPDATE
    assert result.recommendation is None