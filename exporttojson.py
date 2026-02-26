import sqlite3
import json
import gzip
import shutil
import os

greek_to_latin = {
    'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd',
    'ε': 'e', 'ζ': 'z', 'η': 'h', 'θ': 'u',
    'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm',
    'ν': 'n', 'ξ': 'j', 'ο': 'o', 'π': 'p',
    'ρ': 'r', 'σ': 's', 'ς': 'w', 'τ': 't',
    'υ': 'y', 'φ': 'f', 'χ': 'x', 'ψ': 'c',
    'ω': 'v',
}

def transliterate(text):
    if text is None:
      return None
    return ''.join(greek_to_latin.get(char, char) for char in text)

def extract_structure(uid_float):
    whole = int(uid_float)
    book_num = int(whole // 1_000_000) - 1
    chapter = int((whole // 1_000) % 1_000) - 1
    verse = int(whole % 1_000) - 1
    decimal = round(uid_float % 1 * 100) - 1
    return book_num, chapter, verse, decimal

def convert_to_json(db_path="concordance.db", out_file="Website/base.json"):
    import sqlite3
    import json

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT english, greek, uid, raw, guid, ident FROM entries ORDER BY uid")
    rows = cursor.fetchall()

    MAX_BOOK = 66  # adjust as needed

    # Preinitialize books as lists
    data = [[] for _ in range(MAX_BOOK)] 

    def ensure_list_depth(lst, idx):
        while len(lst) <= idx:
            lst.append([])

    for i, (english, greek, uid, raw, guid, ident) in enumerate(rows):
        if uid is None:
            continue

        book, chapter, verse, uid_decimal = extract_structure(uid)

        # Look ahead to the next row if current guid is None
        if guid is None:
            # Try to find the next valid guid
            try:
                _, _, _, _, next_guid, _ = rows[i + 1]
                _, _, _, _, prev_guid, _ = rows[i - 1]
                if next_guid is not None and not raw.endswith('}'):
                    guid_decimal = round(next_guid % 1 * 100) - 1.1
                    guid_decimal = round(guid_decimal, 1)
                elif prev_guid is not None:
                    guid_decimal = round(prev_guid % 1 * 100) - .9
                    guid_decimal = round(guid_decimal, 1)
                else:
                    input(rows[i+1])
            except IndexError:
                input(rows[i+1])
                guid_decimal = -1  # fallback if this is the last row
        else:
            guid_decimal = round(guid % 1 * 100) - 1

        if greek == "none":
            greek = ""

        # Ensure lists exist at each level
        ensure_list_depth(data, book)
        ensure_list_depth(data[book], chapter)
        ensure_list_depth(data[book][chapter], verse)

        # word index = uid_decimal, ensure the word list exists and is big enough
        ensure_list_depth(data[book][chapter][verse], uid_decimal)

        # Store attributes as a list at that word index
        translit = transliterate(greek)
        data[book][chapter][verse][uid_decimal] = [
            ident,
            raw,
            guid_decimal
        ]

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Export complete: {out_file}")
    conn.close()

#    with open('Website/base.json', 'rb') as f_in:
#        with gzip.open('Website/base.json.gz', 'wb') as f_out:
#            shutil.copyfileobj(f_in, f_out)


def export_missing_lxx(db_lxx="lxx.db", base_file="Website/base.json", out_file="Website/basex.json"):
    import sqlite3
    import json
    import os

    # Load existing base.json
    if not os.path.exists(base_file):
        raise FileNotFoundError(f"{base_file} not found")
    with open(base_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn_l = sqlite3.connect(db_lxx)
    cur_l = conn_l.cursor()

    cur_l.execute("SELECT english, greek, uid, raw, guid, ident FROM entries WHERE uid IS NOT NULL ORDER BY uid")
    lxx_rows = cur_l.fetchall()

    def ensure_list_depth(lst, idx):
        while len(lst) <= idx:
            lst.append([])

    for english, greek, uid, raw, guid, ident in lxx_rows:
        if uid is None:
            continue

        book, chapter, verse, word = extract_structure(uid)

        # Ensure list depth at each level
        ensure_list_depth(data, book)
        ensure_list_depth(data[book], chapter)
        ensure_list_depth(data[book][chapter], verse)
        ensure_list_depth(data[book][chapter][verse], word)

        # Skip if already populated in base.json
        if data[book][chapter][verse][word]:
            continue

        # Compute guid_decimal like your original function
        if guid is not None:
            guid_decimal = round(guid % 1 * 100) - 1
        else:
            guid_decimal = -1

        if greek == "none":
            greek = ""

        # Transliterate if available
        try:
            translit = transliterate(greek)
        except NameError:
            translit = greek

        # If ident missing/empty, use translit instead
        first_value = ident if ident else translit

        data[book][chapter][verse][word] = [
            first_value,
            raw,
            guid_decimal
        ]

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Export complete: {out_file}")

    conn_l.close()


import sqlite3, json

def expand_root(cursor, root, seen=None):
    if seen is None:
        seen = set()
    if root in seen:
        return []  # avoid cycles
    seen.add(root)

    expanded = [root]  # always include the current root

    cursor.execute("SELECT subs FROM greek_roots WHERE root = ?", (root,))
    result = cursor.fetchone()
    if result and result[0]:
        subs = [s.strip() for s in result[0].split(',')]
        for sub in subs:
            expanded.extend(expand_root(cursor, sub, seen))
    
    return expanded

def exportlookups():
    conn = sqlite3.connect('concordance.db')
    cursor = conn.cursor()

    cursor.execute("SELECT ident, english, greek, pcode, strongs, roots, count FROM word_map ORDER BY ident")
    rows = cursor.fetchall()

    # Find the max ident so we know how big the list should be
    max_ident = max(row[0] for row in rows) if rows else 0
    data = [[] for _ in range(max_ident + 1)]  # pre-fill with []

    for ident, english, greek, pcode, strongs, roots, count in rows:
        if roots:
            # Expand roots recursively
            all_roots = expand_root(cursor, roots)
            # Join them into a comma-separated string
            roots = ",".join(all_roots)

        if roots and roots == "none":
            roots = None
        if roots and roots.endswith(",none"):
            roots = roots[:-5]
        if roots and roots.endswith(",ω"):
            roots = roots[:-2]

        roots_translit = transliterate(roots) if roots else ""

        if greek == "none":
            greek = ""

        data[ident] = [
            transliterate(greek),
            pcode,
            strongs,
            roots_translit,
            english,
            count
        ]

    with open('Website/lookups.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    conn.close()

import sqlite3
import json

def exportlookupsex():
    # Connect to concordance.db for word_map
    conn_conc = sqlite3.connect('concordance.db')
    cursor_conc = conn_conc.cursor()

    # Connect to lxx-wh.db for parsings
    conn_lxx = sqlite3.connect('lxx-wh.db')
    cursor_lxx = conn_lxx.cursor()

    # Fetch from word_map
    cursor_conc.execute("SELECT ident, english, greek, pcode, strongs, roots, count FROM word_map ORDER BY ident")
    word_map_rows = cursor_conc.fetchall()

    # Fetch from parsings
    cursor_lxx.execute("SELECT ident, english, greek, mac, strongs, roots, count FROM parsings ORDER BY ident")
    parsing_rows = cursor_lxx.fetchall()

    # Determine max ident
    all_idents = [row[0] for row in word_map_rows] + [row[0] for row in parsing_rows]
    max_ident = max(all_idents) if all_idents else 0

    data = [[] for _ in range(max_ident + 1)]  # Pre-fill with empty lists

    def process_row(cursor, row):
        ident, english, greek, pcode, strongs, roots, count = row

        if roots:
            # Use cursor from appropriate DB
            all_roots = expand_root(cursor, roots)
            roots = ",".join(all_roots)

        if roots and roots.endswith(",none"):
            roots = roots[:-5]
        #if roots and roots.endswith(",ω"):
        #    roots = roots[:-2]

        roots_translit = transliterate(roots) if roots else ""

        if greek == "none":
            greek = ""

        # Normalize strongs
        if strongs is None or strongs == "":
            strongs_val = None
        else:
            s = str(strongs).strip()
            try:
                strongs_val = float(s) if "." in s else int(s)
            except ValueError:
                strongs_val = None

        return [
            transliterate(greek),
            pcode,
            strongs,
            roots_translit,
            english,
            count
        ]

    # Add data from word_map (concordance.db)
    for row in word_map_rows:
        ident = row[0]
        entry = process_row(cursor_conc, row)
        data[ident].extend(entry)

    # Add data from parsings (lxx-wh.db)
    for row in parsing_rows:
        ident = row[0]
        entry = process_row(cursor_lxx, row)
        data[ident].extend(entry)

    # Write combined JSON
    with open('Website/lookupsex.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    conn_conc.close()
    conn_lxx.close()

def copy_json_to_dev():
    src = "Website"
    dst = "WebsiteDev"

    os.makedirs(dst, exist_ok=True)

    for filename in os.listdir(src):
        if not filename.lower().endswith(".json"):
            continue

        src_path = os.path.join(src, filename)
        dst_path = os.path.join(dst, filename)

        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)

# Run the script
if __name__ == "__main__":
    convert_to_json()
    exportlookups()
    export_missing_lxx()
    exportlookupsex()
    copy_json_to_dev()

