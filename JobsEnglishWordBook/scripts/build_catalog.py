"""从有来源记录的备考词书与 ECDICT 构建离线 SQLite 词库。"""
import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
import re
import sqlite3
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/jobs_english_wordbook/assets"
BOOKS = {
    "ChuZhongluan_2": ("junior", "1521164669076_ChuZhongluan_2.zip", 1420),
    "GaoZhongluan_2": ("senior", "1521164673602_GaoZhongluan_2.zip", 3668),
    "CET4_2": ("cet4", "1521164635506_CET4_2.zip", 3739),
    "CET4_3": ("cet4", "1521164643060_CET4_3.zip", 2607),
    "CET6_2": ("cet6", "1524052554766_CET6_2.zip", 2078),
    "CET6_3": ("cet6", "1521164633851_CET6_3.zip", 2345),
    "Level8_2": ("tem8", "1521164663794_Level8_2.zip", 12197),
    "IELTS_2": ("ielts", "1521164657744_IELTS_2.zip", 3427),
    "IELTS_3": ("ielts", "1521164666922_IELTS_3.zip", 3575),
}


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def normalize(value):
    return unicodedata.normalize("NFKC", value).strip()


def add_sense(entry, pos, meaning, english=""):
    # 分号是原词库的义项边界，逗号可能属于同一解释，不拆开。
    for part in re.split(r"[；;\n]+", meaning):
        part = part.strip()
        if not part:
            continue
        pos = pos.strip().rstrip(".")
        if not any(s["pos"] == pos and s["meaning"] == part for s in entry["senses"]):
            entry["senses"].append({"pos": pos, "meaning": part, "english": english.strip()})


def append_example(target, en, zh):
    en, zh = en.strip(), zh.strip()
    if en and not any(e["en"] == en for e in target):
        target.append({"en": en, "zh": zh})


def build(sources: Path, ecdict: Path | None = None):
    entries, groups, report_sources = {}, {}, []
    for book, (group, filename, expected) in BOOKS.items():
        path = sources / f"{book}.zip"
        count = 0
        with zipfile.ZipFile(path) as archive:
            files = [n for n in archive.namelist() if n.endswith(".json")]
            if len(files) != 1:
                raise ValueError(f"词书结构异常：{book}")
            for line in archive.read(files[0]).decode("utf-8-sig").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                count += 1
                word = normalize(obj["headWord"])
                key = word.casefold()
                c = obj["content"]["word"]["content"]
                if not word or not c.get("trans"):
                    raise ValueError(f"缺失单词或释义：{book} 第 {count} 行")
                entry = entries.setdefault(key, {"word": word, "phonetic": "", "senses": [], "examples": [], "phrases": [], "sources": [], "frequency": 10**9})
                if not entry["phonetic"]:
                    entry["phonetic"] = " / ".join(f'{region} /{c[field]}/' for region, field in [("英", "ukphone"), ("美", "usphone")] if c.get(field))
                if book not in entry["sources"]:
                    entry["sources"].append(book)
                for sense in c["trans"]:
                    add_sense(entry, sense.get("pos", ""), sense.get("tranCn", ""), sense.get("tranOther", ""))
                for example in c.get("sentence", {}).get("sentences", []):
                    append_example(entry["examples"], example.get("sContent", ""), example.get("sCn", ""))
                for phrase in c.get("phrase", {}).get("phrases", []):
                    append_example(entry["phrases"], phrase.get("pContent", ""), phrase.get("pCn", ""))
                groups.setdefault(group, set()).add(key)
        if count != expected:
            raise ValueError(f"源词书不完整：{book} 应有 {expected}，实际 {count}")
        report_sources.append({"book": book, "records": count, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "url": f"https://github.com/kajweb/dict/blob/master/book/{filename}"})
        logging.info("完整导入 %s: %s", book, count)
    if ecdict is not None:
        ec_rows, ec_matches = 0, 0
        tags = {"zk": "junior", "gk": "senior", "cet4": "cet4", "cet6": "cet6", "ielts": "ielts"}
        with ecdict.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                ec_rows += 1
                key = normalize(row["word"]).casefold()
                relevant = set(row.get("tag", "").split()) & tags.keys()
                if key not in entries and not relevant:
                    continue
                if not row.get("translation") and key not in entries:
                    continue
                entry = entries.setdefault(key, {"word": normalize(row["word"]), "phonetic": row["phonetic"], "senses": [], "examples": [], "phrases": [], "sources": [], "frequency": 10**9})
                entry["sources"].append("ECDICT")
                ec_matches += 1
                for tag in relevant:
                    groups.setdefault(tags[tag], set()).add(key)
                rank = int(row.get("bnc") or 0) or int(row.get("frq") or 0)
                entry["frequency"] = rank or 10**9
                for meaning in row["translation"].replace("\\n", "\n").splitlines():
                    match = re.match(r"^([a-z./ ]{1,20})\.\s*(.*)", meaning)
                    add_sense(entry, match[1] if match else "", match[2] if match else meaning)
        if ec_rows < 700_000:
            raise ValueError(f"ECDICT 文件不完整：{ec_rows} 条")
        report_sources.append({"book": "ECDICT", "records": ec_rows, "matched": ec_matches, "sha256": hashlib.sha256(ecdict.read_bytes()).hexdigest(), "url": "https://github.com/skywind3000/ECDICT/blob/master/ecdict.csv"})
    else:
        from wordfreq import zipf_frequency
        for entry in entries.values():
            entry["frequency"] = -zipf_frequency(entry["word"], "en")
        report_sources.append({"book": "wordfreq 3.1.1", "purpose": "仅用于雅思学习档词频排序", "url": "https://github.com/rspeer/wordfreq", "license": "frequency data CC BY-SA 4.0"})
    levels, memberships = [], {}
    previous = set()
    for index, (key, name) in enumerate([("junior", "初中"), ("senior", "高中"), ("cet4", "大学 CET4"), ("cet6", "大学 CET6"), ("tem8", "英语专八")]):
        previous |= groups[key]
        memberships[key] = set(previous)
        levels.append((key, name, index, "公开备考词书合集；累计包含前序学段基础词。完整范围以所列来源为准。"))
    pool = groups["junior"] | groups["senior"] | groups["ielts"]
    ranked = sorted(pool, key=lambda k: (entries[k]["frequency"], k))
    limits = [500, 1000, 1800, 3000, 4500, 6000, len(ranked)]
    for band, size in enumerate(limits, 1):
        key = f"ielts{band}"
        memberships[key] = set(ranked[:size])
        levels.append((key, f"雅思 {band} 分 · 学习档", band + 4, "自定义学习分级，非官方分数词表：初高中基础词 + 雅思词库，按通用英语词频累计纳入；不保证考试分数。"))
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS / "catalog.sqlite3"
    temp = ASSETS / "catalog.building.sqlite3"
    if temp.exists():
        temp.unlink()
    db = sqlite3.connect(temp)
    db.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE levels(id TEXT PRIMARY KEY, name TEXT, position INTEGER, description TEXT);
        CREATE TABLE words(id INTEGER PRIMARY KEY, word TEXT, initial TEXT, phonetic TEXT, senses TEXT, examples TEXT, phrases TEXT, sources TEXT, search_text TEXT);
        CREATE TABLE membership(level_id TEXT REFERENCES levels(id), word_id INTEGER REFERENCES words(id), PRIMARY KEY(level_id,word_id));
        CREATE INDEX words_order ON words(word COLLATE NOCASE);
        CREATE INDEX words_initial ON words(initial);
    ''')
    db.executemany("INSERT INTO levels VALUES (?,?,?,?)", levels)
    ids = {}
    for wid, (key, entry) in enumerate(sorted(entries.items()), 1):
        if not entry["senses"]:
            raise ValueError(f"词条无释义：{key}")
        ids[key] = wid
        first = unicodedata.normalize("NFKD", entry["word"])[0].upper()
        initial = first if first in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" else "#"
        db.execute("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?)", (wid, entry["word"], initial, entry["phonetic"], dump(entry["senses"]), dump(entry["examples"]), dump(entry["phrases"]), dump(entry["sources"]), " ".join(s["meaning"] for s in entry["senses"])))
    for key, members in memberships.items():
        db.executemany("INSERT INTO membership VALUES (?,?)", [(key, ids[word]) for word in sorted(members)])
    db.commit()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    db.close()
    temp.replace(target)
    report = {
        "sources": report_sources,
        "words": len(entries),
        "examples": sum(len(e["examples"]) for e in entries.values()),
        "words_without_examples": sum(not e["examples"] for e in entries.values()),
        "words_without_examples_or_phrases": sum(not e["examples"] and not e["phrases"] for e in entries.values()),
        "levels": [{"id": key, "name": name, "count": len(memberships[key]), "missing_examples": sum(not entries[k]["examples"] for k in memberships[key])} for key, name, _, _ in levels],
        "ielts_rule": {"pool": len(ranked), "limits": limits, "sort": "BNC / COCA 排名" if ecdict else "wordfreq 3.1.1 英语 Zipf 词频降序；同频次按单词排序", "official": False},
        "scope": "完整导入所列词书记录；不承诺官方大纲、全部义项或逐义例句覆盖。",
    }
    (ASSETS / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("词库完成：%s", dump({k: v for k, v in report.items() if k != "sources"}))


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "work/sources")
    parser.add_argument("--ecdict", type=Path, help="可选：完整 ECDICT CSV，缺省使用 wordfreq 3.1.1")
    args = parser.parse_args()
    build(args.sources, args.ecdict)


if __name__ == "__main__":
    main()
