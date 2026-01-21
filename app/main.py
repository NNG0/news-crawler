import argparse
from datetime import datetime

from feed.parse_feeds import parse_feeds, store_feeds

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["feeds"], help="Command to run")
    parser.add_argument("--feeds-file", default="data/feeds_de.txt")
    parser.add_argument("--lang", default="german")
    parser.add_argument("--out-dir", default="out/feeds")

    args = parser.parse_args()

    if args.cmd == "feeds":
        now = datetime.now()
        feeds, failed = parse_feeds(args.feeds_file, day=now)
        out_path = store_feeds(
            feeds,
            lang=args.lang,
            day=now,
            out_dir=args.out_dir,
            failures=failed,
        )
        items = sum(len(feed.items) for feed in feeds)
        print(f"Wrote {out_path} (feeds={len(feeds)}, items={items}, failures={len(failed)})")
        return


if __name__ == "__main__":
    main()
