from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.normalized_message import NormalizedMessage
from app.models.recommendation import Recommendation
from app.parsers.recommendation_parser import (
    INSTRUMENT_UNKNOWN,
    STATUS_SUCCESS,
    ParsedMessage,
    parse_message,
)


@dataclass(slots=True)
class ReprocessSummary:
    scanned: int = 0
    normalized_updated: int = 0
    recommendations_created: int = 0
    recommendations_updated: int = 0
    recommendations_deleted: int = 0
    success: int = 0
    update: int = 0
    informational: int = 0
    no_recommendation: int = 0
    unsupported_format: int = 0
    validation_failed: int = 0
    multiple_recommendations: int = 0
    repost: int = 0

    def record_status(self, status: str) -> None:
        key = status.casefold()
        if hasattr(self, key):
            setattr(self, key, getattr(self, key) + 1)

    def to_dict(self) -> dict[str, int]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


class MessageReprocessingService:
    def __init__(self, db: Session):
        self.db = db

    def reprocess_all(
        self,
        dry_run: bool = False,
        start_message_id: int | None = None,
        end_message_id: int | None = None,
    ) -> ReprocessSummary:
        query = self.db.query(Message).order_by(Message.id)
        if start_message_id is not None:
            query = query.filter(Message.id >= start_message_id)
        if end_message_id is not None:
            query = query.filter(Message.id <= end_message_id)

        summary = ReprocessSummary()
        known_hashes: set[str] = set()

        try:
            for message in query.yield_per(250):
                summary.scanned += 1
                parsed = parse_message(
                    text=message.message_text,
                    tags=message.tags,
                    known_content_hashes=known_hashes,
                )
                if parsed.content_hash:
                    known_hashes.add(parsed.content_hash)

                summary.record_status(parsed.parser_status)
                self._upsert_normalized(message, parsed)
                summary.normalized_updated += 1

                recommendation = (
                    self.db.query(Recommendation)
                    .filter(Recommendation.message_id == message.id)
                    .one_or_none()
                )

                if (
                    parsed.parser_status == STATUS_SUCCESS
                    and parsed.recommendation is not None
                ):
                    if recommendation is None:
                        recommendation = Recommendation(
                            message_id=message.id
                        )
                        self.db.add(recommendation)
                        summary.recommendations_created += 1
                    else:
                        summary.recommendations_updated += 1
                    self._apply_recommendation(
                        recommendation,
                        parsed,
                    )
                elif recommendation is not None:
                    self.db.delete(recommendation)
                    summary.recommendations_deleted += 1

                if summary.scanned % 250 == 0:
                    self.db.flush()

            if dry_run:
                self.db.rollback()
            else:
                self.db.commit()
            return summary
        except Exception:
            self.db.rollback()
            raise

    def _upsert_normalized(
        self,
        message: Message,
        parsed: ParsedMessage,
    ) -> NormalizedMessage:
        normalized = (
            self.db.query(NormalizedMessage)
            .filter(NormalizedMessage.message_id == message.id)
            .one_or_none()
        )
        if normalized is None:
            normalized = NormalizedMessage(message_id=message.id)
            self.db.add(normalized)

        normalized.clean_text = parsed.clean_text
        normalized.symbol = parsed.symbol
        # Prevents the earlier NOT NULL failure.
        normalized.instrument_type = (
            parsed.instrument_type or INSTRUMENT_UNKNOWN
        )
        normalized.action = parsed.action
        normalized.parser_status = parsed.parser_status
        normalized.parser_version = parsed.parser_version
        return normalized

    @staticmethod
    def _apply_recommendation(
        recommendation: Recommendation,
        parsed: ParsedMessage,
    ) -> None:
        result = parsed.recommendation
        if result is None:
            raise ValueError(
                "A SUCCESS parser result must contain a recommendation."
            )

        recommendation.symbol = result.symbol
        recommendation.action = result.action
        recommendation.entry_low = result.entry_low
        recommendation.entry_high = result.entry_high
        recommendation.entry_instruction = result.entry_instruction
        recommendation.entry_instruction_text = (
            result.entry_instruction_text
        )
        recommendation.entry_price_source = result.entry_price_source
        recommendation.stop_loss = result.stop_loss
        recommendation.support_level = result.support_level
        recommendation.trigger_level = result.trigger_level
        recommendation.target1 = result.target1
        recommendation.target2 = result.target2
        recommendation.target3 = result.target3
        recommendation.pattern = result.pattern
        recommendation.risk = result.risk
        recommendation.targets_json = json.dumps(
            result.targets_json,
            sort_keys=True,
        )