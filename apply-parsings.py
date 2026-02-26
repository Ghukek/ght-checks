import sqlite3

def contains_pronouns(word):
    helper_words = {"you", "we", "they", "i", "he", "she", "it"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def contains_subjunctive(word):
    helper_words = {"should", "may", "would"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def contains_optative(word):
    helper_words = {"could", "might"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_1s(word):
    helper_words = {"i"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_1p(word):
    helper_words = {"we"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_2(word):
    helper_words = {"you"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_3s(word):
    helper_words = {"he", "she", "it"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_3p(word):
    helper_words = {"they"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def check_genitive(word, english):
    parts = pcode.split('-')
    # Defensive: sometimes pcode might have fewer parts
    if len(parts) < 2:
        return True  # Can't check further, allow

    case_part = parts[-1]  # The last 'xxx' 

    # Check genitive/dative and presence of "of{" / "to{" in english
    if case_part.startswith("G"):  # Genitive: expect "of{" in English
        if "of{" not in english:
            print("Failed genitive")
            return False
    elif case_part.startswith("D"):  # Dative: expect "to{" in English
        if "to{" not in english:
            print("Failed dative")
            return False
    else:  # Other cases: must NOT have "of{" or "to{"
        if "of{" in english or "to{" in english:
            print("Failed not genitive or dative")
            return False
    return True

def is_plural(word):
    helper_words = {"we", "they"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def is_singular(word):
    helper_words = {"i", "am", "is", "he", "she", "it"}
    parts = word.lower().split('-')
    return any(part in helper_words for part in parts)

def grammatical_match(pcode, english):
    """
    Basic rule-based grammatical match function.
    Expand as needed.
    """
    pcode = pcode.upper()
    english = english.lower()

    if not check_genitive(pcode, english):
        return False

    if pcode.startswith("N-") or pcode == "N":  # Noun checks

        parts = pcode.split('-')
        # Defensive: sometimes pcode might have fewer parts
        if len(parts) < 2:
            return True  # Can't check further, allow

        case_part = parts[1]  # The first 'xxx' after
        # Check plural or singular agreement with English form
        if case_part.endswith("P"):  # Plural expected
            # Prompt the user for plurality.
            valid = input("Is this word plural?")
            if valid == "n" or valid == "ν":
                return False
        elif case_part.endswith("S"):  # Singular expected
            # If it ends with 's', probably plural, so might not match
            valid = input("Is this word singular?")
            if valid == "n" or valid == "ν":
                return False
        return True
    elif pcode.startswith("V-"):  # Noun
        # Ensure Plural
        if pcode.endswith("S"):
            if is_plural(english):
                print("Failed singular")
                return False
        elif pcode.endswith("P"):
            if is_singular(english):
                print("Failed plural")
                return False

        if pcode.endswith("1S"):
            if is_1p(english) or is_2(english) or is_3s(english) or is_3p(english):
                print("Failed 1S")
                return False
        elif pcode.endswith("1P"):
            if is_1s(english) or is_2(english) or is_3s(english) or is_3p(english):
                print("Failed 1P")
                return False
        elif pcode.endswith("2P") or pcode.endswith("2S"):
            if is_1p(english) or is_1s(english) or is_3s(english) or is_3p(english):
                print("Failed 2nd")
                return False
        elif pcode.endswith("3S"):
            if is_1p(english) or is_2(english) or is_1s(english) or is_3p(english):
                print("Failed 3S")
                return False
        elif pcode.endswith("3P"):
            if is_1p(english) or is_2(english) or is_3s(english) or is_1s(english):
                print("Failed 3P")
                return False

        # Ensure tenses
        if pcode[2] == "F":
            if "will-" not in english:
                print("Failed Future")
                return False
        else:
            if "will-" in english:
                valid = input("Should 'will-' be here?")
                if valid == "n" or valid == "ν":
                    return False

        if pcode[2] == "L":
            if "had-" not in english:
                print("Failed Pluperfect")
                return False
        else:
            if "had-" in english:
                valid = input("Should 'had-' be here?")
                if valid == "n" or valid == "ν":
                    return False

        if pcode[2] == "R":
            if ("has-" not in english and "having-" not in english and "have-" not in english) or "being" in english:
                print("Failed Perfect")
                return False
            if pcode.endswith("3S") and "has-" not in english:
                print("Should have 'has-'")
                return False
            elif not pcode.endswith("3S") and "has-" in english:
                print("Should have 'have-'")
                return False
        elif pcode[2] == "I":
            if "has-been-" not in english and "have-been-" not in english:
                print("Failed Imperfect")
                return False
            if pcode.endswith("3S") and "has-" not in english:
                print("Should have 'has-'")
                return False
            elif not pcode.endswith("3S") and "has-" in english:
                print("Should have 'have-'")
                return False
        else:
            if "has-" in english or "have-" in english or "having-" in english:
                valid = input("Should 'has/have/having' be here?")
                if valid == "n" or valid == "ν":
                    return False

        if pcode[2] == "A":
            if "being-" in english:
                print("Failed Aorist")
                return False
            if "ing" in english and "[ing]" not in english:
                valid = input("Should this aorist have 'ing'?")
                if valid == "n" or valid == "ν":
                    return False
        elif pcode[2] == "P":
            if "[ing]" in english and "-" not in english:
                print("Failed Present")
                return False

        if pcode[3] == "S":
            if not contains_subjunctive(english) or contains_optative(english):
                print("Failed Subjunctive")
                return False
        elif pcode[3] == "O":
            if not contains_optative(english) or contains_subjunctive(english):
                print("Failed Optative")
                return False
        elif pcode[3] == "M" or pcode[3] == "I" or pcode[3] == "N":
            if contains_subjunctive(english) or contains_optative(english):
                print("Failed Imp/Ind/Inf")
                return False
        elif pcode[3] == "P":
            if contains_pronouns(english) or contains_subjunctive(english):
                print("Failed Participle")
                return False

        if "V-PM" in pcode:
            if not english.startswith("be-"):
                valid = input("Is this a valid present imperative: ")
                if valid == "n" or valid == "ν":
                    return False
        elif "V-AM" in pcode:
            if english.startswith("be-"):
                valid = input("Is this a valid aorist imperative: ")
                if valid == "n" or valid == "ν":
                    return False
        elif english.startswith("be-"):
                valid = input("Should this seem like an imperative?: ")
                if valid == "n" or valid == "ν":
                    return False

        if "APA" in pcode:
            if "[ing]" not in english:
                print("Failed Aorist Participle Active")
                return False
            if "-" in english:
                valid = input("Is this a valid aorist participle?: ")
                if valid == "n" or valid == "ν":
                    return False
        if "PPA" in pcode:
            if "ing" not in english:
                print("Failed Present Participle Active")
                return False
            if "-" in english:
                valid = input("Is this a valid present participle?: ")
                if valid == "n" or valid == "ν":
                    return False
        if "PSA" in pcode:
            if "ing" not in english or "-be-" not in english:
                print("Failed present subjunctive.")
                return False

        if "[ing]" in english and "APA" not in pcode:
            valid = input("Is this a valid use of [ing]?: ")
            if valid == "n" or valid == "ν":
                return False

        if "V-PI" in pcode:
            if "-" not in english:
                print("Invalid present indicative")
                return False
            if "are-" not in english and "is-" not in english and "am-" not in english:
                print("Invalid present indicative")
                return False

        if pcode[2] == "I":
            if "has-been" in english:
                # He/she has been
                if not pcode.endswith("3S"):
                    print("Failed number.")
                    return False
            elif "have-been" in english:
                # They have, I have, We have, You have
                if pcode.endswith("3S"):
                    print("Failed number.")
                    return False
            else:
                return False

        if pcode.endswith("1P") or pcode.endswith("3P") or pcode.endswith("2P") or pcode.endswith("2S"):
            # We are, they are, you are, you are
            if "is-" in english or "am-" in english:
                print("Failed number")
                return False
        elif pcode.endswith("1S"):
            # I am
            if "is-" in english or "are-" in english:
                print("Failed number")
                return False
        elif pcode.endswith("3S"):
            # He/she is
            if "am-" in english or "are-" in english:
                print("Failed number")
                return False
        if len(pcode) > 4 and pcode[4] == "P":
            if english[-2:] != "ed" and english[-2:] != "en":
                valid = input("Is this word passive?: ")
                if valid == "n" or valid == "ν":
                    return False
            if english[-3] == "ing":
                return False
        if pcode[3] == "N":
            if not english.startswith("to-") or contains_pronouns(english) or contains_subjunctive(english) or contains_optative(english):
                print("not infinitive")
                return False
            if pcode[2] == "A" and "-be-" in english and english.endswith("ing"):
                print("not aorist")
                return False
            elif pcode[2] == "P" and "-be-" not in english and not english.endswith("ing"):
                print("not present")
                return False
        else:
            if english.startswith("to-"):
                valid = input("Is this a valid use of 'to-'?: ")
                if valid == "n" or valid == "ν":
                    return False             
        if "V-P" in pcode:
            if "ing" not in english:
                print("Not Present")
                return False

        if "-self" in english:
            if pcode.endswith("P"):
                print("Should be 'selves'")
                return False
        elif "-selves" in english:
            if pcode.endswith("S"):
                print("Should be 'self'")
                return False

            
        #input(f"{pcode} no conflicts found, continue?")
        return True
    elif pcode.startswith("Adv"):
        if english[-2:] == "ly":
            return True
        valid = input("Is this a valid adverb?: ")
        if valid == "n" or valid == "ν":
            return False
    else:
        #input(f"{pcode} no conflicts found, continue?")
        return True  # Default fallback if unsure

# Connect to database
conn = sqlite3.connect('concordance.db')
cursor = conn.cursor()

cursor.execute("SELECT rowid, english, greek, pcode, strongs FROM word_map")
rows = cursor.fetchall()

for row in rows:
    rowid, english, greek, current_pcode, current_strongs = row

    if current_pcode is not None and current_strongs is not None:
        continue

    if greek == "none":
        continue
    # Find possible matches from parsings
    cursor.execute("SELECT pcode, strongs FROM parsings WHERE inflection = ?", (greek,))
    parsing_matches = cursor.fetchall()

    if parsing_matches:
        print(f"\nMatches for: '{greek}' | '{english}'")
        for idx, (pcode, strongs) in enumerate(parsing_matches):
            print(f"  [{idx}] pcode: {pcode}, strongs: {strongs}")
    else:
        print(f"\nNo parsings found for: '{greek}' | '{english}'")

        # Prompt user for manual entry
        pcode = input(f"Enter pcode for '{greek}': ").strip()
        strongs = input(f"Enter Strong's number for '{greek}': ").strip()

        if not pcode:
            print("Skipping...")
            continue

        # Validate and convert Strong's number to integer if possible
        try:
            strongs = int(strongs)
        except ValueError:
            print("Invalid Strong's number. Skipping...")
            continue

        # Insert into parsings table
        try:
            cursor.execute("""
                INSERT INTO parsings (inflection, pcode, strongs)
                VALUES (?, ?, ?)
            """, (greek, pcode, strongs))
            conn.commit()
            print(f"Inserted manual entry into parsings: ({greek}, {pcode}, {strongs})")
        except sqlite3.IntegrityError as e:
            print(f"Failed to insert into parsings due to integrity error: {e}")
        continue

    valid_matches = []

    for pcode, strongs in parsing_matches:
        if grammatical_match(pcode, english):
            valid_matches.append((pcode, strongs))

    if len(valid_matches) == 1:
        best_match = valid_matches[0]
    elif len(valid_matches) > 1:
        print("Valid matches based on grammatical rules:")
        for idx, (pcode, strongs) in enumerate(valid_matches):
            print(f"  [{idx}] pcode: {pcode}, strongs: {strongs}")

        while True:
            choice = input("Select the best match by number (or blank to skip): ").strip()
            if choice == "":
                best_match = None
                break
            if choice.isdigit() and int(choice) < len(valid_matches):
                best_match = valid_matches[int(choice)]
                break
            else:
                print("Invalid choice. Try again.")
    else:
        print("No valid grammatical matches.")
        input()
        best_match = None

    if best_match:
        # Show top 5 matching entries
        cursor.execute("""
            SELECT greek, english, count, pcode
            FROM word_map
            WHERE strongs = ?
            ORDER BY count DESC
        """, (best_match[1],))
        
        top_matches = cursor.fetchall()
        proceed = None
        if top_matches:
          print(f"\nTop matches for Strong's #{best_match[1]}:")
          for i, p in enumerate(top_matches, start=1):
              print(f"{i}. {p[0]} | {p[1]}, {p[3]} {p[2]}")
              if i == 10:
                  break
          
          # Prompt the user to confirm
          proceed = input("\nProceed with update? (n to cancel): ").strip().lower()
        
        if proceed != 'n':
            cursor.execute("""
                UPDATE word_map
                SET pcode = ?, strongs = ?
                WHERE rowid = ?
            """, (best_match[0], best_match[1], rowid))
            conn.commit()
            print("Update committed.\n")
        else:
            print("Update cancelled.\n")

# Save and close
conn.commit()
conn.close()

print("Update complete.")
