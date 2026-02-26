import sqlite3

def setwordmap():

  # Connect to the database
  conn = sqlite3.connect("concordance.db")
  cursor = conn.cursor()

  # Get all rows sorted by count (highest first)
  cursor.execute("SELECT greek, english FROM word_map ORDER BY count DESC")
  rows = cursor.fetchall()

  # Assign ident values globally (1 = highest count)
  for ident_value, (greek, english) in enumerate(rows, start=0):
      cursor.execute("""
          UPDATE word_map
          SET ident = ?
          WHERE greek = ? AND english = ?
      """, (ident_value, greek, english))

  # Commit changes
  conn.commit()
  conn.close()

  print("Finished assigning ident values globally by count.")

def update_entries(entries_db_path, word_map_db_path):
    # Connect to word_map source DB
    wm_conn = sqlite3.connect(word_map_db_path)
    wm_cursor = wm_conn.cursor()
    wm_cursor.execute("SELECT greek, english, ident FROM word_map")
    word_map_data = wm_cursor.fetchall()
    wm_conn.close()

    # Create lookup dictionary
    lookup = {(grk, eng): ident for grk, eng, ident in word_map_data}

    # Connect to entries target DB
    ent_conn = sqlite3.connect(entries_db_path)
    ent_cursor = ent_conn.cursor()

    ent_cursor.execute("SELECT rowid, greek, english FROM entries")
    entries = ent_cursor.fetchall()

    for rowid, grk, eng in entries:
        # Skip entries that don't have english text
        if not eng or eng.strip() == "":
            continue  

        ident = lookup.get((grk, eng))

        if ident is not None:  # only update if we found a match
            ent_cursor.execute(
                "UPDATE entries SET ident = ? WHERE rowid = ?",
                (ident, rowid)
            )

    ent_conn.commit()
    ent_conn.close()
    print(f"Updated entries.ident in {entries_db_path} using word_map from {word_map_db_path}")

def assign_missing_english(entries_db_path, parsings_db_path):
    ent_conn = sqlite3.connect(entries_db_path)
    ent_cur = ent_conn.cursor()

    par_conn = sqlite3.connect(parsings_db_path)
    par_cur = par_conn.cursor()

    # Find entries with non-empty English and no ident (i.e., not found in word_map)
    ent_cur.execute("""
        SELECT DISTINCT greek, english
        FROM entries
        WHERE ident=="" AND english IS NOT NULL AND TRIM(english) != ''
    """)
    missing_pairs = ent_cur.fetchall()
    print(f"Found {len(missing_pairs)} entries with missing ident but valid English.")

    for greek, english in missing_pairs:
        # Find matching parsings with that Greek word
        par_cur.execute("""
            SELECT ident, mac, strongs, english
            FROM parsings
            WHERE greek = ?
        """, (greek,))
        candidates = par_cur.fetchall()

        if not candidates:
            print(f"No matching parsing entries found for Greek word '{greek}', skipping.")
            continue

        print(f"\n--- Assigning English '{english}' to Greek '{greek}' ---")

        chosen_ident = None

        if len(candidates) == 1:
            ident, mac, strongs, existing_eng = candidates[0]
            if existing_eng is None or existing_eng.strip() == "":
                print(f"Only one parsing entry (mac={mac}), assigning directly.")
                par_cur.execute("""
                    UPDATE parsings
                    SET english = ?
                    WHERE ident = ?
                """, (english, ident))
                chosen_ident = ident
            else:
                print(f"Existing English already present: '{existing_eng}', creating new parsing.")
        else:
            print("Multiple parsing entries found:")
            for idx, (ident, mac, strongs, eng) in enumerate(candidates):
                print(f"  [{idx}] ident={ident}, mac={mac}, strongs={strongs}, english={eng}")
            while True:
                try:
                    choice = int(input("Choose which mac to assign the new English to (or press Enter to skip): "))
                    if 0 <= choice < len(candidates):
                        ident, mac, strongs, existing_eng = candidates[choice]
                        break
                except ValueError:
                    print("Invalid choice. Enter a number.")
                    continue

            if existing_eng is None or existing_eng.strip() == "":
                print(f"Assigning directly to ident {ident}")
                par_cur.execute("""
                    UPDATE parsings
                    SET english = ?
                    WHERE ident = ?
                """, (english, ident))
                chosen_ident = ident
            else:
                print(f"Existing English already present: '{existing_eng}', creating new parsing.")

        # If existing parsing already has English, make new row
        if chosen_ident is None:
            # Use selected or only parsing as template
            mac = mac
            strongs = strongs
            par_cur.execute("""
                INSERT INTO parsings (greek, mac, strongs, english)
                VALUES (?, ?, ?, ?)
            """, (greek, mac, strongs, english))
            new_ident = par_cur.lastrowid
            chosen_ident = new_ident
            print(f"Created new parsing entry with ident={new_ident}")

        # Now update entries with this (greek, english) to use chosen_ident
        ent_cur.execute("""
            UPDATE entries
            SET ident = ?
            WHERE greek = ? AND english = ? AND ident IS NULL
        """, (chosen_ident, greek, english))

        ent_conn.commit()
        par_conn.commit()

    ent_conn.close()
    par_conn.close()
    print("Finished assigning missing English values.")

def renumber_conflicting_idents(parsings_db_path, entries_db_path, word_map_db_path):
    wm_conn = sqlite3.connect(word_map_db_path)
    wm_cursor = wm_conn.cursor()
    wm_cursor.execute("SELECT MAX(ident) FROM word_map")
    max_wm_ident = wm_cursor.fetchone()[0]
    wm_conn.close()

    if max_wm_ident is None:
        max_wm_ident = 0

    print(f"Max word_map ident: {max_wm_ident}")

    par_conn = sqlite3.connect(parsings_db_path)
    par_cursor = par_conn.cursor()

    ent_conn = sqlite3.connect(entries_db_path)
    ent_cursor = ent_conn.cursor()

    # Get all idents currently in lxx-wh.entries
    ent_cursor.execute("SELECT DISTINCT ident FROM entries")
    all_idents = set(row[0] for row in ent_cursor.fetchall())

    # Find idents in lxx-wh.entries that are <= max_wm_ident (conflicting)
    ent_cursor.execute("SELECT DISTINCT ident FROM entries WHERE ident <= ?", (max_wm_ident,))
    conflicting_idents = [row[0] for row in ent_cursor.fetchall()]
    print(f"Found {len(conflicting_idents)} conflicting idents to renumber.")

    # Prepare new idents: start from max_wm_ident + 1 upwards, skipping any already in all_idents
    new_ident = max_wm_ident + 1
    new_idents_map = {}
    for old_ident in conflicting_idents:
        # Find next available new_ident
        while new_ident in all_idents:
            new_ident += 1
        new_idents_map[old_ident] = new_ident
        all_idents.add(new_ident)
        new_ident += 1

    # Update parsings table
    for old_ident, new_ident in new_idents_map.items():
        #print(old_ident, new_ident)
        par_cursor.execute("UPDATE parsings SET ident = ? WHERE ident = ?", (new_ident, old_ident))

    par_conn.commit()

    # Update entries table
    for old_ident, new_ident in new_idents_map.items():
        ent_cursor.execute("UPDATE entries SET ident = ? WHERE ident = ?", (new_ident, old_ident))

    ent_conn.commit()

    par_conn.close()
    ent_conn.close()

    print(f"Renumbered {len(conflicting_idents)} conflicting idents in parsings and entries.")

def update_entries_from_multiple_sources(entries_db_path, concordance_db_path, lxx_wh_db_path):
    # Load lookup from concordance.db (word_map)
    conc_conn = sqlite3.connect(concordance_db_path)
    conc_cursor = conc_conn.cursor()
    conc_cursor.execute("SELECT greek, english, ident FROM word_map")
    word_map_data = conc_cursor.fetchall()
    conc_conn.close()

    # Load lookup from lxx-wh.db (parsings)
    lxx_conn = sqlite3.connect(lxx_wh_db_path)
    lxx_cursor = lxx_conn.cursor()
    lxx_cursor.execute("SELECT greek, english, ident FROM parsings")
    parsings_data = lxx_cursor.fetchall()
    lxx_conn.close()

    # Merge both into one lookup dictionary
    # Priority: concordance.db > lxx-wh.db (can reverse if needed)
    lookup = {}
    for grk, eng, ident in parsings_data:
        lookup[(grk, eng)] = ident
    for grk, eng, ident in word_map_data:
        lookup[(grk, eng)] = ident  # overwrite with concordance version if it exists

    # Connect to lxx.db
    ent_conn = sqlite3.connect(entries_db_path)
    ent_cursor = ent_conn.cursor()
    ent_cursor.execute("SELECT rowid, greek, english FROM entries")
    entries = ent_cursor.fetchall()

    updated_count = 0
    for rowid, grk, eng in entries:
        if not eng or eng.strip() == "":
            continue

        ident = lookup.get((grk, eng))
        if ident is not None:
            ent_cursor.execute(
                "UPDATE entries SET ident = ? WHERE rowid = ?",
                (ident, rowid)
            )
            updated_count += 1

    ent_conn.commit()
    ent_conn.close()

    print(f"Updated {updated_count} entries.ident in {entries_db_path} using concordance + lxx-wh")

def clear_stale_idents(entries_db_path, concordance_db_path, lxx_wh_db_path):
    print("Clearing stale idents in lxx.db...")

    # open databases
    lxx_conn = sqlite3.connect(entries_db_path)
    concordance_conn = sqlite3.connect(concordance_db_path)
    wh_conn = sqlite3.connect(lxx_wh_db_path)

    lxx_conn.row_factory = concordance_conn.row_factory = wh_conn.row_factory = sqlite3.Row
    lxx_cur = lxx_conn.cursor()
    conc_cur = concordance_conn.cursor()
    wh_cur = wh_conn.cursor()

    # --- 1. Collect valid (greek, english, ident) from authoritative sources ---
    valid_pairs = set()

    for row in conc_cur.execute("SELECT greek, english, ident FROM word_map WHERE ident IS NOT NULL"):
        valid_pairs.add((row["greek"], row["english"], row["ident"]))

    for row in wh_cur.execute("SELECT greek, english, ident FROM parsings WHERE ident IS NOT NULL"):
        valid_pairs.add((row["greek"], row["english"], row["ident"]))

    print(f"Loaded {len(valid_pairs)} valid ident triplets from external sources.")

    # --- 2. Identify stale idents in lxx.db.entries ---
    stale_ids = []
    for row in lxx_cur.execute("SELECT rowid, greek, english, ident FROM entries WHERE ident != ''"):
        triplet = (row["greek"], row["english"], row["ident"])
        if triplet not in valid_pairs:
            #input(f"found stale {triplet}")
            stale_ids.append(row["rowid"])

    # --- 3. Nullify stale idents ---
    if stale_ids:
        placeholders = ",".join("?" for _ in stale_ids)
        lxx_cur.execute(f"UPDATE entries SET ident = '' WHERE rowid IN ({placeholders})", stale_ids)
        lxx_conn.commit()
        print(f"Cleared {len(stale_ids)} stale idents.")
    else:
        print("No stale idents found.")

    # --- 4. Clean up ---
    lxx_conn.close()
    concordance_conn.close()
    wh_conn.close()

import sqlite3

def compact_lxx_wh_idents(lxx_wh_db_path, lxx_entries_db_path, start_at=0):
    """
    Renumber parsings.ident in lxx-wh.db to be contiguous with no gaps,
    starting at start_at (default 0), and update lxx.db.entries.ident accordingly.
    """

    print("Compacting lxx-wh idents...")

    # Connect
    wh_conn = sqlite3.connect(lxx_wh_db_path)
    wh_cur = wh_conn.cursor()

    ent_conn = sqlite3.connect(lxx_entries_db_path)
    ent_cur = ent_conn.cursor()

    # Load existing idents (sorted, unique)
    wh_cur.execute("""
        SELECT DISTINCT ident
        FROM parsings
        WHERE ident IS NOT NULL AND ident != ''
        ORDER BY ident
    """)
    old_idents = [row[0] for row in wh_cur.fetchall()]

    print(f"Found {len(old_idents)} idents in parsings.")

    # Build remapping
    remap = {}
    new_ident = start_at
    for old in old_idents:
        remap[old] = new_ident
        new_ident += 1

    if not remap:
        print("No idents to compact.")
        return

    # Apply to parsings
    for old, new in remap.items():
        wh_cur.execute(
            "UPDATE parsings SET ident = ? WHERE ident = ?",
            (new, old)
        )

    wh_conn.commit()

    # Apply to entries
    for old, new in remap.items():
        ent_cur.execute(
            "UPDATE entries SET ident = ? WHERE ident = ?",
            (new, old)
        )

    ent_conn.commit()

    wh_conn.close()
    ent_conn.close()

    print(f"Compacted {len(remap)} idents. New range: {start_at} → {new_ident - 1}")


setwordmap() 
renumber_conflicting_idents("lxx-wh.db", "lxx-wh.db", "concordance.db")
update_entries("concordance.db", "concordance.db")
update_entries_from_multiple_sources("lxx.db", "concordance.db", "lxx-wh.db")
clear_stale_idents("lxx.db", "concordance.db", "lxx-wh.db")
assign_missing_english("lxx.db", "lxx-wh.db")
#compact_lxx_wh_idents("lxx-wh.db", "lxx.db", start_at=20723)
