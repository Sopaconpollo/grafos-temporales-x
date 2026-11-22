"""Build a self-contained viewer with community graphs and local account samples."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from auditar import MONTHS
from validar_objetivos import greedy_modularity, main_component, read


def build(audit, partitions):
    networks = defaultdict(Counter)
    for row in read(audit / "edges.csv"):
        pair = row["source"], row["target"]
        for layer in ("all", row["type"]):
            networks[row["month"], layer][pair] += int(row["weight"])
    spectral = defaultdict(dict)
    for row in read(partitions / "pertenencia.csv"):
        spectral[row["month"], row["type"]][row["user_id"]] = int(row["group"])
    data = {}
    for (month, layer), directed in sorted(networks.items()):
        undirected = Counter()
        for (source, target), weight in directed.items():
            undirected[tuple(sorted((source, target)))] += weight
        nodes, edges, component_count = main_component(undirected)
        greedy, modularity, _ = greedy_modularity(len(nodes), edges)
        spectral_labels = spectral[month, layer]
        assert set(nodes) == spectral_labels.keys()
        modes = {}
        for mode, labels in (("modularidad", greedy), ("espectral", [spectral_labels[n] for n in nodes])):
            sizes = Counter(labels)
            order = sorted(sizes, key=lambda label: (-sizes[label], label))
            ranks = {label: i for i, label in enumerate(order)}
            memberships = {node: ranks[label] for node, label in zip(nodes, labels)}
            inter = Counter()
            level = defaultdict(list)
            incoming = Counter()
            internal = Counter()
            arcs = Counter()
            for (source, target), weight in directed.items():
                if source not in memberships or target not in memberships:
                    continue
                a, b = memberships[source], memberships[target]
                inter[a, b] += weight
                if a == b:
                    internal[a] += weight
                    arcs[a] += 1
                    level[a].append((source, target, weight))
                    incoming[source] += weight
                    incoming[target] += weight
            groups = []
            for i, label in enumerate(order):
                accounts = sorted((n for n in nodes if memberships[n] == i),
                                  key=lambda node: (-incoming[node], node))[:24]
                pos = {node: j for j, node in enumerate(accounts)}
                detail = [[pos[a], pos[b], w] for a, b, w in level[i] if a in pos and b in pos]
                groups.append([sizes[label], internal[i], arcs[i], len(accounts), detail])
            modes[mode] = {
                "groups": groups,
                "links": [[a, b, w] for (a, b), w in sorted(inter.items()) if a != b],
            }
            assert sum(g[1] for g in groups) + sum(w for _, _, w in modes[mode]["links"]) == sum(edges.values())
        modes["modularidad"]["q"] = round(modularity, 4)
        data.setdefault(month, {})[layer] = {
            "total": len({n for pair in directed for n in pair}), "lcc": len(nodes),
            "components": component_count, "modes": modes,
        }
    assert set(data) == set(MONTHS) and sum(map(len, data.values())) == 24
    return data


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("audit", "partitions", "template", "output"):
        p.add_argument(arg, type=Path)
    args = p.parse_args()
    template = args.template.read_text(encoding="utf-8")
    assert template.count("__GRAPH_DATA__") == 1
    data = json.dumps(build(args.audit, args.partitions), separators=(",", ":"))
    args.output.write_text(template.replace("__GRAPH_DATA__", data), encoding="utf-8")
