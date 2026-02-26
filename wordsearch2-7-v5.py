# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sqlite3
import sys
import codecs

# Set the default encoding for sys.stdout to handle Unicode output
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

def search_database(column, table, db_path, exact):
    """
    Repeatedly prompts the user for input and searches a SQLite database 
    in the specified column and table.

    Args:
        column (str): The column to search.
        table (str): The table to search.
        db_path (str): Path to the SQLite database file.
        exact (str): "=" for exact match, "LIKE" for partial match.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("Searching in table '{}', column '{}'.".format(table, column))
    #print("Type '\\' to quit the search.")

    while True:
        # Prompt user for search term
        print("\nStart with a period '.' if you want to search for exact matches.")
        search_term = raw_input("Enter search term ('\\' to go back): ").strip().decode('utf-8')  # Decode to Unicode
        search_term = search_term.lower()
        if search_term == "\\":
            print("Exiting search.")
            break

        if search_term[0] == ".":
            exact = "="
            search_term = search_term[1:]
        else:
            exact = "LIKE"

        if 'a' <= search_term[0] <= 'z' or search_term[0] == '-':
            if table == "entries":
                column = "raw"
            else:
                column = "english"
            if table == "greek_roots":
                column = "eroot"
        elif '\u0370' <= search_term[0] <= '\u03FF':
            column = "greek"
            if table == "greek_roots":
                column = "root"
        else:
            print("Please use latin or greek alpha characters.")
            continue

        if exact == "=":
            if column == "greek":
                notcolumn = "english"
            else:
                notcolumn = "greek"
        else:
            notcolumn = column
        
        try:
            # Prepare and execute the query
            if table == "entries":
                query = "SELECT * FROM {} WHERE {} {} ? ORDER BY uid".format(table, column, exact)
            elif table == "greek_roots":
                query = "SELECT root, subs, eroot, strongs, type FROM {} WHERE {} {} ? OR {} {} ? ORDER BY {}".format(table, column, exact, "subs", exact, "root")
            else:
                query = "SELECT * FROM {} WHERE {} {} ? ORDER BY {}".format(table, column, exact, notcolumn)

            if exact == "=":
                c.execute(query, (search_term,))
            elif table == "greek_roots":
                c.execute(query, ("%{}%".format(search_term),"%{}%".format(search_term),))
            else:
                c.execute(query, ("%{}%".format(search_term),))
            results = c.fetchall()

            # Display results
            if results:
                #print(results)
                if table == "entries":
                    results = [(row[-3],) + row[1:-3] for row in results]
                print("Results for '{}':\n".format(search_term))

                #tempres = list(results[:][1])
                #print(tempres)

                for i in range(len(results) - 1, -1, -1):
                    #print(i)
                    negation_words = {u'\u03bf\u03c5', u'\u03bf\u03c5\u03c7', u'\u03bf\u03c5\u03ba', u'\u03bc\u03b7'}  # {'ου', 'ουχ', 'ουκ', 'μη'}

                    # Look ahead to the next row (if it exists)
                    next_row = results[i + 1] if i + 1 < len(results) else None

                    if i == len(results) - 1:
                        continue

                    if results[i][1] in negation_words and results[i + 1][1] not in negation_words:
                        #input(round(results[i + 1][2] - results[i][2],2))
                        if round(results[i + 1][2] - results[i][2],2) == .01:
                            tempres = list(results[i + 1])
                            tempres[1] = results[i][1] + ' ' + tempres[1]
                            results[i + 1] = tuple(tempres)
                            del results[i]

                if isinstance(results[0][2], float):
                    new_results = []
                    for row in results:
                        row = list(row)
                        #row.append(row[2])
                        row[2] = format_reference(row[2])
                        new_results.append(tuple(row))
                    results = new_results

                # Calculate maximum widths for each column
                max_widths = [max(len(unicode(row[i])) for row in results) for i in range(len(results[0]))]

                for row in results:
                    # Format each column with padding based on max_widths
                    formatted_row = [
                        unicode(item).ljust(max_widths[i]) for i, item in enumerate(row)
                    ]
                    print(u" | ".join(formatted_row))
            else:
                print("No matches found for '{}'.".format(search_term))
        except sqlite3.Error as e:
            print("An error occurred: {}".format(e))

    conn.close()

def format_reference(num):
    book_codes = {
        40: "Matt",
        41: "Mark",
        42: "Luke",
        43: "John",
        44: "Acts",
        45: "Rom",
        46: "1Cor",
        47: "2Cor",
        48: "Gal",
        49: "Eph",
        50: "Phil",
        51: "Col",
        52: "1Th",
        53: "2Th",
        54: "1Tim",
        55: "2Tim",
        56: "Tit",
        57: "Phlm",
        58: "Heb",
        59: "Jam",
        60: "1Pet",
        61: "2Pet",
        62: "1Jo",
        63: "2Jo",
        64: "3Jo",
        65: "Jude",
        66: "Rev"
    }

    # Separate integer and decimal parts
    whole = int(num)
    uid = int(round((num % 1) * 100))

    # Extract parts
    book_num = whole // 10**6
    chapter = (whole // 10**3) % 1000
    verse = whole % 1000

    # Map book number to name
    book = book_codes.get(book_num, "Book%d" % book_num)

    return "%s %d:%d:%d" % (book, chapter, verse, uid)

def get_numbers(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM greek_roots WHERE root != "none" and type=1')
    roots = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM greek_roots WHERE root != "none" and type=2')
    construct = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM greek_roots WHERE root != "none" and type=0')
    morph = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM greek_roots WHERE root != "none" and type=3')
    prop = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM word_map WHERE greek != "none"')
    pairs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM entries WHERE greek != "none"')
    words = c.fetchone()[0]
    conn.close()
    return roots, construct, pairs, words, morph, prop

def main():
    db_path = "concordance.db"
    roots, construct, pairs, words, morph, prop = get_numbers(db_path)
    while True:
        print("There are {} primitive roots and {} constructed roots.".format(roots, construct))
        print("There are {} morpheme roots and {} proper nouns.".format(morph, prop))
        print("There are {} unique pairs out of {} words in database.".format(pairs, words))
        print("\nSelect an option:")
        print("1. Search pairs.")
        print("2. Search verses.")
        print("3. Search roots.")
        print("\. Exit")
        
        choice = raw_input("Enter your choice (1, 2, or \): ").strip()
        
        if choice == "1":
            search_database("english", "word_map", db_path, "=")
        elif choice == "2":
            search_database("raw", "entries", db_path, "=")
        elif choice == "3":
            search_database("english", "greek_roots", db_path, "")
        elif choice == "\\":
            print("Exiting the program. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

