import sqlite3
from collections import defaultdict
import re
from ghtbooks import full_book_codes, book_codes

def is_latin_tag(word):
    """Detects Latin-script tags like 'TR/BM', 'Ax', 'TR(1550)/BM/Ax', etc."""
    return bool(re.fullmatch(r'[A-Za-z0-9/()]+', word))

def format_reference(num):

    # Convert to int to discard the decimal part
    whole = int(num)

    # Extract book, chapter, and verse
    book_num = whole // 10**6
    chapter = (whole // 10**3) % 1000
    verse = whole % 1000

    # Map book number to name
    book_name = book_codes.get(book_num, f"Book{book_num}")

    return f"{book_name} {chapter}:{verse}"

def reference_to_number(reference):
    # Split the reference
    try:
        book_part, rest = reference.strip().split()
        chapter_str, verse_str = rest.split(':')

        book_num = full_book_codes[book_part]
        chapter = int(chapter_str)
        verse = int(verse_str)

        number = book_num * 10**6 + chapter * 1000 + verse
        return number
    except Exception as e:
        raise ValueError("Invalid reference format. Use 'Book c:v'") from e

def load_verse_map(filepath):
    verse_map = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    for i in range(0, len(lines), 3):
        try:
            uid = reference_to_number(lines[i].strip())
            verse_text = lines[i + 1].strip()
            verse_map[uid] = verse_text.split()
        except (ValueError, IndexError):
            continue
    return verse_map

def update_guids(conn, verse_map):
    c = conn.cursor()

    # Find entries with empty or zero guid
    c.execute("SELECT uid, greek FROM entries WHERE guid IS NULL OR guid = 0 ORDER BY uid")
    # Reset all
    #c.execute("SELECT uid, greek FROM entries ORDER BY uid")
    entries = c.fetchall()

    last_uid = None
    seen = defaultdict(int)
    
    inputs = []

    updated = 0
    for uid, greek in entries:
        verse_id = int(uid)  # This strips off the decimal portion (bbcccvvv)
        verse_words = verse_map.get(verse_id)
        #print(greek)     
        #input(verse_words)
        if not verse_words:
            continue

        # Reset tracking when a new verse starts
        if verse_id != last_uid:
            seen = defaultdict(int)
            last_uid = verse_id

        try:
            count = seen.get(greek, 0)
            #input(count)
            occurrence = 0
            for i, word in enumerate(verse_words):
                if word == greek:
                    if occurrence == count:
                        position = i + 1  # 1-based index
                        break
                    occurrence += 1
            else:
                continue  # Not enough matches found

            if verse_id not in inputs:
                inputs.append(verse_id)

            seen[greek] = seen.get(greek, 0) + 1
            #input(seen[greek])
            newguid = round(int(uid) + position * 0.01, 2)
            #input(greek + str(newguid))
            c.execute("UPDATE entries SET guid = ? WHERE uid = ?", (newguid, uid))
            updated += 1
        except Exception as e:
            print(e)
            continue

    conn.commit()
    
    print(f"Updated {updated} entries.")
    return inputs

def next_check(conn):
    c = conn.cursor()

    # Find GUIDs with more than one matching entry
    c.execute("""
        SELECT guid
        FROM entries
        WHERE guid IS NOT NULL AND guid != 0
        GROUP BY guid
        HAVING COUNT(*) > 1
    """)
    duplicate_guids = [row[0] for row in c.fetchall()]
    print(f"Found {len(duplicate_guids)} duplicates")

    for guid in duplicate_guids:
        print(f"\nDuplicate guid found: {guid}")
        c.execute("SELECT english, greek, uid, raw FROM entries WHERE guid = ?", (guid,))
        rows = c.fetchall()
        

        for idx, row in enumerate(rows, 1):
            print(f"{idx}. EN: {row[0]}, GR: {row[1]}, UID: {row[2]}")

        for row in rows:
            new_guid = input(f"Set new guid for ID {row[0]} (leave blank to skip): ").strip()
            if new_guid:
                try:
                    new_guid = round(int(row[2]) + float(new_guid) * 0.01, 2)
                    c.execute("UPDATE entries SET guid = ? WHERE uid = ?", (new_guid, row[2]))
                    conn.commit()
                    print("Updated.")
                except ValueError:
                    print("Invalid number entered. Skipped.")

def second_pass(conn):
    c = conn.cursor()

    # Find entries with empty or zero guid
    c.execute("SELECT uid, greek FROM entries WHERE (guid IS NULL OR guid = 0) AND greek != 'none' ORDER BY uid")

    entries = c.fetchall()

    print(f"Found {len(entries)} remaining missing:")
    updated = 0

    for uid, greek in entries:
        verse_id = int(uid)  # This strips off the decimal portion (bbcccvvv)
   
        print(f"\nMissing entry found: {greek} {uid}")

        new_guid = input(f"Set new guid (leave blank to skip): ").strip()
        if new_guid:
            try:
                new_guid = round(int(uid) + float(new_guid) * 0.01, 2)
                c.execute("UPDATE entries SET guid = ? WHERE uid = ?", (new_guid, uid))
                conn.commit()
                print("Updated.")
            except ValueError:
                print("Invalid number entered. Skipped.")

    conn.commit()
    
    print(f"Updated {updated} entries.")

def clean_up(conn, verse_map, inputs):
    c = conn.cursor()
    #checkhowmany = 0
    i = 40001001
    while i < 66023000:
        if inputs:
            if i not in inputs:
                i += 1
                continue

        c.execute("SELECT uid, greek, guid FROM entries WHERE uid > ? AND uid < ? AND greek!='none' ORDER BY guid", (i, i+1))
        entries = c.fetchall()
        if entries:
            #print(i)
            guids = [round(guid % 1 * 100) for _, _, guid in entries if guid]
            expected = list(range(1, len(entries) + 1))

            if sorted(guids) != expected:
                #checkhowmany += 1
                #i += 1
                #continue
                #input(guids)
                #input(expected)
                print(f"\nProblem detected in verse: {format_reference(i)}")

                # Get expected Greek words from verse_map
                verse_words = verse_map.get(i)
                if not verse_words:
                    print("Verse text not found.")
                    i += 1
                    continue

                print("Verse text:")
                for idx, word in enumerate(verse_words, 1):
                    print(f"{idx}: {word}", end='  ')
                print("\n")

                greek_entries = [greek for _, greek, _ in entries]
                verse_word_counts = defaultdict(int)
                for word in verse_words:
                    verse_word_counts[word] += 1

                entry_word_counts = defaultdict(int)
                for word in greek_entries:
                    entry_word_counts[word] += 1

                used_positions = set()
                for uid, greek, guid in entries:
                    verse_matches = [idx + 1 for idx, word in enumerate(verse_words) if word == greek and (idx + 1) not in used_positions]

                    if verse_word_counts[greek] == entry_word_counts[greek]:
                        print(f"Word {greek} skipped.")
                        continue
                    print(f"\nEntry: {greek} {uid} {guid}")
                    if not verse_matches:
                        input("No match in verse text. Skipping.")
                        continue

                    print("Possible positions:", verse_matches)
                    try:
                        chosen = int(input(f"Choose correct position for '{greek}': "))
                        new_guid = round(i + chosen * 0.01, 2)
                        c.execute("UPDATE entries SET guid = ? WHERE uid = ?", (new_guid, uid))
                        print(f"Update entries with {new_guid} and {uid}")
                        conn.commit()
                    except Exception as e:
                        print("Error or invalid input. Skipped.")

                # Re-check and compress GUIDs
                c.execute("SELECT uid, guid FROM entries WHERE uid > ? AND uid < ? AND greek!='none' ORDER BY guid", (i, i + 1))

                updated = c.fetchall()
                for idx, (uid, old_guid) in enumerate(updated, 1): 
                    #input(uid + old_guid)
                    new_guid = round(i + idx * 0.01, 2)
                    if old_guid != new_guid:
                        c.execute("UPDATE entries SET guid = ? WHERE uid = ?", (new_guid, uid))
                        print(f"Update entries with {new_guid} and {uid}")
                conn.commit()
            i += 1
        else:
            if i % 1000 == 1:
                i = (round(i/1000000) + 1) * 1000000 + 1001
                #print(i)
                #print(checkhowmany)
            else:
                i = (round(i/1000) + 1) * 1000 + 1
    #print(checkhowmany)
    print("Done resolving word order conflicts.")

def verify_verse_map_words(conn, verse_map, inputs):
    c = conn.cursor()
    total_missing = 0

    for uid, words in verse_map.items():
        if inputs:
            if uid not in inputs:
                continue
        # Filter verse_map words
        filtered = []
        skip_next = False

        for word in words:
            if skip_next:
                skip_next = False
                continue
            if is_latin_tag(word):
                skip_next = True
                continue
            filtered.append(word)

        unique_filtered = set(filtered)

        if unique_filtered:
            # Fetch Greek words in DB for this verse
            c.execute("SELECT greek FROM entries WHERE uid > ? AND uid < ?", (uid, uid + 1))
            db_rows = c.fetchall()

            if not db_rows:
                print(f"\n Finished at Verse {format_reference(uid)}.")
                return  # Stop further processing entirely

            db_words = set(row[0] for row in db_rows)

            # Compare with DB
            missing = sorted(word for word in unique_filtered if word not in db_words)

            if missing:
                print(f"\nMissing in {format_reference(uid)}:")
                for word in missing:
                    print(f"  - {word}")
                total_missing += len(missing)

    print(f"Done. {total_missing} total missing word entries found.")

def split_tag(tag):
    return set(tag.split('/'))

def verify_variant_sets_against_db(conn, verse_map, verbose=False):
    """
    Check textual variant sets against the DB using GUID adjacency.

    Rules:
    - Only adjacent TAG–GREEK pairs with differing tags form a variant set
    - Sub-tag repetition closes a set
    - Failure if:
        * zero variant words present in DB
        * multiple variant words present and adjacent in DB by GUID
    - Success otherwise
    """
    c = conn.cursor()

    for uid, words in verse_map.items():
        # Fetch DB entries for this verse, sorted by GUID
        c.execute(
            "SELECT greek, guid FROM entries WHERE uid > ? AND uid < ? ORDER BY guid",
            (uid, uid + 1)
        )
        db_entries = c.fetchall()
        if not db_entries:
            continue

        db_words = [row[0] for row in db_entries]
        db_guids = [row[1] for row in db_entries]

        # --- Build variant sets ---
        variant_sets = []
        current = []
        seen_subtags = set()
        i = 0
        while i < len(words) - 1:
            if is_latin_tag(words[i]) and not is_latin_tag(words[i + 1]):
                tag = words[i]
                greek = words[i + 1]
                subtags = set(tag.split('/'))

                # Close set if sub-tag repeats
                if seen_subtags & subtags:
                    if len({t for t, _, _ in current}) > 1:
                        variant_sets.append(current)
                    current = []
                    seen_subtags = set()

                current.append((tag, greek, i))
                seen_subtags |= subtags
                i += 2
            else:
                if len({t for t, _, _ in current}) > 1:
                    variant_sets.append(current)
                current = []
                seen_subtags = set()
                i += 1

        if len({t for t, _, _ in current}) > 1:
            variant_sets.append(current)

        # --- DB validation ---
        for vset in variant_sets:
            variant_words = [g for _, g, _ in vset]

            # Find which variant words are present in DB and their GUIDs
            present_entries = [(w, guid) for w, guid in db_entries if w in variant_words]
            present_words = [w for w, _ in present_entries]

            # Verbose output
            if verbose:
                print(f"\nVerse {format_reference(uid)}:")
                print("  Variant set:")
                for t, g, pos in vset:
                    print(f"    Pos {pos}: {t} {g}")
                print("  DB entries for variant words:")
                for w, guid in present_entries:
                    print(f"    {w}: {guid}")

            # Determine failure
            fail = False
            if len(present_words) == 0:
                fail = True
            elif len(present_words) > 1:
                # Check adjacency by GUID
                guids_sorted = [guid for _, guid in present_entries]
                guids_sorted.sort()
                for a, b in zip(guids_sorted, guids_sorted[1:]):
                    # adjacent if difference in hundredths place is 0.01
                    # (or just check if GUIDs are consecutive? depends on your scheme)
                    if abs(b - a) <= 0.01:  
                        fail = True
                        break

            if fail:
                print(f"\nVariant error in {format_reference(uid)}")
                print(f"Variant set: {sorted(variant_words)}")
                print(f"DB contains: {present_words if present_words else 'NONE'}")


# Usage
verse_map = load_verse_map("textusreceptuspullnt.txt")
conn = sqlite3.connect("concordance.db")
inputs = update_guids(conn, verse_map)
next_check(conn)
second_pass(conn)

# For temporary uses, comment out normally:
#inputs = [40001001]

clean_up(conn, verse_map, inputs)
verify_verse_map_words(conn, verse_map, inputs)

#A particularly unique algorithm for finding cases where variant sets (this or that) turn up with this and that or none in the GHT.
#verify_variant_sets_against_db(conn, verse_map, False)
conn.close()
