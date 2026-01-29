import argparse
from datetime import datetime, timedelta, date
from feed.parse_feeds import parse_and_export


def parse_day(value: str) -> datetime:
    v = value.strip().lower()
    now = datetime.now()
    if v == "today":
        return now
    if v == "yesterday":
        return now - timedelta(days=1)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.combine(date.fromisoformat(value), datetime.min.time())


def main():
    parser = argparse.ArgumentParser(description="News crawler with NoDCore export")
    parser.add_argument("cmd", choices=["scrape"], help="Command to run")
    parser.add_argument(
        "--feeds-file",
        default="data/feeds_de.txt",
        help="Path to feeds file",
    )
    parser.add_argument(
        "--lang",
        default="german",
        help="Language folder name for NoDCore output (e.g. german, english)",
    )
    parser.add_argument(
        "--out-dir",
        default="out/nod",
        help="Output directory root for .bz2 files",
    )
    parser.add_argument(
        "--day",
        default="yesterday",
        help="Which day to export (yesterday, today, or ISO date like 2026-01-26)",
    )
    parser.add_argument(
        "--content-source",
        choices=["article", "feed"],
        default="article",
        help='Extract sentences from fetched article HTML ("article") or from feed summary ("feed")',
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.cmd == "scrape":
        target_day = parse_day(args.day)
        
        created_files = parse_and_export(
            feeds_file=args.feeds_file,
            lang=args.lang,
            out_root=args.out_dir,
            day=target_day,
            content_source=args.content_source,
            verbose=args.verbose
        )
        
        print(f"\n✓ Pipeline complete!")
        print(f"  Created {len(created_files)} .bz2 file(s)")
        for f in created_files:
            print(f"    {f}")


if __name__ == "__main__":
    main()
