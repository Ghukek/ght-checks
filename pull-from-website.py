import requests
from bs4 import BeautifulSoup
from shutil import copyfile
import re
import os
import logging

from ftplib import FTP
import logging

def upload_via_ftp(file_path, remote_filename, ftp_host, ftp_user, ftp_pass):
    try:
        with FTP(ftp_host) as ftp:
            ftp.login(user=ftp_user, passwd=ftp_pass)
            logging.info(f"Connected to FTP server: {ftp_host}")

            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)

            logging.info(f"Uploaded {file_path} as {remote_filename} to {ftp_host}")
    except Exception as e:
        logging.error(f"FTP upload failed: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to fetch HTML content
def fetch_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an error for bad responses
        return response.content
    except requests.RequestException as e:
        logging.error(f"Error fetching the URL: {e}")
        exit()

# Function to extract and clean the text
def clean_html(soup):
    for element in soup.find_all(['a', 'b', 'i', 'u']):
        element.unwrap()  # Keep text, remove tags
    return soup.get_text()

# Function to save processed text to a file
def save_to_file(filename, content):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        logging.info(f"Processed text saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving to file: {e}")

def save_raw_html(filename, content):
    try:
        with open(filename, 'wb') as f:
            f.write(content)
        logging.info(f"Raw HTML saved to {filename}")
    except IOError as e:
        logging.error(f"Error saving raw HTML to file: {e}")

import os
import logging
from collections import defaultdict

def align_files(old_file, new_file, output_file=None):
    with open(old_file, encoding="utf-8") as f:
        old_lines = [line.rstrip("\n") for line in f]

    with open(new_file, encoding="utf-8") as f:
        new_lines = [line.rstrip("\n") for line in f]

    # Build index map for occurrences in new file
    positions = defaultdict(list)
    for i, line in enumerate(new_lines):
        positions[line].append(i)

    def next_pos(line, start_idx):
        """Find first occurrence of line in new_lines after start_idx"""
        for p in positions.get(line, []):
            if p >= start_idx:
                return p
        return None

    aligned_old = []
    new_idx = 0

    for old_line in old_lines:
        if new_idx >= len(new_lines):
            aligned_old.append(old_line)
            continue

        target = next_pos(old_line, new_idx)

        # Case 1: line never appears again in new → consume both
        if target is None:
            aligned_old.append(old_line)
            new_idx += 1  # force advancement in new stream
            continue

        # Case 2: new has extra lines before match → insert blanks
        while new_idx < target:
            aligned_old.append("")  # blank line inserted into old
            new_idx += 1

        # Case 3: lines match → consume both
        aligned_old.append(old_line)
        new_idx += 1

    # Optional: if new has trailing lines, reflect them as blanks in old
    while new_idx < len(new_lines):
        aligned_old.append("")
        new_idx += 1

    result = "\n".join(aligned_old) + "\n"

    if output_file is None:
        output_file = old_file

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    logging.info(f"Aligned file written to {output_file}")

# Main function
def main(url, output_file):
    if os.path.exists(output_file):
        old_file = f"{os.path.splitext(output_file)[0]}_old{os.path.splitext(output_file)[1]}"
        copyfile(output_file, old_file)
        print(f"Existing file saved as: {old_file}")

    html_content = fetch_html(url)

    # Save the raw HTML before parsing
    raw_html_file = "ght_mirror.htm"
    save_raw_html(raw_html_file, html_content)

    soup = BeautifulSoup(html_content, 'html.parser')
    text = clean_html(soup)
    save_to_file(output_file, text)

    # Align old backup with new file
    old_file = f"{os.path.splitext(output_file)[0]}_old{os.path.splitext(output_file)[1]}"
    if os.path.exists(old_file):
        align_files(old_file, output_file)

if __name__ == "__main__":
    URL = 'https://www.wiebefamily.org/GHT.htm'
    OUTPUT_FILE = "rawtext.txt"
    main(URL, OUTPUT_FILE)
