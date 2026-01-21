import argparse
from datetime import datetime
from pathlib import Path
from feed.parse_feeds import parse_and_export


def main():
    parser = argparse.ArgumentParser(description="News crawler with NoDCore export")
    parser.add_argument("cmd", choices=["scrape"], help="Command to run")
    parser.add_argument("--feeds-file", default="data/feeds_de.txt", help="Path to feeds file")
    parser.add_argument("--lang", default="de", help="Language code (de, en, etc.)")
    parser.add_argument("--out-dir", default="out/nod", help="Output directory for .bz2 files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.cmd == "scrape":
        now = datetime.now()
        
        created_files = parse_and_export(
            feeds_file=args.feeds_file,
            lang=args.lang,
            out_root=args.out_dir,
            day=now,
            verbose=args.verbose
        )
        
        print(f"\n✓ Pipeline complete!")
        print(f"  Created {len(created_files)} .bz2 file(s)")
        for f in created_files:
            print(f"    {f}")


if __name__ == "__main__":
    main()