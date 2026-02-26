import sqlite3
import re
from itertools import zip_longest
from ghtbooks import book_map, book_codes
# Mapping for book names to numbers

def selectword(word, cursor):
    # Look up the Greek word in the database
    if word.startswith("."):
        partial = f"%{word[1:]}%"
        cursor.execute("SELECT english, count FROM word_map WHERE greek LIKE ?", (partial,))
    else:
        cursor.execute("SELECT english, count FROM word_map WHERE greek = ?", (word,))
    return cursor.fetchall(), cursor

# Check if the word is already present in the database
def check_if_present(conn, word, uid, o_word):
    c = conn.cursor()

    # Query the database for an existing entry with the same word, uid
    c.execute("""
        SELECT 1 FROM entries
        WHERE english = ? AND uid = ? AND raw = ?
    """, (word, uid, o_word))
    
    result = c.fetchone()
    
    # Return True if a matching entry is found, else False
    return result is not None

# Check if the word is already present in the database
def check_if_extra(conn, uid):
    c = conn.cursor()

    # Query the database for an existing entry with the same word, uid
    c.execute("""
        SELECT 1 FROM entries
        WHERE uid = ?
    """, (uid,))
    
    result = c.fetchone()
    
    # Return True if a matching entry is found, else False
    return result is not None

# Check if the word is already present in the database
def check_if_other(conn, uid):
    c = conn.cursor()

    # Query the database for an existing entry with the same word, book, chapter, verse, and uid
    c.execute("""
        SELECT 1 FROM entries
        WHERE uid = ?
    """, (uid,))
    
    result = c.fetchone()
    
    # Return True if a matching entry is found, else False
    return result is not None

def check_and_update_raw(conn, word, uid, o_word):
    # Used for when only punctuation is different.
    c = conn.cursor()

    # Check if an entry exists with matching english + uid
    c.execute("""
        SELECT raw FROM entries
        WHERE english = ? AND uid = ?
    """, (word, uid))
    
    row = c.fetchone()

    if row is None:
        # No matching entry found
        return False
    
    # If the raw field is already the desired value, no need to update
    if row[0] == o_word:
        return True  # Already correct
    
    print(f"Punctuation fixed from {row[0]} to {o_word}")

    # Update raw to the new o_word
    c.execute("""
        UPDATE entries
        SET raw = ?
        WHERE english = ? AND uid = ?
    """, (o_word, word, uid))

    #print("fixed")
    conn.commit()
    return True

def displayexisting(word, eng, cursor):
    # Look up the Greek word in the database
    results, cursor = selectword(word, cursor)

    less = False
    greater = False
    override = False

    # Display existing words
    if results:
        print(f"Existing cases of '{word}':")
        for i, result in enumerate(results, start=1):
            print(f"{i}. {result[0]} {result[1]}")

            value = result[1]
            if value is not None:
                value_int = int(value)
                if value_int < 5:
                    less = True
                if value_int > 25:
                    greater = True
                if value_int < 5 and result[0] == eng:
                    override = True

    if (less and not greater) or override:
        input("\nDouble Check These")

    return cursor

# Delete all entries for a given book, chapter, and current_verse from the database
def delete_verse_entries(conn, uid):
    c = conn.cursor()

    # Check how many entries exist for the UID
    c.execute("SELECT COUNT(*) FROM entries WHERE uid = ?", (uid,))
    count = c.fetchone()[0]

    if count == 0:
        print("No entry found with that UID.")
    elif count > 1:
        print(f"Warning: {count} entries found with UID {uid}. Expected only one.")
    else:
        # Proceed to fetch the single entry
        c.execute("SELECT english, greek, raw, guid FROM entries WHERE uid = ?", (uid,))
        existing_english, existing_greek, existing_raw, existing_guid = c.fetchone()
        print("Deleting:")
        print(f"{existing_english} - {existing_greek} - {existing_raw}")

    # SQL query to delete entries from the entries table based on book, chapter, and verse
    c.execute("""
        DELETE FROM entries
        WHERE uid = ?
    """, (uid,))

    update_word_map(conn, existing_english, existing_greek, -1)

    reference = format_reference(uid)

    print(f"Deleted word: {reference}")    

    return existing_greek, existing_guid

def format_reference(num):

    # Separate integer and decimal parts
    whole = int(num)
    uid = int(round((num % 1) * 100))

    # Extract parts
    book_num = whole // 10**6
    chapter = (whole // 10**3) % 1000
    verse = whole % 1000

    # Map book number to name
    book = book_codes.get(book_num, f"Book{book_num}")

    return f"{book} {chapter}:{verse}:{uid}"
    

# Delete all entries for a given book, chapter, and current_verse from the database
def delete_english_entries(conn, word, book, chapter, current_verse):
    c = conn.cursor()

    # SQL query to delete entries from the entries table based on book, chapter, and verse
    c.execute("""
        DELETE FROM entries
        WHERE book = ? AND chapter = ? AND verse = ? AND english = ? AND uid = 1
    """, (book, chapter, current_verse, word))
    
    print(f"Deleting all entries for {word} in {book} {chapter} [:{current_verse}]")

# Check if the verse is already present in the database
def check_verse(conn, book, chapter, current_verse):
    c = conn.cursor()
    
    # Query to check if there are any entries for the given book, chapter, and verse
    c.execute("""
        SELECT 1 FROM entries
        WHERE book = ? AND chapter = ? AND verse = ?
        LIMIT 1
    """, (book, chapter, current_verse))
    
    result = c.fetchone()

    # Return True if a matching entry is found, else False
    return result is not None

def update_word_map(conn, english, greek, incr):
    c = conn.cursor()

    # Check if entry exists and get its current ident and count
    c.execute("""
        SELECT ident, count FROM word_map WHERE english = ? AND greek = ?
    """, (english, greek))
    result = c.fetchone()

    if result is None:
        # Assign a new global ident
        c.execute("SELECT MAX(ident) FROM word_map")
        max_ident = c.fetchone()[0]
        next_ident = (max_ident or 0) + 1

        # Insert new entry with count=0 and new ident
        c.execute("""
            INSERT INTO word_map (english, greek, count, ident) VALUES (?, ?, 0, ?)
        """, (english, greek, next_ident))
        current_ident = next_ident
    else:
        current_ident, current_count = result
        if current_ident is None:
            # Defensive: assign first unassigned global ident
            c.execute("SELECT MAX(ident) FROM word_map")
            max_ident = c.fetchone()[0]
            current_ident = (max_ident or 0) + 1
            c.execute("""
                UPDATE word_map SET ident = ? WHERE english = ? AND greek = ?
            """, (current_ident, english, greek))

    # Update the count
    c.execute("""
        UPDATE word_map
        SET count = count + ?
        WHERE english = ? AND greek = ?
    """, (incr, english, greek))

    # Remove entry if count is now 0
    c.execute("""
        DELETE FROM word_map
        WHERE english = ? AND greek = ? AND count = 0
    """, (english, greek))

    return current_ident

# Insert or update word mapping
def add_word_mapping(conn, english, uid, grk, o_word, guid):
    c = conn.cursor()

    # Fetch Greek words and their counts for the given English word, sorted by count in descending order
    c.execute("""
        SELECT greek, count
        FROM word_map
        WHERE english = ?
        GROUP BY greek
        ORDER BY count DESC
    """, (english,))
    result = c.fetchall()

    skip = 0

    # If the word exists, suggest all Greek words one by one
    if result:
        print(f"Suggestions for '{english}':")
        # Display the list of existing Greek words
        for idx, (existing_greek, count) in enumerate(result, start=1):
            print(f"{idx}. {existing_greek}")
        
        if len(result) == 1:
            greek = input(f"Press Enter to accept or type a new word (n to skip): ").strip()
            if greek == "" or greek == "1":
                choice_idx = 0
                if 0 <= choice_idx < len(result):
                    greek = result[choice_idx][0]  # Use the selected Greek word
                    print(f"Selected Greek word: {greek}")
                    ident = update_word_map(conn, english, greek, 1)
            elif greek == "n":
                print("Skipping")
                return
            else:
                print(f"Entered Greek word: {greek}")
                ident = update_word_map(conn, english, greek, 1)
        else:
            # Allow user to select an existing Greek word or add a new one
            choice = input(f"Select the corresponding Greek word (1-{len(result)}) or type a new one: ").strip()

            if choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(result):
                    greek = result[choice_idx][0]  # Use the selected Greek word
                    print(f"Selected Greek word: {greek}")
                    ident = update_word_map(conn, english, greek, 1)
                else:
                    print("Invalid choice, proceeding to add a new Greek word.")
                    greek = input("Enter the new Greek word: ").strip()
                    # Insert the new Greek word under this English word
                    ident = update_word_map(conn, english, greek, 1)
            elif choice == "" or choice == "n":
                print("Skipping")
                greek = ""
                skip = 1
            else:
                #print("No existing Greek word selected, proceeding to add a new Greek word.")
                #greek = input("Enter the new Greek word: ").strip()
                greek = choice
                print(f"Entered Greek word: {greek}")
                # Insert the new Greek word under this English word
                ident = update_word_map(conn, english, greek, 1)
    elif grk != "":
        choice = input(f"Old greek word: {grk}, press Enter to accept or type a new word (n to skip): ").strip()
        if choice == "":
            greek = grk
            ident = update_word_map(conn, english, greek, 1)
        elif choice == "n":
            print("Skipping")
            greek = ""
            skip = 1
        else:
            greek = choice
            ident = update_word_map(conn, english, greek, 1)
    else:
        # If no Greek word is found, insert the first one
        greek = input("Enter the new Greek word: ").strip()
        if greek == "":
            print("Skipping")
            skip = 1
        else:
            ident = update_word_map(conn, english, greek, 1)

    if greek != grk and grk != "":
        guid = None
        c.execute("UPDATE entries SET guid = NULL WHERE uid > ? and uid < ?", (round(uid), round(uid) + 1))

    if not skip:
        # Add verse record
        c.execute("INSERT INTO entries (english, greek, uid, raw, guid, ident) VALUES (?, ?, ?, ?, ?, ?)",
                  (english, greek, uid, o_word, guid, ident))

        if greek != "none":
            c = displayexisting(greek, english, c)
    
    conn.commit()
    print("---Commit---\n")

# Helper function to split a single line into verses
def split_verses(line): 
    # Match verse markers and split text based on them
    #print(line)
    verse_parts = re.split(r'(\[:\d+\])', line)
    verses = []
    for i in range(1, len(verse_parts), 2):  # Odd indices contain the verse markers
        marker = verse_parts[i]
        content = verse_parts[i + 1] if i + 1 < len(verse_parts) else ''
        verses.append((marker, content.strip()))
    return verses

def oforto(word, addto):
    # Check the start of the word.
    if word[0:3] == "of{" or word[0:3] == "to{":
        addto.append(word[0:3])
    elif word[0:5] == "[of-]":
        if '}' in word:
            word = re.sub(r'}','',word)
            addto.pop()
        return word, addto
    else:
        word = addto[-1] + word

    # Check the end of the word.
    if word[-1] == '}':
        if word[-2] == '}':
            addto.pop()
            word = word[:-1]
        addto.pop()
    else:
        word = word + "}"

    return word, addto

def processword(word, addto):
    word = re.sub(r'\[gathering/synagogue \(Luke 8:41\)\]|\["\]|,/;|\[;\]|\[\,\]', '', word)
    word = re.sub(r'\,|\.|:|"|\'|;|\[\?\]|!', '', word)
    #print(word[-2:])
    if word[-2:] == "--":
        word = word[0:-2]
    word = word.lower()

    if len(addto) > 0 or word[0:3] == "of{" or word[0:3] == "to{":
        word, addto = oforto(word, addto)

    return word, addto

# Process text file
def process_text_file(filename, conn, start_uid, oldfile, skipold):
    with open(filename, "r") as file:
        content = file.read()

    with open(oldfile, "r") as file2:
        content2 = file2.read()

    # Variables to track the book, chapter, and verse
    book = None
    chapter = None
    current_verse = None
    parsing_started = False
    doneskip = None

    # Split the text into lines
    lines = content.splitlines()
    lines2 = content2.splitlines()
    for line, line2 in zip_longest(lines, lines2, fillvalue="[empty]"):
        line = line.strip()
        line2 = line2.strip()
        if not line:
            continue

        # Check for the start of a new chapter
        match = re.match(r'\[(\w+)\s(\d+)\]\[:1\]', line)

        if match:
            book, chapter = match.groups()
            book = book.title()  # Normalize book name
            book_num = book_map[book]
            chapter = int(chapter)
            current_verse = 1
            parsing_started = True
            uid_decimal = 1
            current_uid = float(f"{book_num:02}{chapter:03}{current_verse:03}.{uid_decimal:02}")
            print(f"\nProcessing {book} Chapter {chapter} : {current_uid}")

        # Skip lines before parsing begins
        if not parsing_started:
            if line != line2:
                print(line)
                print(line2)
                input()
            continue

        # Split the line into verses
        verses = split_verses(line)
        verses2 = split_verses(line2)

        addto = []
        strangecase = None

        #print(verses)
        for (marker, verse_content), (marker2, verse_content2) in zip_longest(verses, verses2, fillvalue=("[empty]","[empty]")):
            # Extract verse number from the marker
            verse_match = re.match(r'\[:(\d+)\]', marker)
            current_verse = int(verse_match.group(1))

            # Set verse in current_uid
            if current_verse > 1:
                # Step 1: Add 1 to the integer part
                new_uid_int = int(current_uid) + 1

                # Step 2: Add 0.01 to get the final value
                current_uid = float(f"{new_uid_int}.01")

            while int(current_verse) != (int(current_uid) % 1000):
                current_uid = round(current_uid + 1, 2)
                if int(current_uid) % 1000 > 200:
                    raise Exception("Something went wrong, there are never more than 200 verses.")

            #input(current_uid)

            if not doneskip:
                #skip anything before the start point
                if current_uid - start_uid < 0:
                    pass
                else:
                    doneskip = 1

            if not doneskip and not skipold:
                if verse_content == verse_content2:
                    #input()
                    continue

            # Check if verse already in database.
            # present = check_verse(conn, book, chapter, current_verse)
            
            # Process the verse content
            print(f"\n{book} {chapter} [:{current_verse}] - {verse_content}\n")
            words = verse_content.split()
            orig_words = words.copy()

            # Combine words that are continued inside brackets first
            combined_words = []
            combined_orig = []
            wordcontinue = ''
            o_wordcontinue = ''

            for word, orig_word in zip(words, orig_words):
                if word.count("[") > word.count("]") or len(wordcontinue) > 0:
                    wordcontinue = (wordcontinue + ' ' + word).strip() if wordcontinue else word
                    o_wordcontinue = (o_wordcontinue + ' ' + orig_word).strip() if o_wordcontinue else orig_word
                    if wordcontinue.count("[") == wordcontinue.count("]"):
                        combined_words.append(wordcontinue)
                        combined_orig.append(o_wordcontinue)
                        wordcontinue = ''
                        o_wordcontinue = ''
                    # else keep accumulating
                else:
                    combined_words.append(word)
                    combined_orig.append(orig_word)

            words = combined_words
            orig_words = combined_orig

            i = 0
            while i < len(words):
                word = words[i]
                if strangecase and word != "and":
                    #input("here")
                    if word.endswith("}"):
                        words[i] = strangecase + "-" + word[0:-1]
                        #input(word)
                        strangecase = None
                    else:
                        words[i] = strangecase + "-" + word
                    print("Reformatted word: {word}")
                if '_' in word:
                    # Split the word by underscores
                    parts = word.split('_')
                    if len(parts) == 3:
                        if parts[2].startswith("{"):
                            #input("strangecase")
                            strangecase = parts[0]
                            parts[2] = parts[2][1:]
                            #input(parts[2])
                        # If there are exactly three parts, format it as <word2> <word1>-<word3> 
                        new_word1 = f"{parts[0]}-{parts[2]}"
                        new_word2 = parts[1]
                        print(f"Reformatted word: {new_word2} {new_word1}")
                        # You can now use new_word1 and new_word2 as individual words
                        # Proceed to add them to the word processing flow
                        words[i] = new_word2  # Assign one of the new words to word for processing
                        words.insert(i+1, new_word1)
                        orig_words.insert(i+1, orig_words[i])
                        #input(words)
                        #input(orig_words)
                        i += 2
                        continue
                        # Add the second word separately
                        # process_word(new_word2) or whatever logic is needed
                    elif len(parts) == 2:
                        words[i] = parts[0]
                        words.insert(i+1, parts[1])
                        orig_words.insert(i+1, orig_words[i])
                        print(f"Reformatted word: {parts[0]} {parts[1]}")
                        input()
                    elif len(parts) == 4:
                        # If there are exactly four parts, format it as <word2> <word3> <word1>-<word4> 
                        new_word1 = f"{parts[0]}-{parts[3]}"
                        new_word2 = parts[1]
                        new_word3 = parts[2]
                        print(f"Reformatted word: {new_word2} {new_word3} {new_word1}")
                        # You can now use new_word1 and new_word2 as individual words
                        # Proceed to add them to the word processing flow
                        words[i] = new_word2  # Assign one of the new words to word for processing
                        words.insert(i+1, new_word3)
                        words.insert(i+2, new_word1)
                        orig_words.insert(i+1, orig_words[i])
                        orig_words.insert(i+2, orig_words[i])
                        i += 3
                        continue
                        # Add the second word separately
                        # process_word(new_word2) or whatever logic is needed
                    else:
                        # Handle the case where the word has more or fewer than 3 parts (if needed)
                        print(f"Unexpected format for word: {word}")
                i += 1

            wordcontinue = ''
            o_wordcontinue = ''
            for (word, orig_word) in zip(words, orig_words):                 

                if word.count("[") > word.count("]"):
                    wordcontinue = wordcontinue + word
                    o_wordcontinue = o_wordcontinue + orig_word
                    continue

                if len(wordcontinue) > 0:
                    wordcontinue = wordcontinue + ' ' + word
                    o_wordcontinue = o_wordcontinue + ' ' + orig_word
                    if wordcontinue.count("[") == wordcontinue.count("]"):
                        word = wordcontinue
                        orig_word = o_wordcontinue
                        wordcontinue = ''
                        o_wordcontinue = ''
                    else:
                        continue
                word, addto = processword(word, addto)

                uid = int(round(current_uid % 1, 2) * 100)

                print(f"English word: {word} | {orig_word} (Word #{uid})")   
                #if word != orig_word:          
                #    print(f"From: {orig_word}")
                #greek = input("Enter corresponding Greek word (or press Enter to skip): ").strip()
                # Check if the word already exists in the database
                if not check_if_present(conn, word, current_uid, orig_word):
                    if check_if_other(conn, current_uid):
                        #input(current_uid)
                        if check_and_update_raw(conn, word, current_uid, orig_word):
                            #input("ready to continue")
                            current_uid = round(current_uid + .01, 2)
                            continue
                        #input("you shouldn't be here")
                        cont = input(f"Word '{word}|{orig_word}' does not match existing entry. (n to cancel)")
                        if cont != "":
                            current_uid = round(current_uid + .01, 2)
                            continue
                        greek, guid = delete_verse_entries(conn, current_uid)
                    else:
                        greek = ""
                        guid = None
                    add_word_mapping(conn, word, current_uid, greek, orig_word, guid)
                else:
                    print(f"Word '{word}' already exists in the database for {book} {chapter} [:{current_verse}] UID={uid}.")
                current_uid = round(current_uid + .01, 2)
            # verse end, add a final check to see if there's an extra word (happens if words are deleted earlier in verse)
            while check_if_extra(conn, current_uid):
                cont = input("An extra word was found, delete it? (n to cancel)")
                if cont != "":
                    continue
                greek, guid = delete_verse_entries(conn, current_uid)
                current_uid = round(current_uid + .01, 2)
                conn.commit()
                print("--Commit---\n")

# Main function
def main():
    conn = sqlite3.connect("concordance.db")
    start_uid = 80001001.01
    skipold = 0
    # File input
    #filename = input("Enter the path to the text file: ").strip()
    filename = "rawtext.txt"
    oldfile = "rawtext_old.txt"
    process_text_file(filename, conn, start_uid, oldfile, skipold)
    
    conn.close()

if __name__ == "__main__":
    main()

