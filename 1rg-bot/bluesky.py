import discord
from atproto import Client, models
import os
import typing as t
import re


class BlueskyPoster:
    def __init__(self) -> None:
        self.client = Client()
        self.client.login("overheard.1rg.space", os.environ["BLUESKY_APP_PASSWORD"])

    def _extract_url_byte_positions(
        self, text: str, *, encoding: str = "UTF-8"
    ) -> t.List[t.Tuple[str, int, int]]:
        """This function will detect any links beginning with http or https."""
        encoded_text = text.encode(encoding)

        # Adjusted URL matching pattern
        pattern = rb"https?://[^ \n\r\t]*"

        matches = re.finditer(pattern, encoded_text)
        url_byte_positions = []

        for match in matches:
            url_bytes = match.group(0)
            url = url_bytes.decode(encoding)
            url_byte_positions.append((url, match.start(), match.end()))

        return url_byte_positions

    def post(self, message: discord.Message):
        # Determine locations of URLs in the post's text
        url_positions = self._extract_url_byte_positions(message.content)
        facets = []

        for link_data in url_positions:
            uri, byte_start, byte_end = link_data
            facets.append(
                models.AppBskyRichtextFacet.Main(
                    features=[models.AppBskyRichtextFacet.Link(uri=uri)],
                    index=models.AppBskyRichtextFacet.ByteSlice(
                        byte_start=byte_start, byte_end=byte_end
                    ),
                )
            )

        # Send the post
        self.client.send_post(message.content, facets=facets if facets else None)
