from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.normalized_message import NormalizedMessage
from app.models.recommendation import Recommendation
from app.parsers.recommendation_parser import (
    STATUS_SUCCESS,
    ParsedMessage,
    parse_message,
)


UNKNOWN_SYMBOL = "UNKNOWN"
UNKNOWN_INSTRUMENT_TYPE = "UNKNOWN"
UNKNOWN_ACTION = "UNKNOWN"


@dataclass(slots=True)
class ReprocessSummary:
    scanned: int = 0

    normalized_created: int = 0
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
    multiple_recs: int = 0
    repost: int = 0

    def record_status(self, status: str) -> None:
        attribute_name = status.casefold()

        if hasattr(self, attribute_name):
            current_value = getattr(self, attribute_name)
            setattr(
                self,
                attribute_name,
                current_value + 1,
            )

    def to_dict(self) -> dict[str, int]:
        return {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }


class MessageReprocessingService:
    """
    Rebuild normalized_messages and recommendations from immutable messages.

    The messages table is never modified.

    The normalized_messages table currently contains NOT NULL columns.
    Therefore, messages that do not contain a recommendation must use
    explicit UNKNOWN values instead of NULL.
    """

    def __init__(self, db: Session):
        self.db = db

    def reprocess_all(
        self,
        dry_run: bool = False,
        start_message_id: int | None = None,
        end_message_id: int | None = None,
    ) -> ReprocessSummary:
        query = (
            self.db.query(Message)
            .order_by(Message.id)
        )

        if start_message_id is not None:
            query = query.filter(
                Message.id >= start_message_id
            )

        if end_message_id is not None:
            query = query.filter(
                Message.id <= end_message_id
            )

        summary = ReprocessSummary()
        known_content_hashes: set[str] = set()

        try:
            for message in query.yield_per(250):
                summary.scanned += 1

                parsed = parse_message(
                    text=message.message_text,
                    tags=message.tags,
                    known_content_hashes=known_content_hashes,
                )

                if parsed.content_hash:
                    known_content_hashes.add(
                        parsed.content_hash
                    )

                summary.record_status(
                    parsed.parser_status
                )

                normalized, was_created = (
                    self._upsert_normalized(
                        message=message,
                        parsed=parsed,
                    )
                )

                if was_created:
                    summary.normalized_created += 1
                else:
                    summary.normalized_updated += 1

                recommendation = (
                    self.db.query(Recommendation)
                    .filter(
                        Recommendation.message_id
                        == message.id
                    )
                    .one_or_none()
                )

                if (
                    parsed.parser_status
                    == STATUS_SUCCESS
                    and parsed.recommendation
                    is not None
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
                        recommendation=recommendation,
                        parsed=parsed,
                    )

                elif recommendation is not None:
                    self.db.delete(recommendation)
                    summary.recommendations_deleted += 1

                if summary.scanned % 250 == 0:
                    self.db.flush()

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
    ) -> tuple[NormalizedMessage, bool]:
        normalized = (
            self.db.query(NormalizedMessage)
            .filter(
                NormalizedMessage.message_id
                == message.id
            )
            .one_or_none()
        )

        was_created = normalized is None

        if normalized is None:
            normalized = NormalizedMessage(
                message_id=message.id
            )
            self.db.add(normalized)

        normalized.clean_text = (
            parsed.clean_text
            if parsed.clean_text
            else message.message_text
            or ""
        )

        normalized.symbol = self._required_value(
            parsed_value=parsed.symbol,
            existing_value=normalized.symbol,
            fallback=UNKNOWN_SYMBOL,
        )

        normalized.instrument_type = (
            self._required_value(
                parsed_value=parsed.instrument_type,
                existing_value=(
                    normalized.instrument_type
                ),
                fallback=UNKNOWN_INSTRUMENT_TYPE,
            )
        )

        normalized.action = self._required_value(
            parsed_value=parsed.action,
            existing_value=normalized.action,
            fallback=UNKNOWN_ACTION,
        )

        normalized.parser_status = (
            parsed.parser_status
        )

        normalized.parser_version = str(
            parsed.parser_version
        )

        return normalized, was_created

    @staticmethod
    def _required_value(
        parsed_value: str | None,
        existing_value: str | None,
        fallback: str,
    ) -> str:
        """
        Return a valid nonblank value for a NOT NULL column.

        Priority:
        1. Current parser value
        2. Existing database value
        3. Explicit UNKNOWN fallback
        """

        if parsed_value is not None:
            parsed_value = str(
                parsed_value
            ).strip()

            if parsed_value:
                return parsed_value

        if existing_value is not None:
            existing_value = str(
                existing_value
            ).strip()

            if existing_value:
                return existing_value

        return fallback

    @staticmethod
    def _apply_recommendation(
        recommendation: Recommendation,
        parsed: ParsedMessage,
    ) -> None:
        result = parsed.recommendation

        if result is None:
            raise ValueError(
                "A SUCCESS parser result must "
                "contain a recommendation."
            )

        recommendation.symbol = result.symbol
        recommendation.action = result.action

        recommendation.entry_low = (
            result.entry_low
        )

        recommendation.entry_high = (
            result.entry_high
        )

        recommendation.stop_loss = (
            result.stop_loss
        )

        recommendation.target1 = (
            result.target1
        )

        recommendation.target2 = (
            result.target2
        )

        recommendation.target3 = (
            result.target3
        )

        recommendation.pattern = result.pattern
        recommendation.risk = result.risk

        recommendation.targets_json = json.dumps(
            result.targets_json,
            sort_keys=True,
        )