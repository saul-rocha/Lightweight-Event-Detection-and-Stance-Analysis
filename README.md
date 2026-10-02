# Lightweight Event Detection and Stance Analysis

Code and data to reproduce the experiments of the paper. The repository has two independent parts:

- **Event-Detection**: groups YouTube videos into events (police operations) based on named entities (NER) extracted from the title and description, using time windows.
- **Stance-Detection**: classifies the stance (against, neutral, in favor) of YouTube comments with BERTimbau Large and computes bootstrap confidence intervals.

## Structure

```
.
├── datasets/                              # full monitored corpus (2019–2025), IDs only
│   ├── comments_stance_2019_2025.tsv.gz
│   └── videos_events_2019_2025.tsv
├── Event-Detection/
│   ├── ner_cluster_pipeline.py
│   ├── requirements.txt
│   ├── data/
│   │   └── videos_operations_combined.csv # video IDs + reference event label
│   └── outputs/                           # created at runtime
└── Stance-Detection/
    ├── hydrate_comments.py                # downloads the comment text from the API
    ├── train_bertimbau.py                 # training + evaluation
    ├── bootstrap_ci.py                    # confidence intervals
    ├── requirements.txt
    ├── data/
    │   └── comment_ids_labels.tsv         # comment IDs + label
    └── outputs/                           # created at runtime
```

The default paths of every script are relative to the script's own folder: inputs in `data/`, results in `outputs/`. All scripts accept other paths as arguments (`--help`).

The data column names are in Portuguese, as in the original collection (`titulo` = title, `descricao` = description, `data_postagem` = publication date, `canal` = channel, `id_comentario` = comment ID, `comentario` = comment text, `rotulo` = label).

## About the data: YouTube and LGPD

The data comes from the YouTube Data API v3 and is distributed here **only as video and comment IDs**, together with the annotations produced by the research. The reasons:

- **YouTube policy.** The [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies) forbid redistributing data obtained through the API (section III.G.1) and limit its storage to 30 days (section III.E.4). This covers text, titles, descriptions, channels, publication dates and statistics. IDs are the intended way for third parties to retrieve the content through the API themselves.
- **LGPD (Brazil's General Data Protection Law, Law 13,709/2018).** Comments are written by individuals, mention other people and express opinions on public security. Video titles and descriptions name victims and suspects. The necessity principle (art. 6, III) and the recommendation to anonymize research data whenever possible (arts. 7, IV and 11, II, c) lead us to publish only the minimum needed to reproduce the results.

| Published | Not published |
|---|---|
| `id_video`, `id_comentario` | comment text, authors, @mentions |
| annotated stance labels (`rotulo`) | titles, descriptions, tags, channel names |
| numeric ID of the reference event (`operation`) | publication dates and statistics (views, likes, comment counts) |
| | event names, which are entities extracted from the videos and include people's names |

To reproduce the work, each person retrieves the content with their own API key ("hydration"). Comments and videos deleted after the collection are no longer returned by the API. This respects the decision of whoever removed them, but makes the numbers vary slightly from the paper. Treat the hydrated content as personal data: do not redistribute it, and delete it within 30 days.

To get a key: create a project in the [Google Cloud Console](https://console.cloud.google.com/), enable the **YouTube Data API v3** and create an *API key* under *Credentials*.

## Requirements

- Event-Detection: **Python 3.12 or newer**.
- Stance-Detection: Python 3.10 to 3.12.
- An NVIDIA GPU is optional for Event-Detection, but in practice required to train BERTimbau Large in Stance-Detection (the original experiments ran on Google Colab).

Use a separate virtual environment for each part, because they need different `transformers` versions.

## 1. Event-Detection

### Installation

```bash
cd Event-Detection
python3.12 -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt   # includes the spaCy model pt_core_news_lg
```

To use a GPU, install PyTorch with CUDA following <https://pytorch.org/get-started/locally/>.

### Preparing the input

`data/videos_operations_combined.csv` (`;`-separated) contains `id_video` and `operation`, the numeric ID of the reference event used for evaluation. Fill in these videos' metadata with the [`videos.list`](https://developers.google.com/youtube/v3/docs/videos/list) endpoint (`part=snippet`, up to 50 IDs per call) and save **`data/videos.tsv`**, tab-separated, with the columns:

| column          | API source                | required |
|-----------------|---------------------------|----------|
| `id_video`      | `id`                      | yes      |
| `titulo`        | `snippet.title`           | yes      |
| `descricao`     | `snippet.description`     | yes      |
| `data_postagem` | `snippet.publishedAt`, written as `YYYY-MM-DD HH:MM:SS` (UTC) | yes |
| `canal`         | `snippet.channelTitle`    | no (enables the broadcaster-brand filter) |
| `operation`     | repository file           | no       |

### Running

```bash
python ner_cluster_pipeline.py --check-setup   # validates environment and models
python ner_cluster_pipeline.py                 # data/videos.tsv -> outputs/operations_ner.tsv
```

Outputs in `outputs/`:

- `operations_ner.tsv`: input columns + `ner_titulo`, `ner_descricao`, `all_ners` and `operation_ner` (assigned event).
- `cache/ner_results_<year-tag>.tsv`: cache of the NER extraction, the most expensive step. Use `--use-cache` to reuse it.
- `cache/logs_<year-tag>.log`: detailed log.

The grouping parameters (`--window-days`, `--core-support`, `--ablate`, etc.) are documented in the script header and in `python ner_cluster_pipeline.py --help`.

## 2. Stance-Detection

### Installation

```bash
cd Stance-Detection
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Labels

`data/comment_ids_labels.tsv` contains `id_comentario` and `rotulo` for 3,171 annotated comments: `-1` = against, `0` = neutral, `1` = in favor. During training, `-1` is remapped to class `2`, so in the outputs: class 0 = neutral, 1 = in favor, 2 = against.

### Step 1: download the comment text

```bash
export YOUTUBE_API_KEY="your-key"
python hydrate_comments.py        # -> data/comments.tsv
```

The script queries [`comments.list`](https://developers.google.com/youtube/v3/docs/comments/list) in batches of 50 IDs and applies the same preprocessing as the annotated dataset: lowercasing and removal of accents, punctuation, emojis and line breaks. Comments that are no longer available are reported and left out.

### Step 2: train and evaluate

```bash
python train_bertimbau.py
```

Default hyperparameters (those of the paper): `neuralmind/bert-large-portuguese-cased`, `--max-len 180`, `--batch-size 16`, `--epochs 10`, `--lr 1e-5`, `--seed 42`, 80/20 split. If `data/comments.tsv` has a `split` column (`train`/`test`), it defines the split. Otherwise the split is drawn with `--seed`.

To evaluate already trained weights without training again:

```bash
python train_bertimbau.py --eval-only --checkpoint outputs/models/stance_bertimbau.bin
```

Outputs in `outputs/`:

- `models/stance_bertimbau.bin`: model weights.
- `splits/split_ids.tsv`: train and test IDs used.
- `predictions/test_predictions_and_labels.npz`: test predictions and labels.
- `metrics/metrics_bert.csv`: per-class precision, recall, F1, support, AUC-ROC and TP/FN/FP/TN, plus accuracy.

### Step 3: bootstrap confidence intervals

```bash
python bootstrap_ci.py            # 5000 resamples, seed 2024
```

Writes `outputs/metrics/bootstrap_results.csv` with the mean, standard deviation and 95% CI of each class's precision, recall and F1. With `--predictions` the script evaluates the `.npz` of any other model.

## Monitored corpus (`datasets/`)

IDs of all videos and comments collected between 2019 and 2025, which can be hydrated through the API as described above:

- `videos_events_2019_2025.tsv`: 2,925 videos (`id_video`).
- `comments_stance_2019_2025.tsv.gz`: 1,328,644 comments (`id_comentario`, `id_video`). Use `id_video` to link each comment to its video.

## License

Code under the MIT license (`LICENSE`). Third-party models (BERTimbau, Babelscape/wikineural-multilingual-ner, spaCy `pt_core_news_lg`) have their own licenses. YouTube content is subject to the YouTube Terms of Service.
