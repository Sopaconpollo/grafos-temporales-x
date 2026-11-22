"""Contraste exploratorio de similitud léxica sin exportar texto ni cuentas."""
import argparse
from collections import Counter, defaultdict
import csv
from itertools import combinations
import json
from math import log, sqrt
from pathlib import Path
import random
import re

from auditar import MONTHS, csv_out, field
from validar_objetivos import greedy_modularity, main_component

STOP = set("para como pero este esta estos estas desde donde cuando quien quienes porque sobre entre"
           " todo toda todos todas ellos ellas usted ustedes nosotros también tiene tienen puede"
           " pueden hacer hecho hace cada esto esos esas dicho dicha sido será eran fueron haber"
           " hasta sean algo mucho solo sólo mismo misma ahora entonces aquí allí".split())


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def tokenize(text):
    plain = re.sub(r"https?://\S+|@\w+", " ", text.lower())
    return [word for word in re.findall(r"(?u)\b[^\W\d_]{4,}\b", plain) if word not in STOP]


def authors_text(source, audit, members):
    wanted = defaultdict(dict)
    for row in rows(audit / "provenance.csv"):
        if row["status"] == "included":
            wanted[row["file"]][int(row["line"])] = row["post_id"]
    dates = {}
    # created_at and IDs were checked by the audit. Use the longest tokenized copy.
    from email.utils import parsedate_to_datetime
    from auditar import BOGOTA
    for name, selected in sorted(wanted.items()):
        with (source / name).open(encoding="utf-8-sig") as file:
            for number, line in enumerate(file, 1):
                pid = selected.get(number)
                if pid is None:
                    continue
                tweet = json.loads(line)["data"]
                if field(tweet, "legacy", "lang") != "es":
                    continue
                node = field(tweet, "legacy", "user_id_str")
                month = parsedate_to_datetime(tweet["legacy"]["created_at"]).astimezone(BOGOTA).strftime("%Y-%m")
                if node not in members[month]:
                    continue
                note = field(tweet, "note_tweet", "note_tweet_results", "result", "text")
                tokens = tokenize(note or field(tweet, "legacy", "full_text") or "")
                if len(tokens) >= 5 and (pid not in dates or len(tokens) > len(dates[pid][2])):
                    dates[pid] = month, node, tokens
    by_author = defaultdict(Counter)
    counts = Counter()
    for month, node, tokens in dates.values():
        counts[month, node] += 1
        by_author[month, node].update(tokens)
    return by_author, counts


def pair_scores(vectors, left, right, rng):
    n, m = len(left), len(right)
    same = left is right
    possible = n * (n - 1) // 2 if same else n * m
    if not possible:
        return 0, ""
    if possible <= 3000:
        pairs = combinations(left, 2) if same else ((a, b) for a in left for b in right)
    else:
        pairs = (rng.sample(left, 2) if same else (rng.choice(left), rng.choice(right))
                 for _ in range(3000))
    total = 0
    for a, b in pairs:
        u, v = vectors[a], vectors[b]
        if len(u) > len(v):
            u, v = v, u
        total += sum(value * v.get(term, 0) for term, value in u.items())
    size = min(possible, 3000)
    return size, total / size


def run(source, audit, communities, output):
    members = defaultdict(dict)
    for row in rows(communities / "pertenencia.csv"):
        if row["type"] == "all":
            members[row["month"]][row["user_id"]] = int(row["group"])
    words, post_counts = authors_text(source, audit, members)
    layers = defaultdict(Counter)
    for row in rows(audit / "edges.csv"):
        edge = tuple(sorted((row["source"], row["target"])))
        layers[row["month"]][edge] += int(row["weight"])
    rng = random.Random(92)
    results = []
    for month in MONTHS:
        account_groups = members[month]
        eligible = sorted(node for node in account_groups if post_counts[month, node] >= 5)
        df = Counter(term for node in eligible for term in words[month, node])
        vectors = {}
        for node in eligible:
            values = {term: (1 + log(freq)) * (1 + log((1 + len(eligible)) / (1 + df[term])))
                      for term, freq in words[month, node].items() if df[term] >= 2}
            norm = sqrt(sum(value * value for value in values.values()))
            if norm:
                vectors[node] = {term: value / norm for term, value in values.items()}
        nodes, edges, _ = main_component(layers[month])
        labels, _, _ = greedy_modularity(len(nodes), edges)
        for method, groups in (("spectral", account_groups), ("greedy_top2", dict(zip(nodes, labels)))):
            sizes = Counter(groups.values())
            if len(sizes) < 2:
                continue
            second, first = sorted(sizes, key=lambda group: (-sizes[group], group))[:2]
            small = [node for node in vectors if groups[node] == first]
            large = [node for node in vectors if groups[node] == second]
            # Below five represented accounts per group, report coverage only.
            scores = [None] * 6
            if min(len(small), len(large)) >= 5:
                scores = [value for left, right in ((small, small), (large, large), (small, large))
                          for value in pair_scores(vectors, left, right, rng)]
            results.append((month, method, sizes[first], sizes[second], len(small), len(large), *scores))
    output.mkdir(parents=True, exist_ok=True)
    csv_out(output / "similitud_textual.csv",
            ["month", "method", "small_group", "large_group", "eligible_small", "eligible_large",
             "pairs_small", "cosine_small", "pairs_large", "cosine_large",
             "pairs_between", "cosine_between"], results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "audit", "communities", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.source, args.audit, args.communities, args.output)
