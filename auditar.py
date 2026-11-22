"""Auditoria y red temporal de X. Requiere Python 3.10+ y NumPy."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import re

import numpy as np


MONTHS = [f"2026-{i:02d}" for i in range(1, 7)]
TYPES = ("reply", "quote", "repost", "mention")
BOGOTA = timezone(timedelta(hours=-5))


def field(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def identifier(value, name, audit):
    if value is None:
        return None
    audit[f"id_type:{name}:{type(value).__name__}"] += 1
    if type(value) in (str, int) and re.fullmatch("[1-9][0-9]*", str(value)):
        return str(value)
    audit[f"invalid_id:{name}"] += 1
    return None


def author(tweet, audit):
    ids = [
        identifier(field(tweet, "legacy", "user_id_str"), "author_legacy", audit),
        identifier(field(tweet, "core", "user_results", "result", "rest_id"),
                   "author_core", audit),
    ]
    if all(ids) and ids[0] != ids[1]:
        audit["author_conflict"] += 1
        return None
    return ids[0] or ids[1]


def references(tweet, legacy, audit):
    result = {}
    for kind, branch, prefix in (
        ("quote", "quoted_status_result", "quoted"),
        ("repost", "retweeted_status_result", "retweeted"),
    ):
        wrapper = tweet.get(branch) or legacy.get(branch)
        post = field(wrapper, "result")
        post = field(post, "tweet") or post
        parent = identifier(legacy.get(prefix + "_status_id_str"), kind + "_post", audit)
        embedded = identifier(field(post, "rest_id"), kind + "_embedded", audit)
        if parent and embedded and parent != embedded:
            audit[f"{kind}_reference_conflict"] += 1
            result[kind] = (True, None, None)
            continue
        signaled = bool(wrapper or parent or (kind == "quote" and legacy.get("is_quote_status")))
        result[kind] = (signaled, author(post, audit), parent or embedded)
    parent = identifier(legacy.get("in_reply_to_status_id_str"), "reply_post", audit)
    target = identifier(legacy.get("in_reply_to_user_id_str"), "reply_user", audit)
    result["reply"] = (bool(parent or target or legacy.get("in_reply_to_screen_name")),
                       target, parent)
    mentions = set()
    entity_lists = [
        field(legacy, "entities", "user_mentions"),
        field(tweet, "note_tweet", "note_tweet_results", "result", "entity_set", "user_mentions"),
    ]
    for entities in entity_lists:
        if not isinstance(entities, list):
            continue
        for entity in entities:
            target = identifier(field(entity, "id_str"), "mention", audit)
            target = target or identifier(field(entity, "id"), "mention_fallback", audit)
            mentions.add(target)
    if legacy.get("retweeted") is True:
        audit["viewer_retweeted_flag"] += 1
    if re.match(r"^RT @", legacy.get("full_text") or ""):
        audit["rt_text_prefix"] += 1
    return result, mentions


def csv_out(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(header)
        writer.writerows(rows)


def ingest(root):
    inventory, audits, paths, groups = [], {}, Counter(), defaultdict(list)
    manifest = {}
    lines = (root / "MANIFIESTO_SHA256.txt").read_text(encoding="utf-8-sig").splitlines()
    for line in lines[1:]:
        sha, tail = line.split(None, 1)
        name, size = tail.rsplit(None, 1)
        manifest[name.strip()] = (sha.lower(), int(size))
    found = {p.relative_to(root).as_posix() for p in root.rglob("*.ndjson")}
    if found != manifest.keys():
        raise ValueError(f"Manifest discrepancy: {found ^ manifest.keys()}")
    for name in sorted(found):
        path = root / name
        digest = hashlib.sha256()
        audit = Counter()
        size = 0
        with path.open("rb") as source:
            for number, line in enumerate(source, 1):
                digest.update(line)
                size += len(line)
                audit["lines"] += 1
                try:
                    record = json.loads(line.decode("utf-8-sig"))
                except (ValueError, UnicodeError):
                    audit["invalid_json"] += 1
                    continue
                tweet = field(record, "data")
                legacy = field(tweet, "legacy")
                if not isinstance(legacy, dict):
                    audit["missing_legacy"] += 1
                    continue
                for label, obj in (("record", record), ("data", tweet), ("legacy", legacy)):
                    paths.update(f"{label}.{key}" for key in obj)
                post_ids = {
                    identifier(value, label, audit) for label, value in (
                        ("rest_id", tweet.get("rest_id")), ("id_str", legacy.get("id_str")),
                        ("item_id", record.get("item_id")), ("data_id", tweet.get("id")),
                    )
                } - {None}
                if len(post_ids) != 1:
                    audit["missing_or_conflicting_post_id"] += 1
                    continue
                post_id = next(iter(post_ids))
                stamp = None
                try:
                    stamp = parsedate_to_datetime(legacy["created_at"])
                    if stamp.tzinfo is None:
                        raise ValueError("missing offset")
                    stamp = stamp.astimezone(BOGOTA)
                except (KeyError, TypeError, ValueError, OverflowError):
                    audit["invalid_date"] += 1
                    stamp = None
                day = stamp.date().isoformat() if stamp else ""
                audit[f"publication_month:{day[:7] or 'unknown'}"] += 1
                if day and day[5:7] != name[:2]:
                    audit["different_month_than_folder"] += 1
                if day and day[:7] not in MONTHS:
                    audit["outside_window"] += 1
                collected = record.get("timestamp_collected")
                if type(collected) is int:
                    try:
                        capture_day = datetime.fromtimestamp(collected / 1000, BOGOTA).date()
                        audit[f"collection_month:{capture_day.isoformat()[:7]}"] += 1
                    except (ValueError, OverflowError, OSError):
                        audit["invalid_collection_timestamp"] += 1
                refs, mentions = references(tweet, legacy, audit)
                actor = author(tweet, audit)
                if not actor:
                    audit["missing_author"] += 1
                views = field(tweet, "views", "count")
                audit["views_present"] += views is not None
                groups[post_id].append((actor, stamp, refs, mentions, name, number))
        if (digest.hexdigest(), size) != manifest[name]:
            raise ValueError(f"Hash or size discrepancy: {name}")
        inventory.append((name, digest.hexdigest(), size, audit["lines"], "OK"))
        audits[name] = audit
    return inventory, audits, paths, groups


def consolidate(groups, out):
    identities = {}
    audit = Counter()
    provenance = []
    for pid, copies in sorted(groups.items()):
        actors = {row[0] for row in copies if row[0]}
        stamps = {row[1] for row in copies if row[1]}
        audit["duplicate_ids"] += len(copies) > 1
        audit["duplicate_rows"] += len(copies) - 1
        audit["duplicates_across_files"] += len({row[4] for row in copies}) > 1
        if len(actors) == 1:
            identities[pid] = next(iter(actors))
        if len(actors) > 1 or len(stamps) > 1:
            status = "identity_or_date_conflict"
        elif not actors or not stamps:
            status = "missing_author_or_date"
        else:
            status = "included" if next(iter(stamps)).strftime("%Y-%m") in MONTHS else "outside"
        audit[status] += 1
        for row in copies:
            provenance.append((pid, status, row[4], row[5]))
    csv_out(out / "provenance.csv", ["post_id", "status", "file", "line"], provenance)
    return identities, audit


def events(groups, identities, out):
    rows, quality, daily, monthly, authors = [], Counter(), Counter(), Counter(), defaultdict(set)
    for pid, copies in sorted(groups.items()):
        stamps = {row[1] for row in copies if row[1]}
        actor = identities.get(pid)
        if len(stamps) != 1 or not actor:
            continue
        stamp = next(iter(stamps))
        month = stamp.strftime("%Y-%m")
        if month not in MONTHS:
            continue
        day = stamp.date().isoformat()
        monthly[month] += 1
        daily[day] += 1
        authors[month].add(actor)
        for kind in TYPES[:-1]:
            refs = [row[2][kind] for row in copies]
            if not any(ref[0] for ref in refs):
                continue
            quality[month, kind, "signaled_posts"] += 1
            parents = {ref[2] for ref in refs if ref[2]}
            direct = {ref[1] for ref in refs if ref[1]}
            via_post = {identities[parent] for parent in parents if parent in identities}
            targets = direct | via_post
            if len(parents) > 1 or len(targets) > 1:
                quality[month, kind, "conflict"] += 1
            elif not targets:
                quality[month, kind, "unresolved"] += 1
            else:
                target = next(iter(targets))
                method = "direct" if direct else "post_lookup"
                rows.append((month, stamp.isoformat(), kind, pid, actor, target,
                             next(iter(parents), ""), method))
                quality[month, kind, method] += 1
        mentions = set().union(*(row[3] for row in copies))
        if mentions:
            quality[month, "mention", "signaled_posts"] += 1
        if None in mentions:
            quality[month, "mention", "posts_with_unresolved_entity"] += 1
        for target in sorted(mentions - {None}):
            rows.append((month, stamp.isoformat(), "mention", pid, actor, target, "", "entity"))
        quality[month, "mention", "resolved_targets"] += len(mentions - {None})
    csv_out(out / "events.csv",
            ["month", "published_bogota", "type", "post_id", "source", "target",
             "referenced_post_id", "resolution"], rows)
    csv_out(out / "interactions_quality.csv", ["month", "type", "metric", "value"],
            [(m, k, metric, quality[m, k, metric]) for m in MONTHS for k in TYPES
             for metric in (("signaled_posts", "posts_with_unresolved_entity", "resolved_targets")
                            if k == "mention" else
                            ("signaled_posts", "direct", "post_lookup", "unresolved", "conflict"))])
    all_days = [date(2026, 1, 1) + timedelta(days=i) for i in range(181)]
    csv_out(out / "daily.csv", ["date", "posts"], [(d.isoformat(), daily[d.isoformat()]) for d in all_days])
    csv_out(out / "monthly.csv", ["month", "posts", "authors", "days_observed", "days_in_month"],
            [(m, monthly[m], len(authors[m]),
              sum(daily[d.isoformat()] > 0 for d in all_days if d.strftime("%Y-%m") == m),
              sum(d.strftime("%Y-%m") == m for d in all_days)) for m in MONTHS])
    return rows


def matrix_market(path, n, entries, real=False):
    with path.open("w", encoding="ascii", newline="\n") as file:
        dtype = "real" if real else "integer"
        file.write(f"%%MatrixMarket matrix coordinate {dtype} general\n")
        file.write(f"{n} {n} {len(entries)}\n")
        for (i, j), value in sorted(entries.items()):
            file.write(f"{i + 1} {j + 1} {value}\n")


def components(n, edges):
    neighbors = [set() for _ in range(n)]
    for i, j in edges:
        neighbors[i].add(j)
        neighbors[j].add(i)
    unseen = set(range(n))
    parts = []
    for first in range(n):
        if first not in unseen:
            continue
        unseen.remove(first)
        part = [first]
        for node in part:
            new = neighbors[node] & unseen
            unseen.difference_update(new)
            part.extend(sorted(new))
        parts.append(sorted(part))
    return sorted(parts, key=lambda part: (-len(part), part[0]))


def spectrum(n, i, j, weights, return_vectors=False):
    """Smallest Ritz pairs of normalized Laplacian, with explicit residuals."""
    def matvec(v):
        return v - np.bincount(i, weights=weights * v[j], minlength=n)

    if n <= 256:
        laplacian = np.eye(n)
        laplacian[i, j] -= weights
        values, vectors = np.linalg.eigh(laplacian)
    else:
        rng = np.random.default_rng(42)
        q = rng.standard_normal(n)
        q /= np.linalg.norm(q)
        basis, image = np.empty((180, n)), np.empty((180, n))
        for step in range(180):
            basis[step], image[step] = q, matvec(q)
            active = basis[:step + 1]
            residual = image[step].copy()
            for _ in range(2):
                residual -= (active @ residual) @ active
            norm = np.linalg.norm(residual)
            if norm < 1e-12:
                break
            q = residual / norm
        projected = active @ image[:step + 1].T
        values, small = np.linalg.eigh((projected + projected.T) / 2)
        vectors = active.T @ small[:, :min(6, n)]
    diagnostics = [(float(value), float(np.linalg.norm(matvec(v) - value * v)))
                   for value, v in zip(values[:6], vectors[:, :6].T)]
    return (diagnostics, vectors[:, :6]) if return_vectors else diagnostics


def graphs(rows, out):
    by_layer = defaultdict(Counter)
    loops = Counter()
    for month, _, kind, _, source, target, _, _ in rows:
        for layer in (kind, "all"):
            if source == target:
                loops[month, layer] += 1
            else:
                by_layer[month, layer][source, target] += 1
    matrices = out / "matrices"
    matrices.mkdir(exist_ok=True)
    diagnostics, eigenvalues, edges = [], [], []
    node_sets = {}
    for month in MONTHS:
        for kind in (*TYPES, "all"):
            counts = by_layer[month, kind]
            if kind != "all":
                edges.extend((month, kind, s, t, w) for (s, t), w in sorted(counts.items()))
            nodes = sorted({node for pair in counts for node in pair})
            node_sets[month, kind] = set(nodes)
            index = {node: i for i, node in enumerate(nodes)}
            directed = {(index[s], index[t]): w for (s, t), w in counts.items()}
            prefix = f"{month}_{kind}"
            csv_out(matrices / f"{prefix}_nodes.csv", ["index", "user_id"],
                    [(i + 1, node) for i, node in enumerate(nodes)])
            n = len(nodes)
            matrix_market(matrices / f"{prefix}_A.mtx", n, directed)
            parts = components(n, directed)
            giant = parts[0] if parts else []
            g = len(giant)
            local = {index: i for i, index in enumerate(giant)}
            csv_out(matrices / f"{prefix}_lcc_nodes.csv", ["index", "user_id"],
                    [(i + 1, nodes[index]) for i, index in enumerate(giant)])
            sym = Counter()
            for (source, target), weight in directed.items():
                if source in local and target in local:
                    a, b = local[source], local[target]
                    sym[a, b] += weight
                    sym[b, a] += weight
            pairs = sorted(sym)
            laplacian = {}
            results = []
            if g > 1:
                i, j = np.asarray(pairs).T
                weights = np.array([sym[pair] for pair in pairs], dtype=float)
                degree = np.bincount(i, weights=weights, minlength=g)
                normalized = weights / np.sqrt(degree[i] * degree[j])
                laplacian = {pair: -v for pair, v in zip(pairs, normalized)}
                laplacian.update({(index, index): 1.0 for index in range(g)})
                results = spectrum(g, i, j, normalized)
            matrix_market(matrices / f"{prefix}_Lnorm_lcc.mtx", g, laplacian, real=True)
            eigenvalues.extend((month, kind, k, value, error, int(error <= 1e-7))
                               for k, (value, error) in enumerate(results, 1))
            first_two_ok = len(results) >= 2 and all(err <= 1e-7 for _, err in results[:2])
            gap = results[1][0] if first_two_ok else ""
            status = "converged" if first_two_ok else ("empty" if not n else "residual_high")
            diagnostics.append((month, kind, n, len(counts), sum(counts.values()), loops[month, kind],
                                len(parts), g, g / n if n else "",
                                len(counts) / (n * (n - 1)) if n > 1 else "", gap, status))
    csv_out(out / "edges.csv", ["month", "type", "source", "target", "weight"], edges)
    csv_out(out / "spectral.csv", ["month", "type", "nodes", "arcs", "weight", "loops_excluded",
                                  "weak_components", "lcc_nodes", "lcc_fraction", "density",
                                  "lambda2_lcc", "status"], diagnostics)
    csv_out(out / "eigenvalues.csv",
            ["month", "type", "index", "lambda", "residual_l2", "residual_le_1e_7"], eigenvalues)
    overlap = []
    for previous, current in zip(MONTHS, MONTHS[1:]):
        for kind in (*TYPES, "all"):
            a, b = node_sets[previous, kind], node_sets[current, kind]
            overlap.append((previous, current, kind, len(a & b), len(a | b),
                            len(a & b) / len(a | b) if a or b else ""))
    csv_out(out / "node_overlap.csv",
            ["previous_month", "month", "type", "intersection", "union", "jaccard"], overlap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, out = args.source.resolve(), args.output.resolve()
    if root == out or root in out.parents:
        parser.error("Output must be outside the source tree")
    inventory, audits, paths, groups = ingest(root)
    out.mkdir(parents=True, exist_ok=True)
    csv_out(out / "inventory.csv", ["file", "sha256", "bytes", "lines", "manifest"], inventory)
    csv_out(out / "file_quality.csv", ["file", "metric", "value"],
            [(name, key, val) for name, audit in audits.items() for key, val in sorted(audit.items())])
    csv_out(out / "schema.csv", ["path", "present_rows"], sorted(paths.items()))
    identities, audit = consolidate(groups, out)
    (out / "summary.json").write_text(
        json.dumps({"files": len(inventory), "rows": sum(row[3] for row in inventory),
                    "distinct_post_ids": len(groups), **audit}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    rows = events(groups, identities, out)
    graphs(rows, out)


if __name__ == "__main__":
    main()
