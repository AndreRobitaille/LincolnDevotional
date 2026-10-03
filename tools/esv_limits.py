"""Count cached ESV passages against verse totals in the bundled KJV module."""

from collections import Counter
from pathlib import Path
import re
import struct
import zlib


KJV_PATH = Path(__file__).resolve().parent.parent / "data" / "kjv-bible"
# Reference names to SWORD/OSIS identifiers, not verse totals.
BOOK_IDS = dict(pair.split("=") for pair in (
    "Genesis=Gen|Exodus=Exod|Leviticus=Lev|Numbers=Num|Deuteronomy=Deut|"
    "Joshua=Josh|Judges=Judg|Ruth=Ruth|1 Samuel=1Sam|2 Samuel=2Sam|"
    "1 Kings=1Kgs|2 Kings=2Kgs|1 Chronicles=1Chr|2 Chronicles=2Chr|"
    "Ezra=Ezra|Nehemiah=Neh|Esther=Esth|Job=Job|Psalm=Ps|Psalms=Ps|"
    "Proverbs=Prov|Ecclesiastes=Eccl|Song of Solomon=Song|Isaiah=Isa|"
    "Jeremiah=Jer|Lamentations=Lam|Ezekiel=Ezek|Daniel=Dan|Hosea=Hos|"
    "Joel=Joel|Amos=Amos|Obadiah=Obad|Jonah=Jonah|Micah=Mic|Nahum=Nah|"
    "Habakkuk=Hab|Zephaniah=Zeph|Haggai=Hag|Zechariah=Zech|Malachi=Mal|"
    "Matthew=Matt|Mark=Mark|Luke=Luke|John=John|Acts=Acts|Romans=Rom|"
    "1 Corinthians=1Cor|2 Corinthians=2Cor|Galatians=Gal|Ephesians=Eph|"
    "Philippians=Phil|Colossians=Col|1 Thessalonians=1Thess|"
    "2 Thessalonians=2Thess|1 Timothy=1Tim|2 Timothy=2Tim|Titus=Titus|"
    "Philemon=Phlm|Hebrews=Heb|James=Jas|1 Peter=1Pet|2 Peter=2Pet|"
    "1 John=1John|2 John=2John|3 John=3John|Jude=Jude|Revelation=Rev"
).split("|"))


def load_kjv_verse_counts(bible_path=KJV_PATH):
    """Read chapter lengths from this book-compressed SWORD zText module.

    .bzs records contain compressed-block offset, size, and uncompressed size
    (three little-endian uint32s). .bzv records contain block number, text
    offset, and length (uint32, uint32, uint16). Each verse has one record;
    book/chapter introductions carry OSIS opening milestones instead.
    Closing milestones belong to the last verse and must not reset counts.
    """
    module_path = Path(bible_path) / "modules" / "texts" / "ztext" / "kjv"
    counts = {}
    for testament in ("ot", "nt"):
        compressed = (module_path / f"{testament}.bzz").read_bytes()
        blocks = []
        for offset, size, raw_size in struct.iter_unpack(
            "<III", (module_path / f"{testament}.bzs").read_bytes()
        ):
            block = zlib.decompress(compressed[offset:offset + size])
            if len(block) != raw_size:
                raise ValueError("Invalid KJV compressed block size")
            blocks.append(block)

        book = chapter = None
        for block_number, offset, length in struct.iter_unpack(
            "<IIH", (module_path / f"{testament}.bzv").read_bytes()
        ):
            if not length:
                continue
            text = blocks[block_number][offset:offset + length].decode("utf-8")
            book_start = re.search(
                r'<div\b(?=[^>]*\bsID=)(?=[^>]*\btype="book")[^>]*\bosisID="([^"]+)"',
                text,
            )
            chapter_start = re.search(
                r'<chapter\b(?=[^>]*\bsID=)[^>]*\bosisID="([^"]+)"', text
            )
            if book_start:
                book = book_start[1]
                chapter = None
                counts[book] = {}
            elif chapter_start:
                chapter = int(chapter_start[1].split(".")[-1])
                counts[book][chapter] = 0
            elif book and chapter:
                counts[book][chapter] += 1

    if set(counts) != set(BOOK_IDS.values()) or any(
        not chapters or any(total <= 0 for total in chapters.values())
        for chapters in counts.values()
    ):
        raise ValueError("Incomplete KJV module verse counts")
    return counts


def expand_reference(reference, verse_counts):
    """Expand ranges, comma lists, and single-chapter references into verses."""
    if not isinstance(reference, str):
        raise ValueError(f"Missing ESV reference: {reference!r}")
    match = re.fullmatch(r"(.+?)\s+(\d[\d\s,:;\-–]*)", reference.strip())
    if not match or match[1] not in BOOK_IDS:
        raise ValueError(f"Unsupported ESV reference: {reference!r}")
    book = BOOK_IDS[match[1]]
    chapters = verse_counts[book]
    current_chapter = 1 if len(chapters) == 1 else None
    verses = []
    for part in re.split(r"[,;]", match[2].replace("–", "-")):
        span = re.fullmatch(
            r"\s*(?:(\d+):)?(\d+)(?:\s*-\s*(?:(\d+):)?(\d+))?\s*", part
        )
        if not span:
            raise ValueError(f"Unsupported ESV reference: {reference!r}")
        start_chapter = int(span[1]) if span[1] else current_chapter
        end_chapter = int(span[3]) if span[3] else start_chapter
        start_verse = int(span[2])
        end_verse = int(span[4]) if span[4] else start_verse
        if (
            start_chapter not in chapters or end_chapter not in chapters
            or not 1 <= start_verse <= chapters[start_chapter]
            or not 1 <= end_verse <= chapters[end_chapter]
            or (end_chapter, end_verse) < (start_chapter, start_verse)
        ):
            raise ValueError(f"Invalid ESV verse range: {reference!r}")
        for chapter in range(start_chapter, end_chapter + 1):
            first = start_verse if chapter == start_chapter else 1
            last = end_verse if chapter == end_chapter else chapters[chapter]
            verses.extend((book, chapter, verse) for verse in range(first, last + 1))
        current_chapter = end_chapter
    return verses


def validate_esv_cache(esv_cache, verse_counts=None):
    """Fail closed on uncountable references or either cache limit.

    Count occurrences, including overlaps and repeats, conservatively rather
    than deduplicating verses that are quoted by more than one entry.
    """
    if verse_counts is None:
        verse_counts = load_kjv_verse_counts()
    by_book = Counter()
    for cached in esv_cache.values():
        verses = expand_reference(cached.get("ref"), verse_counts)
        by_book.update(book for book, _, _ in verses)
    total = sum(by_book.values())
    if total > 500:
        raise ValueError(f"ESV cache contains {total} verses; maximum is 500")
    for book, count in by_book.items():
        book_total = sum(verse_counts[book].values())
        if count * 2 > book_total:
            raise ValueError(
                f"ESV cache contains {count}/{book_total} verses of {book}; maximum is half"
            )
    return total
