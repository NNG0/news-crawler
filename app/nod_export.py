import bz2
from pathlib import Path
from datetime import date
from typing import Iterable, NamedTuple

class SentenceRecord(NamedTuple):
    text: str
    url: str
    day: date

def normalize_sentence(text: str) -> str:
    # Collapse whitespace and remove pipes
    text = " ".join(text.split())
    return text.replace("|", " ")

def should_keep(text: str) -> bool:
    return 20 <= len(text) <= 256 

def write_nod_corpus(
        sentences: Iterable[SentenceRecord],
        lang: str,
        out_root: Path = Path("out/nod"),
) -> None:
    """
    Group sentences by day and write one YYYYMMDD.bz2 file per day
    under out_root/lang/, in the exact format NoDCore expects
    """
    out_dir = out_root / lang
    out_dir.mkdir(parents=True, exist_ok=True)

    by_day = {}
    for rec in sentences:
        by_day.setdefault(rec.day, []).append(rec)
    
    for day, records in by_day.items():
        filename = day.strftime("%Y%m%d") + ".bz2"
        out_path = out_dir / filename

        with bz2.open(out_path, "wt", encoding="utf-8") as f:
            for rec in records:
                text = normalize_sentence(rec.text)
                if not should_keep(text):
                    continue
                if not rec.url:
                    continue
                f.write(f"{text}\t{rec.url}\n")