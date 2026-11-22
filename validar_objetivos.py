"""Completa el contraste de comunidades, sensibilidad y calendario electoral."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import heapq
from pathlib import Path
from statistics import median

import numpy as np

from auditar import MONTHS, components, csv_out, spectrum
from comunidades import adjusted_rand, partition


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main_component(edges):
    nodes = sorted({node for edge in edges for node in edge})
    indexes = {node: i for i, node in enumerate(nodes)}
    parts = components(len(nodes), [(indexes[a], indexes[b]) for a, b in edges])
    selected = [nodes[i] for i in parts[0]]
    index = {node: i for i, node in enumerate(selected)}
    pairs = {(index[a], index[b]): w for (a, b), w in edges.items()
             if a in index and b in index}
    return selected, pairs, len(parts)


def greedy_modularity(n, edges):
    """Agglomerate the pair with the highest positive modularity gain."""
    total = sum(edges.values())
    adjacent = [Counter() for _ in range(n)]
    for (a, b), w in edges.items():
        adjacent[a][b] = adjacent[b][a] = w
    degrees = [sum(row.values()) for row in adjacent]
    volumes = degrees.copy()
    members = {i: [i] for i in range(n)}
    versions = [0] * n
    queue = []

    def enqueue(a, b):
        a, b = sorted((a, b))
        gain = adjacent[a][b] * (2 * total) - volumes[a] * volumes[b]
        if gain > 0:
            heapq.heappush(queue, (-gain, a, b, versions[a], versions[b]))

    for a, b in edges:
        enqueue(a, b)
    while queue:
        _, a, b, va, vb = heapq.heappop(queue)
        if versions[a] != va or versions[b] != vb:
            continue
        adjacent[a].pop(b)
        adjacent[b].pop(a)
        for c, weight in adjacent[b].items():
            adjacent[c].pop(b)
            adjacent[a][c] += weight
            adjacent[c][a] = adjacent[a][c]
        adjacent[b].clear()
        members[a].extend(members.pop(b))
        volumes[a] += volumes[b]
        versions[a] += 1
        versions[b] += 1
        for c in adjacent[a]:
            enqueue(a, c)
    labels = [0] * n
    for label, community in enumerate(members.values()):
        for node in community:
            labels[node] = label
    internal = sum(w for (a, b), w in edges.items() if labels[a] == labels[b])
    q = internal / total - sum((volumes[a] / (2 * total)) ** 2 for a in members)
    return labels, q, degrees


def jaccard_rows(groups, method):
    for previous, current in zip(MONTHS, MONTHS[1:]):
        for kind in ("all", "reply", "mention", "quote"):
            for a, left in sorted(groups[previous, kind].items()):
                for b, right in sorted(groups[current, kind].items()):
                    intersection = len(left & right)
                    union = len(left | right)
                    yield previous, current, kind, method, a, b, intersection, union, intersection / union


def electoral(audit):
    posts = {date.fromisoformat(r["date"]): int(r["posts"]) for r in read(audit / "daily.csv")}
    events = defaultdict(list)
    for row in read(audit / "events.csv"):
        if row["source"] != row["target"]:
            events[date.fromisoformat(row["published_bogota"][:10])].append(row)
    for label, day in (
        ("Congreso y consultas", date(2026, 3, 8)),
        ("Primera vuelta", date(2026, 5, 31)),
        ("Segunda vuelta", date(2026, 6, 21)),
    ):
        for window, offsets in (("pre", range(-7, 0)), ("jornada", range(1)), ("post", range(1, 8))):
            days = [day + timedelta(days=i) for i in offsets]
            rows = [row for d in days for row in events[d]]
            pairs = {(r["source"], r["target"]) for r in rows}
            nodes = sorted({node for pair in pairs for node in pair})
            index = {node: i for i, node in enumerate(nodes)}
            parts = components(len(nodes), [(index[a], index[b]) for a, b in pairs])
            gap = ""
            if rows:
                weights = Counter(tuple(sorted((row["source"], row["target"]))) for row in rows)
                selected, undirected, _ = main_component(weights)
                triples = [(i, j, w) for (a, b), w in undirected.items()
                           for i, j in ((a, b), (b, a))]
                i, j, w = np.asarray(triples).T
                degree = np.bincount(i, weights=w, minlength=len(selected))
                pairs_eigen = spectrum(len(selected), i, j, w / np.sqrt(degree[i] * degree[j]))
                if all(residual <= 1e-7 for _, residual in pairs_eigen[:2]):
                    gap = pairs_eigen[1][0]
            yield (label, day.isoformat(), window, days[0].isoformat(), days[-1].isoformat(),
                   sum(posts[d] > 0 for d in days), sum(posts[d] for d in days), len(rows),
                   len(nodes), len(pairs), len(parts), len(parts[0]) / len(nodes) if nodes else "", gap)


def run(audit, communities, output):
    layers = defaultdict(Counter)
    for row in read(audit / "edges.csv"):
        month, kind = row["month"], row["type"]
        edge = tuple(sorted((row["source"], row["target"])))
        layers[month, kind][edge] += int(row["weight"])
        layers[month, "all"][edge] += int(row["weight"])
    spectral = defaultdict(dict)
    spectral_groups = defaultdict(lambda: defaultdict(set))
    for row in read(communities / "pertenencia.csv"):
        key = row["month"], row["type"]
        group = int(row["group"])
        spectral[key][row["user_id"]] = group
        spectral_groups[key][group].add(row["user_id"])
    greedy_groups = defaultdict(lambda: defaultdict(set))
    comparison, sensitivity, degrees_summary = [], [], []
    for (month, kind), edges in sorted(layers.items()):
        nodes, pairs, part_count = main_component(edges)
        labels, q, _ = greedy_modularity(len(nodes), pairs)
        reference = spectral[month, kind]
        assert set(nodes) == reference.keys()
        for node, label in zip(nodes, labels):
            greedy_groups[month, kind][label].add(node)
        sizes = Counter(labels)
        comparison.append((month, kind, len(nodes), len(sizes), max(sizes.values()), q,
                           adjusted_rand([reference[node] for node in nodes], labels)))
        degree, strength = Counter(), Counter()
        for (a, b), w in edges.items():
            for node in (a, b):
                degree[node] += 1
                strength[node] += w
        degrees_summary.append((month, kind, len(degree), part_count, median(degree.values()),
                                max(degree.values()), median(strength.values()), max(strength.values()),
                                0 if part_count > 1 else ""))
        if kind != "all":
            continue
        for scenario, factors in (
            ("sin_menciones", {"mention": 0, "reply": 1, "quote": 1}),
            ("doble_respuestas", {"mention": 1, "reply": 2, "quote": 1}),
            ("doble_citas", {"mention": 1, "reply": 1, "quote": 2}),
        ):
            changed = Counter()
            for layer, factor in factors.items():
                if factor:
                    for edge, w in layers[month, layer].items():
                        changed[edge] += factor * w
            target, candidate, _ = main_component(changed)
            triples = [(i, j, w) for (a, b), w in candidate.items() for i, j in ((a, b), (b, a))]
            i, j, weights = np.asarray(triples).T
            result = partition(i, j, weights.astype(float), len(target))
            shared = [k for k, node in enumerate(target) if node in reference]
            ari = (adjusted_rand([reference[target[k]] for k in shared], result[0][shared])
                   if result is not None else "")
            sensitivity.append((month, scenario, len(target), len(shared), ari))
    output.mkdir(parents=True, exist_ok=True)
    csv_out(output / "modularidad.csv",
            ["month", "type", "lcc", "groups", "largest_group", "greedy_q", "ari_vs_spectral"], comparison)
    csv_out(output / "ponderaciones.csv", ["month", "scenario", "lcc", "shared", "ari"], sensitivity)
    csv_out(output / "grados.csv",
            ["month", "type", "nodes", "components", "median_degree", "max_degree",
             "median_strength", "max_strength", "lambda2_full_if_disconnected"], degrees_summary)
    csv_out(output / "jaccard.csv",
            ["previous", "current", "type", "method", "previous_group", "current_group",
             "intersection", "union", "jaccard"],
            [*jaccard_rows(spectral_groups, "spectral"), *jaccard_rows(greedy_groups, "greedy")])
    csv_out(output / "calendario.csv",
            ["event", "date", "window", "start", "end", "days_observed", "posts", "interactions",
             "nodes", "arcs", "components", "lcc_fraction", "lambda2_lcc"], electoral(audit))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("audit", "communities", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.audit, args.communities, args.output)
