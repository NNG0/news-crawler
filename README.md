# news-crawler
This project is crawling, extracting, indexing and processing the content of daily published news articles. This project also provides tooling to extract and preprocess the content for the [NoD](https://github.com/uhh-lt/NoDCore) project. This project is a reimplementation of [news-crawler](https://github.com/uhh-lt/news-crawler) in python.

## start project
```bash
sudo docker compose up --build
```

## NoDCore integration
Run from `news-crawler/` so `${PWD}` volume mounts resolve correctly:
```bash
docker compose -f docker-compose.nod.yml up --build
```
The crawler writes daily corpora to `news-crawler/out/nod/german/YYYYMMDD.bz2`, and `nodcore` reads the same folder via a bind mount.

## architecture

[News Sources]
      ↓
[Python Crawler]
      ↓
[Article Text Extraction]
      ↓
[NLP: NER + Relation Extraction]
      ↓
[Entity Normalization]
      ↓
[Export in Existing Format]
      ↓
[Visualizer]
