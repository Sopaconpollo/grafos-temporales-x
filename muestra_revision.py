"""Genera fichas locales de revisión a partir de una muestra reproducible."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import random

from auditar import MONTHS, BOGOTA, csv_out, field, parsedate_to_datetime


def read(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def evidence(tweet):
    legacy = tweet["legacy"]
    quote = field(tweet, "quoted_status_result", "result")
    quote = field(quote, "tweet") or quote
    return {
        "text": field(tweet, "note_tweet", "note_tweet_results", "result", "text") or legacy.get("full_text"),
        "author": legacy.get("user_id_str"),
        "reply_to": legacy.get("in_reply_to_user_id_str"),
        "reply_post": legacy.get("in_reply_to_status_id_str"),
        "quote_post": legacy.get("quoted_status_id_str"),
        "quote_author": field(quote, "legacy", "user_id_str")
        or field(quote, "core", "user_results", "result", "rest_id"),
        "mentions": sorted({entity["id_str"] for entities in (
            field(legacy, "entities", "user_mentions"),
            field(tweet, "note_tweet", "note_tweet_results", "result", "entity_set", "user_mentions"),
        ) if isinstance(entities, list) for entity in entities if entity.get("id_str")}),
    }


def corroborated(event, raw):
    target = event["target"]
    parent = event["referenced_post_id"]
    sources = [record for record in raw[event["post_id"]] if record["author"] == event["source"]]
    if event["type"] == "reply":
        return any(record["reply_to"] == target and (record["reply_post"] or "") == parent
                   for record in sources)
    if event["type"] == "mention":
        return any(target in record["mentions"] for record in sources)
    if event["resolution"] == "post_lookup":
        return (any(record["quote_post"] == parent for record in sources)
                and any(record["author"] == target for record in raw[parent]))
    return any(record["quote_post"] == parent and record["quote_author"] == target
               for record in sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "audit", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    by_file = defaultdict(dict)
    chosen = defaultdict(dict)
    events = read(args.audit / "events.csv")
    for row in read(args.audit / "provenance.csv"):
        by_file[row["file"]][int(row["line"])] = row["post_id"], row["status"]
    rng = random.Random(20261122)
    edge_checks = []
    for kind in ("reply", "quote", "mention"):
        eligible = [r for r in events if r["type"] == kind and r["source"] != r["target"]]
        for month in MONTHS:
            pool = [r for r in eligible if r["month"] == month and
                    (kind != "quote" or r["resolution"] == "direct")]
            edge_checks.extend(rng.sample(pool, min(2, len(pool))))
    edge_checks.extend(r for r in events if r["resolution"] == "post_lookup")
    probe = {r["post_id"] for r in edge_checks}
    probe.update(r["referenced_post_id"] for r in edge_checks if r["resolution"] == "post_lookup")
    raw = defaultdict(list)
    for name, index in sorted(by_file.items()):
        with (args.source / name).open(encoding="utf-8-sig") as file:
            for line_number, line in enumerate(file, 1):
                pid, status = index.get(line_number, ("", ""))
                if status != "included" and pid not in probe:
                    continue
                tweet = json.loads(line)["data"]
                item = evidence(tweet)
                if pid in probe:
                    raw[pid].append(item)
                if status == "included":
                    month = parsedate_to_datetime(tweet["legacy"]["created_at"]).astimezone(BOGOTA).strftime("%Y-%m")
                    if pid not in chosen[month] or len(item["text"] or "") > len(chosen[month][pid] or ""):
                        chosen[month][pid] = item["text"]
    texts = []
    for month in MONTHS:
        posts = rng.sample(sorted(chosen[month]), 8)
        for number, pid in enumerate(posts, 1):
            texts.append({"sample": f"{month}-{number:02}", "post_id": pid, "text": chosen[month][pid]})
    args.output.write_text(json.dumps({"texts": texts, "edges": edge_checks, "evidence": raw},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    csv_out(args.output.with_suffix(".csv"), ["sample", "month", "type", "resolution", "corroborated"],
            [(f"edge-{number:02}", event["month"], event["type"], event["resolution"],
              int(corroborated(event, raw))) for number, event in enumerate(edge_checks, 1)])


if __name__ == "__main__":
    main()
