from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from app.analytics.records import RecommendationAnalyticsRecord


class RecommendationExportService:
    """Export canonical Sprint 5 analytics records without modifying the database."""

    @staticmethod
    def write_csv(
        path: str | Path,
        rows: Iterable[dict[str, Any]],
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        materialized = list(rows)
        fieldnames = RecommendationExportService._fieldnames(materialized)

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in materialized:
                writer.writerow(RecommendationExportService._csv_safe(row))
        return output_path

    @staticmethod
    def write_json(
        path: str | Path,
        rows: Iterable[dict[str, Any]],
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(list(rows), handle, indent=2, ensure_ascii=False, default=str)
        return output_path

    @staticmethod
    def export_recommendations(
        output_directory: str | Path,
        records: Iterable[RecommendationAnalyticsRecord],
    ) -> tuple[Path, Path, Path]:
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        materialized = list(records)
        dictionaries = [record.to_dict() for record in materialized]

        csv_path = RecommendationExportService.write_csv(
            output_dir / "recommendations_export.csv",
            dictionaries,
        )
        json_path = RecommendationExportService.write_json(
            output_dir / "recommendations_export.json",
            dictionaries,
        )
        text_path = output_dir / "recommendations_rag_ready.jsonl"
        with text_path.open("w", encoding="utf-8") as handle:
            for record in materialized:
                payload = {
                    "recommendation_id": record.recommendation_id,
                    "message_id": record.message_id,
                    "text": RecommendationExportService._rag_text(record),
                    "metadata": {
                        "channel": record.channel_name,
                        "signal_date": record.signal_date.isoformat()
                        if record.signal_date
                        else None,
                        "symbol": record.symbol,
                        "action": record.action,
                        "pattern": record.pattern,
                        "risk": record.risk,
                        "status": record.lifecycle_status,
                        "current_return_pct": record.current_return_pct,
                        "max_return_pct": record.max_return_pct,
                        "target_hit": record.target_hit,
                        "stop_loss_hit": record.stop_loss_hit,
                    },
                }
                handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

        return csv_path, json_path, text_path

    @staticmethod
    def _rag_text(record: RecommendationAnalyticsRecord) -> str:
        parts = [
            f"Recommendation {record.recommendation_id}",
            f"Channel: {record.channel_name or 'Unknown'}",
            f"Date: {record.signal_date.isoformat() if record.signal_date else 'Unknown'}",
            f"Action: {record.action or 'Unknown'}",
            f"Symbol: {record.symbol or 'Unknown'}",
            f"Entry: {record.entry_low} to {record.entry_high}",
            f"Stop loss: {record.stop_loss}",
            f"Targets: {record.targets}",
            f"Pattern: {record.pattern or 'Unknown'}",
            f"Risk: {record.risk or 'Unknown'}",
            f"Status: {record.lifecycle_status or 'Unknown'}",
            f"Current return percent: {record.current_return_pct}",
            f"Maximum return percent: {record.max_return_pct}",
            f"Target hit: {record.target_hit}",
            f"Stop loss hit: {record.stop_loss_hit}",
        ]
        if record.normalized_text:
            parts.append(f"Normalized message: {record.normalized_text}")
        elif record.raw_message_text:
            parts.append(f"Raw message: {record.raw_message_text}")
        return "\n".join(parts)

    @staticmethod
    def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    ordered.append(key)
        return ordered or ["no_data"]

    @staticmethod
    def _csv_safe(row: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                safe[key] = json.dumps(value, ensure_ascii=False, default=str)
            else:
                safe[key] = value
        return safe