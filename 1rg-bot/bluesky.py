import discord
from atproto import Client, models
import os
import typing as t
import re


class BlueskyPoster:
    def __init__(self) -> None:
        self.client = Client()
        self.client.login(
            os.environ["BLUESKY_USERNAME"], os.environ["BLUESKY_APP_PASSWORD"]
        )

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

    def post(self, message: discord.Message) -> str:
        # Determine locations of URLs in the post's text
        url_positions = self._extract_url_byte_positions(message.clean_content)
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

        response = self.client.send_post(
            message.clean_content, facets=facets if facets else None
        )

        # Construct the post URL
        # The response contains the post's AT URI, we need to convert it to a web URL
        post_uri = response.uri
        # Extract the DID and record key from the AT URI
        # Format: at://did:plc:xyz/app.bsky.feed.post/recordkey
        parts = post_uri.split("/")
        did = parts[2]
        record_key = parts[-1]

        # Convert to web URL format
        return f"https://bsky.app/profile/{did}/post/{record_key}"
