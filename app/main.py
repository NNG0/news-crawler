import argparse
from feed.parse_feeds import parse_feeds
from ner import pipeline as ner_pipeline



def main():
    parser = argparse.ArgumentParser(description="News crawler with feed parsing and NER")
    parser.add_argument('--parse-feeds', action='store_true', help='Parse RSS/Atom feeds')
    parser.add_argument('--ner', action='store_true', help='Perform Named Entity Recognition on feeds')
    parser.add_argument('--model', type=str, default='de_core_news_sm', 
                        help='spaCy model for NER (default: de_core_news_sm)')
    parser.add_argument('--feed-path', type=str, default='news-crawler/app/data/feeds_output.json',
                        help='Path to feed JSON file')
    parser.add_argument('--output-path', type=str, default='news-crawler/app/data/feeds_with_ner.json',
                        help='Path to save NER results')
    
    args = parser.parse_args()
    
    # If no arguments provided, run both parse and NER
    if not args.parse_feeds and not args.ner:
        print("Running full pipeline: parsing feeds and performing NER...")
        parse_feeds()
        ner_pipeline(
            feed_path=args.feed_path,
            model=args.model,
            output_path=args.output_path
        )
    else:
        if args.parse_feeds:
            print("Parsing feeds...")
            parse_feeds()
        
        if args.ner:
            print(f"Performing NER with model: {args.model}")
            ner_pipeline(
                feed_path=args.feed_path,
                model=args.model,
                output_path=args.output_path
            )

if __name__ == "__main__":
    main()
