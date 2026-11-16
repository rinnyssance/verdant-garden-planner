"""SQLite implementation of the Repository interface with versioned migrations."""

from __future__ import annotations

import json
import sqlite3
import types
import typing
from contextlib import contextmanager
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path

from .repository import GARDEN_SCOPED, TABLES

MIGRATIONS = Path(__file__).with_name("migrations")


def _base_type(hint):
    """Unwrap Optional[X] / X | None to X."""
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(hint) if a is not type(None)]
        return _base_type(args[0])
    return origin or hint


def _encode(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return value


def _decode(hint, value):
    if value is None:
        return None
    kind = _base_type(hint)
    if kind is datetime:
        return datetime.fromisoformat(value)
    if kind is date:
        return date.fromisoformat(value)
    if kind is bool:
        return bool(value)
    if kind in (list, dict):
        return json.loads(value)
    if kind is float:
        return float(value)
    return value


class SQLiteRepository:
    def __init__(self, path: str | Path = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._depth = 0
        self.migrate()

    # -- schema -----------------------------------------------------------
    def migrate(self) -> int:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for script in sorted(MIGRATIONS.glob("*.sql")):
            number = int(script.name.split("_")[0])
            if number > version:
                with self.conn:
                    self.conn.executescript(script.read_text(encoding="utf-8"))
                    self.conn.execute(f"PRAGMA user_version = {number}")
                version = number
        return version

    # -- transactions -----------------------------------------------------
    @contextmanager
    def transaction(self):
        """Group several writes; nested use joins the outer transaction."""
        self._depth += 1
        try:
            yield self
            if self._depth == 1:
                self.conn.commit()
        except BaseException:
            if self._depth == 1:
                self.conn.rollback()
            raise
        finally:
            self._depth -= 1

    def _autocommit(self):
        if self._depth == 0:
            self.conn.commit()

    # -- CRUD -------------------------------------------------------------
    def save(self, obj) -> None:
        cls = type(obj)
        table = TABLES[cls]
        names = [f.name for f in fields(cls)]
        values = [_encode(getattr(obj, n)) for n in names]
        updates = ", ".join(f"{n} = excluded.{n}" for n in names if n != "id")
        self.conn.execute(
            f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' * len(names))}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}", values)
        self._autocommit()

    def _row_to_obj(self, cls, row):
        hints = typing.get_type_hints(cls)
        return cls(**{f.name: _decode(hints[f.name], row[f.name]) for f in fields(cls)})

    def get(self, cls, id: str):
        row = self.conn.execute(f"SELECT * FROM {TABLES[cls]} WHERE id = ?", (id,)).fetchone()
        return self._row_to_obj(cls, row) if row else None

    def _where(self, cls, garden_id, filters):
        if cls in GARDEN_SCOPED and garden_id is None:
            raise ValueError(f"Listing {cls.__name__} requires a garden_id.")
        allowed = {f.name for f in fields(cls)}
        clauses, params = [], []
        if garden_id is not None:
            clauses.append("garden_id = ?")
            params.append(garden_id)
        for name, value in filters.items():
            if name not in allowed:
                raise ValueError(f"Unknown filter: {name}")
            if value is None:
                clauses.append(f"{name} IS NULL")
            elif isinstance(value, (list, tuple, set)):
                clauses.append(f"{name} IN ({', '.join('?' * len(value))})")
                params.extend(_encode(v) for v in value)
            else:
                clauses.append(f"{name} = ?")
                params.append(_encode(value))
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def list(self, cls, garden_id: str | None = None, **filters) -> list:
        where, params = self._where(cls, garden_id, filters)
        rows = self.conn.execute(f"SELECT * FROM {TABLES[cls]}{where} ORDER BY rowid", params).fetchall()
        return [self._row_to_obj(cls, row) for row in rows]

    def delete(self, cls, id: str) -> None:
        self.conn.execute(f"DELETE FROM {TABLES[cls]} WHERE id = ?", (id,))
        self._autocommit()

    def delete_where(self, cls, garden_id: str, **filters) -> int:
        if garden_id is None:
            raise ValueError("Bulk deletes must be scoped to a garden.")
        where, params = self._where(cls, garden_id, filters)
        count = self.conn.execute(f"DELETE FROM {TABLES[cls]}{where}", params).rowcount
        self._autocommit()
        return count

    def close(self):
        self.conn.close()
