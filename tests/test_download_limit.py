"""Verify the download cap without contacting arXiv or writing files."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from arxiv_curator.data_processor import DataProcessor


@pytest.mark.parametrize(
    "available,failed,expected",
    [(100, 0, 70), (100, 3, 70), (12, 0, 12), (0, 0, 0)],
)
def test_download_limit_saves_successful_metadata(available, failed, expected):
    papers = []
    for index in range(available):
        paper = MagicMock()
        paper.get_short_id.return_value = f"paper-{index}"
        paper.title = f"Paper {index}"
        paper.authors = [SimpleNamespace(name="Author")]
        paper.summary = "Abstract"
        paper.pdf_url = f"https://example.com/{index}.pdf"
        paper.published = datetime(2026, 11, 4, tzinfo=timezone.utc)
        if index < failed:
            paper.download_pdf.side_effect = OSError("Download failed")
        papers.append(paper)

    spark = MagicMock()
    cfg = SimpleNamespace(catalog="catalog", schema="schema", volume="files")
    with (
        patch("arxiv_curator.data_processor.os.makedirs"),
        patch("arxiv_curator.data_processor.arxiv.Client") as client,
        patch("arxiv_curator.data_processor.time.sleep"),
        patch("arxiv_curator.data_processor.current_timestamp"),
        patch.object(DataProcessor, "_get_range_start", return_value="202611010000"),
    ):
        client.return_value.results.return_value = iter(papers)
        processor = DataProcessor(spark=spark, config=cfg)
        records = processor.download_and_store_papers()

    assert sum(paper.download_pdf.call_count for paper in papers) == expected + failed
    if expected:
        assert len(records) == expected
        assert [row["arxiv_id"] for row in records] == [
            f"paper-{index}" for index in range(failed, failed + expected)
        ]
        assert spark.createDataFrame.call_args.args[0] == records
        saved = spark.createDataFrame.return_value.withColumn.return_value
        saved.write.format.return_value.mode.return_value.saveAsTable.assert_called_once_with(
            "catalog.schema.arxiv_papers"
        )
    else:
        assert records is None
        spark.createDataFrame.assert_not_called()
