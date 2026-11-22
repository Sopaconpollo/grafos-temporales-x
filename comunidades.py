"""Particiones espectrales exploratorias y comparacion de nodos compartidos."""
import argparse
from collections import Counter, defaultdict
import csv
from math import comb
from pathlib import Path

import numpy as np

from auditar import MONTHS, components, csv_out, spectrum


def partition(i, j, weights, n):
    degree = np.bincount(i, weights=weights, minlength=n)
    normalized = weights / np.sqrt(degree[i] * degree[j])
    diagnostics, vectors = spectrum(n, i, j, normalized, return_vectors=True)
    if any(residual > 1e-7 for _, residual in diagnostics[:2]):
        return None
    # Row normalization followed by two-cluster k-means with fixed restarts.
    points = vectors[:, :2]
    points = points / np.linalg.norm(points, axis=1, keepdims=True)
    rng = np.random.default_rng(62)
    best = None
    for _ in range(20):
        centers = points[rng.choice(n, 2, replace=False)]
        for _ in range(100):
            distances = ((points[:, None, :] - centers) ** 2).sum(axis=2)
            labels = distances.argmin(axis=1)
            masks = [labels == k for k in range(2)]
            if not all(mask.any() for mask in masks):
                break
            new = np.array([points[mask].mean(axis=0) for mask in masks])
            if np.allclose(new, centers, atol=1e-10, rtol=0):
                loss = float(((points - centers[labels]) ** 2).sum())
                if best is None or loss < best[0]:
                    best = loss, labels
                break
            centers = new
    return None if best is None else (best[1], degree, diagnostics[1][0])


def adjusted_rand(a, b):
    n = len(a)
    if n < 2 or len(set(a)) < 2 or len(set(b)) < 2:
        return ""
    together = sum(comb(v, 2) for v in Counter(zip(a, b)).values())
    left = sum(comb(v, 2) for v in Counter(a).values())
    right = sum(comb(v, 2) for v in Counter(b).values())
    expected = left * right / comb(n, 2)
    upper = (left + right) / 2
    return (together - expected) / (upper - expected) if upper != expected else 1.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    layers = defaultdict(Counter)
    with (args.audit / "edges.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            month, kind = row["month"], row["type"]
            pair = tuple(sorted((row["source"], row["target"])))
            for layer in (kind, "all"):
                layers[month, layer][pair] += int(row["weight"])
    metrics, memberships, temporal = [], [], []
    partitions = {}
    for month in MONTHS:
        for kind in ("all", "mention", "reply", "quote"):
            edges = layers[month, kind]
            nodes = sorted({node for pair in edges for node in pair})
            if not nodes:
                continue
            index = {node: i for i, node in enumerate(nodes)}
            pairs = {(index[a], index[b]): w for (a, b), w in edges.items()}
            giant = components(len(nodes), pairs)[0]
            local = {v: k for k, v in enumerate(giant)}
            sym = {(local[a], local[b]): w for (a, b), w in pairs.items()
                   if a in local and b in local}
            sym.update({(b, a): w for (a, b), w in list(sym.items())})
            ordered = sorted(sym)
            i, j = np.array(ordered).T
            w = np.array([sym[pair] for pair in ordered], dtype=float)
            n = len(giant)
            weighted = partition(i, j, w, n)
            binary = partition(i, j, np.ones_like(w), n)
            if weighted is None:
                metrics.append((month, kind, len(nodes), n, "", "", "", "", "", "", "unresolved"))
                continue
            labels, degree, lambda2 = weighted
            volume = np.bincount(labels, weights=degree, minlength=2)
            cut = w[labels[i] != labels[j]].sum() / 2
            modularity = 1 - cut / (w.sum() / 2) - ((volume / w.sum()) ** 2).sum()
            sensitivity = adjusted_rand(labels, binary[0]) if binary else ""
            size = np.bincount(labels)
            metrics.append((month, kind, len(nodes), n, int(size.min()), int(size.max()),
                            lambda2, float(modularity), float(cut / volume.min()),
                            sensitivity, "ok"))
            # Canonical label 0 contains the first lexicographically ordered account.
            mapping = {nodes[g]: int(label != labels[0]) for g, label in zip(giant, labels)}
            partitions[month, kind] = mapping
            memberships.extend((month, kind, node, label) for node, label in mapping.items())
    for previous, month in zip(MONTHS, MONTHS[1:]):
        for kind in ("all", "mention", "reply", "quote"):
            a = partitions.get((previous, kind), {})
            b = partitions.get((month, kind), {})
            shared = sorted(a.keys() & b.keys())
            temporal.append((previous, month, kind, len(shared), len(a), len(b),
                             adjusted_rand([a[v] for v in shared], [b[v] for v in shared])))
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    csv_out(out / "particiones.csv",
            ["month", "type", "nodes", "lcc_nodes", "small_group", "large_group", "lambda2",
             "modularity", "conductance", "ari_weighted_vs_binary", "status"], metrics)
    csv_out(out / "pertenencia.csv", ["month", "type", "user_id", "group"], memberships)
    csv_out(out / "estabilidad.csv",
            ["previous_month", "month", "type", "shared", "previous_lcc", "current_lcc", "ari"],
            temporal)


if __name__ == "__main__":
    main()
