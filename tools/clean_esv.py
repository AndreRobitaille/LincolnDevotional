import json
from pathlib import Path
import sys

def clean_esv_cache():
    cache_file = Path("data/esv_cache.json")
    
    if not cache_file.exists():
        print("esv_cache.json not found.")
        return

    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)

    fixed_count = 0
    
    for mmdd, data in cache.items():
        text = data.get("text", "")
        if not text:
            continue
            
        original_text = text
        stripped = text.strip()
        
        # 1. Fix Endings
        if stripped.endswith(",") or stripped.endswith(";"):
            # Replace trailing comma/semicolon with period
            stripped = stripped[:-1] + "."
        elif stripped.endswith("—"):
             stripped = stripped[:-1] + "."
        elif stripped.endswith(":"):
             # Also catch colons just in case audit missed one
             stripped = stripped[:-1] + "."
        elif stripped[-1].isalpha():
            # If it ends with a letter, append period
            stripped = stripped + "."
            
        # 2. Fix Capitalization
        if len(stripped) > 0:
            first_char = stripped[0]
            # Standard capitalization
            if first_char.islower():
                stripped = first_char.upper() + stripped[1:]
            # Handle quotes: "knowing... -> "Knowing...
            elif first_char in ('"', '“', "'", '‘') and len(stripped) > 1:
                second_char = stripped[1]
                if second_char.islower():
                    stripped = first_char + second_char.upper() + stripped[2:]

        # 3. Clean up double spaces if any
        stripped = " ".join(stripped.split())
        
        if stripped != original_text:
            cache[mmdd]["text"] = stripped
            fixed_count += 1
            # Debug output (optional)
            # if original_text[0] != stripped[0]:
            #    print(f"Capitalized {mmdd}: {original_text[:20]}... -> {stripped[:20]}...")

    if fixed_count > 0:
        print(f"Fixed {fixed_count} entries.")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False, sort_keys=True)
    else:
        print("No entries needed fixing.")

if __name__ == "__main__":
    clean_esv_cache()
