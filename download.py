"""
download images
"""

import argparse
import datetime
import json
import logging
import random
import time

from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from fake_useragent import UserAgent


def _download_image(url, headers, savefile):
    logging.info(f"request url = {url}")
    status = None
    try:
        response = requests.get(url, headers=headers, timeout=30)
        status = response.status_code
        if response.status_code == 200:
            data = response.content
            if not savefile.parent.exists():
                logging.info(f"Create dir = {savefile.parent}")
                savefile.parent.mkdir(parents=True, exist_ok=True)
            logging.info(f"Save to {savefile}")
            with open(savefile, "wb") as f:
                f.write(data)
        return response.status_code
    except Exception:
        logging.warning(f"Error status = {status}")

    return -1


def download_image(url, headers, savefile, retry=2):
    for i in range(retry):
        if i > 0:
            logging.info(f"Retry = {i+1}/{retry}")

        res = _download_image(url, headers, savefile)
        if res in [200, 404]:
            return True

        if i + 1 < retry:
            time.sleep(random.randint(3, 10))
    return False


def download_json(url, headers, savefile, json_savefile, keys, sleep):
    logging.info(f"request url = {url}")
    status = None
    try:
        response = requests.get(url, headers=headers)
        status = response.status_code
        if response.status_code == 200:
            data = response.json()
            # save json
            json_savefile.parent.mkdir(parents=True, exist_ok=True)
            with open(json_savefile, "w") as f:
                json.dump(data, f, indent=None, ensure_ascii=False)

            image_url = data
            for key in keys:
                if key in image_url:
                    image_url = image_url[key]
                else:
                    return False

            if isinstance(image_url, str) and image_url.startswith("http"):
                if sleep:
                    time.sleep(random.randint(3, 10))
                return download_image(image_url, headers, savefile)
    except Exception:
        logging.warning(f"Error status = {status}")

    return False


def download(info, date, save_dir, json_save_dir, sleep=True) -> bool:
    year, month, day = date.split("-")
    filename = date.replace("-", "") + ".jpg"
    savefile = Path(save_dir, year, filename)
    json_savefile = Path(json_save_dir, year, date.replace("-", "") + ".json")
    if savefile.exists():
        if info["format"] != "json" or json_savefile.exists():
            logging.debug(f"Exits save file, ignore, format={info['format']}")
            return False

    ua = UserAgent(platforms=["pc", "desktop"])
    headers = {"User-Agent": ua.random, "referrer": info["site"]}
    url = info["path"].format(base=info["base"], year=year, month=month, day=day)

    if info["format"] == "image":
        return download_image(url, headers, savefile)
    elif info["format"] == "json":
        return download_json(url, headers, savefile, json_savefile, info["keys"], sleep)

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
        json_subdir = Path(save_dir, name + "-json")
        download(config[name], date, subdir, json_subdir)


def process_v2(config_file, save_dir, names, date=None):
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
    else:
        now = datetime.datetime.strptime(date, "%Y-%m-%d")
    logging.info(f"now = {now}")
    for name in names:
        gaps = config[name]["gaps"]
        logging.info(f"Process name={name}, gaps={gaps}")
        subdir = Path(save_dir, name)
        json_subdir = Path(save_dir, name + "-json")
        for day in gaps:
            new_date = (now + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
            download(config[name], new_date, subdir, json_subdir)


def process_batch(config_file, save_dir, days=30):
    config = read_config(config_file)
    if config is None:
        logging.warning("Error: config is None")
        return

    # 过滤失效
    config = {k: v for k, v in config.items() if v["status"] == 1}

    names = sorted(config.keys())
    now = datetime.datetime.now(datetime.UTC)
    logging.info(f"Download batch, names = {names}, now={now}")
    start, end = min(days, 0), max(days, 0)
    for gap in range(start, end):
        day = now - datetime.timedelta(days=gap)
        date = day.strftime("%Y-%m-%d")
        logging.info(f"Download date = {date}")
        success = 0
        for name in names:
            logging.info(f"Process name={name}")
            subdir = Path(save_dir, name)
            json_subdir = Path(save_dir, name + "-json")
            res = download(config[name], date, subdir, json_subdir, sleep=False)
            if res:
                success += 1
        if success > 0:
            time.sleep(random.randint(1, 5))


if __name__ == "__main__":
    fmt = "%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json")
    parser.add_argument("--out", type=str, default="data")
    parser.add_argument("--names", type=str, default=None)
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--days", type=int, default=0)

    args = parser.parse_args()
    config_file = args.config
    save_dir = args.out
    names = args.names
    date = args.date
    days = args.days
    logging.info(f"Args = {args}")

    if days != 0:
        process_batch(config_file, save_dir, days)
    else:
        process_v2(config_file, save_dir, names, date)
