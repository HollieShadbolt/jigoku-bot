"""A script for announcing new YouTube Videos to Discord."""

import logging
import typing
import json
import time
import sys

import scrapetube
import requests


class Looper():
    """Looping class to continuously check for updates."""

    CONTENT_TYPES = typing.Literal['videos', 'shorts', 'streams']

    def __init__(
            self, announcements: dict[CONTENT_TYPES, dict[str, str]],
            channel_username: str, token: str,
            limit: typing.Optional[int] = None) -> None:
        self.channel_username = channel_username
        self.announcements = announcements
        self.video_ids = set()
        self.token = token

        logging.info("Getting initial Video IDs...")

        for content_type in announcements.keys():
            self.video_ids.update(self.get_ids(content_type, limit=limit))

        logging.info("Got %s Video IDs.", f"{len(self.video_ids):,}")

    def get_ids(self, content_type: CONTENT_TYPES, **kwargs) -> set[str]:
        """Get all Video IDs for a given Content Type."""

        return {video['videoId'] for video in scrapetube.get_channel(
            channel_username=self.channel_username,
            content_type=content_type,
            limit=kwargs.get("limit", None)
        )}

    def run(self) -> None:
        """Main entry point."""

        while True:
            self.looper()

    def looper(self) -> None:
        """Looping method."""

        time.sleep(2)

        for content_type in self.announcements:
            self.try_check_video_ids(content_type)

    def try_check_video_ids(self, content_type: CONTENT_TYPES) -> None:
        """Try to check and announce any new Video IDs."""

        try:
            video_ids = self.get_ids(content_type, limit=10)
        except (requests.exceptions.ConnectionError,
                json.decoder.JSONDecodeError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError) as exception:
            logging.error(exception)
        else:
            self.check_new_video_ids(content_type, video_ids)

    def check_new_video_ids(
            self, content_type: CONTENT_TYPES, video_ids: set[str]) -> None:
        """Check and announce new Video IDs for the Content Type."""

        for video_id in video_ids:
            self.check_new_video_id(content_type, video_id)

    def check_new_video_id(
            self, content_type: CONTENT_TYPES, video_id: str) -> None:
        """Check and try to announce if the Video ID is new."""

        if video_id in self.video_ids:
            return

        logging.info("Found new Video ID: '%s'.", video_id)

        try:
            self.send_announcment(content_type, video_id)
        except requests.exceptions.Timeout:
            logging.error("Announcement attempt timed out.")

    def send_announcment(
            self, content_type: CONTENT_TYPES, video_id: str) -> None:
        """Announce the new Video ID for the Content Type."""

        data = self.announcements[content_type]
        url = f"https://discordapp.com/api/channels/ \
            {data['channel_id']}/messages"

        content = f"{data['content']} \
            \nhttps://www.youtube.com/watch?v={video_id}"

        logging.info("Sending announcement: '%s'...", content)

        response = requests.post(
            url,
            {"content": f"{content}"},
            headers={"Authorization": f"Bot {self.token}"},
            timeout=60
        )

        if response.status_code == 200:
            logging.info("Announcement sent.")
            self.video_ids.add(video_id)
        else:
            logging.error("Post failed: '%s'.", response)


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
