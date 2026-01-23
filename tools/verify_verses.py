import sys
import os
import json
import re
import difflib
from typing import List, Dict, Tuple, Optional

# Add venv site-packages to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'venv/lib/python3.13/site-packages'))

try:
    from pysword.modules import SwordModules
except ImportError:
    pass

class BibleVerifier:
    def __init__(self, entries_path: str, bible_path: str):
        self.entries_path = entries_path
        self.bible_path = bible_path
        self.entries = []
        self.kjv = None
        self.book_map = {} 
        self.bible_structure = None
        
        self.manual_review_list = []
        self.corrections_count = 0
        self.expanded_refs_count = 0
        self.verified_count = 0
        
        self.load_entries()
        self.load_bible()
        self.build_book_map()

    def load_entries(self):
        with open(self.entries_path, 'r', encoding='utf-8') as f:
            self.entries = json.load(f)
            
    def load_bible(self):
        modules = SwordModules(self.bible_path)
        try:
            modules.parse_modules()
            self.kjv = modules.get_bible_from_module('KJV')
            self.bible_structure = self.kjv.get_structure()
        except Exception as e:
            print(f"Failed to load Bible: {e}")
            sys.exit(1)

    def build_book_map(self):
        sword_books = []
        tree = self.bible_structure.get_books()
        for testament in ['ot', 'nt']:
             if testament in tree:
                 for book in tree[testament]:
                     sword_books.append(book.name)
        
        self.book_map = {}
        for b in sword_books:
            self.book_map[b] = b
            if b.startswith('I '):
                self.book_map[b.replace('I ', '1 ')] = b
            if b.startswith('II '):
                self.book_map[b.replace('II ', '2 ')] = b
            if b.startswith('III '):
                self.book_map[b.replace('III ', '3 ')] = b
                
        self.book_map['Psalm'] = 'Psalms'
        self.book_map['Revelation'] = 'Revelation of John'
        self.book_map['Song of Solomon'] = 'Song of Solomon'
        self.book_map['Canticles'] = 'Song of Solomon'
        
    def normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def get_verse_text(self, book: str, chapter: int, verse: int) -> str:
        try:
            return self.kjv.get(books=[book], chapters=[chapter], verses=[verse])
        except:
            return ""

    def parse_ref(self, ref: str) -> Optional[Dict]:
        single_chap_books = ['Jude', 'Philemon', 'Obadiah', '2 John', '3 John', 'II John', 'III John']
        
        match = re.match(r'^(\d?\s?[A-Za-z ]+)\s+(\d+)(?::([\d\-, ]+))?$', ref.strip())
        if not match:
            return None
            
        book_name = match.group(1).strip()
        val = int(match.group(2))
        verses_str = match.group(3)
        
        verses = []
        chapter = val
        
        if verses_str:
            parts = verses_str.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    s, e = part.split('-')
                    verses.extend(range(int(s), int(e)+1))
                else:
                    verses.append(int(part))
        else:
            # "Book Num" -> Could be "Psalm 23" (Full Chap) or "Jude 21" (Verse)
            is_single = False
            for sb in single_chap_books:
                if book_name == sb or book_name == sb.replace('II ', '2 ').replace('III ', '3 '):
                    is_single = True
                    break
            
            if is_single:
                chapter = 1
                verses = [val]
            else:
                # Full chapter
                pass
            
        return {
            'book': book_name,
            'chapter': chapter,
            'verses': verses
        }

    def get_chapter_data(self, book: str, chapter: int) -> Tuple[Dict[int, str], str, List[Tuple[int, int, int]]]:
        raw_verses = {}
        norm_full_text = ""
        norm_v_map = []
        
        for v in range(1, 200):
            t = self.get_verse_text(book, chapter, v)
            if not t:
                if not self.get_verse_text(book, chapter, v+1): break
                continue
            
            raw_verses[v] = t
            nt = self.normalize_text(t)
            start = len(norm_full_text)
            if start > 0:
                norm_full_text += " "
                start += 1
            
            norm_full_text += nt
            end = len(norm_full_text)
            norm_v_map.append((start, end, v))
            
        return raw_verses, norm_full_text, norm_v_map

    def format_verses(self, verses: List[int]) -> str:
        if not verses: return ""
        verses = sorted(list(set(verses)))
        ranges = []
        start = verses[0]
        prev = start
        for v in verses[1:]:
            if v == prev + 1:
                prev = v
            else:
                ranges.append((start, prev))
                start = v
                prev = v
        ranges.append((start, prev))
        
        parts = []
        for s, e in ranges:
            if s == e:
                parts.append(str(s))
            else:
                parts.append(f"{s}-{e}")
        return ", ".join(parts)

    def verify_entry(self, entry):
        ref = entry.get('verse_ref')
        text = entry.get('bible_verse')
        mmdd = entry.get('mmdd')
        
        if not ref or not text:
            self.manual_review_list.append({'entry': entry, 'reason': "Missing ref or text"})
            return

        parsed = self.parse_ref(ref)
        if not parsed:
            self.manual_review_list.append({'entry': entry, 'reason': f"Unparseable ref: {ref}"})
            return

        book_key = self.book_map.get(parsed['book'])
        if not book_key:
             self.manual_review_list.append({'entry': entry, 'reason': f"Unknown book: {parsed['book']}"})
             return
             
        raw_verses, norm_full_text, norm_v_map = self.get_chapter_data(book_key, parsed['chapter'])
        
        if not raw_verses:
             self.manual_review_list.append({'entry': entry, 'reason': f"Empty chapter: {book_key} {parsed['chapter']}"})
             return

        target_norm_text = ""
        for v in parsed['verses']:
             if v in raw_verses:
                 if target_norm_text: target_norm_text += " "
                 target_norm_text += self.normalize_text(raw_verses[v])
        
        norm_entry = self.normalize_text(text)
        
        strict_matcher = difflib.SequenceMatcher(None, norm_entry, target_norm_text)
        strict_ratio = strict_matcher.ratio()
        
        if strict_ratio > 0.85:
             new_text = " ".join([raw_verses[v] for v in parsed['verses'] if v in raw_verses])
             
             if self.normalize_text(new_text) != self.normalize_text(text):
                 entry['bible_verse'] = new_text
                 self.corrections_count += 1
             
             self.verified_count += 1
             return

        # Check for Subsequence / Edited Match (e.g. "Verse part A... Verse part B")
        # We check against target_norm_text (the verses in ref)
        block_matcher = difflib.SequenceMatcher(None, target_norm_text, norm_entry)
        matches = block_matcher.get_matching_blocks()
        matched_len = sum(m.size for m in matches)
        subseq_ratio = matched_len / len(norm_entry) if len(norm_entry) > 0 else 0
        
        if subseq_ratio > 0.90:
             # High subsequence match implies valid editing/skipping
             # We assume text is mostly correct (or intentionally edited)
             # To be safe, we don't auto-correct edited text to avoid breaking ellipses
             self.verified_count += 1
             return

        matcher = difflib.SequenceMatcher(None, norm_full_text, norm_entry)
        match = matcher.find_longest_match(0, len(norm_full_text), 0, len(norm_entry))
        
        match_ratio = match.size / len(norm_entry) if len(norm_entry) > 0 else 0
        
        if match_ratio > 0.85:
             match_start = match.a
             match_end = match.a + match.size
             
             covered_verses = []
             for (vs, ve, vnum) in norm_v_map:
                 if max(match_start, vs) < min(match_end, ve):
                     covered_verses.append(vnum)
             
             if not covered_verses:
                 self.manual_review_list.append({'entry': entry, 'reason': "Match found but no verses mapped?"})
                 return

             new_ref_str = f"{parsed['book']} {parsed['chapter']}:{self.format_verses(covered_verses)}"
             
             old_set = set(parsed['verses'])
             new_set = set(covered_verses)
             new_text = " ".join([raw_verses[v] for v in covered_verses])

             if old_set != new_set:
                 entry['verse_ref'] = new_ref_str
                 entry['bible_verse'] = new_text
                 self.expanded_refs_count += 1
             else:
                 if self.normalize_text(new_text) != self.normalize_text(text):
                    entry['bible_verse'] = new_text
                    self.corrections_count += 1
             
             self.verified_count += 1
             return
             
        self.manual_review_list.append({
            'entry': entry, 
            'reason': f"Low match ({max(strict_ratio, match_ratio):.2f})",
            'ref_text_len': len(target_norm_text),
            'entry_len': len(norm_entry)
        })

    def run(self):
        print(f"Processing {len(self.entries)} entries...")
        for entry in self.entries:
            self.verify_entry(entry)
            
        print(f"Verified: {self.verified_count}")
        print(f"Corrections (Text only): {self.corrections_count}")
        print(f"Ref Expansions: {self.expanded_refs_count}")
        print(f"Manual Review: {len(self.manual_review_list)}")
        
        with open('docs/verse_review.md', 'w') as f:
            f.write("# Verse Review Report\n\n")
            f.write(f"- Verified: {self.verified_count}\n")
            f.write(f"- Corrections: {self.corrections_count}\n")
            f.write(f"- Ref Expansions: {self.expanded_refs_count}\n")
            f.write(f"- Manual Review: {len(self.manual_review_list)}\n\n")
            
            f.write("## Manual Review Items\n")
            for item in self.manual_review_list:
                e = item['entry']
                f.write(f"### {e.get('mmdd')} - {e.get('title')}\n")
                f.write(f"- Ref: `{e.get('verse_ref')}`\n")
                f.write(f"- Reason: {item['reason']}\n")
                f.write(f"- Entry Text: {e.get('bible_verse')}\n")
                f.write("\n")
                
        with open('data/entries.json', 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    verifier = BibleVerifier('data/entries.json', 'data/kjv-bible')
    verifier.run()
