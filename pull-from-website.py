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

def align_marker_line(old_file, new_file, marker="Table of Contents"):
    def find_line(path):
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if marker in line:
                    return i
        return None

    old_idx = find_line(old_file)
    new_idx = find_line(new_file)

    if old_idx is None or new_idx is None:
        logging.warning("Marker not found in one of the files; skipping alignment.")
        return

    if old_idx < new_idx:
        diff = new_idx - old_idx
        with open(old_file, encoding="utf-8") as f:
            content = f.read()
        with open(old_file, "w", encoding="utf-8") as f:
            f.write("\n" * diff + content)
        logging.info(f"Prepended {diff} blank lines to {old_file} for alignment.")

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
        align_marker_line(old_file, output_file)

if __name__ == "__main__":
    URL = 'https://www.wiebefamily.org/GHT.htm'
    OUTPUT_FILE = "rawtext.txt"
    main(URL, OUTPUT_FILE)
