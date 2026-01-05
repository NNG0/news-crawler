# news-crawler
This project is crawling, extracting, indexing and processing the content of daily published news articles. This project also provides tooling to extract and preprocess the content for the [NoD](https://github.com/uhh-lt/NoDCore) project. This project is a reimplementation of [news-crawler](https://github.com/uhh-lt/news-crawler) in python.

## start project
```bash
sudo docker compose up --build
```

## todo-list
- [ ] analyze current crawler
    - [ ] list of features
    - [ ] data access
    - [ ] integration into frontend
- [ ] implementation
    - [ ] fetching feeds
    - [ ] extracting data 
    - [ ] data processing
        - [ ] NER
        - [ ] relationship clusters
    - [ ] output formatting
- [ ] evaluation
    - [ ] validate completeness and correctness

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
