import re
from urllib.parse import urlparse,urljoin, urldefrag
from utils import get_urlhash
from bs4 import BeautifulSoup
import os

class Scraper:
    def __init__(self):
        self.visited_urls = set()
       
        
    def scraper(self, url, resp):

        if url in self.visited_urls:
            return []  # Skip processing if URL has already been visited - URL deduplication
        else:
            self.visited_urls.add(url)  # Mark the URL as visited
            links = self.extract_next_links(url, resp)
            if links:
                print("yes links")
            # self.save_to_local_disk(url, resp)
            return [link for link in links if self.is_valid(link)]



    def extract_next_links(self,url, resp):
        if resp.status == 200 and resp.raw_response.content:
            print("yes extract")
            soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
            base_url = resp.raw_response.url

            # Extract all anchor tags (<a>) with an 'href' attribute
            links = soup.find_all('a', href=True)

            # Extract the href attribute from each anchor tag and create absolute URLs
            scraped_urls = [urljoin(base_url, link['href']) for link in links]

            # Remove fragments from the URLs
            scraped_urls = [urldefrag(url)[0] for url in scraped_urls]

            # Filter URLs to include only those within the specified domains and paths
            scraped_urls = [url for url in scraped_urls if self.is_valid(url)]
            print(scraped_urls)
            return scraped_urls
        else:
            return []


    def is_valid(self, url):
        # List of allowed domains and paths
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu",
            "today.uci.edu"
        ]
        allowed_paths = [
            "/",
            "/department/information_computer_sciences/"
        ]

        try:
            
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return False
            netloc = parsed.netloc.replace("www.", "")
#             if netloc not in allowed_domains:
#                 print("Not allowed domain:", parsed.netloc)
#                 print("Allowed domains:", allowed_domains)
#                 return False
            
#             if not any(parsed.path.startswith(path) for path in allowed_paths):
#                 return False
            
            # Check if the URL starts with "https://swiki.ics.uci.edu/" - temporary fix to avoid getting there
            if parsed.scheme == "https" and netloc == "swiki.ics.uci.edu" and parsed.path.startswith("/"):
                return False
            # Check if the URL starts with "https://wiki.ics.uci.edu/" - temporary fix to avoid getting there
            if parsed.scheme == "https" and netloc == "wiki.ics.uci.edu" and parsed.path.startswith("/"):
                return False

            return not re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ova"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        except TypeError:
            print("TypeError for ", parsed)
            raise

    def save_to_local_disk(self, url, resp):
        if resp.status == 200 and resp.raw_response.content:
            with open("url_list.txt", 'a') as url_file:
                url_file.write(url + '\n')

            # save_path = os.path.join("IR-Winter 24/spacetime-crawler4py/webContent", get_urlhash(url) + ".html")
            # with open(save_path, 'wb') as file:
            #     file.write(resp.raw_response.content)