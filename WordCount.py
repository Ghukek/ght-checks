import sqlite3

# List of book abbreviations (adjust as needed)
books = ['Matt', 'Mark', 'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor',
         'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim', '2Tim',
         'Titus', 'Phlm', 'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John',
         '3John', 'Jude', 'Rev', 'All']

# Path to your SQLite database
db_path = 'concordance.db'  # <-- Change to your DB file

# Connect to SQLite
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# UID prefixes for book ranges
book_uids = range(40000000, 67000000, 1000000)
i = 0;

def printcount(i, start_uid, end_uid):
    # Query: greek != 'none'
    cursor.execute("""
        SELECT COUNT(*) FROM entries
        WHERE uid > ? AND uid < ? AND greek != 'none'
    """, (start_uid, end_uid))
    count_not_none = cursor.fetchone()[0]

    # Query: greek == 'none'
    cursor.execute("""
        SELECT COUNT(*) FROM entries
        WHERE uid > ? AND uid < ? AND greek = 'none'
    """, (start_uid, end_uid))
    count_none = cursor.fetchone()[0]

    print(f"{books[i]}: {count_not_none} words, with {count_none} added")

# Iterate over UID ranges
for base_uid in book_uids:
    start_uid = base_uid
    end_uid = base_uid + 999999  # exclusive upper bound

    printcount(i, start_uid, end_uid)

    i += 1

printcount(27, 0, 66999999)
# Close connection
conn.close()
