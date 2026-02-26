import sqlite3
import re
from collections import defaultdict

def parse_guid(guid):
    guid_str = str(guid)
    # Use regex to extract numbers before and after the dot, ignoring other chars
    match = re.search(r"(\d{8})\.(\d{1,2})", guid_str)
    if not match:
        return None, None
    prefix = match.group(1)
    suffix = int(match.group(2))
    return prefix, suffix

conn = sqlite3.connect("concordance.db")
cursor = conn.cursor()

cursor.execute("SELECT rowid, guid, raw FROM entries")
rows = cursor.fetchall()

# Group entries by raw (only those containing underscore)
raw_groups = defaultdict(list)
for rowid, guid, raw in rows:
    if '_' not in raw:
        continue  # Skip raw values without underscore
    prefix, suffix = parse_guid(guid)
    if prefix is not None:
        raw_groups[raw].append((prefix, suffix, rowid, guid))

for raw, entries in raw_groups.items():
    if len(entries) < 2:
        continue

    # Group by prefix
    prefix_groups = defaultdict(list)
    for prefix, suffix, rowid, guid in entries:
        prefix_groups[prefix].append((suffix, rowid, guid))

    for prefix, group in prefix_groups.items():
        if len(group) < 2:
            continue

        # Sort suffixes
        group.sort(key=lambda x: x[0])
        suffixes = [s for s, _, _ in group]

        # Check for duplicates with non-adjacent suffixes
        found_non_adjacent = False
        for i in range(len(suffixes)):
            for j in range(i + 1, len(suffixes)):
                if abs(suffixes[i] - suffixes[j]) > 1:
                    found_non_adjacent = True
                    break
            if found_non_adjacent:
                break

        if found_non_adjacent:
            print(f"Non-adjacent duplicates for raw='{raw}', prefix='{prefix}':")
            for suffix, rowid, guid in group:
                print(f"  rowid={rowid}, guid={guid}")
            print()

conn.close()

conn = sqlite3.connect("concordance.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT raw, COUNT(*) as count_rows
    FROM entries
    WHERE raw LIKE '%_%_%_%' -- at least 3 underscores
    GROUP BY raw
""")
rows = cursor.fetchall()

# Filter raw values that have exactly 3 underscores
def count_underscores(s):
    return s.count('_')

exact_three_underscore = [raw for raw, _ in rows if count_underscores(raw) == 3]

print(f"Number of distinct raw values with exactly 3 underscores: {len(exact_three_underscore)}")

conn.close()

conn = sqlite3.connect("concordance.db")
cursor = conn.cursor()

# Get all distinct raw values containing underscores
cursor.execute("SELECT DISTINCT raw FROM entries WHERE raw LIKE '%\_%' ESCAPE '\\'")
rows = cursor.fetchall()

unique_print_words = set()

for (raw,) in rows:
    parts = raw.split('_')
    length = len(parts)

    # Pattern 1: exactly 3 parts -> [ignore]_[print]_[ignore]
    if length == 3:
        unique_print_words.add(parts[1])

    # Pattern 2: exactly 4 parts -> [ignore]_[print]_[print]_[ignore]
    elif length == 4:
        unique_print_words.add(parts[1])
        unique_print_words.add(parts[2])

# Print all unique words found between underscores
print("Unique 'print' words found in patterns:")
for word in sorted(unique_print_words):
    print(word)

conn.close()
