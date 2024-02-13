import os
from configparser import ConfigParser
from argparse import ArgumentParser
from threading import Lock
from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler
from crawler import Frontier, Worker
from threading import Thread, Lock

def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    frontier = Frontier(config, restart)
    politeness = 0.5  # Politeness delay in seconds
    workers = []

    # Create and start worker threads
    for i in range(config.num_threads):
        worker = Worker(i, config, frontier, politeness)
        workers.append(worker)
        worker.start()

    # Wait for all worker threads to finish
    for worker in workers:
        worker.join()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
