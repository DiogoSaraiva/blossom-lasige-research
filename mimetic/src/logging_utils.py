"""
logging_utils.py
~~~~~~~~~~~~~~~~
Lightweight CSV logger for the Blossom-mimetic pipeline.

Typical usage
-------------
from logging_utils import DataLogger

with DataLogger(fields=["x", "y", "z", "sent"]) as log:
    log.log_sample(x=0.12, y=-0.05, z=0.9, sent=True)
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Iterable, Mapping, Sequence


class DataLogger:
    """
    Logs timestamped records to a CSV file.

    Parameters
    ----------
    filename : str | None, optional
        Path to CSV file.  If *None*, a file named
        ``logs/pose_YYYYmmdd_HHMMSS.csv`` is created.
    fields : Sequence[str] | None, optional
        Ordered list of data columns (excluding ``timestamp``).
        If *None*, the logger will infer the order from the first call to
        :py:meth:`log_sample`, but explicit definition is safer.
    autosave_every : int, default 1
        Every *N* samples a ``flush()`` is issued to persist data.
    """

    def __init__(
        self,
        filename: str | None = None,
        fields: Sequence[str] | None = None,
        autosave_every: int = 1,
    ) -> None:
        self.fields: list[str] | None = list(fields) if fields else None
        self.autosave_every = max(1, int(autosave_every))
        self._samples_since_flush = 0

        # Create default file name
        if filename is None:
            os.makedirs("logs", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/pose_{ts}_{os.getpid()}.csv"

        # Open file
        self.file = open(filename, mode="w", newline="", encoding="utf-8")
        self.writer = None  # created lazily after header is known

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def log_sample(self, **data: float | bool | int) -> None:
        """
        Write a single sample. Any unmapped keys will enlarge the header
        automatically (first write only).

        Example
        -------
        >>> log.log_sample(x=0.1, y=0.2, z=0.3, sent=True)
        """
        if self.fields is None:  # infer order from first sample
            self.fields = list(data.keys())

        if self.writer is None:
            self._init_csv()

        row = [datetime.now().isoformat()]
        for field in self.fields:
            row.append(str(data.get(field, "")))  # empty if missing field
        self.writer.writerow(row)

        # Autosave
        self._samples_since_flush += 1
        if self._samples_since_flush >= self.autosave_every:
            self.flush()

    def flush(self) -> None:
        """Force buffered data to be written to disk."""
        self.file.flush()
        os.fsync(self.file.fileno())
        self._samples_since_flush = 0

    def close(self) -> None:
        """Flush and close the file. Safe to call multiple times."""
        try:
            self.flush()
        finally:
            self.file.close()

    # ------------------------------------------------------------------
    # Context-manager helpers
    # ------------------------------------------------------------------
    def __enter__(self) -> "DataLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _init_csv(self) -> None:
        """Write header row once the fields list is known."""
        header = ["timestamp"] + self.fields
        self.writer = csv.writer(self.file)
        self.writer.writerow(header)


# ----------------------------------------------------------------------
# Convenience function for bulk logging
# ----------------------------------------------------------------------
def log_bulk(
    logger: DataLogger,
    samples: Iterable[Mapping[str, float | bool | int]],
) -> None:
    """
    Log a sequence of samples in one go.

    Parameters
    ----------
    logger : DataLogger
        Active logger instance.
    samples : Iterable[Mapping[str, ...]]
        Each mapping should contain keys matching ``logger.fields``.
    """
    for sample in samples:
        logger.log_sample(**sample)
