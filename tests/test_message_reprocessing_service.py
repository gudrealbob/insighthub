import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.parsers.recommendation_parser import parse_message
from app.services.message_reprocessing_service import MessageReprocessingService


def test_apply_recommendation_populates_targets_json():
    parsed = parse_message(
        "#Freshview\nRVN/USDT - 0.189$\nCan add now.\nTgt double",
        ["Freshview", "Crypto"],
    )
    recommendation = SimpleNamespace()

    MessageReprocessingService._apply_recommendation(recommendation, parsed)

    assert recommendation.symbol == "RVN/USDT"
    assert recommendation.target1 == parsed.recommendation.target1
    metadata = json.loads(recommendation.targets_json)
    assert metadata["target_type"] == "MULTIPLIER"
    assert metadata["multiplier"] == 2.0