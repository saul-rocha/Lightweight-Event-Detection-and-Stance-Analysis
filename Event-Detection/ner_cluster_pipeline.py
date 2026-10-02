r"""
ner_cluster_pipeline.py
=======================

Single pipeline to *extract NER*, *normalize* it and *group operations* from
video metadata (title, description and optionally transcript). It keeps the
*original grouping logic* (+/- 15-day time windows, creating suffixes -2, -3…
when needed), adds a *cache* for the expensive step (NER), improves the
*terminal experience* (clean console + progress bar) and saves **detailed
logs to a file**.

----------------------------------------------------------------------
GOAL
----------------------------------------------------------------------
1) Identify entities (LOC, PER, EVENT, DATE, LAW and the spaCy "OPERACAO" rule).
2) Clean them (noise removal only, without changing the decision logic).
3) Assign one operation label per row, reusing time windows.
4) Write a final TSV/CSV with all original columns + operation_ner.

----------------------------------------------------------------------
HOW IT WORKS (overview)
----------------------------------------------------------------------
- Reads the input file.
- Initializes the models:
  - Hugging Face: Babelscape/wikineural-multilingual-ner
  - spaCy: pt_core_news_lg + EntityRuler ("OPERACAO" rule)
- Extracts NER from titulo and descricao (and transcribedText, if present).
- Saves a *cache* outputs/cache/ner_results_<year-tag>.tsv (reused with --use-cache).
- *Normalizes* the NER columns (lowercase, accent/punctuation removal; cleaning only).
- *Groups* by time windows (+/- 15 days) and assigns operation_ner.
- Writes the output and prints a friendly *summary* to the console.

----------------------------------------------------------------------
INPUT (CSV/TSV file)
----------------------------------------------------------------------
Minimum expected columns:
- id_video (string)
- titulo (string)       — video title
- descricao (string)    — video description
- data_postagem (datetime) — publication date

Useful optional columns:
- canal (string, channel name; enables the broadcaster-brand filter)
- operation (reference event label, used for evaluation)
- transcribedText (string, to apply NER to transcripts)

Input/output separator configurable with --sep (default: \t).

----------------------------------------------------------------------
OUTPUT (final CSV/TSV file)
----------------------------------------------------------------------
- All original input columns.
- + operation_ner (string) — label assigned by the grouping.
- If you use the cache as a working step, the cache file also contains:
  - ner_titulo, ner_descricao, (ner_transcribedText, if present)
  - all_ners (intermediate column used to identify generic entities)

----------------------------------------------------------------------
DIRECTORIES
----------------------------------------------------------------------
Default paths are relative to this script's folder:
- data/     : input (filled in by whoever reproduces the work; see README.md).
- outputs/  : final output, NER cache and logs (created automatically).

----------------------------------------------------------------------
CLI PARAMETERS
----------------------------------------------------------------------
--input <str>                : Input CSV/TSV path (default: data/videos.tsv).
--year-tag <str>             : Label used in the cache file name (default: "all").
--final-output <str>         : Final file path (default: outputs/operations_ner.tsv).
--cache-dir <str>            : Cache and log directory (default: outputs/cache).
--use-cache                  : Reuse the cache if compatible.
--force                      : Ignore the cache and redo NER extraction.
--sep <str>                  : I/O separator (default: "\t").
--log-level {DEBUG..}        : Log level (file). The console is clean by default.
--check-setup                : Only validate environment/models and exit.
--summary-head-percent <int> : Percentage (1–99) used in the summary (default: 20).
--version                    : Show the script version.


----------------------------------------------------------------------
ENVIRONMENT AND INSTALLATION
----------------------------------------------------------------------

1- *Create and activate a virtual environment (venv)*

Windows (PowerShell):
---------------------
python -m venv venv
.\venv\Scripts\Activate.ps1

Linux/macOS (bash/zsh):
-----------------------
python3 -m venv venv
source venv/bin/activate

2- *Install the dependencies*
------------------------------
With the environment active, run:
pip install -r requirements.txt

> requirements.txt contains all required libraries
> (pandas, torch, transformers, spacy, tqdm, the spaCy model, etc.)

3- *Download and check the spaCy model* (already covered by requirements.txt)
----------------------------------------
python -m spacy download pt_core_news_lg
or
pip install "https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.8.0/pt_core_news_lg-3.8.0-py3-none-any.whl"

Then confirm everything is fine:
python -c "import spacy; nlp = spacy.load('pt_core_news_lg'); print('Model OK:', nlp.meta.get('lang'), nlp.meta.get('name'))"

> Expected output:
> Model OK: pt core_news_lg

4- *(Optional) GPU / CUDA*
-----------------------------
If you have an NVIDIA GPU and want to speed up NER extraction:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

Check whether PyTorch detects your GPU:
python -c "import torch; print(torch.cuda.is_available())"
# True → GPU ready
# False → CPU will be used normally

----------------------------------------------------------------------
USAGE EXAMPLES
----------------------------------------------------------------------
PowerShell (Windows)
--------------------
# Running with the default directories (data/videos.tsv -> outputs/operations_ner.tsv)
python .\\ner_cluster_pipeline.py --use-cache --log-level INFO

# Forcing NER to be redone (ignores the cache)
python .\\ner_cluster_pipeline.py `
  --input ".\\data\\videos.tsv" `
  --year-tag "all" `
  --final-output ".\\outputs\\operations_ner.tsv" `
  --force --log-level INFO

# Only check environment and models
python .\\ner_cluster_pipeline.py --check-setup

Bash (Linux/macOS)
------------------
python ./ner_cluster_pipeline.py \
  --input "./data/videos.tsv" \
  --year-tag "all" \
  --final-output "./outputs/operations_ner.tsv" \
  --use-cache --log-level INFO

----------------------------------------------------------------------
PROGRESS AND LOGS
----------------------------------------------------------------------
- *Console*: short phase messages + **progress bar** (tqdm) during NER extraction.
- *Log file*: outputs/cache/logs_<year-tag>.log with details (level from --log-level).
- Transformers with reduced verbosity (errors only).

----------------------------------------------------------------------
EXIT CODES
----------------------------------------------------------------------
0  : Success
2  : Input validation failed
3  : --check-setup failed (environment/models)
4  : Error reading the full file
5  : Failed to initialize models
6  : Normalization error / empty DataFrame
130: Interrupted by the user (Ctrl+C)

----------------------------------------------------------------------
REQUIREMENTS
----------------------------------------------------------------------
Python 3.12+ (required: the code uses f-strings with backslashes, 3.12 syntax)
pip install:
  - pandas
  - torch (CPU or GPU, depending on your environment)
  - transformers
  - spacy
  - tqdm   (optional, for the progress bar)

Models:
  - spaCy pt:  pt_core_news_lg
    * If downloading via python -m spacy download pt_core_news_lg fails,
      install the official Explosion wheel (compatible with your spaCy version).

GPU (optional):
  - If CUDA is available, the HF pipeline uses the GPU automatically.
----------------------------------------------------------------------
TROUBLESHOOTING
----------------------------------------------------------------------
- spaCy error loading pt_core_news_lg:
  * Install via: python -m spacy download pt_core_news_lg
  * or via wheel: pip install https://github.com/explosion/spacy-models/.../pt_core_news_lg-<ver>-py3-none-any.whl
- Progress bar does not show up:
  * Make sure tqdm is installed. Without tqdm the script runs normally, just without the bar.
- Too many console messages:
  * The console is intentionally clean; details are in outputs/cache/logs_<year-tag>.log.

----------------------------------------------------------------------
LICENSE
----------------------------------------------------------------------
This script uses third-party models (Hugging Face / spaCy) with their own
licenses. Check the model licenses before any commercial use.

"""

from __future__ import annotations

import warnings
import argparse
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union, cast, TypedDict

import pandas as pd
import numpy as np
import torch
import bisect
import unicodedata
import re

import spacy
from spacy.pipeline import EntityRuler

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
from transformers.pipelines import TokenClassificationPipeline
from transformers.utils import logging as hf_logging

# Silence Transformers noise on the console
hf_logging.set_verbosity_error()

# Silence the Period-with-timezone warning
warnings.filterwarnings(
    "ignore",
    message="Converting to PeriodArray/Index representation will drop timezone information.",
    category=UserWarning
)

# Progress bar (optional)
try:
    from tqdm import tqdm  # type: ignore[import-untyped]
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False

version = "0.4.0-v4-180926-cenario-real"

# Default directories, relative to the script folder (independent of the cwd).
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


# =========================
# Logging / CLI utilities
# =========================

def setup_logging(level: str, log_file: str) -> Tuple[logging.Logger, logging.Logger]:
    """
    Returns (APP_LOG, UX_LOG):
      - APP_LOG: use .debug/.info across the WHOLE pipeline (goes to the file).
      - UX_LOG : use only for user-friendly console messages.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)  # capture everything and route per handler

    # file (detailed)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    # console (clean)
    ch = logging.StreamHandler(sys.stdout)

    class OnlyUX(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.name == "UX"

    ch.addFilter(OnlyUX())
    ch.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(ch)

    app_log = logging.getLogger("APP")
    ux_log = logging.getLogger("UX")

    ux_log.info(f"ner_cluster {version}")
    ux_log.info(f"[full logs] {log_file}")

    return app_log, ux_log


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ner_cluster_pipeline",
        description="Single pipeline to extract NER, normalize it and group operations from videos.",
    )
    parser.add_argument(
        "--input", default=str(DATA_DIR / "videos.tsv"),
        help="Input CSV/TSV (default: data/videos.tsv).",
    )
    parser.add_argument("--year-tag", default="all", help="Label used for the cache (default: all).")
    parser.add_argument(
        "--final-output", default=str(OUTPUT_DIR / "operations_ner.tsv"),
        help="Final TSV/CSV file (default: outputs/operations_ner.tsv).",
    )
    parser.add_argument(
        "--cache-dir", default=str(OUTPUT_DIR / "cache"),
        help="Cache and log directory (default: outputs/cache).",
    )
    parser.add_argument("--use-cache", action="store_true", help="Reuse the cache if compatible.")
    parser.add_argument("--force", action="store_true", help="Redo everything, ignoring the cache.")
    parser.add_argument("--sep", default="\t", help=r"I/O separator (default: '\t').")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (the file gets full detail; the console stays clean).",
    )
    parser.add_argument("--check-setup", action="store_true", help="Validate the setup and exit.")
    parser.add_argument(
        "--window-days", type=int, default=15,
        help="Time-window radius in days (default: 15, as in the original HT).",
    )
    parser.add_argument(
        "--title-share-cap", type=float, default=0.12,
        help="Ceiling of the boilerplate cut: a key whose title share is below "
             "this and whose df is high is outlet noise (default: 0.12).",
    )
    parser.add_argument(
        "--generic-max-burst", type=float, default=0.25,
        help="A generic-entity candidate that concentrates this fraction of its own "
             "occurrences in a ±15-day window counts as evidence again "
             "(default: 0.25). Background vocabulary has no burst.",
    )
    parser.add_argument(
        "--core-support", type=float, default=0.0,
        help="Minimum fraction of a group's members that must mention the shared "
             "entity for the video to join (default: 0.50). Prevents the "
             "group from drifting into another event.",
    )
    parser.add_argument(
        "--max-span-days", type=int, default=0,
        help="Maximum span of a group, in days (default: 30 = 2x the window). "
             "Prevents a group from drifting indefinitely, 15 days at a time.",
    )
    parser.add_argument(
        "--ablate", default="",
        help="Comma-separated list of improvements to disable, for ablation: "
             "tag, boilerplate, alias, signature, span, relabel, brand, burst, core.",
    )
    parser.add_argument(
        "--summary-head-percent",
        type=int,
        default=20,
        help="Percentage for the 'operations in the first X%% of the data' metric (default: 20).",
    )
    parser.add_argument("--version", action="version", version=version)
    return parser.parse_args()


def print_params_clean(args: argparse.Namespace, log_file: str) -> None:
    print("=== Run ===")
    print(f"• Input       : {args.input}")
    print(f"• Final output: {args.final_output}")
    print(f"• Cache dir   : {args.cache_dir}")
    print(f"• Year tag    : {args.year_tag}")
    print(f"• Sep I/O     : {'\\t' if args.sep == '\\t' else args.sep}")
    print(f"• Logs        : {log_file}")
    if args.use_cache:
        print("• Cache       : reuse if available")
    if args.force:
        print("• Force       : redo even with cache")
    if args.check_setup:
        print("• Mode        : check-setup\n")


def quick_validate_input(input_path: str, sep: str) -> bool:
    try:
        sample = pd.read_csv(input_path, sep=sep, nrows=50)
        cols = set(sample.columns.tolist())
        expected_min = {"id_video", "titulo", "descricao"}
        missing = expected_min - cols
        if missing:
            logging.warning(f"[check] minimum columns missing from the sample: {missing}")
        logging.info(f"[check] sample ok: {len(sample)} rows | columns: {list(sample.columns)}")
        return True
    except Exception as e:
        logging.error(f"[check] failed to read input: {e}")
        return False


# =========================
# Models (HF and spaCy)
# =========================

class SpacyTokenPattern(TypedDict, total=False):
    LOWER: Union[str, Dict[str, Any]]

# Dict alias kept separate from the TypedDict to avoid Pylance/mypy conflicts
SpacyEntityPatternDict = Dict[str, Union[str, List[Dict[str, Any]]]]

def init_models() -> Tuple[TokenClassificationPipeline, spacy.Language, EntityRuler]:
    logging.info("[1/4] Initializing models…")
    # HF
    tokenizer_hf = AutoTokenizer.from_pretrained("Babelscape/wikineural-multilingual-ner")
    model_hf = AutoModelForTokenClassification.from_pretrained("Babelscape/wikineural-multilingual-ner")
    device: int | str = 0 if torch.cuda.is_available() else -1
    logging.info(f" - Device: {'GPU' if device == 0 else 'CPU'}")

    nlp_hf = cast(
        TokenClassificationPipeline,
        pipeline(
            task="token-classification",
            model=model_hf,
            tokenizer=tokenizer_hf,
            aggregation_strategy="simple",
            device=device,
        ),
    )

    # spaCy + EntityRuler
    try:
        nlp_spacy = spacy.load("pt_core_news_lg")
    except Exception as e:
        logging.error("spaCy model 'pt_core_news_lg' not found. Install it and try again.")
        raise e

    if "entity_ruler" not in nlp_spacy.pipe_names:
        ruler = cast(EntityRuler, nlp_spacy.add_pipe("entity_ruler", before="ner"))
    else:
        ruler = cast(EntityRuler, nlp_spacy.get_pipe("entity_ruler"))

    # The original rule captured "operação" + ONE token, truncating names such
    # as "Operação Novo Cangaço". Here the name may have up to four tokens; each
    # extra token must be capitalized, which stops the capture at verbs and
    # complements ("operação prende", "operação no Rio").
    _NAO_NOME = ["policial", "policiais", "conjunta", "contra", "no", "na", "de",
                 "do", "da", "em", "que", "e", "com", "para"]
    _SEGUINTE = {"IS_TITLE": True, "IS_STOP": False}
    patterns: List[SpacyEntityPatternDict] = [
        {
            "label": "OPERACAO",
            "pattern": [
                {"LOWER": "operação"},
                {"LOWER": {"NOT_IN": _NAO_NOME}, "IS_TITLE": True},
            ] + [dict(_SEGUINTE, OP="?") for _ in range(extra)],
        }
        for extra in (3, 2, 1, 0)
    ]
    ruler.add_patterns(patterns)

    logging.info("[1/4] Models ready.")
    return nlp_hf, nlp_spacy, ruler


# =========================
# NER + Normalization
# =========================

def extract_entities(text: Any, nlp_hf: TokenClassificationPipeline, nlp_spacy: spacy.Language) -> str:
    if pd.isna(text):
        return ""
    text_str = str(text)

    ner_results = nlp_hf(text_str)
    # Accepting ORG/MISC from wikineural was measured and rejected: it raised the
    # macro F1 on the high-repercussion set (0.328 -> 0.476) precisely because it
    # merged too much, while ARI dropped (0.957 -> 0.679). This is the 7/k ceiling
    # artifact — fewer clusters inflate F1 while the merges are wrong.
    categories_of_interest = {"LOC", "PER", "EVENT", "DATE", "LAW", "OPERACAO"}
    entities: List[str] = []

    for result in ner_results:
        grp = result.get("entity_group", "")
        if grp in categories_of_interest:
            entities.append(f"{result['word']}:{grp}")

    # The original HT discarded all of spaCy's own entities and only used the
    # OPERACAO rule — throwing away a whole extractor. Here the classes already
    # accepted by the pipeline are used too, mapped to the same wikineural
    # labels.
    equivalencia = {"PER": "PER", "PERSON": "PER", "LOC": "LOC", "GPE": "LOC",
                    "EVENT": "EVENT", "LAW": "LAW", "OPERACAO": "OPERACAO"}
    doc_spacy = nlp_spacy(text_str)
    for ent in doc_spacy.ents:
        destino = equivalencia.get(ent.label_.upper())
        if destino:
            entities.append(f"{ent.text}:{destino}")

    return ", ".join(sorted(set(entities)))


def _progress_iterable(iterable, desc: str):
    if _HAS_TQDM:
        return tqdm(iterable, desc=desc, unit="lin", dynamic_ncols=True, leave=False)
    return iterable


def process_videos_and_extract_entities(
    df: pd.DataFrame,
    year_tag: str,
    cache_dir: str,
    use_cache: bool,
    force: bool,
    sep: str,
    nlp_hf: TokenClassificationPipeline,
    nlp_spacy: spacy.Language,
) -> Tuple[pd.DataFrame, str]:
    """
    Extract entities from the 'titulo' and 'descricao' columns (and 'transcribedText' if present).
    Saves a cache to disk for reuse (expensive step).
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"ner_results_{year_tag}.tsv")

    if use_cache and not force and os.path.exists(cache_path):
        print("[2/4] NER extraction: using existing cache")
        logging.info(f"[NER] using cache: {cache_path}")
        cached = pd.read_csv(cache_path, sep="\t")
        return cached, cache_path

    print("[2/4] NER extraction: in progress…")
    logging.info("[NER] starting extraction (no cache)")

    if "titulo" not in df.columns or "descricao" not in df.columns:
        raise ValueError("The 'titulo' and 'descricao' columns are required for NER extraction.")

    df_proc = df.copy()

    # Row-by-row progress bar (equivalent to apply; UX only)
    titles = df_proc["titulo"].tolist()
    descrs = df_proc["descricao"].tolist()

    ner_tit: List[str] = []
    for t in _progress_iterable(titles, desc="NER titles"):
        ner_tit.append(extract_entities(t, nlp_hf, nlp_spacy))
    df_proc["ner_titulo"] = ner_tit

    ner_desc: List[str] = []
    for d in _progress_iterable(descrs, desc="NER descriptions"):
        ner_desc.append(extract_entities(d, nlp_hf, nlp_spacy))
    df_proc["ner_descricao"] = ner_desc

    if "transcribedText" in df_proc.columns:
        logging.info("[NER] also applying to 'transcribedText'")
        trans_list = df_proc["transcribedText"].fillna("").tolist()
        ner_trs: List[str] = []
        for t in _progress_iterable(trans_list, desc="NER transcripts"):
            ner_trs.append(extract_entities(t, nlp_hf, nlp_spacy))
        df_proc["ner_transcribedText"] = ner_trs
    else:
        logging.info("[NER] column 'transcribedText' not found (skipping)")

    # save cache (all columns + ner_* columns)
    df_proc.to_csv(cache_path, index=False, sep="\t")
    logging.info(f"[NER] done; cache saved to {cache_path}")
    return df_proc, cache_path


# ==========
# Phase 4: anti-noise utilities (cleaning only; does not change the decision)
# ==========

_VALID_LABELS: Set[str] = {"loc", "per", "event", "date", "law", "operacao"}
_ENTITY_RE = re.compile(r"^([a-z0-9][a-z0-9\s\-]{2,}):([a-z]+)$")

def _is_valid_entity_token(token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    m = _ENTITY_RE.match(token)
    if not m:
        return False
    left, label = m.groups()
    return label in _VALID_LABELS and left.strip() != ""

def _clean_entity_field(s: str) -> str:
    """
    Takes a string "e1, e2, e3" and returns only valid entities, deduplicated
    and sorted (cleaning only; does not change later decisions).
    """
    if not isinstance(s, str) or not s:
        return ""
    parts = [p.strip() for p in s.split(",")]
    kept = {p for p in parts if _is_valid_entity_token(p)}
    if not kept:
        return ""
    return ", ".join(sorted(kept))


# =========================
# Post-cache normalization
# =========================

def load_data(file_path: str) -> pd.DataFrame:
    """
    Load and normalize the NER columns that exist
    ('ner_titulo', 'ner_descricao', and optionally 'ner_transcribedText').
    """
    try:
        df = pd.read_csv(file_path, sep="\t", parse_dates=["data_postagem"])
        logging.info(f"[norm] loaded from {file_path}; columns: {list(df.columns)}")

        ner_cols_to_process: List[str] = []
        if "ner_titulo" in df.columns:
            ner_cols_to_process.append("ner_titulo")
        if "ner_descricao" in df.columns:
            ner_cols_to_process.append("ner_descricao")
        if "ner_transcribedText" in df.columns:
            logging.info("[norm] including 'ner_transcribedText'")
            ner_cols_to_process.append("ner_transcribedText")

        def remove_accents(input_str: Any) -> str:
            if pd.isna(input_str):
                return ""
            nfkd_form = unicodedata.normalize("NFD", str(input_str))
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        for col in ner_cols_to_process:
            df[col] = df[col].fillna("")
            df[col] = df[col].str.lower()
            df[col] = df[col].apply(remove_accents)
            df[col] = df[col].str.replace(r"[^a-z0-9\s,:]", "", regex=True)
            df[col] = df[col].apply(_clean_entity_field)

        logging.info("[norm] done")
        return df
    except Exception as e:
        logging.error(f"[norm] error while loading/normalizing: {e}")
        return pd.DataFrame()


# =========================
# Window and count logic (ORIGINAL LOGIC)
# =========================

def get_time_window(df: pd.DataFrame, base_date: pd.Timestamp, days: int = 15) -> pd.DataFrame:
    start_date = base_date - datetime.timedelta(days=days)
    end_date = base_date + datetime.timedelta(days=days)
    return df[(df['data_postagem'] >= start_date) & (df['data_postagem'] <= end_date)]


def count_entities_in_window(df: pd.DataFrame) -> Dict[str, int]:
    """
    Count the frequency of all entities in the time window. Includes the
    transcript entities if the column exists.
    """
    series_to_count = df['ner_titulo'].str.cat(df['ner_descricao'], sep=', ')
    if 'ner_transcribedText' in df.columns:
        series_to_count = series_to_count.str.cat(df['ner_transcribedText'].fillna(''), sep=', ')

    entity_counts: Dict[str, int] = {}
    for entities in series_to_count.str.split(', '):
        for entity in entities:
            entity = entity.strip()
            if entity:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1
    return entity_counts


# =========================
# v4 (180926): tag-free identity, outlet noise, lexical unification
# =========================

def _sem_acento(texto: str) -> str:
    forma = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in forma if not unicodedata.combining(c))


def _split_entity_token(token: str) -> Tuple[str, str]:
    """Split an already normalized "name:tag". Returns ("", "") if the token is invalid."""
    token = token.strip()
    if not _is_valid_entity_token(token):
        return "", ""
    left, label = token.rsplit(":", 1)
    return re.sub(r"\s+", " ", left).strip(), label.strip()


def entity_keys(field: Any, keep_tag: bool = False) -> Set[str]:
    """Keys of an ner_* field.

    Without ``keep_tag`` the tag is dropped from the identity: measured on the
    real corpus, 992 entities (12.8%) receive more than one tag across 12,215
    occurrences, and the generic-entity detector running on "name:tag" caught
    only 1 of the 4 variants of "tiktok" — which became the label of 11 groups.
    """
    out: Set[str] = set()
    if not isinstance(field, str) or not field:
        return out
    for token in field.split(","):
        name, tag = _split_entity_token(token)
        if not name:
            continue
        out.add(f"{name}:{tag}" if keep_tag else name)
    return out


def build_key_columns(df: pd.DataFrame, keep_tag: bool = False) -> pd.DataFrame:
    """Add ``_keys`` (all keys) and ``_keys_title`` (title keys only)."""
    cols = [c for c in ("ner_titulo", "ner_descricao", "ner_transcribedText") if c in df.columns]
    df = df.copy()
    df["_keys"] = [
        frozenset().union(*(entity_keys(row[c], keep_tag) for c in cols)) if cols else frozenset()
        for _, row in df[cols].iterrows()
    ] if cols else [frozenset()] * len(df)
    if "ner_titulo" in df.columns:
        df["_keys_title"] = [frozenset(entity_keys(v, keep_tag)) for v in df["ner_titulo"]]
    else:
        df["_keys_title"] = [frozenset()] * len(df)
    return df


def _joelho(valores: "np.ndarray") -> float:
    """Kneedle: point with the largest perpendicular distance to the chord (same
    method already used to detect generic entities)."""
    y = np.asarray(valores, dtype=float)
    if len(y) < 3:
        return float("nan")
    x = np.arange(len(y))
    p1, p2 = np.array([x[0], y[0]]), np.array([x[-1], y[-1]])
    dy, dx = p2[1] - p1[1], p2[0] - p1[0]
    denom = np.sqrt(dy ** 2 + dx ** 2)
    if denom <= 0:
        return float("nan")
    dist = np.abs(dy * x - dx * y + p2[0] * p1[1] - p2[1] * p1[0]) / denom
    return float(y[int(np.argmax(dist))])


def get_boilerplate_entities(
    df: pd.DataFrame, min_docs: int = 10, cap: float = 0.12
) -> Set[str]:
    """Outlet watermark: a frequent entity that almost never appears in the title.

    The event is named in the title; the channel signature lives in the
    description. Measured on the real corpus: event entities appear in 21%–86%
    of the titles of the videos where they occur (jacarezinho 70%, varginha 86%,
    mare 78%, penha 41%, comando vermelho 21%); boilerplate stays at 0%–4%
    (facebook, twitter, instagram, tiktok, whatsapp, youtube, playplus, panflix,
    balanco geral). These are 100 keys with df>=20 and 31.4% of all evidence in
    the corpus.

    The cut comes from the corpus itself, at the knee of the title-share curve,
    but is bounded by ``cap``: the filter never discards something that is in
    more than ``cap`` of the titles, so it does not swallow event entities in
    datasets with poor descriptions.
    """
    docs: Dict[str, int] = {}
    tits: Dict[str, int] = {}
    for keys, keys_t in zip(df["_keys"], df["_keys_title"]):
        for k in keys:
            docs[k] = docs.get(k, 0) + 1
        for k in keys_t:
            tits[k] = tits.get(k, 0) + 1
    freq = {k: c for k, c in docs.items() if c >= min_docs}
    if not freq:
        logging.info("[boiler] no key with df>=%d; filter inactive", min_docs)
        return set()
    share = {k: tits.get(k, 0) / c for k, c in freq.items()}
    joelho = _joelho(np.array(sorted(share.values())))
    corte = cap if not np.isfinite(joelho) else min(joelho, cap)
    boiler = {k for k, v in share.items() if v < corte}
    logging.info(
        "[boiler] cut=%.3f (knee=%.3f, cap=%.3f); %d of %d keys with df>=%d "
        "flagged as outlet noise",
        corte, joelho, cap, len(boiler), len(freq), min_docs,
    )
    return boiler


def get_channel_brands(
    df: pd.DataFrame, min_concentracao: float = 0.70,
) -> Set[str]:
    """Broadcaster/show brand, recognized through the ``canal`` (channel) column.

    The title-share filter does not reach these: "Cidade Alerta", "#SBTManhã"
    and "Balanço Geral" are in the **title** and still name the outlet, not the
    event — on the real corpus they became groups of 15, 14 and 10 videos. Two
    pieces of evidence, both taken from the data itself:

    1. the key matches the name of a channel in the corpus (or that name without
       spaces, which is how hashtags appear);
    2. the key is frequent, almost all of it comes from a single channel and it
       spreads over many months — the signature of a show opener, not of a fact.

    Without the ``canal`` column the function returns an empty set: the
    annotated datasets do not have it, and applying the rule there would erase
    event entities.
    """
    if "canal" not in df.columns:
        logging.info("[brand] column 'canal' missing; broadcaster filter inactive")
        return set()
    nomes: Set[str] = set()
    for bruto in df["canal"].dropna().astype(str).unique():
        canal = re.sub(r"\s+", " ", _sem_acento(bruto).lower()).strip()
        canal = re.sub(r"[^a-z0-9 ]", "", canal).strip()
        if canal:
            nomes.add(canal)
            nomes.add(canal.replace(" ", ""))

    docs: Dict[str, int] = {}
    por_canal: Dict[str, Dict[str, int]] = {}
    for keys, canal in zip(df["_keys"], df["canal"].fillna("").astype(str)):
        for k in keys:
            docs[k] = docs.get(k, 0) + 1
            por_canal.setdefault(k, {})
            por_canal[k][canal] = por_canal[k].get(canal, 0) + 1
    candidatas = {k for k in set().union(*df["_keys"]) if k in nomes or k.replace(" ", "") in nomes}
    # Matching a channel name is not enough: public figures have channels too.
    # What singles out the show brand is its origin — it only appears in the
    # videos of whoever owns it. Measured: "balancogeral", "linhadecombate",
    # "tv atalaia" and "sbtnews" come 100% from a single channel; "jair
    # bolsonaro" comes 19% from the largest one, across 15 channels, and "rio de
    # janeiro" 35% across 67 channels.
    marcas: Set[str] = set()
    for k in candidatas:
        total = docs.get(k, 0)
        if total and max(por_canal.get(k, {0: 0}).values()) / total >= min_concentracao:
            marcas.add(k)

    # Concentration alone, without the name match, was tested and rejected: it
    # would flag place names covered by a local broadcaster — "varginha" appears
    # in 86% of TV Alterosa's videos and is the massive event of Oct/2021. That
    # is why it only applies to keys that already matched a channel name.
    logging.info("[brand] %d keys identified as broadcaster/show brands", len(marcas))
    return marcas


def build_canonical_map(
    df: pd.DataFrame, ignored: Set[str], min_docs: int = 2, min_cooccur: int = 2,
    raio: int = 15,
) -> Dict[str, str]:
    """Unify spellings where one key is a contiguous sub-phrase of the other.

    Measured on the real corpus: 941 containment pairs among keys with df>=3.
    This is the direct cause of massive events being sliced — Maré becomes
    ``complexo da mare`` (12 videos) + ``mare`` (7), Lázaro becomes
    ``lazaro barbosa`` (8) + ``lazaro`` (4), Vila Cruzeiro splits into three.

    It only unifies when both spellings appear together in the same video at
    least ``min_cooccur`` times — this is what separates "complexo da mare"/
    "mare" (same place) from homonyms that never meet.
    """
    docs: Dict[str, int] = {}
    for keys in df["_keys"]:
        for k in keys - ignored:
            docs[k] = docs.get(k, 0) + 1
    validas = {k for k, c in docs.items() if c >= min_docs}

    # Co-occurrence of both spellings in the same video.
    co: Dict[Tuple[str, str], int] = {}
    for keys in df["_keys"]:
        usaveis = sorted(k for k in keys - ignored if k in validas)
        for curta in usaveis:
            alvo = f" {curta} "
            for longa in usaveis:
                if len(longa) > len(curta) and alvo in f" {longa} ":
                    par = (curta, longa)
                    co[par] = co.get(par, 0) + 1

    # A single hop, without transitive closure. Closing transitivity collapses
    # distinct territories: on the real corpus "complexo do alemao" linked to
    # "alemao", which appeared inside a key "alemao penha", which pulled in
    # "penha" and "complexo da penha" — four places in a single family, and
    # groups of different events with the same name.
    # When both spellings almost never appear in the same video, temporal
    # coincidence counts: "lazaro" and "lazaro barbosa" share a single video in
    # the whole corpus, but both only occur in the same weeks of 2021.
    datas: Dict[str, List[int]] = {}
    for keys, data in zip(df["_keys"], df["data_postagem"]):
        dia = pd.Timestamp(data).value // 86_400_000_000_000
        for k in keys - ignored:
            if k in validas:
                datas.setdefault(k, []).append(dia)
    for v in datas.values():
        v.sort()

    def _sobreposicao(a: str, b: str) -> float:
        da, db = datas.get(a, []), datas.get(b, [])
        if not da or not db:
            return 0.0
        perto = sum(
            1 for d in da
            if db[min(bisect.bisect_left(db, d), len(db) - 1)] - raio <= d <= db[-1] + raio
            and any(abs(d - o) <= raio for o in db)
        )
        return perto / len(da)

    parceiros: Dict[str, Set[str]] = {}
    for (curta, longa), n in co.items():
        junta = n >= min_cooccur
        if not junta:
            junta = min(_sobreposicao(curta, longa), _sobreposicao(longa, curta)) >= 0.60
        if junta:
            parceiros.setdefault(curta, set()).add(longa)
            parceiros.setdefault(longa, set()).add(curta)

    cmap: Dict[str, str] = {}

    # A long, rare spelling that contains a frequent key is a bad NER span, not
    # another entity: "verao match o boticario", "contragolpe i", "escudo em
    # 2023 na mesma" appeared once each and became groups of their own.
    # Map it to the longest frequent sub-phrase (the most specific one).
    raras = [k for k, c in docs.items() if c < min_docs and " " in k]
    for k in sorted(raras):
        alvo = f" {k} "
        contidas = [f for f in validas if len(f) < len(k) and f" {f} " in alvo]
        if contidas:
            cmap[k] = sorted(contidas, key=lambda x: (-len(x), x))[0]

    for k, vizinhos in parceiros.items():
        escolha = sorted({k} | vizinhos, key=lambda x: (-docs.get(x, 0), len(x), x))[0]
        if escolha != k:
            cmap[k] = escolha
    logging.info(
        "[alias] %d containment pairs confirmed; %d spellings remapped",
        sum(1 for n in co.values() if n >= min_cooccur), len(cmap),
    )
    return cmap


def apply_canonical(df: pd.DataFrame, cmap: Dict[str, str], ignored: Set[str]) -> pd.DataFrame:
    """Build ``_keys_canon``: usable keys already in canonical form."""
    df = df.copy()
    df["_keys_canon"] = [
        frozenset(cmap.get(k, k) for k in keys - ignored) for keys in df["_keys"]
    ]
    return df


def window_counts(
    dias: "np.ndarray", chaves: List[frozenset], centro: int, raio: int
) -> Dict[str, int]:
    """Frequency of each key in the ±raio window, counted per video.

    The original HT concatenated title and description and counted field
    occurrences, so the same entity counted twice in a single video. Here each
    video votes once per key.
    """
    ini = int(np.searchsorted(dias, dias[centro] - raio, side="left"))
    fim = int(np.searchsorted(dias, dias[centro] + raio, side="right"))
    contagem: Dict[str, int] = {}
    for i in range(ini, fim):
        for k in chaves[i]:
            contagem[k] = contagem.get(k, 0) + 1
    return contagem


class _Grupo:
    """State of a group: time interval and cumulative signature."""

    __slots__ = ("gid", "nome", "base", "inicio", "fim", "assinatura", "membros", "visto")

    def __init__(self, gid: int, nome: str, base: str, data: pd.Timestamp):
        self.gid = gid
        self.nome = nome
        self.base = base
        self.inicio = data
        self.fim = data
        self.assinatura: Dict[str, int] = {}
        # Last date on which each signature entity was actually mentioned.
        self.visto: Dict[str, pd.Timestamp] = {}
        self.membros = 0

    def adiciona(self, data: pd.Timestamp, chaves: "frozenset[str]") -> None:
        self.inicio = min(self.inicio, data)
        self.fim = max(self.fim, data)
        self.membros += 1
        for k in chaves:
            self.assinatura[k] = self.assinatura.get(k, 0) + 1
            anterior = self.visto.get(k)
            if anterior is None or data > anterior:
                self.visto[k] = data


def assign_operations(
    df: pd.DataFrame,
    raio: int = 15,
    usar_assinatura: bool = True,
    max_span: int = 0,
    relabel_grupos: bool = True,
    suporte_central: float = 0.0,
    min_membros_centro: int = 3,
) -> pd.DataFrame:
    """Group videos by entity signature within the time window.

    Differences from the original HT, all measured on the real corpus:

    * the group keeps a **cumulative signature** of entities, not a single
      winning string. In the Oct/2025 mega-operation, 26 videos elected 10
      different entities and became 10 groups;
    * the video joins the co-temporal group that shares the most entities with
      it, not the first one that matches by string;
    * tie-breaking is deterministic. The original HT sorted a ``set`` by
      frequency, so ties depended on the string hash and the output changed
      between runs;
    * all suffixed siblings are evaluated, by temporal proximity. The original
      scan was lexicographic, so ``-10`` was tested before ``-2``.

    The numeric suffix is preserved: the same entity at another time still
    produces ``entity-2``, ``entity-3``, which is what separates two distinct
    events in the same territory.
    """
    if "_keys_canon" not in df.columns:
        raise ValueError("assign_operations requires the _keys_canon column")

    janela = datetime.timedelta(days=raio)
    ordem = list(df["data_postagem"].sort_values(kind="stable").index)
    datas = [df.at[i, "data_postagem"] for i in ordem]
    dias = np.array([d.value // 86_400_000_000_000 for d in datas], dtype=np.int64)
    chaves: List[frozenset] = [df.at[i, "_keys_canon"] for i in ordem]

    relabel = bool(relabel_grupos)
    grupos: Dict[int, _Grupo] = {}
    indice_chave: Dict[str, Set[int]] = {}
    rotulos: Dict[Any, str] = {}
    contadores: Dict[str, int] = {}
    gid_seq = 0
    op_seq = 0
    orfaos = 0

    print("[3/4] Grouping operations…")
    for pos, indice in enumerate(ordem):
        data = datas[pos]
        atuais = chaves[pos]
        if not atuais:
            op_seq += 1
            rotulos[indice] = f"OP{op_seq}"
            orfaos += 1
            logging.info(f"[{indice}] no usable entity -> OP{op_seq}")
            continue

        contagem = window_counts(dias, chaves, pos, raio)
        candidatas = sorted(atuais, key=lambda k: (-contagem.get(k, 0), k))
        topo = candidatas[0]

        possiveis: Set[int] = set()
        for k in atuais:
            possiveis |= indice_chave.get(k, set())

        melhor: Any = None
        for gid in sorted(possiveis):
            g = grupos[gid]
            if data < g.inicio - janela or data > g.fim + janela:
                continue
            # Span ceiling, if configured. Off by default: a fixed ceiling
            # splits legitimate long operations — the Mossoró manhunt (Feb to
            # Apr) and Operação Verão (Feb to Jul) were cut into two and four
            # pieces. Drift is prevented by the central-entity requirement
            # just below.
            if max_span > 0:
                novo_inicio = min(g.inicio, data)
                novo_fim = max(g.fim, data)
                if (novo_fim - novo_inicio).days > max_span:
                    continue
            comuns = atuais & g.assinatura.keys()
            if not comuns:
                continue
            # Evidence must be local in time, which is the premise of the HT: it
            # is not enough for the entity to be in the accumulated signature;
            # some member must have mentioned it within the window. Without this
            # the group drifts — on the real corpus a group started at the murder
            # of a former police chief on Sep 15 (São Paulo coast) and reached
            # the Rio mega-operation on Nov 6, 68 videos and 52 days later,
            # because the entity that opened it stayed in the signature long
            # after it went out of circulation.
            comuns = {k for k in comuns if abs((data - g.visto[k]).days) <= raio}
            if not comuns:
                continue
            if usar_assinatura:
                # Reasons to join: sharing the group's identity, sharing the
                # video's own winner, or sharing two entities.
                if not (len(comuns) >= 2 or g.base in comuns or topo in comuns):
                    continue
                # And, above all, sharing something **central** to the group: an
                # entity that many of its members mention. Without this the group
                # drifts — the accumulated signature grows, a video joins through
                # a peripheral entity, and within a few weeks the group has become
                # another event. Small groups have no defined center, so the
                # requirement only applies from ``min_membros_centro`` members on.
                if g.membros >= min_membros_centro:
                    apoio = max(g.assinatura[k] for k in comuns) / g.membros
                    if apoio < suporte_central:
                        continue
            elif g.base != topo:
                # "signature" ablation: reproduces the single winner of the original HT.
                continue
            if g.inicio <= data <= g.fim:
                dist = 0
            else:
                dist = min(abs((data - g.fim).days), abs((g.inicio - data).days))
            peso = sum(contagem.get(k, 0) for k in comuns)
            chave_ordem = (-len(comuns), -peso, dist, g.gid)
            if melhor is None or chave_ordem < melhor[0]:
                melhor = (chave_ordem, g)

        if melhor is not None:
            g = melhor[1]
            comuns_n = -melhor[0][0]
            antes = set(g.assinatura)
            g.adiciona(data, atuais)
            for k in set(g.assinatura) - antes:
                indice_chave.setdefault(k, set()).add(g.gid)
            rotulos[indice] = g.nome
            logging.info(f"[{indice}] -> existing group '{g.nome}' ({comuns_n} entities in common)")
            continue

        n = contadores.get(topo, 0) + 1
        contadores[topo] = n
        nome = topo if n == 1 else f"{topo}-{n}"
        gid_seq += 1
        g = _Grupo(gid_seq, nome, topo, data)
        g.adiciona(data, atuais)
        grupos[gid_seq] = g
        for k in g.assinatura:
            indice_chave.setdefault(k, set()).add(gid_seq)
        rotulos[indice] = nome
        logging.info(f"[{indice}] -> new group '{nome}' (window: {contagem.get(topo, 0)} videos mention '{topo}')")

    if relabel:
        rotulos = _rerrotula(grupos, rotulos)

    df = df.copy()
    df["operation_ner"] = pd.Series(rotulos).reindex(df.index)
    logging.info(
        f"[3/4] {len(grupos)} entity groups + {orfaos} videos without usable evidence"
    )
    return df


def _rerrotula(grupos: Dict[int, "_Grupo"], rotulos: Dict[Any, str]) -> Dict[Any, str]:
    """Rename each group after the entity mentioned by most of its members.

    The original name was the entity that won the window when the **first**
    video arrived, which produced misleading labels: the July 2022 operation in
    Complexo do Alemão came out as ``penha-4`` and the Vila Cruzeiro one as
    ``policia rodoviaria federal``. Renaming by the consolidated signature does
    not change any grouping — only the name — and makes the output auditable.
    """
    novo_nome: Dict[int, str] = {}
    for gid, g in grupos.items():
        if not g.assinatura:
            novo_nome[gid] = g.base
            continue
        novo_nome[gid] = sorted(g.assinatura, key=lambda k: (-g.assinatura[k], k))[0]
    familias: Dict[str, List[int]] = {}
    for gid in sorted(grupos, key=lambda i: (grupos[i].inicio, i)):
        familias.setdefault(novo_nome[gid], []).append(gid)
    final: Dict[int, str] = {}
    for base, ids in familias.items():
        for n, gid in enumerate(ids, start=1):
            final[gid] = base if n == 1 else f"{base}-{n}"
    traducao = {g.nome: final[gid] for gid, g in grupos.items()}
    logging.info("[relabel] %d groups renamed by signature", len(traducao))
    return {idx: traducao.get(nome, nome) for idx, nome in rotulos.items()}


def calcular_limite_densidade_histograma(
    porcentagem_meses: pd.Series, 
    corte_joelho: float,
    largura_janela: float = 10.0,
    limiar_entidades: int = 2,
    passo: float = 0.5
) -> float | None:
    """
    Compute the dynamic generic-entity threshold from the density of entities in sliding windows.
    The search starts at the knee cut (long-tail cleanup) and moves right until it finds an
    interval with few entities (sparsity).
    
    Returns the month-percentage value (start of the sparse window) or None.
    """
    y_filtrado = porcentagem_meses[porcentagem_meses >= corte_joelho].to_numpy(dtype=float)
    if len(y_filtrado) < 3:
        return None
        
    atual = corte_joelho
    while atual + largura_janela <= 100.0:
        # Count the entities in the interval [atual, atual + largura_janela]
        qtd_entidades = np.sum((y_filtrado >= atual) & (y_filtrado < atual + largura_janela))  # type: ignore[operator]
        if qtd_entidades <= limiar_entidades:
            return atual
        atual += passo
        
    return None


def get_generic_entities_unsupervised(
    df: pd.DataFrame, min_threshold: int = 5, ratio: float = 0.4167,
    max_burst: float = 0.25, raio_surto: int = 15,
) -> Set[str]:
    # Avoid timezone-conversion warnings when working with periods
    df = df.copy()
    if "data_postagem" in df.columns:
        if df["data_postagem"].dt.tz is not None:
            df["data_postagem"] = df["data_postagem"].dt.tz_localize(None)

    total_months = 0
    if "data_postagem" in df.columns:
        total_months = df["data_postagem"].dt.to_period("M").nunique()
    
    if total_months == 0 or len(df) == 0:
        logging.warning("[gen] total months or videos is 0. No generic entity found.")
        return set()

    logging.info(f"[gen] identifying generic entities (months detected: {total_months}, videos: {len(df)})")
    # Same statistic as the original HT — monthly coverage per entity — but on
    # the tag-free key. Measured on the real corpus: with "name:tag" the
    # detector caught "tiktok" in 1 of 4 variants; on "name" it captures 11 of
    # the 12 known noise entities.
    if "_keys" not in df.columns:
        raise ValueError("get_generic_entities_unsupervised requires the _keys column")
    ner_date_df = (
        df[["data_postagem", "_keys"]]
        .assign(_keys=[sorted(k) for k in df["_keys"]])
        .explode("_keys")
        .rename(columns={"_keys": "entity"})
    )
    ner_date_df.dropna(subset=["entity"], inplace=True)
    ner_date_df = ner_date_df[ner_date_df["entity"] != ""]

    if ner_date_df.empty:
        logging.info("[gen] no NER entity found in the videos.")
        return set()

    ner_date_df["year_month"] = ner_date_df["data_postagem"].dt.to_period("M")

    # 1. Share of months
    meses_por_entidade = ner_date_df.groupby("entity")["year_month"].nunique()
    porcentagem_meses = (meses_por_entidade / total_months) * 100

    # Sorting and preparation for the overall knee computation
    entidades_ordenadas = porcentagem_meses.sort_values(ascending=False)
    y = entidades_ordenadas.values
    x = np.arange(len(y))

    # 2. Overall knee algorithm (long-tail noise filter)
    corte_joelho = ratio * 100  # Initial fallback
    if len(y) >= 3:
        p1 = np.array([x[0], y[0]])
        p2 = np.array([x[-1], y[-1]])
        dy = p2[1] - p1[1]
        dx = p2[0] - p1[0]
        denom = np.sqrt(dy**2 + dx**2)
        if denom > 0:
            distancias = [np.abs(dy * x[i] - dx * y[i] + p2[0]*p1[1] - p2[1]*p1[0]) / denom for i in range(len(y))]
            corte_joelho = y[np.argmax(distancias)]

    # 3. Dynamic computation via density histogram (option 1)
    limite_calculado = calcular_limite_densidade_histograma(
        porcentagem_meses=porcentagem_meses,
        corte_joelho=corte_joelho,
        largura_janela=10.0,
        limiar_entidades=2,
        passo=0.5
    )

    if limite_calculado is not None:
        # Main logic: dynamic density threshold
        logging.info(f"[gen] generic threshold computed dynamically: {limite_calculado:.2f}% of months (knee cut: {corte_joelho:.2f}%)")
        generic_entities = set(porcentagem_meses[porcentagem_meses >= limite_calculado].index)
    else:
        # Safe fallback: 41.67% of active months
        limite_fallback = ratio * 100
        logging.warning(f"[gen] dynamic density computation failed or returned None. Using FALLBACK of {limite_fallback:.2f}% of months")
        generic_entities = set(porcentagem_meses[porcentagem_meses >= limite_fallback].index)

    # Temporal condition, applied both ways: for frequent keys
    # (df >= min_docs_plano) the burst decides — generic is the one WITHOUT it.
    # Monthly coverage still decides for rare keys.
    #
    # Monthly coverage alone breaks on short or single-topic corpora — on the
    # 465 high-repercussion videos, covering 9 months and 7 operations, it
    # classified the operations themselves as generic ("mossoro", "verao",
    # "contragolpe", "tempus veritatis"), erasing the evidence and leaving 368
    # groups for 465 videos.
    #
    # The margin is wide and measured on the real corpus (2,925 videos, 83
    # months): legitimate generic entities concentrate 4%–10% of their
    # occurrences in their largest ±15-day window (p90 = 12%), while event
    # entities range from 40% (complexo do alemao) to 93% (varginha).
    if max_burst > 0:
        por_chave: Dict[str, List[int]] = {}
        for keys, data in zip(df["_keys"], df["data_postagem"]):
            dia = pd.Timestamp(data).value // 86_400_000_000_000
            for k in keys:
                por_chave.setdefault(k, []).append(dia)

        def _surto(k: str) -> float:
            v = np.sort(np.array(por_chave[k], dtype=np.int64))
            if len(v) < 2:
                return 1.0
            ini = np.searchsorted(v, v - raio_surto, side="left")
            fim = np.searchsorted(v, v + raio_surto, side="right")
            return float((fim - ini).max()) / len(v)

        # Rescue: a generic candidate that has a burst counts again.
        com_surto = {k for k in generic_entities if _surto(k) >= max_burst}
        # Rescue only. The reverse path — demoting every frequent key without a
        # burst — was measured and rejected: it cleaned ~6 loose regional groups
        # ("cidade alerta", "aracaju", "baixada fluminense") but cost the
        # consolidation of three massive events, because territories with
        # recurring coverage ("cracolandia", "cidade de deus") also lost the
        # right to anchor. The main criterion is grouping the massive event.
        if com_surto:
            logging.info(
                "[gen] %d candidates have a burst >= %.0f%% and count again (e.g.: %s)",
                len(com_surto), max_burst * 100, ", ".join(sorted(com_surto)[:6]),
            )
        generic_entities = generic_entities - com_surto

    logging.info(f"[gen] {len(generic_entities)} generic entities found in total")
    return generic_entities


# =========================
# Final summary (console)
# =========================

def print_final_summary(final_df: pd.DataFrame, args: argparse.Namespace, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> None:
    print("\n[4/4] Summary")
    total_videos = len(final_df)
    ops_series = final_df.get("operation_ner", pd.Series([], dtype=str)).fillna("")
    ops_distintas = ops_series.replace("", pd.NA).dropna().nunique()
    vazios = int((ops_series == "").sum())
    genericos = int(ops_series.str.match(r"^OP\d+$").sum())

    period_str = "n/d"
    if "data_postagem" in final_df.columns:
        dmin = pd.to_datetime(final_df["data_postagem"], errors="coerce").min()
        dmax = pd.to_datetime(final_df["data_postagem"], errors="coerce").max()
        if pd.notna(dmin) and pd.notna(dmax):
            delta = (dmax - dmin).days
            period_str = f"{dmin.date()} — {dmax.date()} ({delta} days)"

    head_pct = max(1, min(99, args.summary_head_percent))
    head_n = max(1, int(total_videos * head_pct / 100))
    df_ord = final_df.copy()
    if "data_postagem" in df_ord.columns:
        df_ord = df_ord.sort_values("data_postagem", kind="stable")
    head_ops = df_ord.head(head_n)["operation_ner"].replace("", pd.NA).dropna().nunique()

    top_ops = (
        ops_series[ops_series != ""]
        .value_counts()
        .head(5)
        .to_dict()
    )

    elapsed = (end_ts - start_ts).total_seconds()

    print("────────────────────────────────────────")
    print(f"Videos processed             : {total_videos}")
    print(f"Unique operations            : {ops_distintas}")
    print(f"No entity (empty)            : {vazios}")
    print(f"Generic IDs (OP###)          : {genericos}")
    print(f"Date range                   : {period_str}")
    print(f"First {head_pct}% of the data  : {head_ops} distinct operations")
    if top_ops:
        print("Top 5 operations             :")
        for k, v in top_ops.items():
            print(f"  - {k} -> {v}")
    print(f"Total time                   : {elapsed:.2f}s")
    print("────────────────────────────────────────\n")


# =========================
# Orchestration
# =========================

def main() -> int:
    # The Windows console uses cp1252 and broke the final summary (box drawing,
    # ellipses) with UnicodeEncodeError after the file had been saved.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass
    args = parse_args()
    log_path = os.path.join(args.cache_dir, f"logs_{args.year_tag}.log")
    os.makedirs(args.cache_dir, exist_ok=True)
    APP, UX = setup_logging(args.log_level, log_path)

    # Friendly header
    print_params_clean(args, log_path)

    # Check setup?
    if args.check_setup:
        print("[1/4] Checking environment and models…")
        ok = quick_validate_input(args.input, args.sep)
        if not ok:
            return 2
        try:
            init_models()
            print("[OK] Environment OK. Models load correctly.")
            return 0
        except Exception:
            print("[ERROR] Setup check failed. See the log file for details.")
            return 3

    # Quick file validation
    print("[1/4] Validating input file…")
    ok = quick_validate_input(args.input, args.sep)
    if not ok:
        print("[ERROR] Invalid input (details in the log).")
        return 2

    # Load the original input
    try:
        df_input = pd.read_csv(args.input, sep=args.sep)
    except Exception as e:
        logging.error(f"[io] error reading the full input: {e}")
        print("[ERROR] Failed to read the input file.")
        return 4

    # Convert data_postagem if present
    if "data_postagem" in df_input.columns:
        try:
            df_input["data_postagem"] = pd.to_datetime(df_input["data_postagem"], errors="coerce")
        except Exception as e:
            logging.warning(f"[io] could not convert 'data_postagem': {e}")

    # Initialize models
    try:
        nlp_hf, nlp_spacy, _ = init_models()
    except Exception:
        print("[ERROR] Failed to initialize models. See the log file.")
        return 5

    start_ts = pd.Timestamp.now()

    # Expensive step: NER extraction + cache
    df_ner, cache_path = process_videos_and_extract_entities(
        df=df_input,
        year_tag=args.year_tag,
        cache_dir=args.cache_dir,
        use_cache=args.use_cache,
        force=args.force,
        sep=args.sep,
        nlp_hf=nlp_hf,
        nlp_spacy=nlp_spacy,
    )

    # Normalization of the ner_* columns (reading from the cache to keep the flow simple)
    df_norm = load_data(cache_path)
    if df_norm.empty:
        print("[ERROR] Normalization error (details in the log file).")
        return 6

    # >>> We do NOT filter by 'operation' before grouping (keeps OPx for all rows)
    df_work = df_norm.copy()

    ablacao = {a.strip().lower() for a in str(args.ablate).split(",") if a.strip()}
    if ablacao:
        logging.warning(f"[abl] improvements disabled for ablation: {sorted(ablacao)}")

    # Entity keys; without the "tag" ablation, the tag is dropped from the identity.
    df_work = build_key_columns(df_work, keep_tag="tag" in ablacao)

    # Generic entities: monthly coverage + knee + density window (original HT).
    generic_entities = get_generic_entities_unsupervised(
        df_work,
        max_burst=0.0 if "burst" in ablacao else args.generic_max_burst,
        raio_surto=args.window_days,
    )

    # Outlet watermark: frequent, but almost never in the title.
    boilerplate: Set[str] = set()
    if "boilerplate" not in ablacao:
        boilerplate = get_boilerplate_entities(df_work, cap=args.title_share_cap)
    marcas: Set[str] = set()
    if "brand" not in ablacao:
        marcas = get_channel_brands(df_work)
    ignoradas = set(generic_entities) | boilerplate | marcas

    # Unification of spellings contained in one another.
    canonico: Dict[str, str] = {}
    if "alias" not in ablacao:
        canonico = build_canonical_map(df_work, ignoradas)
    df_work = apply_canonical(df_work, canonico, ignoradas)

    vazios = int(sum(1 for k in df_work["_keys_canon"] if not k))
    logging.info(
        f"[prep] {len(generic_entities)} generic, {len(boilerplate)} outlet, "
        f"{len(marcas)} broadcaster brands, {len(canonico)} spellings unified; "
        f"{vazios} videos without usable evidence"
    )

    # Grouping / operation assignment over the WHOLE df_norm
    df_assigned = assign_operations(
        df_work,
        raio=args.window_days,
        usar_assinatura="signature" not in ablacao,
        max_span=0 if "span" in ablacao else args.max_span_days,
        suporte_central=0.0 if "core" in ablacao else args.core_support,
        relabel_grupos="relabel" not in ablacao,
    )

    # Build the final result (includes ner_titulo, ner_descricao and all_ners)
    print("[4/4] Writing results…")

    # Build all_ners in df_norm (based on the existing ner_* columns)
    ner_cols = []
    if "ner_titulo" in df_norm.columns: ner_cols.append("ner_titulo")
    if "ner_descricao" in df_norm.columns: ner_cols.append("ner_descricao")
    if "ner_transcribedText" in df_norm.columns: ner_cols.append("ner_transcribedText")

    def _join_ners(row: pd.Series) -> str:
        vals = [str(row[c]) if pd.notna(row[c]) else "" for c in ner_cols]
        return ", ".join(vals)

    if ner_cols:
        df_norm["all_ners"] = df_norm.apply(_join_ners, axis=1)
    else:
        df_norm["all_ners"] = ""

    # Assemble the final output with:
    # - all columns of the input file
    # - + ner_titulo, ner_descricao, all_ners, operation_ner
    final_df = df_input.copy()

    # Inject ner_titulo / ner_descricao (if present)
    if "ner_titulo" in df_norm.columns:
        final_df["ner_titulo"] = df_norm["ner_titulo"].reindex(final_df.index).fillna("")
    else:
        final_df["ner_titulo"] = ""
    if "ner_descricao" in df_norm.columns:
        final_df["ner_descricao"] = df_norm["ner_descricao"].reindex(final_df.index).fillna("")
    else:
        final_df["ner_descricao"] = ""

    # Inject all_ners
    final_df["all_ners"] = df_norm["all_ners"].reindex(final_df.index).fillna("")

    # Inject operation_ner (filled for ALL rows, including OPx)
    if "operation_ner" in df_assigned.columns:
        final_df["operation_ner"] = df_assigned["operation_ner"].reindex(final_df.index).fillna("")
    else:
        final_df["operation_ner"] = ""

    # Ensure the directory exists and save
    Path(args.final_output).parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(args.final_output, index=False, sep=args.sep)
    end_ts = pd.Timestamp.now()

    print(f"[OK] File saved to: {args.final_output}")
    print_final_summary(final_df, args, start_ts, end_ts)
    logging.info("[done] pipeline finished successfully")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.error("Run interrupted by the user (Ctrl+C).")
        sys.exit(130)