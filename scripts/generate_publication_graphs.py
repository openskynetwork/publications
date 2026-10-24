#!/usr/bin/env python3
"""Generate OpenSky publication timeline and research-category plots."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


RAW_URL = "https://raw.githubusercontent.com/openskynetwork/publications/main/opensky-publications.bib"
DEFAULT_AS_OF = date.today().isoformat()


@dataclass(frozen=True)
class Entry:
    entry_type: str
    key: str
    fields: dict[str, str]


# Topic evidence only; data-source names and venue names never score.
CATEGORIES: list[tuple[str, dict[str, int]]] = [('Air Traffic Management',
  {'air traffic management': 10,
   'air traffic control': 10,
   'traffic flow': 9,
   'airspace': 6,
   'sectorization': 10,
   'runway': 6,
   'taxiway': 6,
   'arrival': 4,
   'arrivals': 4,
   'departure': 3,
   'airport': 2,
   'aerodrome': 3,
   'deconfliction': 10,
   'separation': 8,
   'conflict detection': 12,
   'conflict resolution': 12,
   'approach control': 12,
   'approach stability': 10,
   'traffic pattern': 9,
   'traffic patterns': 9,
   'pushback': 10,
   'holding': 7,
   'sequencing': 9,
   'capacity management': 10,
   'ground operations': 10,
   'operational': 3,
   'operations': 2,
   'flight delay': 8,
   'delays': 6,
   'air traffic monitoring': 10,
   'airports': 2,
   'aerodromes': 3,
   'air traffic distributions': 10,
   'collision risk': 10,
   'ground times': 9,
   'ground time': 9,
   'terminal space': 8,
   'airline networks': 6,
   'airline network': 6,
   'air traffic flow': 10,
   'traffic forecasting': 10,
   'air traffic density': 10,
   'air traffic prediction': 10,
   'arrival time': 9,
   'arrival times': 9}),
 ('Societal & Public-Service Applications',
  {'covid': 10,
   'covid 19': 10,
   'sars cov 2': 10,
   'pandemic': 10,
   'lockdown': 9,
   'epidemic': 10,
   'epidemics': 10,
   'disease': 10,
   'societal': 8,
   'geopolitical': 9,
   'economic': 6,
   'economics': 6,
   'mobility network': 8,
   'mobility networks': 8,
   'air mobility network': 10,
   'human mobility': 10,
   'diplomatic': 10,
   'military conflicts': 10,
   'geopolitics': 10,
   'air medical': 10,
   'firefighting': 9,
   'wildfire': 9,
   'wildfires': 9,
   'emergency': 8,
   'disaster': 8,
   'mobility': 3}),
 ('Surveillance Infrastructure & Data Quality',
  {'aircraft surveillance': 9,
   'air traffic surveillance': 9,
   'surveillance network': 9,
   'surveillance networks': 9,
   'surveillance data': 8,
   'receiver': 6,
   'receivers': 6,
   'reception': 9,
   'sensor network': 9,
   'sensor networks': 9,
   'data quality': 12,
   'data cleaning': 12,
   'data conditioning': 10,
   'conditioning': 7,
   'preprocessing': 10,
   'flight derivation': 12,
   'plateau detectors': 12,
   'ground bit': 10,
   'dropouts': 9,
   'qualifying public flight data': 12,
   'reproducible flight trajectories': 12,
   'volunteer': 8,
   'citizen science': 8,
   'user survey': 8,
   'node': 3,
   'uptime': 9,
   'transponder': 7,
   'transponders': 7,
   'crowdsourced multilateration': 12,
   'multi sensor': 7,
   'multi target tracking': 10,
   'reception probability': 12,
   'sensor coverage': 10,
   'surveillance coverage': 10,
   'network coverage': 9,
   'data coverage': 8,
   'ground station': 9,
   'ground stations': 9,
   'surveillance system': 9,
   'surveillance systems': 9,
   'tracking filter': 9,
   'trajectory preprocessing': 12}),
 ('Cybersecurity & Anomaly Detection',
  {'anomaly detection': 12,
   'anomalies': 10,
   'anomaly': 10,
   'intrusion detection': 12,
   'spoofing': 12,
   'jamming': 12,
   'interference': 8,
   'intrusion': 10,
   'cybersecurity': 12,
   'cyber security': 12,
   'attack': 10,
   'attacks': 10,
   'privacy preserving': 9,
   'secure': 8,
   'security': 9,
   'authentication': 12,
   'cryptographic': 12,
   'cryptography': 12,
   'encryption': 12,
   'post quantum': 12,
   'kinematic integrity': 12,
   'surveillance integrity': 12,
   'ghost record': 12,
   'ghost records': 12,
   'trajectory precursors': 9}),
 ('Aircraft Performance & Environmental Impact',
  {'fuel': 10,
   'fuel burn': 12,
   'fuel consumption': 12,
   'emissions': 10,
   'emission': 10,
   'contrail': 10,
   'contrails': 10,
   'climate': 10,
   'environmental': 9,
   'energy': 8,
   'energy transition': 12,
   'hydrogen': 9,
   'battery': 8,
   'electric': 6,
   'aircraft performance': 12,
   'take off weight': 12,
   'aircraft mass': 12,
   'weight estimation': 12,
   'mass estimation': 12,
   'drag coefficient': 12,
   'aircraft noise': 12,
   'noise': 8,
   'noise prediction': 12,
   'aeroacoustic': 12,
   'acoustic': 9,
   'auralization': 10,
   'sound': 6,
   'propulsion': 10,
   'drag polar': 12,
   'cirrus': 10,
   'aircraft design': 8,
   'performance models': 9,
   'performance model': 9}),
 ('Trajectory Prediction & Generation',
  {'trajectory prediction': 12,
   'trajectory predictions': 12,
   'trajectory reconstruction': 10,
   'trajectory generation': 12,
   'trajectory planning': 10,
   'generative models': 9,
   'vertical profiles': 9,
   'vertical profile': 9,
   'trajectories': 3,
   'trajectory': 2,
   'flight path prediction': 12,
   'eta prediction': 10,
   'landing trajectories': 9,
   'trajectory imputation': 12,
   'synthetic flight tracks': 10,
   'aviation scenario generation': 10,
   'geometric patterns': 6}),
 ('Navigation & Signal Processing',
  {'gnss': 12,
   'gps': 10,
   'navigation': 9,
   'signal processing': 10,
   'positioning': 9,
   'localization': 9,
   'localisation': 9,
   'multilateration': 9,
   'radio': 5,
   'radar': 8,
   'doppler': 8,
   'antenna': 7,
   'antennas': 7,
   'frequency': 5,
   'spectrum': 5,
   'rf': 5,
   'self localisation': 12,
   'self localization': 12,
   'synthetic aperture radar': 12,
   'aircraft to aircraft communication': 12,
   'air ground communication': 10,
   'communication networks': 8,
   'communications': 5}),
 ('Urban Air Mobility & Simulation',
  {'urban air mobility': 12,
   'uam': 12,
   'unmanned': 10,
   'uncrewed': 10,
   'uav': 10,
   'uavs': 10,
   'drone': 10,
   'drones': 10,
   'uas': 10,
   'evtol': 10,
   'evtols': 10,
   'vertiport': 10,
   'vertiports': 10,
   'low altitude': 8,
   'flight simulation': 7,
   'flight simulator': 7}),
 ('Data Tools & Visualisation',
  {'visualization': 10,
   'visualisation': 10,
   'visual analytics': 10,
   'data challenge': 10,
   'data generator': 8,
   'database': 9,
   'databases': 9,
   'data management': 9,
   'query': 8,
   'queries': 8,
   'event processing': 10,
   'data platform': 8,
   'software library': 9,
   'benchmark dataset': 9,
   'open dataset': 8,
   'graph engines': 10,
   'property graph': 8,
   'data asset': 8,
   'randomness': 5}),
 ('Machine Learning & Data Methods',
  {'machine learning': 4,
   'deep learning': 4,
   'neural': 3,
   'transformer': 3,
   'transformers': 3,
   'graph neural': 4,
   'gnn': 3,
   'autoencoder': 3,
   'autoencoders': 3,
   'reinforcement learning': 4,
   'llm': 3,
   'artificial intelligence': 4,
   'classification': 4,
   'clustering': 4,
   'learning': 2,
   'graph representation': 4,
   'link prediction': 4,
   'community detection': 4,
   'communities': 3,
   'tensor decomposition': 4,
   'category identification': 4,
   'behavioral segmentation': 4,
   'bibliometric': 4,
   'dynamic graph': 5,
   'dynamic graphs': 5,
   'temporal graph': 5,
   'temporal graphs': 5,
   'temporal networks': 5,
   'random graphs': 5,
   'preferential attachment': 5,
   'spectral embedding': 5,
   'gaussian process': 4,
   'predictive analytics': 5,
   'generative adversarial networks': 5,
   'graph engines': 5,
   'data analysis': 3})]

CATEGORY_NAMES = [name for name, _ in CATEGORIES] + ["Other"]


def read_bib(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def split_entries(text: str) -> list[str]:
    # Entry declarations are top-level lines. Using the next declaration as the
    # boundary keeps exports complete even when a legacy record has mismatched
    # braces or a missing comma after its citation key.
    starts = [match.start(1) for match in re.finditer(r"(?m)^[ \t]*(@[A-Za-z]+\s*[{(])", text)]
    return [text[start:end].strip() for start, end in zip(starts, starts[1:] + [len(text)])]


def parse_value(body: str, pos: int) -> tuple[str, int]:
    pos = skip_space(body, pos)
    if pos >= len(body):
        return "", pos

    if body[pos] == "{":
        depth = 0
        escaped = False
        start = pos + 1
        for idx in range(pos, len(body)):
            ch = body[idx]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return body[start:idx], idx + 1
    if body[pos] == '"':
        escaped = False
        start = pos + 1
        for idx in range(pos + 1, len(body)):
            ch = body[idx]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                return body[start:idx], idx + 1

    end = pos
    while end < len(body) and body[end] not in ",\n\r":
        end += 1
    return body[pos:end].strip(), end


def skip_space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def parse_entry(raw: str) -> Entry | None:
    header = re.match(r"@([A-Za-z]+)\s*[{(]\s*", raw)
    if not header:
        return None
    entry_type = header.group(1).lower()
    body = raw[header.end() :].rstrip()
    if body.endswith(("}", ")")):
        body = body[:-1]
    key_match = re.match(r"([^,\s]+)", body)
    if not key_match:
        return None
    key = key_match.group(1)
    pos = skip_space(body, key_match.end())
    if pos < len(body) and body[pos] == ",":
        pos += 1
    fields: dict[str, str] = {}

    while pos < len(body):
        pos = skip_space(body, pos)
        while pos < len(body) and body[pos] == ",":
            pos = skip_space(body, pos + 1)
        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", body[pos:])
        if not match:
            break
        name = match.group(1).lower()
        pos += match.end()
        value, pos = parse_value(body, pos)
        fields[name] = clean_latex(value)
        while pos < len(body) and body[pos] not in ",":
            if not body[pos].isspace():
                break
            pos += 1

    return Entry(entry_type=entry_type, key=key, fields=fields)


def clean_latex(value: str) -> str:
    replacements = {
        r"\&": "&",
        r"---": "-",
        r"--": "-",
        r"\_": "_",
        r"\'": "",
        r'\"': "",
        r"\`": "",
        r"\^": "",
        r"\~": "",
    }
    cleaned = value
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"[{}]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_bib(text: str) -> list[Entry]:
    entries = []
    for raw in split_entries(text):
        entry = parse_entry(raw)
        if entry and entry.fields.get("year"):
            entries.append(entry)
    return entries


def entry_text(entry: Entry) -> str:
    """Only content-bearing metadata; venue/publisher names are not topic evidence."""
    return " ".join(entry.fields.get(name, "") for name in ("title", "keywords", "abstract"))


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def topic_scores(text: str) -> list[tuple[str, int, str]]:
    normalized = normalize_text(text)
    ranked = []
    for category, keywords in CATEGORIES:
        # Prefer specific phrases; do not score their component words again.
        if category == "Surveillance Infrastructure & Data Quality" and not re.search(
            r"\b(ads b|adsb|ads c|mode s|opensky|multilateration|aircraft surveillance|air traffic surveillance|flight derivation|flight data|flight trajectories|trajectory preprocessing)\b",
            normalized,
        ):
            continue
        occupied: set[int] = set()
        matches = []
        for phrase, weight in sorted(keywords.items(), key=lambda item: (-len(item[0].split()), -item[1], item[0])):
            pattern = r"(?<!\w)" + re.escape(normalize_text(phrase)) + r"(?!\w)"
            counted = False
            for match in re.finditer(pattern, normalized):
                span = set(range(match.start(), match.end()))
                if not occupied.intersection(span):
                    if not counted:
                        matches.append((phrase, weight))
                        counted = True
                    occupied.update(span)
        if matches:
            ranked.append((category, sum(weight for _, weight in matches), "; ".join(phrase for phrase, _ in matches)))
    return sorted(ranked, key=lambda row: -row[1])  # Stable category-order tie break.


def classify(text: str) -> tuple[str, int, str]:
    ranked = topic_scores(text)
    # Select an application if evidence exists, retaining all scores for auditing.
    topical = [r for r in ranked if r[0] != "Machine Learning & Data Methods" and r[1] >= 5]
    return topical[0] if topical else ranked[0] if ranked else ("Other", 0, "")


def source_mentions(text: str) -> str:
    """Mention tags, not a verification of which datasets were used."""
    normalized = normalize_text(text)
    return "; ".join(label for label, pattern in (
        ("OpenSky", r"\bopensky\b"), ("ADS-B", r"\bads ?b\b"),
        ("ADS-C", r"\bads ?c\b"), ("Mode S", r"\bmode s\b")
    ) if re.search(pattern, normalized))


def year_for(entry: Entry) -> int | None:
    match = re.search(r"\d{4}", entry.fields.get("year", ""))
    return int(match.group(0)) if match else None


def write_counts_csv(path: Path, years: list[int], yearly_counts: dict[int, Counter[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["year", *CATEGORY_NAMES])
        for year in years:
            writer.writerow([year, *[yearly_counts[year].get(category, 0) for category in CATEGORY_NAMES]])


def write_assignments_csv(path: Path, assignments: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["key", "year", "category", "score", "matched_terms", "runner_up", "score_margin", "needs_review", "source_mentions", "all_topic_scores", "method_terms", "title", "venue"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(assignments)


def set_style(plt) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#222222",
            "axes.linewidth": 1.1,
            "axes.titlecolor": "#303030",
            "axes.labelcolor": "#222222",
            "xtick.color": "#303030",
            "ytick.color": "#303030",
            "font.size": 12,
            "axes.titlesize": 22,
            "axes.labelsize": 14,
            "legend.fontsize": 11,
        }
    )


def parse_as_of(value: str) -> date:
    match = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", value)
    if not match:
        raise argparse.ArgumentTypeError("expected YYYY-MM or YYYY-MM-DD")
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def display_year(year: int, as_of: date) -> str:
    if year == as_of.year:
        return f"{year}\n{as_of:%d %b %Y}"
    if year > as_of.year:
        return f"{year}\nforthcoming"
    return str(year)


def coverage_note(years: list[int], as_of: date) -> str:
    notes = [f"Bibliography snapshot: {as_of:%d %B %Y}", "counts reflect bibliography entries"]
    if any(year > as_of.year for year in years):
        notes.append("future years contain forthcoming publications")
    return "; ".join(notes)


def add_coverage_note(ax, years: list[int], as_of: date) -> None:
    note = coverage_note(years, as_of)
    if note:
        ax.text(0.5, 1.01, note, transform=ax.transAxes, ha="center", va="bottom", fontsize=11, color="#555555")


def plot_yearly(path: Path, yearly_totals: Counter[int], as_of: date) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    set_style(plt)
    years = sorted(yearly_totals)
    values = [yearly_totals[year] for year in years]

    fig, ax = plt.subplots(figsize=(13.5, 6.3), dpi=160)
    ax.bar(years, values, color="#f6a400", edgecolor="#d88b00", linewidth=0.9, width=0.72)
    ax.set_title(f"OpenSky Bibliography Entries over Time ({years[0]}-{years[-1]})", pad=28)
    add_coverage_note(ax, years, as_of)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Bibliography Entries")
    ax.grid(True, linestyle="--", linewidth=0.7, color="#cfcfcf")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xticks(years)
    ax.set_xticklabels([display_year(year, as_of) for year in years], rotation=45, ha="right")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_categories(path: Path, years: list[int], yearly_counts: dict[int, Counter[str]], as_of: date) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    set_style(plt)
    colors = dict(zip(CATEGORY_NAMES, [
        "#332288", "#0077BB", "#008877", "#882255", "#117733",
        "#CC6677", "#AA4499", "#999933", "#661100", "#6699CC", "#666666"
    ]))
    recent_years = [year for year in years if year <= as_of.year][-2:]
    recent_totals = Counter()
    for year in recent_years:
        for category, count in yearly_counts[year].items():
            if category not in {"Other", "Cybersecurity & Anomaly Detection"}:
                recent_totals[category] += count
    highlighted = {category for category, _ in recent_totals.most_common(4)}
    highlighted.add("Cybersecurity & Anomaly Detection")

    fig, ax = plt.subplots(figsize=(15.5, 7.4), dpi=160)
    for category_index, category in enumerate(CATEGORY_NAMES):
        values = [yearly_counts[year].get(category, 0) if year <= as_of.year else None for year in years]
        is_highlighted = category in highlighted
        linewidth = 3.2 if is_highlighted else 1.35
        marker = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*"][category_index]
        alpha = 1.0
        ax.plot(
            years,
            values,
            label=category,
            color=colors[category],
            linestyle=["-", "--", "-.", ":"][category_index % 4],
            linewidth=linewidth,
            marker=marker,
            markersize=5,
            alpha=alpha,
        )
        future_points = [
            (year, yearly_counts[year].get(category, 0))
            for year in years
            if year > as_of.year and yearly_counts[year].get(category, 0) > 0
        ]
        if future_points:
            x_offset = (category_index - (len(CATEGORY_NAMES) - 1) / 2) * 0.025
            ax.scatter(
                [year + x_offset for year, _ in future_points],
                [count for _, count in future_points],
                facecolors="white",
                edgecolors=colors[category],
                linewidths=2 if is_highlighted else 1.4,
                s=42 if is_highlighted else 30,
                alpha=max(alpha, 0.7),
                zorder=4,
            )

    ax.set_title(f"OpenSky Bibliography Entries by Research Category ({years[0]}-{years[-1]})", pad=28)
    add_coverage_note(ax, years, as_of)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Bibliography Entries")
    ax.grid(True, linestyle="--", linewidth=0.7, color="#cfcfcf")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xticks(years)
    ax.set_xticklabels([display_year(year, as_of) for year in years], rotation=45, ha="right")
    ax.set_ylim(bottom=0)
    ax.text(0, -0.36, "Topics inferred from titles/keywords/abstracts; one category per entry. Ambiguous cases flagged in CSV.", transform=ax.transAxes, fontsize=10, color="#444444")
    ax.legend(title="Category", bbox_to_anchor=(1.01, 1), loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bib", default="opensky-publications.bib", help=f"BibTeX file path. Source URL: {RAW_URL}")
    parser.add_argument("--outdir", default="output", help="Directory for generated plots and CSVs.")
    parser.add_argument(
        "--as-of",
        type=parse_as_of,
        default=parse_as_of(DEFAULT_AS_OF),
        metavar="YYYY-MM-DD",
        help=f"Snapshot date for labels and the maximum included publication year (default: {DEFAULT_AS_OF}).",
    )
    args = parser.parse_args()

    bib_path = Path(args.bib)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    entries = parse_bib(read_bib(bib_path))
    yearly_totals: Counter[int] = Counter()
    yearly_counts: dict[int, Counter[str]] = defaultdict(Counter)
    assignments: list[dict[str, object]] = []

    for entry in entries:
        year = year_for(entry)
        if year is None or year > args.as_of.year:
            continue
        text = entry_text(entry)
        category, score, terms = classify(text)
        ranked = topic_scores(text)
        runner_up = next((row for row in ranked if row[0] != category), ("", 0, ""))
        margin = score - runner_up[1]
        venue = entry.fields.get("booktitle") or entry.fields.get("journal") or entry.fields.get("school") or ""
        yearly_totals[year] += 1
        yearly_counts[year][category] += 1
        assignments.append(
            {
                "key": entry.key,
                "year": year,
                "category": category,
                "score": score,
                "matched_terms": terms,
                "runner_up": runner_up[0],
                "score_margin": margin,
                "needs_review": category == "Other" or score < 5 or margin <= 2,
                "source_mentions": source_mentions(text),
                "all_topic_scores": json.dumps({r[0]: r[1] for r in ranked}, ensure_ascii=False),
                "method_terms": next((r[2] for r in ranked if r[0] == "Machine Learning & Data Methods"), ""),
                "title": entry.fields.get("title", ""),
                "venue": venue,
            }
        )

    years = list(range(min(yearly_totals), max(yearly_totals) + 1))
    write_counts_csv(outdir / "publications_by_field_per_year.csv", years, yearly_counts)
    write_assignments_csv(outdir / "publication_field_assignments.csv", assignments)
    plot_yearly(outdir / "publications_per_year.png", yearly_totals, args.as_of)
    plot_categories(outdir / "publications_by_field_per_year.png", years, yearly_counts, args.as_of)

    print(f"Parsed {len(entries)} entries from {bib_path}; included {len(assignments)} through publication year {args.as_of.year}")
    print(f"Wrote {outdir / 'publications_per_year.png'}")
    print(f"Wrote {outdir / 'publications_by_field_per_year.png'}")
    print(f"Wrote {outdir / 'publications_by_field_per_year.csv'}")
    print(f"Wrote {outdir / 'publication_field_assignments.csv'}")


if __name__ == "__main__":
    main()
