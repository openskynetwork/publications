#!/usr/bin/env python3
"""Generate OpenSky publication timeline and research-category plots."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path


RAW_URL = "https://raw.githubusercontent.com/openskynetwork/publications/main/opensky-publications.bib"
DEFAULT_AS_OF = "2026-09"


@dataclass(frozen=True)
class Entry:
    entry_type: str
    key: str
    fields: dict[str, str]


CATEGORIES: list[tuple[str, dict[str, int]]] = [
    (
        "Air Traffic Management",
        {
            "air traffic management": 6,
            "air traffic control": 6,
            "traffic flow": 5,
            "airspace": 5,
            "sectorization": 5,
            "terminal": 4,
            "runway": 4,
            "taxiway": 4,
            "arrival": 4,
            "departure": 4,
            "airport": 4,
            "deconfliction": 4,
            "separation": 4,
            "collision risk": 4,
            "controller": 3,
            "enroute": 3,
            "route choice": 3,
            "routing": 2,
            "capacity": 2,
            "holding": 2,
            "operation": 1,
        },
    ),
    (
        "COVID-19 & Societal Impact",
        {
            "covid": 8,
            "sars-cov-2": 8,
            "pandemic": 7,
            "lockdown": 6,
            "epidemic": 5,
            "omicron": 5,
            "delta variant": 5,
            "alpha variant": 5,
            "societal": 3,
            "geopolitical": 2,
            "conflict": 2,
        },
    ),
    (
        "Crowdsourced Surveillance & Control",
        {
            "ads-b": 7,
            "adsb": 7,
            "mode s": 6,
            "opensky": 4,
            "surveillance": 6,
            "flight tracking": 5,
            "transponder": 5,
            "telemetry": 4,
            "radar": 4,
            "receiver": 3,
            "crowdsourced": 3,
            "data cleaning": 3,
            "tracking data": 3,
            "aircraft tracking": 3,
        },
    ),
    (
        "Cybersecurity & Anomaly Detection",
        {
            "anomaly detection": 12,
            "anomalies": 10,
            "anomaly": 10,
            "intrusion detection": 11,
            "spoofing": 10,
            "spoof": 10,
            "jamming": 10,
            "interference": 9,
            "intrusion": 9,
            "cybersecurity": 9,
            "cyber security": 9,
            "attack": 8,
            "privacy-preserving": 9,
            "secure": 8,
            "security": 8,
            "resilient": 5,
            "resilience": 5,
        },
    ),
    (
        "Machine Learning & Noise Analysis",
        {
            "aircraft noise": 8,
            "noise": 7,
            "aeroacoustic": 7,
            "acoustic": 7,
            "auralization": 7,
            "sound": 5,
            "machine learning": 4,
            "deep learning": 4,
            "neural": 3,
            "transformer": 3,
            "graph neural": 3,
            "gnn": 3,
            "autoencoder": 3,
            "reinforcement learning": 3,
            "llm": 3,
            "artificial intelligence": 3,
            "data-driven": 2,
            "classification": 2,
            "clustering": 2,
            "learning": 1,
        },
    ),
    (
        "Navigation & Signal Processing",
        {
            "gnss": 8,
            "gps": 8,
            "navigation": 7,
            "signal processing": 7,
            "signal": 5,
            "positioning": 5,
            "localization": 5,
            "multilateration": 5,
            "radio": 4,
            "antenna": 4,
            "communication": 3,
            "frequency": 3,
            "sensor": 3,
            "spectrum": 3,
            "rf": 3,
        },
    ),
    (
        "Trajectory Prediction",
        {
            "trajectory prediction": 8,
            "trajectory reconstruction": 8,
            "flight trajectory": 7,
            "trajectories": 6,
            "trajectory": 6,
            "flight path": 5,
            "path prediction": 5,
            "eta prediction": 5,
            "prediction": 4,
            "forecast": 4,
            "forecasting": 4,
            "reconstructing": 4,
            "reconstruction": 4,
            "vertical profile": 3,
        },
    ),
    (
        "Urban Air Mobility & Simulation",
        {
            "urban air mobility": 8,
            "uam": 8,
            "unmanned": 7,
            "uav": 7,
            "drone": 7,
            "uas": 6,
            "evtols": 6,
            "evtol": 6,
            "vertiport": 6,
            "low-altitude": 5,
            "simulation": 4,
            "simulator": 4,
            "scenario generation": 3,
            "aerial access": 3,
        },
    ),
]

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
    primary_fields = [
        "title",
        "keywords",
        "abstract",
    ]
    venue_fields = [
        "booktitle",
        "journal",
        "series",
        "publisher",
        "organization",
        "school",
        "institution",
        "note",
    ]
    primary = " ".join(entry.fields.get(name, "") for name in primary_fields)
    venue = " ".join(entry.fields.get(name, "") for name in venue_fields)
    return " ".join([primary, primary, venue])


def classify(text: str) -> tuple[str, int, str]:
    normalized = re.sub(r"\s+", " ", text.lower())
    scores: dict[str, int] = {}
    matched_terms: dict[str, list[str]] = {}
    for category, keywords in CATEGORIES:
        total = 0
        terms = []
        for keyword, weight in keywords.items():
            if keyword in normalized:
                total += weight
                terms.append(keyword)
        if total:
            scores[category] = total
            matched_terms[category] = terms

    if not scores:
        return "Other", 0, ""

    priority = {name: idx for idx, (name, _) in enumerate(CATEGORIES)}
    category = max(scores, key=lambda name: (scores[name], -priority[name]))
    return category, scores[category], "; ".join(matched_terms[category])


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
        fieldnames = ["key", "year", "category", "score", "matched_terms", "title", "venue"]
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
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise argparse.ArgumentTypeError("expected YYYY-MM")
    try:
        return date(int(match.group(1)), int(match.group(2)), 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def display_year(year: int, as_of: date) -> str:
    if year == as_of.year:
        return f"{year}\nYTD"
    if year > as_of.year:
        return f"{year}\nforthcoming"
    return str(year)


def coverage_note(years: list[int], as_of: date) -> str:
    notes = [f"Data through {as_of:%B %Y}", "counts reflect bibliography entries"]
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
    colors = {
        "Air Traffic Management": "#f6a400",
        "COVID-19 & Societal Impact": "#ffc7a9",
        "Crowdsourced Surveillance & Control": "#f53255",
        "Cybersecurity & Anomaly Detection": "#ffb7e8",
        "Machine Learning & Noise Analysis": "#31b9ee",
        "Navigation & Signal Processing": "#14c5ba",
        "Trajectory Prediction": "#9ee8bd",
        "Urban Air Mobility & Simulation": "#d8ef9c",
        "Other": "#8f8f8f",
    }
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
        marker = "o" if is_highlighted else None
        alpha = 1.0 if is_highlighted else 0.38
        ax.plot(
            years,
            values,
            label=category,
            color=colors[category],
            linestyle="-" if is_highlighted else "--",
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
        metavar="YYYY-MM",
        help=f"Data snapshot month used for YTD/forthcoming labels (default: {DEFAULT_AS_OF}).",
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
        if year is None:
            continue
        text = entry_text(entry)
        category, score, terms = classify(text)
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
                "title": entry.fields.get("title", ""),
                "venue": venue,
            }
        )

    years = list(range(min(yearly_totals), max(yearly_totals) + 1))
    write_counts_csv(outdir / "publications_by_field_per_year.csv", years, yearly_counts)
    write_assignments_csv(outdir / "publication_field_assignments.csv", assignments)
    plot_yearly(outdir / "publications_per_year.png", yearly_totals, args.as_of)
    plot_categories(outdir / "publications_by_field_per_year.png", years, yearly_counts, args.as_of)

    print(f"Parsed {len(entries)} entries from {bib_path}")
    print(f"Wrote {outdir / 'publications_per_year.png'}")
    print(f"Wrote {outdir / 'publications_by_field_per_year.png'}")
    print(f"Wrote {outdir / 'publications_by_field_per_year.csv'}")
    print(f"Wrote {outdir / 'publication_field_assignments.csv'}")


if __name__ == "__main__":
    main()
