"""离线词库查询；界面分页不影响字母分区的完整覆盖。"""
from pathlib import Path
import json
import sqlite3

ASSETS = Path(__file__).resolve().parent / "assets"


class Catalog:
    def __init__(self, path: Path | None = None):
        self.path = path or ASSETS / "catalog.sqlite3"
        if not self.path.is_file():
            raise FileNotFoundError(f"词库不存在：{self.path}")
        self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row

    def close(self):
        self.db.close()

    def levels(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM levels ORDER BY position")]

    @staticmethod
    def _filter(level, letter, query):
        clauses, args = ["m.level_id = ?"], [level]
        if letter:
            clauses.append("w.initial = ?")
            args.append(letter)
        if query.strip():
            # LIKE 通配符转义，使 % 和 _ 可以按字面搜索。
            term = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(w.word LIKE ? ESCAPE '\\' OR w.search_text LIKE ? ESCAPE '\\')")
            args.extend([f"%{term}%", f"%{term}%"])
        return " AND ".join(clauses), args

    def count(self, level, letter="", query=""):
        clause, args = self._filter(level, letter, query)
        return self.db.execute(f"SELECT COUNT(*) FROM words w JOIN membership m ON m.word_id=w.id WHERE {clause}", args).fetchone()[0]

    def initials(self, level, query=""):
        clause, args = self._filter(level, "", query)
        return dict(self.db.execute(f"SELECT w.initial, COUNT(*) FROM words w JOIN membership m ON m.word_id=w.id WHERE {clause} GROUP BY w.initial", args))

    def words(self, level, letter="", query="", offset=0, limit=40):
        clause, args = self._filter(level, letter, query)
        rows = self.db.execute(f"SELECT w.* FROM words w JOIN membership m ON m.word_id=w.id WHERE {clause} ORDER BY w.word COLLATE NOCASE, w.id LIMIT ? OFFSET ?", [*args, limit, offset])
        return [self._decode(r) for r in rows]

    def word(self, word_id):
        row = self.db.execute("SELECT * FROM words WHERE id=?", (word_id,)).fetchone()
        if row is None:
            raise KeyError(word_id)
        return self._decode(row)

    @staticmethod
    def _decode(row):
        result = dict(row)
        for key in ("senses", "examples", "phrases", "sources"):
            result[key] = json.loads(result[key])
        return result

    def report(self):
        return json.loads((ASSETS / "coverage.json").read_text(encoding="utf-8"))
