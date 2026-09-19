"""
Generic Entry Model

For custom types defined in kb.yaml that don't match a core type.
Custom fields live in self.metadata and round-trip through frontmatter.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .base import Entry

logger = logging.getLogger(__name__)

# Fields that are handled by Entry base or known frontmatter keys
_KNOWN_KEYS = {
    "id",
    "title",
    "type",
    "body",
    "summary",
    "tags",
    "aliases",
    "sources",
    "links",
    "provenance",
    "metadata",
    "created_at",
    "updated_at",
    "_schema_version",
    "file_path",
    "importance",
    "lifecycle",
}


@dataclass
class GenericEntry(Entry):
    """
    Flexible entry for kb.yaml-defined custom types.

    Custom fields live in self.metadata.
    Frontmatter round-trips all unknown keys through metadata.
    """

    _entry_type: str = "note"

    # Keys that arrived under an explicit nested `metadata:` block. Only these
    # are written back nested; undeclared top-level keys are promoted instead,
    # so the same key can never be emitted twice (issue #149). Private
    # bookkeeping, declared like Entry's `_absent_default_keys` and
    # `_source_frontmatter`: not a constructor argument, not compared, not in
    # `repr`.
    _nested_metadata_keys: frozenset[str] = field(
        default=frozenset(), init=False, repr=False, compare=False
    )

    @property
    def entry_type(self) -> str:
        return self._entry_type

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.summary:
            meta["summary"] = self.summary
        # `_base_frontmatter` writes the whole `self.metadata` mapping as a
        # nested block; for an undeclared top-level key that duplicates the
        # promoted copy below and grows a `metadata:` block the source file
        # never had (#149). Keep only the keys that came from an explicit
        # `metadata:` block nested, and promote the rest.
        nested = {k: v for k, v in self.metadata.items() if k in self._nested_metadata_keys}
        if nested:
            meta["metadata"] = nested
        else:
            meta.pop("metadata", None)
        for key, value in self.metadata.items():
            if key in nested:
                continue
            if key not in meta:
                meta[key] = value
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "GenericEntry":
        kw = cls._base_kwargs(meta, body)

        # `metadata:` is optional, but when the file carries it, it must be a
        # mapping. A null or non-mapping value used to raise out of the merge
        # below, which made the loader fall back to another entry class and save
        # the file back as `type: event`.
        raw_metadata = meta.get("metadata")
        if "metadata" in meta and not isinstance(raw_metadata, Mapping):
            logger.warning(
                "%s %r: `metadata` frontmatter is %s, not a mapping; treating it as empty",
                cls.__name__,
                meta.get("id", ""),
                type(raw_metadata).__name__,
            )
        explicit_metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}

        # Collect unknown frontmatter keys into metadata
        extra_metadata = {k: v for k, v in meta.items() if k not in _KNOWN_KEYS}
        # Merge: explicit metadata wins over inferred
        kw["metadata"] = {**extra_metadata, **explicit_metadata}

        kw["lifecycle"] = meta.get("lifecycle", "active")
        kw["_entry_type"] = meta.get("type", "note")
        entry = cls(**kw)
        # Remember which of those keys were nested in the source, so
        # to_frontmatter puts exactly them back nested and promotes the rest
        # (#149). Set after construction: it is private bookkeeping, not a field
        # the YAML layer should fill (mirrors Entry's `_absent_default_keys`).
        entry._nested_metadata_keys = frozenset(explicit_metadata)
        return entry
