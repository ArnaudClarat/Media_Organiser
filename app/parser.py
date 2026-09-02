from pathlib import Path
from guessit import guessit
from app.models import ParsedMedia, MediaType

class MediaParser:
    """
    Analyzes raw filenames to extract relevant information without altering the original title
    (secure handling of accents, numbers, and punctuation).
    """

    @staticmethod
    def parse(filepath: str) -> ParsedMedia:
        # Pass only the filename to guessit, not the full path
        filename = Path(filepath).name
        
        # Guessit magic analysis
        guess = guessit(filename)
        
        # Determine media type
        g_type = guess.get("type")
        
        if g_type == "movie":
            media_type = MediaType.MOVIE
        elif g_type == "episode":
            media_type = MediaType.TV_EPISODE
        else:
            # Additional safety: if guessit is unsure but there is an S01E01 tag
            if guess.get("season") is not None or guess.get("episode") is not None:
                media_type = MediaType.TV_EPISODE
            elif guess.get("year") is not None:
                media_type = MediaType.MOVIE
            else:
                media_type = MediaType.UNKNOWN

        # Extract "noise" (technical release information)
        # Very useful for refining subtitle searches later
        tag_keys = [
            "language", "screen_size", "format", "video_codec", 
            "audio_codec", "audio_channels", "release_group", "other"
        ]
        
        release_tags = []
        for key in tag_keys:
            val = guess.get(key)
            if val:
                # Guessit can return lists (e.g., ['French', 'English'] for MULTI)
                if isinstance(val, list):
                    release_tags.extend([str(v) for v in val])
                else:
                    release_tags.append(str(val))

        # Return our strict model
        return ParsedMedia(
            raw_filename=filepath,
            # If guessit fails completely (very rare), keep the raw name to prevent a crash
            title=str(guess.get("title", path.stem)),
            year=guess.get("year"),
            media_type=media_type,
            season=guess.get("season"),
            episode=guess.get("episode"),
            # Deduplicate tags just in case
            release_tags=list(set(release_tags))
        )