from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    MOVIE = "movie"
    TV_EPISODE = "tv_episode"
    UNKNOWN = "unknown"


class ParsedMedia(BaseModel):
    raw_filename: str
    title: str
    year: Optional[int] = None
    media_type: MediaType = MediaType.UNKNOWN
    season: Optional[int] = None
    episode: Optional[int] = None
    release_tags: List[str] = Field(default_factory=list)


class TmdbMatch(BaseModel):
    tmdb_id: int
    title: str
    year: Optional[int] = None
    media_type: MediaType
    genre: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    confidence: float = 0.0
    poster_path: Optional[str] = None
    imdb_url: Optional[str] = None


class MediaJobStatus(str, Enum):
    DISCOVERED = "discovered"
    PARSED = "parsed"
    IDENTIFIED = "identified"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaJob(BaseModel):
    job_id: str
    file_path: str
    parsed: Optional[ParsedMedia] = None
    match: Optional[TmdbMatch] = None
    status: MediaJobStatus = MediaJobStatus.DISCOVERED
    destination_path: Optional[str] = None
    error_message: Optional[str] = None


class ValidationAction(BaseModel):
    job_id: str
    action: str  # "accept", "reject", "override_imdb"
    imdb_url: Optional[str] = None