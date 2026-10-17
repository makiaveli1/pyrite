- **Re-indexing a hand file no longer adds a link row per pass (#927).** A hand
  file's link `target` is whatever YAML read — `target: 2024` is an integer,
  `target: true` a boolean — while the link index stores it as text. The
  comparison keyed on the raw value, so it never matched the stored row. A file
  holding both `target: 2024` and `target: '2024'` gained a duplicate link row on
  every `pyrite index sync` or `pyrite update` (2, 3, 4, 5...). The index now
  compares targets the way SQLite stores them, and a link whose key is stored
  twice keeps one row instead of leaving spares behind.