!pip install langchain-typesafe

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from langchain_typesafe import Choice, Noul, Score, TypeSafeClassifier

import pandas as pd
df = pd.read_excel(".xlsx")
df.head()

import argparse
import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

import pandas as pd
from langchain_typesafe import Choice, Noul, TypeSafeClassifier


REQUIRED_COLUMNS = [
    "query",
    "url",
    "Title 1",
    "Meta Description 1",
    "H1-1",
]

OUTPUT_COLUMNS = [
    "query",
    "url_a",
    "segment_a",
    "url_b",
    "segment_b",
    "cannibalization_probability",
    "primary_page",
    "severity",
]


@dataclass
class Page:
    query: str
    url: str
    title: str
    meta: str
    h1: str
    segment: str = ""


def load_pages(path: str) -> dict:
    """
    Read all potential sheets/tabs from an Excel file (e.g. branded, non-brand)
    or a CSV file, and group Page rows by query.
    """
    by_query = defaultdict(list)

    if path.endswith(".xlsx"):
        sheets = pd.read_excel(
            path,
            sheet_name=None
        )
    else:
        sheets = {
            "default": pd.read_csv(path)
        }

    for sheet_name, df in sheets.items():

        missing = [
            col
            for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing:
            sys.exit(
                f"Sheet '{sheet_name}' is missing columns: {missing}"
            )

        for _, row in df.iterrows():

            page = Page(
                query=(
                    str(row["query"])
                    if pd.notna(row["query"])
                    else ""
                ),
                url=(
                    str(row["url"])
                    if pd.notna(row["url"])
                    else ""
                ),
                title=(
                    str(row["Title 1"])
                    if pd.notna(row["Title 1"])
                    else ""
                ),
                meta=(
                    str(row["Meta Description 1"])
                    if pd.notna(row["Meta Description 1"])
                    else ""
                ),
                h1=(
                    str(row["H1-1"])
                    if pd.notna(row["H1-1"])
                    else ""
                ),
                segment=sheet_name,
            )

            by_query[page.query].append(page)

    return by_query


def build_state(
    query: str,
    a: Page,
    b: Page
) -> str:

    return (
        f"Target query: {query}\n\n"

        f"Page A: {a.url}\n"
        f"Title: {a.title}\n"
        f"Meta description: {a.meta}\n"
        f"H1: {a.h1}\n\n"

        f"Page B: {b.url}\n"
        f"Title: {b.title}\n"
        f"Meta description: {b.meta}\n"
        f"H1: {b.h1}"
    )


def build_classifier() -> TypeSafeClassifier:

    if "TYPESAFE_API_KEY" not in os.environ:
        sys.exit(
            "Set TYPESAFE_API_KEY as an environment variable "
            "before running this script."
        )

    return TypeSafeClassifier()


def evaluate_pair(
    classifier: TypeSafeClassifier,
    query: str,
    a: Page,
    b: Page
) -> dict:

    response = classifier.invoke(
        {
            "state": build_state(query, a, b),

            "questions": {

                #CANNIBALISATION RISK
              
                "cannibalization_risk": Noul(
                    instructions=(
                        "Page A and Page B both realistically target "
                        "the same search query and would compete against "
                        "each other in the same SERP, rather than serving "
                        "clearly distinct search intents."
                    )
                ),

                # PRIMARY PAGE
              
                "primary_page": Choice(
                    options=[
                        "page_a",
                        "page_b",
                        "unclear"
                    ],

                    instructions=(
                        "Which page better matches the target query's "
                        "intent and should be treated as the "
                        "canonical/primary page for it, if "
                        "consolidation were needed?"
                    ),

                    criteria={
                        "page_a": (
                            "Page A better matches the query intent."
                        ),

                        "page_b": (
                            "Page B better matches the query intent."
                        ),

                        "unclear": (
                            "It is unclear which page is better."
                        ),
                    }
                ),

                # SEVERITY
                # Output must be a categorical value: low / medium / high.

                "risk_severity": Choice(
                    options=[
                        "low",
                        "medium",
                        "high"
                    ],

                    instructions=(
                        "Classify the severity of the cannibalization "
                        "risk between these two pages for the given query."
                    ),

                    criteria={
                        "low": (
                            "Low cannibalization risk. The pages have "
                            "clearly distinct search intents or are "
                            "unlikely to compete directly in the SERP."
                        ),

                        "medium": (
                            "Medium cannibalization risk. The pages have "
                            "meaningfully overlapping search intent and "
                            "may compete against each other in the SERP."
                        ),

                        "high": (
                            "High cannibalization risk. The pages strongly "
                            "target the same search intent and are likely "
                            "to compete directly against each other in "
                            "the SERP."
                        ),
                    }
                ),
            },
        }
    )
  
    # Extract the categorical severity directly from Choice

    severity = response.choices[
        "risk_severity"
    ].choice

    return {
        "query": query,

        "url_a": a.url,
        "segment_a": a.segment,

        "url_b": b.url,
        "segment_b": b.segment,

        "cannibalization_probability": round(
            response.nouls[
                "cannibalization_risk"
            ].noul,
            4
        ),

        "primary_page": response.choices[
            "primary_page"
        ].choice,

        "severity": severity,
    }


def run(
    in_path: str,
    out_path: str,
    min_probability: float = 0.0
) -> None:

    classifier = build_classifier()

    by_query = load_pages(in_path)

    results = []

    total_pairs = 0

    for query, pages in by_query.items():

        if len(pages) < 2:
            continue

        for a, b in combinations(pages, 2):

            total_pairs += 1

            result = evaluate_pair(
                classifier,
                query,
                a,
                b
            )

            if (
                result["cannibalization_probability"]
                >= min_probability
            ):
                results.append(result)

    # Write results

    with open(
        out_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f_out:

        writer = csv.DictWriter(
            f_out,
            fieldnames=OUTPUT_COLUMNS
        )

        writer.writeheader()

        writer.writerows(results)

    print(
        f"Evaluated {total_pairs} page pairs across "
        f"{len(by_query)} queries."
    )

    print(
        f"Wrote {len(results)} results to {out_path}"
    )


if __name__ == "__main__":

    input_excel = (
        "/content/df cruise cannibilisation.xlsx"
    )

    output_csv = (
        "cannibalization_results.csv"
    )

    run(
        input_excel,
        output_csv,
        min_probability=0.0
    )
