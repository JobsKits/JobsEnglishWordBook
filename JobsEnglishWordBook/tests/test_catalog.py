"""验证完整覆盖、分级集合、搜索边界和源数据保存。"""
import json
import sqlite3
from pathlib import Path
import zipfile
import pytest
from jobs_english_wordbook.catalog import Catalog, ASSETS


@pytest.fixture
def catalog():
    c = Catalog()
    yield c
    c.close()


def test_database_integrity_and_counts(catalog):
    assert catalog.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not list(catalog.db.execute("PRAGMA foreign_key_check"))
    report = catalog.report()
    assert len(catalog.levels()) == 12
    assert catalog.db.execute("SELECT COUNT(*) FROM words").fetchone()[0] == report["words"]
    for level in report["levels"]:
        assert catalog.count(level["id"]) == level["count"] > 0


def test_letter_partitions_cover_every_word_once(catalog):
    for level in catalog.levels():
        ids = []
        for initial, count in catalog.initials(level["id"]).items():
            words = catalog.words(level["id"], initial, limit=100_000)
            assert len(words) == count
            assert all(w["initial"] == initial for w in words)
            ids.extend(w["id"] for w in words)
        assert len(set(ids)) == len(ids) == catalog.count(level["id"])


def test_cumulative_membership(catalog):
    for chain in [["junior", "senior", "cet4", "cet6", "tem8"], [f"ielts{i}" for i in range(1, 8)]]:
        previous = set()
        for level in chain:
            ids = {r[0] for r in catalog.db.execute("SELECT word_id FROM membership WHERE level_id=?", (level,))}
            assert previous <= ids
            previous = ids


def test_pagination_has_no_gaps(catalog):
    total = catalog.count("tem8")
    ids = []
    for offset in range(0, total, 173):
        ids.extend(w["id"] for w in catalog.words("tem8", offset=offset, limit=173))
    assert len(ids) == len(set(ids)) == total


def test_search_literal_wildcards_and_chinese(catalog):
    assert catalog.count("junior", query="学校") > 0
    assert catalog.count("tem8", query="' OR 1=1 --") == 0
    assert catalog.count("tem8", query="%") < catalog.count("tem8")
    assert catalog.count("tem8", query="_") < catalog.count("tem8")
    assert catalog.count("junior", query="SCHOOL") == catalog.count("junior", query="school")


def test_all_records_have_meanings(catalog):
    for row in catalog.db.execute("SELECT senses,examples,phrases FROM words"):
        senses, examples, phrases = map(json.loads, row)
        assert senses and all(s["meaning"].strip() for s in senses)
        assert len({e["en"] for e in examples}) == len(examples)
        assert all(e["en"].strip() for e in examples + phrases)


def test_source_book_records_preserved(catalog):
    source_dir = Path(__file__).resolve().parents[1] / "work/sources"
    if not source_dir.exists():
        pytest.skip("原始词书缓存未随源码复制；成品词库检查仍然执行")
    import unicodedata
    lookup = {unicodedata.normalize("NFKC", r["word"]).strip().casefold(): r for r in catalog.db.execute("SELECT * FROM words")}
    for path in source_dir.glob("*.zip"):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith(".json"))
            for line in z.read(name).decode("utf-8-sig").splitlines():
                obj = json.loads(line)
                key = unicodedata.normalize("NFKC", obj["headWord"]).strip().casefold()
                assert key in lookup
                row = lookup[key]
                assert obj["bookId"] in json.loads(row["sources"])
                english = {e["en"] for e in json.loads(row["examples"])}
                for e in obj["content"]["word"]["content"].get("sentence", {}).get("sentences", []):
                    if e.get("sContent", "").strip():
                        assert e["sContent"].strip() in english
