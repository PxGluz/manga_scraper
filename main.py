import os
import random
import bs4
import requests
import time
from PIL import Image
from tqdm import tqdm
import argparse
import atexit


def exit_handler(folder_name):
    print('Forced exit!')
    all_files = os.listdir(f"{folder_name}/")

    for item in all_files:
        if item.endswith(".jpg"):
            os.remove(os.path.join(folder_name, item))


# Modify these three variables to your liking
delay_between_requests = 0  # Delay in seconds between each image download to avoid time out

# These should not be modified
pdf = None
session = None
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


def download_chapters(base_url, manga_name):
    # Inits
    pdf = None
    current_page = base_url
    pdf_pages = []

    # Creates the dir for the pdfs
    os.makedirs(manga_name, exist_ok=True)
    dir_path = f"{manga_name}/"
    starting_chapter = 0
    for path in os.listdir(dir_path):
        if os.path.isfile(os.path.join(dir_path, path)):
            starting_chapter += 1
    iteration = 0

    # Iterates through all the chapters until there are no more chapters
    while current_page is not None:
        html = session.get(current_page, headers=random.choice(headers_list), allow_redirects=False)
        # Get html of current page
        soup = bs4.BeautifulSoup(html.text, 'html.parser')

        if iteration >= starting_chapter:
            # Getting the images here
            reader_container = soup.find("div", {"class": "container-chapter-reader"})
            image_links = [x['src'] for x in reader_container.findChildren("img")]

            # Here we iterate through all the images of the current chapter
            for i in tqdm(range(len(image_links)), desc=f"Downloading chapter {iteration + 1}!"):
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
                time.sleep(delay_between_requests)
            pdf.save(f'{manga_name}/chapter_{iteration + 1}.pdf', save_all=True, append_images=pdf_pages)
        else:
            print(f"Skipping chapter {iteration + 1}, it already exists!")

        # We check if there is a next chapter
        next_chapter = soup.find("a", {"class": "navi-change-chapter-btn-next"})
        if next_chapter is not None:
            # If there is we go to the next page and create the pdf of the current one
            current_page = next_chapter['href']
            pdf_pages = []
            pdf = None
            iteration += 1
        else:
            # If not, then we end the program
            current_page = None

    print(f"Finished creating {iteration - starting_chapter + 1} chapter pdfs!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='MangaScraper',
                    description='Download pdf mangas from manganato.com',
                    epilog='Program made by PxGluz')
    parser.add_argument('-s', '-search-size', default=5, type=int, dest="search_size", help="how many results should be shown when searching")
    args = parser.parse_args()

    session = requests.Session()
    const_link = "https://manganato.com/search/story/"
    search_size = args.search_size

    while True:
        search_name = input("Please input the name of the manga you want downloaded: ")
        html_page = session.get(const_link + search_name.lower(), headers=random.choice(headers_list), allow_redirects=False)
        search_soup = bs4.BeautifulSoup(html_page.text, 'html.parser')
        search_results = search_soup.find("div", {"class": "panel-search-story"})
        if search_results is not None:
            elements = search_results.findChildren("a", {"class": "item-img bookmark_check"})[:search_size]
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
                            first_chapter_link = chapter_list.findChildren("a", {"class": "chapter-name text-nowrap"})[-1]["href"]
                            atexit.register(exit_handler, titles[choice - 1])
                            download_chapters(first_chapter_link, titles[choice - 1])
                        else:
                            print("\nManga has no chapters... Returning to search")
                            choice = 0
                    break
            if choice != 0:
                break
        else:
            print("\nNo results... Returning to search")
