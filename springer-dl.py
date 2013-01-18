#!/usr/bin/env python

import argparse
import requests
import os
import tempfile
import urllib.parse
import sys
import subprocess
import time
from bs4 import BeautifulSoup

__author__ = "Gregor Wegberg"
__email__ = "github@gregorwegberg.ch"
__license__ = __copyright__ = "see UNLICENSE file"

class UnexpectedSpringerDocumentTypeException(Exception):
    pass


class UnexpectedSpringerContentFileTypeException(Exception):
    pass

class UserCanceledException(Exception):
    pass

def query_yes(str):
    print("%s [Y/n]" % str)
    answer = input().lower()

    if answer.startswith('n'):
        return False
    else:
        return True

def update_cli_progress(text, current, total):
    progress_length = 30

    progress_percent = float(current) / total
    progress_hashes = '#' * int(round(progress_percent * progress_length))
    progress_spaces = ' ' * (progress_length - len(progress_hashes))
    sys.stdout.write("\r%s: [%s] %s%% (%i of %i)" % (text,
                                                     progress_hashes + progress_spaces,
                                                     int(round(progress_percent * 100)),
                                                     current,
                                                     total))
    sys.stdout.flush()

def download_content(session, content_urls):
    local_files = []

    content_count = len(content_urls)
    progress_file = 1

    print("preparing for download")
    for file_url in content_urls:
        # update progress bar
        update_cli_progress("Downloading content", progress_file, content_count)

        # get content
        needs_convert = False
        response = session.get(file_url)

        # check for error
        if (response.status_code != requests.codes.ok) and (not query_yes("Could not get '%s'. Download further?" % file_url)):
            raise UserCanceledException("\nUser canceled further download")

        # guess file ending
        content_header = response.headers["Content-Type"]
        if 'pdf' in content_header:
            file_ending = '.pdf'
        elif 'tiff' in content_header:
            file_ending = '.tif'
            needs_convert = True
        else:
            raise UnexpectedSpringerContentFileTypeException("%s" % content_header)

        # save content into temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ending)
        temp_file.write(response.content)
        temp_file.close()

        # convert if needed
        if needs_convert: #TODO: own function so we can discover and use multiple tools for conversion
            convert_target = '%s.pdf' % temp_file.name #TODO: cleaner way to do this?

            convert_command = ['convert', temp_file.name, convert_target]
            subprocess.Popen(convert_command, shell=True).wait() #TODO: why does it need shell=True
            #TODO: handle error/warnings of convert

            os.remove(temp_file.name)
            local_files.append(convert_target)
        else:
            local_files.append(temp_file.name)
            # update progress vars
        progress_file += 1

    print("\nall files downloaded")
    return local_files


def __book_extract(session, root_page_response, root_page_parsed):
    content_urls = []

    #
    # check for cover image
    #
    about_link_element = root_page_parsed.find('a', id='about-link')
    if about_link_element:
        about_page_url = about_link_element.get('href')
        about_page_response = session.get(about_page_url)
        if about_page_response.status_code == requests.codes.ok:
            about_page_parsed = BeautifulSoup(about_page_response.text)

            book_cover_container = about_page_parsed.find('div', class_='productGraphic')
            if book_cover_container:
                book_cover_url = book_cover_container.find('a').get('href')
                content_urls.append(book_cover_url)
                print("found cover image")
            else:
                print("did *not* find any book cover")
        else:
            print("error requesting about page")
    else:
        print("did *not* find about page hyperlink")

    #
    # check for Front Matter and extract
    #
    front_matter_element = root_page_parsed.find(class_='front-matter-item')
    if front_matter_element:
        # build URL (absolute)
        front_matter_relative = front_matter_element.find('a').get('href')
        front_matter_url = urllib.parse.urljoin(root_page_response.url, front_matter_relative)

        # add to content
        content_urls.append(front_matter_url)
        print("Front Matter found")
    else:
        print("Front Matter *not* found")

    #
    # iterate over pages and extract content
    #
    current_page_url = root_page_response.url
    current_page_parsed = root_page_parsed

    while current_page_parsed and current_page_url:
        #
        # get chapters
        #
        chapter_items = current_page_parsed.find_all('li', class_='chapter-item')
        for chapter in chapter_items:
            chapter_name = chapter.find('p', class_='title').text.strip()

            if chapter.find('p', class_='no-access-message'):
                print("*access denied* for chapter %s" % chapter_name)
            else:
                chapter_pdf_relative_path = chapter.find('a', class_='pdf-link').get('href')
                chapter_pdf_absolute_url = urllib.parse.urljoin(current_page_url, chapter_pdf_relative_path)
                content_urls.append(chapter_pdf_absolute_url)
                print("found chapter '%s'" % chapter_name)

        #
        # check for Back Matter
        #
        back_matter_element = current_page_parsed.find(class_='back-matter-item')
        if back_matter_element:
            back_matter_relative_path = back_matter_element.find('a').get('href')
            back_matter_absolute_url = urllib.parse.urljoin(current_page_url, back_matter_relative_path)
            content_urls.append(back_matter_absolute_url)
            print("Back Matter found")

        # update for next page
        next_element = current_page_parsed.find('link', rel='next')
        if next_element:
            next_page_relative = next_element.get('href')
            next_page_absolute_url = urllib.parse.urljoin(current_page_url, next_page_relative)
            next_page_response = session.get(next_page_absolute_url)

            if next_page_response.status_code == requests.codes.ok:
                current_page_url = next_page_response.url
                current_page_parsed = BeautifulSoup(next_page_response.text)
                print("moving on to next page")
            else:
                print("could not get next page: %s" % next_page_absolute_url)
                current_page_url = current_page_parsed = None
        else:
            print("done with all pages")
            current_page_url = current_page_parsed = None

    return content_urls


def extract_content(session, url, outputfile):
    # get the given web page to get started
    root_page_response = session.get(url)
    root_page_response.raise_for_status()

    # parse page
    root_page_parsed = BeautifulSoup(root_page_response.text)

    # find out what we try to download and delegate the content extractions accordingly
    document_type = root_page_parsed.find('div', id='content').find('div', class_='document').get('id')
    content_urls = None
    if document_type == 'book':
        content_urls = __book_extract(session, root_page_response, root_page_parsed)
    else: # default case
        raise UnexpectedSpringerDocumentTypeException("%s" % document_type)

    # download the found content
    temp_files = download_content(session, content_urls)

    # merge everything
    #TODO: own function, discover different tools and so on
    merge_command = ["pdftk"]
    merge_command.extend(temp_files)
    merge_command.extend(["cat", "output", outputfile])
    pdf_process = subprocess.Popen(merge_command, shell=False)

    chars = '|/-\\-'
    while pdf_process.poll() is None:
        for c in chars:
            sys.stdout.write('\rmerging files into single PDF file... %s' % c)
            sys.stdout.flush()
            time.sleep(1)
    print("\nmerged files and saved at %s" % outputfile)

    # clean up temporary files
    print("deleting temporary files:")
    for file in temp_files:
        print("\t%s" % file)
        os.remove(file)


def main():
    # prepare argument parsing
    #TODO: add option for proxy
    argparser = argparse.ArgumentParser(
        description="Python script to download journals, books, etc. from rd.springer.com")

    argparser.add_argument('url', action='store',
        help="URL to the journal, book, etc. to download")

    argparser.add_argument('output', action='store',
        help="Path to save the PDF at")

    # parse arguments
    args = argparser.parse_args()

    # prepare session to browse the web
    session = requests.session()
    session.headers.update({
        'User-Agent': "Why don't you provide everything in a single PDF file to download? At the end you get paid for it!"})

    extract_content(session, args.url, args.output)


if __name__ == '__main__':
    main()
