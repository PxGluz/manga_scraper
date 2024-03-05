import os
import random
import bs4
import requests
import time
from PIL import Image
from tqdm import tqdm
import argparse
import atexit
import json


def exit_handler(folder_name, pdf_var, pdf_pages, offset, last_chapter, current_pdfs):
    all_files = os.listdir(f"{folder_name}/")
    for item in all_files:
        if item.endswith(".jpg"):
            os.remove(os.path.join(folder_name, item))
    current_pdfs += 1
    pdf_var.save(f'{folder_name}/Batch_{current_pdfs}-{(last_chapter - offset) % args.batch_size + 1}_chapters.pdf', save_all=True, append_images=pdf_pages)

    json_file = json.dumps({
        "last_chapter": last_chapter + 1,
        "current_pdfs": current_pdfs,
    }, indent=4)
    with open(f"{folder_name}/info.json", "w") as outfile:
        outfile.write(json_file)
    print(f"Finished downloading {last_chapter - offset + 1} chapters!")


# These should not be modified
session = None
args = None
headers_list = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.3"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.3"
    },
]
default_json = {
    "last_chapter": 0,
    "current_pdfs": 0,
}


def download_chapters(base_url, manga_name, starting_chapter, current_pdfs):
    # Inits
    pdf = None
    current_page = base_url
    pdf_pages = []

    iteration = starting_chapter

    # Iterates through all the chapters until there are no more chapters
    while current_page is not None:
        html = session.get(current_page, headers=random.choice(headers_list), allow_redirects=False)
        # Get html of current page
        soup = bs4.BeautifulSoup(html.text, 'html.parser')

        # Getting the images here
        reader_container = soup.find("div", {"class": "container-chapter-reader"})
        image_links = [x['src'] for x in reader_container.findChildren("img")]

        # Here we iterate through all the images of the current chapter
        for i in tqdm(range(len(image_links)), desc=f"Downloading chapter {iteration + 1}"):
            image_url = image_links[i]
            file_name = f"{manga_name}/image_{i + 1}.jpg"

            # We update the headers to create a reference to the current chapter page
            headers = random.choice(headers_list)
            headers["Referer"] = current_page

            with session.get(image_url, headers=headers) as response:
                with open(file_name, "wb") as f:
                    f.write(response.content)

            # We add it to the current image list and initialize the first image if it is not already
            if pdf is None:
                pdf = Image.open(file_name).convert('RGB')
            else:
                pdf_pages.append(Image.open(file_name).convert('RGB'))

            # We remove the current image from the pc as it is already stocked in the memory and sleep if we need to
            os.remove(file_name)
            time.sleep(args.delay_between_requests)
        atexit.unregister(exit_handler)
        atexit.register(exit_handler, manga_name, pdf, pdf_pages, starting_chapter, iteration, current_pdfs)

        # We check if there is a next chapter
        next_chapter = soup.find("a", {"class": "navi-change-chapter-btn-next"})
        if next_chapter is not None:
            # If there is we go to the next page and create the pdf of the current one
            current_page = next_chapter['href']

            if (iteration - starting_chapter + 1) % args.batch_size == 0:
                current_pdfs += 1
                pdf.save(f'{manga_name}/Batch_{current_pdfs}-{args.batch_size}_chapters.pdf', save_all=True, append_images=pdf_pages)
                pdf_pages = []
                pdf = None
            iteration += 1
        else:
            # If not, then we end the program
            current_page = None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='MangaScraper',
                    description='Download pdf mangas from manganato.com',
                    epilog='Program made by PxGluz')
    parser.add_argument('-s', '-search-size', default=5, type=int, dest="search_size", help="how many results should be shown when searching")
    parser.add_argument('-b', '-batch-size', default=1, type=int, dest="batch_size", help="how many chapters should be saved in each pdf")
    parser.add_argument('-d', '-delay-between-requests', default=0, type=float, dest="delay_between_requests", help="delay between each of the made requests")
    args = parser.parse_args()

    session = requests.Session()
    const_link = "https://manganato.com/search/story/"

    while True:
        search_name = input("Please input the name of the manga you want downloaded: ").replace(' ', '_')
        html_page = session.get(const_link + search_name.lower(), headers=random.choice(headers_list), allow_redirects=False)
        search_soup = bs4.BeautifulSoup(html_page.text, 'html.parser')
        search_results = search_soup.find("div", {"class": "panel-search-story"})
        if search_results is not None:
            elements = search_results.findChildren("a", {"class": "item-img bookmark_check"})[:args.search_size]
            links = [x['href'] for x in elements]
            titles = [x['title'] for x in elements]

            while True:
                print("\n0. Return to searching\n")
                for i in range(len(titles)):
                    print(f"{i + 1}. {titles[i]}")
                choice = int(input("Choose one of the results: "))
                if choice < 0 or choice > len(titles):
                    print("\nInvalid input!\n")
                else:
                    if choice != 0:
                        chapters_html = session.get(links[choice - 1], headers=random.choice(headers_list),
                                                    allow_redirects=False)
                        chapters_soup = bs4.BeautifulSoup(chapters_html.text, 'html.parser')
                        chapter_list = chapters_soup.find("ul", {"class": "row-content-chapter"})
                        if chapter_list is not None:
                            starting_chapter = 0
                            current_pdfs = 0

                            # Creates the dir for the pdfs
                            os.makedirs(titles[choice - 1], exist_ok=True)
                            dir_path = f"{titles[choice - 1]}/"
                            if not os.path.isfile(f"{dir_path}info.json"):
                                json_file = json.dumps(default_json, indent=4)
                                with open(f"{dir_path}info.json", "w") as outfile:
                                    outfile.write(json_file)
                            else:
                                with open(f"{dir_path}info.json", "r") as openfile:
                                    json_data = json.load(openfile)
                                    starting_chapter = json_data["last_chapter"]
                                    current_pdfs = json_data["current_pdfs"]
                                    print(f"Skipping to chapter: {starting_chapter + 1}")
                            chapter_children = chapter_list.findChildren("a", {"class": "chapter-name text-nowrap"})
                            if starting_chapter >= len(chapter_children):
                                print("\nNo new chapters... Returning to search")
                                choice = 0
                            else:
                                starting_chapter_link = chapter_children[-(starting_chapter + 1)]["href"]
                                download_chapters(starting_chapter_link, titles[choice - 1], starting_chapter, current_pdfs)
                        else:
                            print("\nManga has no chapters... Returning to search")
                            choice = 0
                    break
            if choice != 0:
                break
        else:
            print("\nNo results... Returning to search")
