import discord
from atproto import Client, models
import os
import typing as t
import re
import io
import math
from PIL import Image


class BlueskyPoster:
    IMAGE_MAX_SIZE = 1000000  # 1 MB
    IMAGE_MAX_RESOLUTION = 2000  # px

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

    def _get_url_facets(self, text: str):
        # Determine locations of URLs in the post's text
        url_positions = self._extract_url_byte_positions(text)
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

        return facets if facets else None

    def _url_from_response(self, response):
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

    async def post(self, message: discord.Message) -> str:
        if len(message.attachments) == 0:
            response = self.client.send_post(
                message.clean_content,
                facets=self._get_url_facets(message.clean_content),
            )
            return self._url_from_response(response)

        media_type = message.attachments[0].content_type
        if not media_type:
            # Idk why this would happen
            # Just post the text
            response = self.client.send_post(
                message.clean_content,
                facets=self._get_url_facets(message.clean_content),
            )
            return self._url_from_response(response)

        if media_type.startswith("video/"):
            # Post the video and ignore possible other attachments
            vid_data = await message.attachments[0].read()
            response = self.client.send_video(
                message.clean_content,
                vid_data,
                facets=self._get_url_facets(message.clean_content),
                video_aspect_ratio=models.AppBskyEmbedDefs.AspectRatio(
                    height=message.attachments[0].height,  # type: ignore
                    width=message.attachments[0].width,  # type: ignore
                ),
            )
            return self._url_from_response(response)

        if media_type.startswith("image/"):
            # Send up to 4 images
            images = []
            image_aspect_ratios = []
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith(
                    "image/"
                ):
                    img = await attachment.read()
                    if attachment.size > self.IMAGE_MAX_SIZE:
                        img = self.compressImage(img)
                    images.append(img)
                    image_aspect_ratios.append(
                        models.AppBskyEmbedDefs.AspectRatio(
                            height=attachment.height,  # type: ignore
                            width=attachment.width,  # type: ignore
                        )
                    )
                if len(images) == 4:
                    break

            response = self.client.send_images(
                message.clean_content,
                images,
                facets=self._get_url_facets(message.clean_content),
                image_aspect_ratios=image_aspect_ratios,
            )
            return self._url_from_response(response)

        # Some other kind of attachment, like a PDF
        # Ignore it and just post the message text
        # Another option would be to post the link to the file
        # But that would change the post length and could invalidate it,
        # so let's not for now.
        response = self.client.send_post(
            message.clean_content,
            facets=self._get_url_facets(message.clean_content),
        )
        return self._url_from_response(response)

    def compressImage(self, img_bytes: bytes) -> bytes:
        """Save the image as JPEG with the given name at best quality that makes less than "target" bytes"""

        # Adapted from https://stackoverflow.com/a/52281257/7361270

        im = Image.open(io.BytesIO(img_bytes))

        # First resize image to see if that's good enough
        buffer = io.BytesIO()
        im.thumbnail((self.IMAGE_MAX_RESOLUTION, self.IMAGE_MAX_RESOLUTION))
        im.save(buffer, format="JPEG", quality=96)
        if buffer.getbuffer().nbytes <= self.IMAGE_MAX_SIZE:
            return buffer.getvalue()

        # Min and Max quality
        Qmin, Qmax = 25, 96
        # Highest acceptable quality found
        Qacc = -1

        while Qmin <= Qmax:
            m = math.floor((Qmin + Qmax) / 2)

            # Encode into memory and get size
            buffer = io.BytesIO()
            im.save(buffer, format="JPEG", quality=m)
            s = buffer.getbuffer().nbytes

            if s <= self.IMAGE_MAX_SIZE:
                Qacc = m
                Qmin = m + 1
            elif s > self.IMAGE_MAX_SIZE:
                Qmax = m - 1

        if Qacc > -1:
            buffer = io.BytesIO()
            im.save(buffer, format="JPEG", quality=Qacc)
            return buffer.getvalue()

        raise Exception("unable to compress image")
