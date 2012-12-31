'''
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Copyright (C) 2012 Gregor Wegberg <github@gregorwegberg.com>

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
'''

import argparse
import tempfile
import os
import sys #TODO: REMOVE
import subprocess
import urllib.parse

import requests
from bs4 import BeautifulSoup

# TODO: react if user cannot download files because of missing rights
# TODO: some way to log in?
# TODO: add some sort of progress bar / dl speed / ...
# TODO: error handling

def __download_pdf(url, session):
	# get the pdf
	response = session.get(url)
	response.raise_for_status()
	assert("pdf" in response.headers["Content-Type"])
	
	# create temporary file
	temp_file = tempfile.NamedTemporaryFile(delete=False)
	temp_file.write(response.content)
	temp_file.close()
	
	return temp_file.name

def download_book_content(url, session):
	temp_content_files = []
	
	# get the starting page
	response = session.get(url)
	response.raise_for_status()
	
	# parse the webpage and ...
	soup = BeautifulSoup(response.text)
	
	# ... get cover image
	#TODO
	
	# ... get front matter
	print("Downloading front matter... ")
	front_matter_path = soup.find(class_="front-matter-item").find("a")["href"]
	front_matter_url = urllib.parse.urljoin(response.url, front_matter_path)
	temp_content_files.append(__download_pdf(front_matter_url, session))
	print("done.")
	
	# ... get chapters
	print("Downloading chapters... ")
	chapter_items = soup.find_all("li", class_="chapter-item")
	for chapter in chapter_items:
		chapter_pdf_path = chapter.find("a", class_="pdf-link")["href"]
		chapter_pdf_url = urllib.parse.urljoin(response.url, chapter_pdf_path)
		temp_content_files.append(__download_pdf(chapter_pdf_url, session))
	print("done.")
	
	# ... get back matter
	print("Downloading back matter... ")
	back_matter_path = soup.find(class_="back-matter-item").find("a")["href"]
	back_matter_url = urllib.parse.urljoin(response.url, back_matter_path)
	temp_content_files.append(__download_pdf(back_matter_url, session))
	print("done.")

	return temp_content_files
	
def merge_files(output_file, merge_files):
	print("Merging %i files... " % (len(merge_files)))
	command = ["pdftk"]
	command.extend(merge_files)
	command.extend(["cat", "output", output_file])
	subprocess.Popen(command, shell=False).wait()
	print("done.")

def main():
	argparser = argparse.ArgumentParser(
		description="Python script to download from rd.springer.com")
	argparser.add_argument("url", action="store",
		help="URL to the specific Book to download")
	argparser.add_argument("output", action="store",
		help="Path to save the PDF at")
	args = argparser.parse_args()
	
	headers = {"User-Agent": "why do I need this script? I just need it as a single PDF!"}
	session = requests.Session()
	session.headers.update(headers)
	
	temp_content_files = download_book_content(args.url, session)
	merge_files(args.output, temp_content_files)
	
	# clean up
	for file in temp_content_files:
		os.remove(file)
		
	print("Task finished. Exiting.")
	
if __name__ == '__main__':
	main()