import argparse
import json
import os
import time
import urllib.request
import urllib.parse
from pathlib import Path

# Configuration
API_URL = "https://api.esv.org/v3/passage/text/"
DATA_DIR = Path(__file__).parent.parent / "data"
ENTRIES_FILE = DATA_DIR / "entries.json"
CACHE_FILE = DATA_DIR / "esv_cache.json"

def load_env():
    """Simple .env loader to avoid dependencies."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        # Sort keys to keep file diffs clean
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)

def fetch_esv(reference, api_key):
    params = {
        "q": reference,
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-short-copyright": "false",
        "include-passage-references": "false",
        "indent-paragraphs": "0",
        "indent-poetry": "false",
        "indent-declares": "0",
        "indent-psalm-doxology": "0"
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{API_URL}?{query_string}"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Token {api_key}")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return "".join(data.get("passages", [])).strip()
    except Exception as e:
        print(f"Error fetching {reference}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Fetch ESV verses for the devotional.")
    parser.add_argument("--date", help="Fetch a single date (MMDD format), e.g., 0101")
    parser.add_argument("--month", type=int, help="Fetch an entire month (1-12)")
    parser.add_argument("--all", action="store_true", help="Fetch ALL entries (entire year)")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already cached")
    args = parser.parse_args()

    # If no arguments provided, print help and exit
    if not (args.date or args.month or args.all):
        parser.print_help()
        return

    load_env()
    api_key = os.environ.get("ESV_API_KEY")
    
    if not api_key:
        print("Error: ESV_API_KEY not found in environment or .env file.")
        print("Please create a .env file in the project root with: ESV_API_KEY=your_key_here")
        return

    entries = load_json(ENTRIES_FILE)
    cache = load_json(CACHE_FILE)
    
    # Filter entries based on arguments
    targets = []
    if args.date:
        targets = [e for e in entries if e["mmdd"] == args.date]
        if not targets:
            print(f"No entry found for date {args.date}")
            return
    elif args.month:
        targets = [e for e in entries if e["month"] == args.month]
        if not targets:
            print(f"No entries found for month {args.month}")
            return
    elif args.all:
        print("Fetching ALL entries.")
        confirm = input("Are you sure you want to fetch up to 366 entries? (y/N) ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
        targets = entries

    updated_count = 0
    print(f"Targeting {len(targets)} entries...")
    
    for i, entry in enumerate(targets):
        mmdd = entry["mmdd"]
        verse_ref = entry["verse_ref"]
        
        if not args.force and mmdd in cache:
            # Skip silent if filtered, or maybe verbose? Let's just skip.
            if len(targets) == 1:
                print(f"{mmdd} already in cache. Use --force to update.")
            continue
            
        print(f"[{i+1}/{len(targets)}] Fetching {mmdd}: {verse_ref}")
        esv_text = fetch_esv(verse_ref, api_key)
        
        if esv_text:
            cache[mmdd] = {
                "ref": verse_ref,
                "text": esv_text
            }
            updated_count += 1
            save_json(CACHE_FILE, cache)
            
            # Rate limiting: 1 second delay to be safe (60 req/min max)
            time.sleep(1.0)
        else:
            print(f"Failed to fetch text for {verse_ref}")

    print(f"Done. Added/Updated {updated_count} entries.")

if __name__ == "__main__":
    main()
