import re


class Config(object):
    def __init__(self, config):
        self.user_agent = config["IDENTIFICATION"]["USERAGENT"].strip()
        print (self.user_agent)
        assert self.user_agent != "DEFAULT AGENT", "Set useragent in config.ini"
        assert re.match(r"^[a-zA-Z0-9_ ,]+$", self.user_agent), "User agent should not have any special characters outside '_', ',' and 'space'"
        self.threads_count = int(config["LOCAL PROPERTIES"]["THREADCOUNT"])
        self.save_file = config["LOCAL PROPERTIES"]["SAVE"]
        self.output_dir = config["LOCAL PROPERTIES"]["SAVE_DIR"]

        self.host = config["CONNECTION"]["HOST"]
        self.port = int(config["CONNECTION"]["PORT"])

        self.seed_urls = config["CRAWLER"]["SEEDURL"].split(",")
        self.time_delay = float(config["CRAWLER"]["POLITENESS"])
        self.max_file_size = int(config["CRAWLER"]["MAX_FILE_SIZE"])
        
        # Additional crawler settings
        self.min_content_length_threshold = int(config["CRAWLER"]["MIN_CONTENT"])
        self.min_text_length = int(config["CRAWLER"]["MIN_TXT_LEN"])
        self.min_word_count = int(config["CRAWLER"]["MIN_WORD_COUNT"])
        self.min_unique_word_count = int(config["CRAWLER"]["MIN_UNIQUE_WC"])
        self.min_text_density = float(config["CRAWLER"]["MIN_TEXT_DENSITY"])
        self.min_stopword_density = float(config["CRAWLER"]["MIN_STOPWORD_DENSITY"])
        self.allowed_domains = list(config["CRAWLER"]["ALLOWED_DOMAINS"].split(","))
        self.allowed_paths = list(config["CRAWLER"]["ALLOWED_PATHS"].split(","))
        self.cache_server = None