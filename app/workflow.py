from pathlib import Path
from typing import Optional
from app.models import MediaJob, MediaJobStatus, MediaType
from app.parser import MediaParser
from app.services.tmdb import TMDBClient

class MediaWorkflow:
    """
    Orchestrates the deterministic pipeline:
    INPUT -> PARSE -> IDENTIFY -> CALCULATE CONFIDENCE -> PLAN
    """

    def __init__(self, tmdb_api_key: str, validation_threshold: float = 95.0, min_confidence: float = 70.0):
        self.tmdb_client = TMDBClient(api_key=tmdb_api_key)
        self.validation_threshold = validation_threshold
        self.min_confidence = min_confidence

    def process_file(self, file_path: str, job_id: str) -> MediaJob:
        """Processes a single media file through parse and identification stages."""
        path = Path(file_path)
        
        # Step 1: Parse the filename
        parsed_media = MediaParser.parse(str(path))
        
        job = MediaJob(
            job_id=job_id,
            file_path=str(path),
            parsed=parsed_media,
            status=MediaJobStatus.PARSED
        )

        # Step 2: Identify via TMDB based on media type
        match = None
        if parsed_media.media_type == MediaType.MOVIE:
            match = self.tmdb_client.search_movie(
                title=parsed_media.title,
                year=parsed_media.year,
                validation_threshold=self.validation_threshold
            )
        elif parsed_media.media_type == MediaType.TV_EPISODE:
            if parsed_media.season is not None and parsed_media.episode is not None:
                match = self.tmdb_client.search_tv_episode(
                    title=parsed_media.title,
                    season=parsed_media.season,
                    episode=parsed_media.episode,
                    validation_threshold=self.validation_threshold
                )

        if not match:
            job.status = MediaJobStatus.PENDING_REVIEW
            job.error_message = "No TMDB match found."
            return job

        job.match = match
        job.status = MediaJobStatus.IDENTIFIED

        # Step 3: Apply confidence policy
        if match.confidence >= self.validation_threshold:
            job.status = MediaJobStatus.APPROVED
        elif match.confidence >= self.min_confidence:
            job.status = MediaJobStatus.PENDING_REVIEW
        else:
            job.status = MediaJobStatus.REJECTED
            job.error_message = f"Confidence too low ({match.confidence}%)."

        return job