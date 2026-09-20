"""`query_network` pages both directions and says what it truncated (#63).

On a hub node the old response carried every outlink and backlink at once
(~18k tokens for one cascade node). `limit`/`offset` now apply to each
direction, and the response carries the true totals plus `truncated` so a
caller can tell what it did not see.
"""

import pytest
from pyrite_journalism_investigation.queries import query_network


class _FakeDB:
    """Minimal db stub: only what query_network calls."""

    def __init__(self, outlinks, backlinks, entry=None):
        self._outlinks = list(outlinks)
        self._backlinks = list(backlinks)
        self._entry = entry if entry is not None else {"id": "hub", "title": "Hub"}

    def get_entry(self, entry_id, kb_name):
        return self._entry

    def get_outlinks(self, entry_id, kb_name):
        return list(self._outlinks)

    def get_backlinks(self, entry_id, kb_name):
        return list(self._backlinks)


def _links(prefix, count):
    return [
        {"id": f"{prefix}-{index:03d}", "title": f"{prefix} {index:03d}"} for index in range(count)
    ]


def test_caps_each_direction_and_reports_the_true_totals():
    db = _FakeDB(_links("out", 7), _links("back", 9))

    result = query_network(db, "kb", "hub", limit=5)

    assert len(result["outlinks"]) == 5
    assert len(result["backlinks"]) == 5
    assert result["totals"] == {"outlinks": 7, "backlinks": 9}
    assert result["truncated"] is True


def test_a_small_node_is_not_truncated():
    db = _FakeDB(_links("out", 2), _links("back", 3))

    result = query_network(db, "kb", "hub", limit=50)

    assert result["truncated"] is False
    assert result["totals"] == {"outlinks": 2, "backlinks": 3}
    assert len(result["outlinks"]) == 2


def test_offset_walks_without_repeats_or_gaps():
    db = _FakeDB(_links("out", 7), [])

    pages = [query_network(db, "kb", "hub", limit=3, offset=offset) for offset in (0, 3, 6)]

    walked = [link["id"] for page in pages for link in page["outlinks"]]
    assert walked == [f"out-{index:03d}" for index in range(7)]
    assert pages[0]["truncated"] is True
    assert pages[1]["truncated"] is True
    assert pages[2]["truncated"] is False


def test_offset_past_the_end_is_an_empty_page():
    db = _FakeDB(_links("out", 3), [])

    result = query_network(db, "kb", "hub", limit=5, offset=99)

    assert result["outlinks"] == []
    assert result["truncated"] is False
    assert result["totals"] == {"outlinks": 3, "backlinks": 0}


def test_a_node_with_no_links_is_empty_and_not_truncated():
    result = query_network(_FakeDB([], []), "kb", "hub")

    assert result["outlinks"] == []
    assert result["backlinks"] == []
    assert result["truncated"] is False


@pytest.mark.parametrize("limit", [0, -1])
def test_zero_and_negative_limit_mean_no_cap(limit):
    db = _FakeDB(_links("out", 7), _links("back", 7))

    result = query_network(db, "kb", "hub", limit=limit)

    assert len(result["outlinks"]) == 7
    assert len(result["backlinks"]) == 7
    assert result["truncated"] is False


def test_missing_entry_keeps_the_error_branch():
    class _Missing(_FakeDB):
        def get_entry(self, entry_id, kb_name):
            return None

    assert "error" in query_network(_Missing([], []), "kb", "nope")
