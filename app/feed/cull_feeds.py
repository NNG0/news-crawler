from pathlib import Path
from datetime import datetime
from typing import List, Set, Tuple


def load_feed_urls(feeds_file: Path) -> List[str]:
    """Load feed URLs from file, preserving comments and blank lines"""
    if not feeds_file.exists():
        raise FileNotFoundError(f"Feeds file not found: {feeds_file}")
    
    return feeds_file.read_text(encoding="utf-8").splitlines()


def load_failures(failures_file: Path) -> Set[str]:
    """Load failed URLs from failures.log"""
    if not failures_file.exists():
        return set()
    
    failed_urls = set()
    for line in failures_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            failed_urls.add(line)
    
    return failed_urls


def cull_feeds(
    feeds_file: str | Path,
    failures_file: str | Path,
    output_feeds_file: str | Path = None,
    log_file: str | Path = None,
    dry_run: bool = False,
    verbose: bool = True
) -> Tuple[int, int, int, List[str], List[str]]:
    feeds_path = Path(feeds_file)
    failures_path = Path(failures_file)
    
    # Load data
    feed_lines = load_feed_urls(feeds_path)
    failed_urls = load_failures(failures_path)
    
    if verbose:
        print(f"Loaded {len(feed_lines)} lines from {feeds_path.name}")
        print(f"Loaded {len(failed_urls)} failed URLs from {failures_path.name}")
    
    # proces feed lines
    kept_lines = []
    removed_failed = []
    removed_duplicates = []
    original_feed_count = 0
    seen_urls = set()
    
    for line in feed_lines:
        stripped = line.strip()
        
        #dont remove comments/blank lines
        if not stripped or stripped.startswith("#"):
            kept_lines.append(line)
            continue
        
        original_feed_count += 1
        
        # Check if this URL failed
        if stripped in failed_urls:
            removed_failed.append(stripped)
            if verbose:
                print(f"  Removing (failed): {stripped}")
            continue
        
        # check for duplicate
        if stripped in seen_urls:
            removed_duplicates.append(stripped)
            if verbose:
                print(f"  Removing (duplicate): {stripped}")
            continue
        
        # Keep this URL
        seen_urls.add(stripped)
        kept_lines.append(line)
    
    # Calculate results
    total_removed = len(removed_failed) + len(removed_duplicates)
    remaining_feed_count = original_feed_count - total_removed
    
    # Determine output paths
    if output_feeds_file is None:
        output_feeds_file = feeds_path
    else:
        output_feeds_file = Path(output_feeds_file)
    
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = feeds_path.parent / f"cull_log_{timestamp}.txt"
    else:
        log_file = Path(log_file)
    
    # Write results (unless dry run)
    if not dry_run:
        # Write updated feeds file
        output_feeds_file.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
        
        # Write log file
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Feed Cull Log - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Feeds file: {feeds_path}\n")
            f.write(f"Failures file: {failures_path}\n\n")
            f.write(f"Original feed count: {original_feed_count}\n")
            f.write(f"Removed [not working]: {len(removed_failed)}\n")
            f.write(f"Removed [duplicate]: {len(removed_duplicates)}\n")
            f.write(f"Total removed: {total_removed}\n")
            f.write(f"Remaining: {remaining_feed_count}\n")
            if original_feed_count > 0:
                f.write(f"Removal rate: {total_removed/original_feed_count*100:.1f}%\n")
            f.write("\n")
            
            if removed_failed:
                f.write("Removed URLs (Not Working):\n")
                f.write("-" * 60 + "\n")
                for url in removed_failed:
                    f.write(f"{url}\n")
                f.write("\n")
            
            if removed_duplicates:
                f.write("Removed URLs (Duplicates):\n")
                f.write("-" * 60 + "\n")
                for url in removed_duplicates:
                    f.write(f"{url}\n")
        
        if verbose:
            print(f"\n✓ Updated feeds file: {output_feeds_file}")
            print(f"✓ Created log file: {log_file}")
    else:
        if verbose:
            print(f"\n[DRY RUN] Would update: {output_feeds_file}")
            print(f"[DRY RUN] Would create log: {log_file}")
    
    # Print summary
    if verbose:
        print(f"\n=== Summary ===")
        print(f"Original feeds: {original_feed_count}")
        print(f"Removed [not working]: {len(removed_failed)}")
        print(f"Removed [duplicate]: {len(removed_duplicates)}")
        print(f"Total removed: {total_removed}")
        print(f"Remaining: {remaining_feed_count}")
        if original_feed_count > 0:
            print(f"Removal rate: {total_removed/original_feed_count*100:.1f}%")
    
    return original_feed_count, len(removed_failed), len(removed_duplicates), removed_failed, removed_duplicates


def cull_multiple_languages(
    base_dir: str | Path = "data",
    failures_dir: str | Path = "out/nod",
    dry_run: bool = False,
    verbose: bool = True
) -> None:
    """
    Cull feeds for multiple languages.
    
    Looks for:
    - data/feeds_de.txt, data/feeds_en.txt, etc.
    - out/nod/de/failures.log, out/nod/en/failures.log, etc.
    
    Args:
        base_dir: Directory containing feeds_*.txt files
        failures_dir: Directory containing lang/failures.log files
        dry_run: If True, don't modify files
        verbose: Print progress
    """
    base_path = Path(base_dir)
    failures_path = Path(failures_dir)
    
    # Find all feeds_*.txt files
    feed_files = list(base_path.glob("feeds_*.txt"))
    
    if not feed_files:
        print(f"No feeds_*.txt files found in {base_path}")
        return
    
    for feeds_file in feed_files:
        # Extract language code from filename (e.g., feeds_de.txt -> de)
        lang = feeds_file.stem.replace("feeds_", "")
        
        # Find corresponding failures.log
        failures_file = failures_path / lang / "failures.log"
        
        if not failures_file.exists():
            if verbose:
                print(f"\nSkipping {feeds_file.name}: no failures.log found")
            continue
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Processing {feeds_file.name} (lang: {lang})")
            print(f"{'='*60}")
        
        cull_feeds(
            feeds_file=feeds_file,
            failures_file=failures_file,
            dry_run=dry_run,
            verbose=verbose
        )


def main():
    """Command-line interface for feed culler"""
    import argparse
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Remove failed feeds from feeds list"
    )
    parser.add_argument(
        "--feeds-file",
        default=BASE_DIR / "data" / "feeds_de.txt",
        help="Path to feeds file"
    )

    parser.add_argument(
        "--failures-file",
        default=BASE_DIR / "out" / "nod" / "de" / "failures.log",
        help="Path to failures.log"
    )
    parser.add_argument(
        "--output",
        help="Output feeds file (default: overwrite input)"
    )
    parser.add_argument(
        "--log",
        help="Log file path (default: auto-generated)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't modify files, just report what would be done"
    )
    parser.add_argument(
        "--all-langs",
        action="store_true",
        help="Process all languages (looks for feeds_*.txt and corresponding failures.log)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    if args.all_langs:
        cull_multiple_languages(
            base_dir="data",
            failures_dir="out/nod",
            dry_run=args.dry_run,
            verbose=not args.quiet
        )
    else:
        cull_feeds(
            feeds_file=args.feeds_file,
            failures_file=args.failures_file,
            output_feeds_file=args.output,
            log_file=args.log,
            dry_run=args.dry_run,
            verbose=not args.quiet
        )


if __name__ == "__main__":
    main()