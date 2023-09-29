import os
import random
import bs4
import requests
import time
from PIL import Image
from tqdm import tqdm

# Modify these three variables to your liking
folder_name = "Kakegurui"  # Name of the folder you would like the pdfs to be saved in
base_url = "https://chapmanganato.com/manga-pi952917/chapter-1"  # Put first chapter here from manga site (default works only for Manganato)
delay_between_requests = 0  # Delay in seconds between each image download to avoid time out

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

if __name__ == '__main__':
    # Inits
    pdf = None
    current_page = base_url
    pdf_pages = []
    session = requests.Session()

    # Creates the dir for the pdfs
    os.makedirs(folder_name, exist_ok=True)
    dir_path = f"{folder_name}/"
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
                file_name = f"{folder_name}/image_{i + 1}.jpg"

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
            pdf.save(f'{folder_name}/chapter_{iteration + 1}.pdf', save_all=True, append_images=pdf_pages)
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


