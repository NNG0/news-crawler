import argparse
from feed.parse_feeds import parse_feeds

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('parse_feed')

    args = parser.parse_args()
    if args.parse_feed:
        print("feed args")
        parse_feeds()
    parse_feeds()


if __name__ == "__main__":
    main()
