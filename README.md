# news-crawler
This project is crawling, extracting, indexing and processing the content of daily published news articles. This project also provides tooling to extract and preprocess the content for the [NoD](https://github.com/uhh-lt/NoDCore) project. This project is a reimplementation of [news-crawler](https://github.com/uhh-lt/news-crawler) in python.

## start project
### news-crawler only
```bash
sudo docker compose up --build
```
This starts only the `news-crawler` container (no NoDCore / NoDWeb).

## Start NoD stack (crawler + nodcore + nodweb)
Run from `news-crawler/` so `${PWD}` volume mounts resolve correctly:
```bash
docker compose -f docker-compose.nod.yml up --build
```

Open NoDWeb at `http://localhost:10008` (mapped from container port `9000`).

Stop everything:
```bash
docker compose -f docker-compose.nod.yml down
```

Run in the background:
```bash
docker compose -f docker-compose.nod.yml up -d --build
```

## CLI usage (flags)
The container (and `docker-compose.nod.yml`) runs `python main.py scrape ...` inside `news-crawler/app/`.

### Command
```bash
python main.py scrape [OPTIONS]
```

### Options
| Option | Default | Notes |
| --- | --- | --- |
| `--feeds-file PATH` | `data/feeds_de.txt` | Path to the feeds list. |
| `--lang NAME` | `german` | Language folder name for NoDCore output (e.g. `german`, `english`). |
| `--out-dir DIR` | `out/nod` | Output directory root for `.bz2` files. |
| `--day {yesterday,today,ISO}` | `yesterday` | Accepts `today`, `yesterday`, an ISO date (`2026-01-26`) or ISO datetime (`2026-01-26T12:30:00`). |
| `--content-source {article,feed}` | `article` | Extract sentences from fetched article HTML (`article`) or from feed summary (`feed`). |
| `-v`, `--verbose` | off | Enable verbose output. |

### Examples
Run locally (from `news-crawler/app/`):
```bash
python main.py scrape --day today --verbose
```

Override the crawler command via docker compose (from `news-crawler/`):
```bash
docker compose -f docker-compose.nod.yml run --rm crawler \
  python main.py scrape --day 2026-01-26 --content-source feed
```

## NoDCore integration
Start the full stack via `docker compose -f docker-compose.nod.yml up --build` (see “Start NoD stack” above).
The crawler writes daily corpora to `news-crawler/out/nod/german/YYYYMMDD.bz2`, and `nodcore` reads the same folder via a bind mount.

