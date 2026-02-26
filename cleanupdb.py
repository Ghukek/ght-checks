import sqlite3

def ensure_count_column(conn, destination_table):
    """Ensure the 'count' column exists in the destination table."""
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({destination_table})")
    columns = [row[1] for row in c.fetchall()]
    if "count" not in columns:
        print(f"Adding 'count' column to {destination_table}.")
        c.execute(f"ALTER TABLE {destination_table} ADD COLUMN count INTEGER")
        conn.commit()

# This is obsolete. Need to update it to do this, but instead for each pair and count, verify if the count matches. Otherwise throw a flag.
def copy_and_count_entries(db_path, source_table, destination_table):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Ensure the 'count' column exists in the destination table
    ensure_count_column(conn, destination_table)

    # Query all unique english-greek pairs and their counts from the source table
    c.execute(f"""
        SELECT english, greek, COUNT(*) as pair_count
        FROM {source_table}
        GROUP BY english, greek
    """)
    source_entries = c.fetchall()

    # Iterate through each pair and its count
    for english, greek, pair_count in source_entries:
        # Check if the (english, greek) pair exists in the destination table
        c.execute(f"""
            SELECT count FROM {destination_table}
            WHERE english = ? AND greek = ?
        """, (english, greek))
        result = c.fetchone()

        # If the pair does not exist, insert it with the count
        if not result:
            c.execute(f"""
                INSERT INTO {destination_table} (english, greek, count)
                VALUES (?, ?, ?)
            """, (english, greek, pair_count))
            print(f"Added pair to {destination_table}: {english}, {greek} with count {pair_count}")
        else:
            # Update the count if the pair already exists
            c.execute(f"""
                UPDATE {destination_table}
                SET count = ?
                WHERE english = ? AND greek = ?
            """, (pair_count, english, greek))
            #print(f"Updated count for {english}, {greek} to {pair_count}")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

def remove_unmatched_entries(db_path, source_table, destination_table):
    """Remove entries in the destination table that do not have a corresponding entry in the source table."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Delete only if count is not null
    c.execute(f"""
        DELETE FROM {destination_table}
        WHERE count IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM {source_table}
            WHERE {source_table}.english = {destination_table}.english
              AND {source_table}.greek = {destination_table}.greek
        )
    """)

    deleted_count = c.rowcount  # Count the number of rows deleted
    conn.commit()
    conn.close()

    print(f"Removed {deleted_count} unmatched entries from {destination_table}.")

def ensure_unique_pairs(db_path, destination_table):
    conn = sqlite3.connect(db_path)
    """
    Ensures that the destination_table contains one and only one entry for each unique english-greek pair.

    Parameters:
        conn (sqlite3.Connection): The SQLite connection object.
        destination_table (str): The name of the destination table.
    """
    c = conn.cursor()

    # Identify duplicate entries (english, greek) pairs
    c.execute(f"""
        SELECT english, greek, COUNT(*)
        FROM {destination_table}
        GROUP BY english, greek
        HAVING COUNT(*) > 1
    """)
    duplicates = c.fetchall()

    # Iterate over duplicates and delete all but one for each pair
    for english, greek, count in duplicates:
        print(f"Found {count} duplicate(s) for pair: {english} - {greek}")
        
        # Keep one entry, delete the rest
        c.execute(f"""
            DELETE FROM {destination_table}
            WHERE rowid NOT IN (
                SELECT rowid
                FROM {destination_table}
                WHERE english = ? AND greek = ?
                LIMIT 1
            )
            AND english = ? AND greek = ?
        """, (english, greek, english, greek))
        print(f"Removed duplicates for pair: {english} - {greek}")

    conn.commit()
    print("Duplicate removal completed. All pairs are now unique.")

def find_missing(db_path, source_table, destination_table):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Find all unique (english, greek) pairs in entries
    c.execute(f"SELECT DISTINCT english, greek FROM {source_table}")
    pairs = c.fetchall()

    inserted_count = 0

    # Check and insert into word_map if missing
    for english, greek in pairs:
        c.execute(f"SELECT 1 FROM {destination_table} WHERE english = ? AND greek = ?", (english, greek))
        if not c.fetchone():
            c.execute(f"INSERT INTO {destination_table} (english, greek, count) VALUES (?, ?, ?)", (english, greek, 0))
            inserted_count += 1

    conn.commit()
    conn.close()

    print(f"Inserted {inserted_count} missing word_map entries.")

# Example usage
if __name__ == "__main__":
    database_path = "concordance.db"
    source_table_name = "entries"
    destination_table_name = "word_map"
    copy_and_count_entries(database_path, source_table_name, destination_table_name)
    remove_unmatched_entries(database_path, source_table_name, destination_table_name)
    ensure_unique_pairs(database_path, destination_table_name)
    #find_missing(database_path, source_table_name, destination_table_name) #REDUNDANT

