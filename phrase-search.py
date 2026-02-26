# -*- coding: utf-8 -*-
import sqlite3
import sys

# This software uses Python 2.7

def is_greek(text):
    for c in text:
        if u'\u0370' <= c <= u'\u03FF':
            return True
    return False

def format_reference(num):
    book_codes = {
        40: "Matt", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
        45: "Rom", 46: "1Cor", 47: "2Cor", 48: "Gal", 49: "Eph",
        50: "Phil", 51: "Col", 52: "1Th", 53: "2Th", 54: "1Tim",
        55: "2Tim", 56: "Tit", 57: "Phlm", 58: "Heb", 59: "Jam",
        60: "1Pet", 61: "2Pet", 62: "1Jo", 63: "2Jo", 64: "3Jo",
        65: "Jude", 66: "Rev"
    }

    whole = int(num)
    uid = int(round((num % 1) * 100))
    book_num = whole // 10**6
    chapter = (whole // 10**3) % 1000
    verse = whole % 1000
    book = book_codes.get(book_num, "Book%d" % book_num)
    return "%s %d:%d:%d" % (book, chapter, verse, uid)

def get_context_uids(cursor, base_uid, direction, count):
    context_uids = []
    current_uid = round(base_uid, 2)

    while len(context_uids) < count:
        if direction == -1:
            query = "SELECT uid FROM entries WHERE uid < ? ORDER BY uid DESC LIMIT ?"
        else:
            query = "SELECT uid FROM entries WHERE uid > ? ORDER BY uid ASC LIMIT ?"

        cursor.execute(query, (current_uid, count - len(context_uids)))
        rows = cursor.fetchall()

        if not rows:
            break

        for row in rows:
            uid = float(row[0])
            if direction == -1:
                context_uids.insert(0, uid)
            else:
                context_uids.append(uid)
            current_uid = uid

    return context_uids

def search_sequence_with_context(conn, words, context_count, id_field='uid', lang_field='greek'):
    cursor = conn.cursor()
    num_words = len(words)

    # Get possible starting points (first word match — partial or exact)
    first_word = words[0]
    is_exact = first_word.startswith('.')
    search_val = first_word[1:] if is_exact else first_word

    if not is_exact:
        cursor.execute("""
            SELECT {0} FROM entries 
            WHERE {1} LIKE ? 
            ORDER BY {0} ASC
        """.format(id_field, lang_field), (u'%' + search_val + u'%',))
    else:
        cursor.execute("""
            SELECT {0} FROM entries 
            WHERE {1} = ? 
            ORDER BY {0} ASC
        """.format(id_field, lang_field), (search_val,))

    start_ids = [float(row[0]) for row in cursor.fetchall()]
    match_count = 0

    for start_id in start_ids:
        matched = True
        id_sequence = [round(start_id + i * 0.01, 2) for i in range(num_words)]

        for i, id_val in enumerate(id_sequence):
            word = words[i]
            is_exact = word.startswith('.')
            match_val = word[1:] if is_exact else word

            if not is_exact:
                query = "SELECT {0} FROM entries WHERE {1} = ? AND {0} LIKE ?".format(lang_field, id_field)
                cursor.execute(query, (round(id_val, 2), u'%' + match_val + u'%'))
            else:
                query = "SELECT {0} FROM entries WHERE {1} = ? AND {0} = ?".format(lang_field, id_field)
                cursor.execute(query, (round(id_val, 2), match_val))

            result = cursor.fetchone()
            if not result:
                matched = False
                break

        if matched:
            match_count += 1

            before_uids = get_context_uids(cursor, start_id, -1, context_count)
            main_uids = [round(start_id + i * 0.01, 2) for i in range(num_words)]
            after_uids = get_context_uids(cursor, main_uids[-1], 1, context_count)

            all_uids = before_uids + main_uids + after_uids

            placeholders = ','.join(['?'] * len(all_uids))
            query = """
                SELECT uid, guid, greek, raw FROM entries
                WHERE {0} IN ({1})
            """.format(id_field, placeholders)

            cursor.execute(query, all_uids)
            rows = cursor.fetchall()

            rows.sort(key=lambda r: float(r[0] if id_field == 'uid' else r[1]))

            greek_words = [row[2] for row in rows]
            english_words = [row[3] for row in rows]

            ref = format_reference(start_id)
            print u"\nMatch {}: {} = {}".format(match_count, id_field, ref)
            print u"[Greek]   " + u" ".join(greek_words)
            print u"[English] " + u" ".join(english_words)
            print "-" * 40

    if match_count == 0:
        print u"No consecutive match found for: {}".format(u" ".join(words))

def main():
    conn = sqlite3.connect("concordance.db")
    print "Greek/English Concordance Search (type 'exit' to quit)"

    while True:
        id_field = ''
        while id_field not in ['uid', 'guid']:
            id_field = raw_input("\nSearch using 'uid' or 'guid'? (or type 'exit'): ").strip().lower()
            if id_field == 'exit':
                conn.close()
                sys.exit(0)
            if id_field not in ['uid', 'guid']:
                print "Please type 'uid' or 'guid'."

        while True:
            try:
                user_input = raw_input("\nEnter search phrase and number (e.g., .ιησ .χρισ 2): ").decode('utf-8').strip()
            except (KeyboardInterrupt, EOFError):
                print "\nExiting..."
                conn.close()
                sys.exit(0)

            if user_input.lower() == 'exit':
                break

            parts = user_input.split()
            if len(parts) < 2:
                print "Please enter one or more words followed by a number."
                continue

            try:
                context = int(parts[-1])
            except ValueError:
                print "Last value must be a number."
                continue

            words = parts[:-1]
            lang_field = 'greek' if is_greek(words[0].lstrip('.')) else 'english'

            search_sequence_with_context(conn, words, context, id_field=id_field, lang_field=lang_field)

if __name__ == '__main__':
    main()

