"""Analiza estructura dirigida, robustez al volumen y contenido explícito."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import unicodedata

import numpy as np

from auditar import BOGOTA, MONTHS, components, csv_out, field, parsedate_to_datetime
from comunidades import adjusted_rand
from validar_objetivos import greedy_modularity, main_component


FIGURES = {
    "Cepeda": r"ivan\s+cepeda|ivancepedacast",
    "De la Espriella": r"abelardo(?:\s+de)?\s+la\s+espriella|abdelaespriella",
    "Fajardo": r"sergio\s+fajardo|sergio_fajardo",
    "Valencia": r"paloma\s+valencia|palomavalencial",
}
THEMES = {
    "Voto y elecciones": r"eleccion(?:es)?|vot(?:o|os|ar|acion|aciones)|(?:primera|segunda)\s+vuelta|tarjeton",
    "Encuestas": r"encuesta(?:s)?|intencion\s+de\s+voto|invamer|gad3|guarumo",
    "Campaña y debates": r"campan(?:a|as)|candidat(?:o|a|os|as|ura|uras)|precandidat(?:o|a|os|as)|debate(?:s)?",
    "Seguridad y conflicto": r"seguridad|conflicto(?:\s+armado)?|extorsion|narcotrafico|guerrilla|paramilitar(?:es)?",
    "Economía y empleo": r"economia|empleo|desempleo|impuestos?|inflacion|reforma\s+tributaria",
}


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def structure(arcs):
    nodes = sorted({node for pair in arcs for node in pair})
    index = {node: i for i, node in enumerate(nodes)}
    parts = components(len(nodes), [(index[a], index[b]) for a, b in arcs])
    incoming = Counter()
    for (_, target), weight in arcs.items():
        incoming[target] += weight
    total = sum(arcs.values())
    reciprocal = sum((b, a) in arcs for a, b in arcs)
    top = sum(value for _, value in incoming.most_common(10)) / total
    return len(nodes), len(arcs), total, len(parts), len(parts[0]) / len(nodes), reciprocal / len(arcs), top


def text_statistics(source, audit, output):
    provenance = defaultdict(dict)
    for row in read(audit / "provenance.csv"):
        if row["status"] == "included":
            provenance[row["file"]][int(row["line"])] = row["post_id"]
    posts = {}
    for name, targets in sorted(provenance.items()):
        with (source / name).open(encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, 1):
                if line_number not in targets:
                    continue
                pid = targets[line_number]
                t = json.loads(line)["data"]
                raw = field(t, "note_tweet", "note_tweet_results", "result", "text") or field(t, "legacy", "full_text") or ""
                month = parsedate_to_datetime(t["legacy"]["created_at"]).astimezone(BOGOTA).strftime("%Y-%m")
                if pid not in posts or len(raw) > len(posts[pid][1]):
                    posts[pid] = month, raw
    figures = {key: re.compile(r"\b(?:" + pattern + r")\b") for key, pattern in FIGURES.items()}
    themes = {key: re.compile(r"\b(?:" + pattern + r")\b") for key, pattern in THEMES.items()}
    total = Counter()
    counts = Counter()
    multi = Counter()
    cross = Counter()
    for month, raw in posts.values():
        plain = re.sub(r"https?://\S+", " ", raw.lower())
        plain = "".join(c for c in unicodedata.normalize("NFKD", plain) if not unicodedata.combining(c))
        total[month] += bool(plain.strip())
        f = [key for key, reg in figures.items() if reg.search(plain)]
        t = [key for key, reg in themes.items() if reg.search(plain)]
        multi[month, "alguna_figura"] += bool(f)
        multi[month, "varias_figuras"] += len(f) >= 2
        multi[month, "algun_tema"] += bool(t)
        counts.update((month, "figura", key) for key in f)
        counts.update((month, "tema", key) for key in t)
        cross.update((month, figure, theme) for figure in f for theme in t)
    csv_out(output / "contenido.csv", ["mes", "tipo", "etiqueta", "textos", "total", "proporcion"], [
        (month, kind, key, counts[month,kind,key], total[month], counts[month,kind,key]/total[month])
        for month in MONTHS for kind, keys in (("figura", figures), ("tema", themes)) for key in keys])
    csv_out(output / "cobertura_lexica.csv", ["mes", "textos", "alguna_figura", "varias_figuras", "algun_tema"],
            [(m,total[m],multi[m,"alguna_figura"],multi[m,"varias_figuras"],multi[m,"algun_tema"]) for m in MONTHS])
    csv_out(output / "figuras_temas.csv", ["mes","figura","tema","coocurrencias","textos_figura","proporcion"], [
        (m,f,t,cross[m,f,t],counts[m,"figura",f],cross[m,f,t]/counts[m,"figura",f] if counts[m,"figura",f] else "")
        for m in MONTHS for f in figures for t in themes])


def analyze(audit, output):
    arcs = defaultdict(Counter)
    by_post = defaultdict(lambda: defaultdict(list))
    for row in read(audit / "events.csv"):
        if row["source"] == row["target"]:
            continue
        m, kind = row["month"], row["type"]
        pair = row["source"], row["target"]
        arcs[m, kind][pair] += 1
        arcs[m, "all"][pair] += 1
        by_post[m][row["post_id"]].append(pair)
    csv_out(output / "estructura.csv", ["mes","capa","nodos","arcos","eventos","componentes","fraccion_cm",
                                        "reciprocidad_arcos","fraccion_peso_10_destinatarios"],
            [(m,k,*structure(counts)) for (m,k),counts in sorted(arcs.items())])
    target = min(len(by_post[m]) for m in MONTHS)
    rng = np.random.default_rng(16)
    rarefaction, comparison = [], []
    partitions = {}
    for month in MONTHS:
        pool = sorted(by_post[month])
        trials = []
        for _ in range(120):
            sample = rng.choice(len(pool), target, replace=False)
            counts = Counter(pair for i in sample for pair in by_post[month][pool[i]])
            trials.append(structure(counts))
        for index, metric in ((0,"nodos"),(3,"componentes"),(4,"fraccion_cm"),(5,"reciprocidad_arcos")):
            lo, mid, hi = np.quantile(np.asarray(trials)[:,index], [0.05,0.5,0.95])
            rarefaction.append((month,metric,target,len(pool),float(lo),float(mid),float(hi)))
        undirected = Counter()
        for (a,b), w in arcs[month,"all"].items():
            undirected[tuple(sorted((a,b)))] += w
        nodes, edges, _ = main_component(undirected)
        labels, _, _ = greedy_modularity(len(nodes), edges)
        partitions[month] = dict(zip(nodes,labels))
    for previous, month in zip(MONTHS, MONTHS[1:]):
        a,b = partitions[previous],partitions[month]
        shared = sorted(a.keys() & b.keys())
        pairs = Counter((a[v],b[v]) for v in shared)
        left, right = Counter(a[v] for v in shared), Counter(b[v] for v in shared)
        best = max((n/(left[i]+right[j]-n) for (i,j),n in pairs.items()), default="")
        comparison.append((previous,month,len(shared),len(a),len(b),
                           adjusted_rand([a[v] for v in shared],[b[v] for v in shared]),best))
    csv_out(output / "volumen_igualado.csv", ["mes","metrica","publicaciones_muestra","publicaciones_elegibles",
                                             "p05","mediana","p95"], rarefaction)
    csv_out(output / "ari_modularidad.csv", ["mes_anterior","mes","compartidas","cm_anterior","cm_actual",
                                           "ari","max_jaccard_restringido"], comparison)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source","audit","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    analyze(args.audit,args.output)
    text_statistics(args.source,args.audit,args.output)
