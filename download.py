"""
download images
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from fake_useragent import UserAgent
import time
import random


def _download_image(url, headers, savefile):
    logging.info(f"request url = {url}")
    response = requests.get(url, headers=headers)

    if response.ok:
        data = response.content
        if not savefile.parent.exists():
            logging.info(f"Create dir = {savefile.parent}")
            savefile.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"Save to {savefile}")
        with open(savefile, "wb") as f:
            f.write(data)
        return True

    logging.warning(f"Error status = {response.status_code}")
    return False


def download_image(url, headers, savefile, retry=2):
    res = False
    for i in range(retry):
        if i > 0:
            logging.info(f"Retry = {i+1}/{retry}")
        res = _download_image(url, headers, savefile)
        if res:
            return res

        time.sleep(random.randint(3, 10))
    return res


def download_json(url, headers, savefile, keys, sleep):
    logging.info(f"request url = {url}")
    response = requests.get(url, headers=headers)
    if response.ok:
        data = response.json()
        image_url = data
        for key in keys:
            image_url = image_url[key]

        if isinstance(image_url, str) and image_url.startswith("http"):
            if sleep:
                time.sleep(random.randint(3, 10))
            return download_image(image_url, headers, savefile)

    logging.warning(f"Error status = {response.status_code}")
    return False


def download(info, date, save_dir, sleep=True) -> bool:
    year, month, day = date.split("-")
    filename = date.replace("-", "") + ".jpg"

    url = info["path"].format(base=info["base"], year=year, month=month, day=day)
    savefile = Path(save_dir, year, filename)
    if savefile.exists():
        logging.debug("Exits save file, ignore")
        return False

    ua = UserAgent(platforms=["pc"])
    headers = {"User-Agent": ua.random, "referrer": info["site"]}

    if info["format"] == "image":
        return download_image(url, headers, savefile)
    elif info["format"] == "json":
        return download_json(url, headers, savefile, info["keys"], sleep)

    return False


def read_config(config_file):

    if Path(config_file).exists():
        logging.info(f"Read config = {config_file}")
        with open(config_file) as f:
            return json.load(f)
    logging.info(f"Error, no config file = {config_file}")
    return None


def process(config_file, save_dir, names, date):
    config = read_config(config_file)
    if config is None:
        logging.warning("Error: config is None")
        return

    if names is None:
        names = sorted(config.keys())
    logging.info(f"names = {names}")

    if date is None:
        LOS_ANGELES = ZoneInfo("Asia/Shanghai")
        now = datetime.datetime.now(tz=LOS_ANGELES)
        logging.info(f"now = {now}")
        date = now.strftime("%Y-%m-%d")
    logging.info(f"Date = {date}")

    for name in names:
        logging.info(f"Process name={name}")
        subdir = Path(save_dir, name)
        download(config[name], date, subdir)


def process_batch(config_file, save_dir, days=30):
    config = read_config(config_file)
    if config is None:
        logging.warning("Error: config is None")
        return

    names = sorted(config.keys())
    now = datetime.datetime.now(datetime.UTC)
    logging.info(f"Download batch, names = {names}, now={now}")

    for gap in range(days):
        day = now - datetime.timedelta(days=gap)
        date = day.strftime("%Y-%m-%d")
        logging.info(f"Download date = {date}")
        success = 0
        for name in names:
            logging.info(f"Process name={name}")
            subdir = Path(save_dir, name)
            res = download(config[name], date, subdir, sleep=False)
            if res:
                success += 1
        if success > 0:
            time.sleep(random.randint(1, 5))


if __name__ == "__main__":
    fmt = "%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    args = argparse.ArgumentParser()
    args.add_argument("--config", type=str, default="config.json")
    args.add_argument("--out", type=str, default="data")
    args.add_argument("--names", type=str, default=None)
    args.add_argument("--date", type=str, default=None)
    args.add_argument("--days", type=int, default=0)

    parser = args.parse_args()
    config_file = parser.config
    save_dir = parser.out
    names = parser.names
    date = parser.date
    days = parser.days

    if days > 0:
        process_batch(config_file, save_dir, 30)
    else:
        process(config_file, save_dir, names, date)
