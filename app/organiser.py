import os, shutil
from pathlib import Path
from typing import Tuple
from app.models import TmdbMatch, MediaType


class MediaOrganizer:

    def __init__(self, movies_path: str, series_path: str, operation_mode: str = "move", dry_run: bool = True):
        self.movies_path = Path(movies_path)
        self.series_path = Path(series_path)
        self.operation_mode = operation_mode
        self.dry_run = dry_run

    def plan_destination(self, match: TmdbMatch, original_filename: str) -> Path:
        ext = Path(original_filename).suffix
        
        if match.media_type == MediaType.MOVIE:
            genre = match.genre if match.genre else "Uncategorized"
            genre = "".join(c for c in genre if c.isalnum() or c in " .-_").strip()
            safe_title = "".join(c for c in match.title if c.isalnum() or c in " .-_()").strip()
            year_str = f" ({match.year})" if match.year else ""
            filename = f"{safe_title}{year_str}{ext}"
            return self.movies_path / genre / filename

        elif match.media_type == MediaType.TV_EPISODE:
            safe_series = "".join(c for c in match.title if c.isalnum() or c in " .-_").strip()
            season_str = f"Season {match.season:02d}" if match.season is not None else "Season 01"
            
            ep_num = f"S{match.season:02d}E{match.episode:02d}" if match.season is not None and match.episode is not None else "S01E01"
            ep_title = f" - {match.episode_title}" if match.episode_title else ""
            filename = f"{ep_num}{ep_title}{ext}"
            
            return self.series_path / safe_series / season_str / filename

        raise ValueError(f"Unknown media type for destination planning: {match.media_type}")

    def check_duplicate(self, destination: Path) -> Tuple[bool, str]:
        if not destination.exists():
            return False, "Destination does not exist. Safe to proceed."
        
        return True, "Duplicate detected at destination. Manual validation required."

    def apply_operation(self, source: Path, destination: Path) -> bool:
        if self.dry_run:
            print(f"[DRY RUN] Would {self.operation_mode} {source} -> {destination}")
            return True

        destination.parent.mkdir(parents=True, exist_ok=True)
        
        is_dup, reason = self.check_duplicate(destination)
        if is_dup:
            raise FileExistsError(f"Operation aborted: {reason}")

        if self.operation_mode == "copy":
            shutil.copy2(source, destination)
        else:
            shutil.move(str(source), str(destination))
        
        return destination.exists()