from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
from scraper import Scraper
from urllib.parse import urlparse,urljoin, urldefrag
from utils import get_urlhash
import re
import time
import inspect
import nltk
from nltk.corpus import stopwords

import hashlib
import os


class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        self.scraper = Scraper() 
        self.crawled_hashes = set()
        self.text_content = ""
        self.visited_urls = set()

        # Basic check for requests in scraper
        scraper_source = inspect.getsource(Scraper)
        assert scraper_source.find("import requests") == -1, "Do not use requests in scraper.py"
        assert scraper_source.find("import urllib.request") == -1, "Do not use urllib.request in scraper.py"

        super().__init__(daemon=True)
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break
            '''
            # Avoid infinite loops by checking if the URL has been visited before
            if tbd_url in self.visited_urls:
                self.logger.info(f"Avoiding {tbd_url} to prevent infinite loop.")
                self.frontier.mark_url_complete(tbd_url)
                continue

            # Mark the URL as visited
            self.visited_urls.add(tbd_url)
            ''' 
            
            # Honor the politeness delay
            time.sleep(self.config.time_delay)

            resp = download(tbd_url, self.config, self.logger)
            
            self.logger.info( f"Downloaded {tbd_url}, status <{resp.status}> ")
            
            # Check invalid responses
            if not resp:
                self.logger.info(f"Skipping {tbd_url} due to empty or invalid response.")
                self.frontier.mark_url_complete(tbd_url)
                continue
                
            else:
                
                #Detect and avoid dead URLs that return a 200 status but no data
                if resp.status == 200 and (not resp.raw_response.content or len(resp.raw_response.content) < self.config.min_content_length_threshold):
                    self.logger.info(f"Detected a URL with no data: {tbd_url}")
                    self.frontier.mark_url_complete(tbd_url)
                    continue


                # Check for very large files
                if resp is not None and resp.raw_response is not None:
                    if len(resp.raw_response.content) > self.config.max_file_size and self.has_low_information_value(resp):
                        self.logger.info(f"Skipping {tbd_url} due to its large size and low information value.")
                        self.frontier.mark_url_complete(tbd_url)
                        continue
                        
                '''
                ##### Get the text content from the html file 
                soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
                # kill all script and style elements
                for script in soup(["script", "style"]):
                    script.extract()    # rip it out
                
                # get text
                text = soup.get_text()
                self.text_content = text
                ''' 

                #self.text_content= resp.raw_response.content.decode("utf-8", "ignore")
                if resp.raw_response is not None:
                    self.text_content = resp.raw_response.content.decode("utf-8", "ignore") 
                    
                    # download the text content if all checks are passed
                    self.download_text(tbd_url)
                    # if self.should_avoid(tbd_url):
                    #     self.logger.info(f"Avoiding {tbd_url} to prevent external crawl.")
                    #     continue              
                    scraped_urls = self.scraper.scraper(tbd_url, resp)

                    if not scraped_urls:
                        self.logger.info(f"Skipping {tbd_url} as it has no information content.")
                        self.frontier.mark_url_complete(tbd_url)
                        continue

                    for scraped_url in scraped_urls:
                        # Detect and avoid prohibited sites                                


                        # Check similarity with already scraped pages
                        if self.is_similar_to_scraped(scraped_url):
                            self.logger.info(f"Skipping {scraped_url} as it is similar to already scraped pages.")
                            continue


                        self.frontier.add_url(scraped_url)
                        self.logger.info(f"Added {scraped_url} to the frontier.")

                        # Check if the download was successful
                        if resp is None:
                            self.logger.info(f"Failed to download {tbd_url}. Skipping.")
                            self.frontier.mark_url_complete(tbd_url)
                            continue

                        self.logger.info( f"Downloaded {tbd_url}, status <{resp.status}> ")

                    self.frontier.mark_url_complete(tbd_url)
                else:
                    None

                
                
                
                
    
            
    def is_non_textual_content(self, resp):
        """
        Check if the response contains non-textual content.
        """
        # List of non-textual content types (example: images, videos, executables)
        non_textual_content_types = {"image", "video", "audio", "application"}

        content_type = resp.headers.get("Content-Type", "")
        for non_textual_type in non_textual_content_types:
            if non_textual_type in content_type:
                return True
        return False

    def has_low_information_value(self, resp):
        """
        check for meaningful text, 
        """
        
        # Get the Content-Type header from the response
        content_type = resp.raw_response.headers.get("Content-Type", "")

#         # Define non-textual content types
#         non_textual_content_types = {"image", "video", "audio", "application"}

#         # Check if any non-textual content type is present in the Content-Type header
#         for content_type_keyword in non_textual_content_types:
#             if content_type_keyword in content_type:
#                 return True        
    
        #minimum text length
        if len(self.text_content) < self.config.min_text_length:
            return True
        
        # Word count threshold
        word_count_threshold = self.config.min_word_count
        if len(self.text_content.split()) < word_count_threshold:
            return True

        # Unique word count threshold
        unique_word_count_threshold = self.config.min_unique_word_count
        unique_words = set(self.text_content.split())
        if len(unique_words) < unique_word_count_threshold:
            return True

        # Text density threshold
        text_density_threshold = self.config.min_text_density
        text_density = sum(c.isalpha() for c in self.text_content) / len(self.text_content)
        if text_density < text_density_threshold:
            return True

        # Stopword density threshold
        stop_words = set(stopwords.words("english"))
        content_words = [word for word in self.text_content.split() if word.lower() not in stop_words]
        stopword_density_threshold = self.config.min_stopword_density
        stopword_density = 1 - (len(content_words) / len(self.text_content.split()))
        if stopword_density > stopword_density_threshold:
            return True
        
        return False
    
    
    def should_avoid(self, url):
        """
        Check if the given URL should be avoided to prevent infinite traps.
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        print("Allowed Domains:", self.config.allowed_domains)
        print("Allowed Paths:", self.config.allowed_paths)
        
        # Check if the domain is in the list of allowed domains
        if not any(domain.endswith(allowed_domain) for allowed_domain in self.config.allowed_domains):
            self.logger.info(f"Avoiding {url} because it's not in the allowed domains.")
            return True

        # Check if the path is in the list of allowed paths for the domain
        if not any(path.startswith(allowed_path) for allowed_path in self.config.allowed_paths):
            self.logger.info(f"Avoiding {url} because it's not in the allowed paths.")
            return True
        
        

        return False

    def download_text(self, url):
        """
        save the correct url and save the content in results dir.
        """
        with open("finalURL.txt", 'a') as op:
            op.write(url + '\n')
        
        folder = os.path.join(self.config.output_dir, "downloaded")
        os.makedirs(folder, exist_ok=True)
        filename = f"{hashlib.sha256(url.encode()).hexdigest()}.txt"
        # Create the full file path
        file_path = os.path.join(folder, filename)

        # Write the text to the file
        with open(file_path, 'w') as file:
            file.write(self.text_content)

        print(f'Saved text to {file_path}')
        

    def hash_content(self, content):

        # Create a new sha256 hash object
        hash_object = hashlib.sha256()

        # If content is bytes, decode it to string
        if isinstance(content, bytes):
            content = content.decode('utf-8', 'ignore')

        # Encode the content and update the hash object with this data
        hash_object.update(content.encode('utf-8'))

        # Get the hexadecimal representation of the hash
        hash_hex = hash_object.hexdigest()

        return hash_hex
    
    def is_similar_to_scraped(self, url):
        """
        Check if the content of the given URL is similar to the content of already scraped pages.
        """
        # Download the content of the URL
        resp = download(url, self.config, self.logger)
        
        # Check if the URL has been visited before
        if url in self.visited_urls:
            self.logger.info(f"Skipping {url} as it has already been visited.")
            return True

        if resp and resp.raw_response and resp.raw_response.content:
            # Calculate hash of the content
            content_hash = self.hash_content(resp.raw_response.content)

            # Check if the hash is already in the set of crawled hashes
            if content_hash in self.crawled_hashes:
                return True

            # Add the hash to the set of crawled hashes
            self.crawled_hashes.add(content_hash)

        return False


