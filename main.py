"""A script for announcing new YouTube Videos to Discord."""

import logging
import typing
import json
import time
import sys

from typing import Literal

import scrapetube
import requests


class Looper():
    """Looping class to continuously check for updates."""

    CONTENT_TYPES = Literal['videos', 'shorts', 'streams']

    def __init__(
            self,
            announcements: dict[CONTENT_TYPES, dict[str, str]],
            channel_username: str,
            token: str) -> None:
        self.channel_username = channel_username
        self.announcements = announcements
        self.video_ids = {}
        self.token = token

        logging.info("Initializing...")

        for content_type in typing.get_args(self.CONTENT_TYPES):
            logging.info("Getting '%s' Video IDs...", content_type)
            self.video_ids[content_type] = self.get_video_ids(content_type)
            count = f"{len(self.video_ids[content_type]):,}"
            logging.info("Got %s Video IDs for '%s'.", count, content_type)

        logging.info("Initialized.")

    def get_video_ids(
            self,
            content_type: CONTENT_TYPES,
            **kwargs) -> set[str]:
        """Get a set of all Video IDs for a given Content Type."""

        logging.debug("Getting '%s' Video IDs...", content_type)

        video_ids = set([video['videoId'] for video in scrapetube.get_channel(
            channel_username=self.channel_username,
            content_type=content_type,
            limit=kwargs.get("limit", None)
        )])

        logging.debug("Got'%s' Video IDs: %s", content_type, video_ids)

        return video_ids

    def run(self) -> None:
        """Main entry point."""

        logging.info("Starting...")

        while True:
            self.looper()

    def looper(self) -> None:
        """Looping method."""

        logging.debug("Sleeping...")

        time.sleep(1)

        logging.debug("Checking for updates...")

        for content_type in self.video_ids:
            self.try_check_video_ids(content_type)

    def try_check_video_ids(
            self,
            content_type: CONTENT_TYPES) -> None:
        """Try to check and announce any new Video IDs."""

        try:
            video_ids = self.get_video_ids(content_type, limit=28)
        except (requests.exceptions.ConnectionError,
                json.decoder.JSONDecodeError):
            logging.error("Failed to get Video IDs for '%s'.", content_type)
        else:
            self.check_new_video_ids(content_type, video_ids)

    def check_new_video_ids(
            self,
            content_type: CONTENT_TYPES,
            video_ids: set[str]) -> None:
        """Check and announce new Video IDs for the Content Type."""

        for video_id in video_ids:
            self.check_new_video_id(content_type, video_id)

    def check_new_video_id(
            self,
            content_type: CONTENT_TYPES,
            video_id: str) -> None:
        """Try to check and announce if the Video ID is new."""

        if video_id in self.video_ids[content_type]:
            return

        logging.info("Found new Video ID: '%s'.", video_id)

        try:
            result = self.send_announcment(content_type, video_id)
        except requests.exceptions.Timeout:
            logging.error("Announcement attempt timed out.")
            return

        if result:
            self.video_ids[content_type].add(video_id)

    def send_announcment(
            self,
            content_type: CONTENT_TYPES,
            video_id: str) -> bool:
        """Announce the new Video ID for the Content Type."""

        data = self.announcements[content_type]
        url = f"https://discordapp.com/api/channels/ \
            {data['channel_id']}/messages"

        content = f"{data['content']} \
            https://www.youtube.com/watch?v={video_id}"

        logging.info("Sending announcement: '%s'...", content)

        response = requests.post(
            url,
            {"content": f"@everyone {content}"},
            headers={"Authorization": f"Bot {self.token}"},
            timeout=60
        )

        result = response.status_code == 200

        if result:
            logging.info("Announcement sent.")
        else:
            logging.error("Post failed: '%s'.", response.content)

        return result


def main():
    """Main entry method when running the script directly."""

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    with open(sys.argv[1], encoding="utf-8") as file:
        config = json.load(file)

    Looper(**config).run()


if __name__ == '__main__':
    main()
