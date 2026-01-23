import json
from pathlib import Path
import sys

def audit_esv():
    data_dir = Path("data")
    entries_file = data_dir / "entries.json"
    cache_file = data_dir / "esv_cache.json"

    if not entries_file.exists() or not cache_file.exists():
        print("Error: Missing data files.")
        return

    with open(entries_file, "r", encoding="utf-8") as f:
        entries = json.load(f)
    
    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)

    entries_map = {e["mmdd"]: e for e in entries}
    
    issues_found = 0
    
    print(f"{'MMDD':<6} | {'Issue Type':<20} | {'Details':<50}")
    print("-" * 80)

    for mmdd, entry in entries_map.items():
        if mmdd not in cache:
            print(f"{mmdd:<6} | Missing in Cache     | Entry exists in entries.json but not in esv_cache.json")
            issues_found += 1
            continue

        esv_data = cache[mmdd]
        kjv_text = entry.get("bible_verse", "")
        esv_text = esv_data.get("text", "")
        
        # 1. Check Reference Mismatch
        # normalize spaces
        entry_ref = " ".join(entry.get("verse_ref", "").split())
        cache_ref = " ".join(esv_data.get("ref", "").split())
        
        if entry_ref != cache_ref:
             print(f"{mmdd:<6} | Ref Mismatch         | Entry: '{entry_ref}' vs Cache: '{cache_ref}'")
             issues_found += 1

        # 2. Check for Empty Text
        if not esv_text.strip():
            print(f"{mmdd:<6} | Empty Text           | ESV text is empty")
            issues_found += 1
            continue

        # 3. Check Length Discrepancy (Heuristic)
        # ESV and KJV shouldn't differ wildly in length usually.
        # Length check: < 50% or > 200% length might indicate missing verses or extra content.
        kjv_len = len(kjv_text)
        esv_len = len(esv_text)
        
        if kjv_len > 0:
            ratio = esv_len / kjv_len
            if ratio < 0.5:
                print(f"{mmdd:<6} | Length Warning (Low) | ESV is {int(ratio*100)}% length of KJV. ({esv_len} vs {kjv_len} chars)")
                # Print snippet for context
                # print(f"       KJV: {kjv_text[:50]}...")
                # print(f"       ESV: {esv_text[:50]}...")
                issues_found += 1
            elif ratio > 2.0:
                print(f"{mmdd:<6} | Length Warning (High)| ESV is {int(ratio*100)}% length of KJV. ({esv_len} vs {kjv_len} chars)")
                issues_found += 1

        # 4. Check for suspicious endings (truncation)
        # If it doesn't end with punctuation or quote
        valid_endings = ('.', '!', '?', '"', '”', "'", "’")
        if not esv_text.strip().endswith(valid_endings):
             print(f"{mmdd:<6} | Suspicious Ending    | Ends with: '{esv_text.strip()[-1]}'")
             issues_found += 1

    print("-" * 80)
    print(f"Audit complete. Found {issues_found} potential issues.")

if __name__ == "__main__":
    audit_esv()
