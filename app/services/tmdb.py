import requests
from difflib import SequenceMatcher
from typing import Optional
from app.models import TmdbMatch, MediaType

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key, "language": "en-US"}

    def _calculate_confidence(self, parsed_title: str, tmdb_title: str, parsed_year: Optional[int], tmdb_year: Optional[int]) -> float:
        """Calculates a confidence score from 0 to 100% based on title and year."""
        if not parsed_title or not tmdb_title:
            return 0.0
        
        # Title similarity (e.g., "The Last Of Us" vs "The Last of Us" -> ~100%)
        title_similarity = SequenceMatcher(None, parsed_title.lower(), tmdb_title.lower()).ratio()
        score = title_similarity * 80.0
        
        # Year accounts for 20% of the score
        if parsed_year and tmdb_year:
            if parsed_year == tmdb_year:
                score += 20.0
            elif abs(parsed_year - tmdb_year) == 1: # One-year tolerance (difference between theatrical/release dates)
                score += 10.0
        elif not parsed_year:
            score = title_similarity * 100.0 # If no year was found in the filename, weigh the title at 100%
            
        return round(score, 2)

    def search_movie(self, title: str, year: Optional[int] = None, validation_threshold: float = 95.0) -> Optional[TmdbMatch]:
        params = {"query": title}
        if year:
            params["year"] = year
            
        response = self.session.get(f"{self.BASE_URL}/search/movie", params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return None
            
        best_result = results[0]
        movie_id = best_result["id"]
        tmdb_year = int(best_result["release_date"][:4]) if best_result.get("release_date") else None
        
        confidence = self._calculate_confidence(title, best_result["title"], year, tmdb_year)
        
        # Retrieve IMDb link if the confidence is below the threshold
        imdb_url = None
        if confidence < validation_threshold:
            details_resp = self.session.get(f"{self.BASE_URL}/movie/{movie_id}")
            if details_resp.status_code == 200:
                imdb_id = details_resp.json().get("imdb_id")
                if imdb_id:
                    imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        
        return TmdbMatch(
            tmdb_id=movie_id,
            title=best_result["title"],
            year=tmdb_year,
            media_type=MediaType.MOVIE,
            confidence=confidence,
            poster_path=best_result.get("poster_path"),
            imdb_url=imdb_url
        )

    def search_tv_episode(self, title: str, season: int, episode: int, validation_threshold: float = 95.0) -> Optional[TmdbMatch]:
        response = self.session.get(f"{self.BASE_URL}/search/tv", params={"query": title})
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return None
            
        best_series = results[0]
        series_id = best_series["id"]
        series_title = best_series["name"]
        
        confidence = self._calculate_confidence(title, series_title, None, None)
        
        # Retrieve IMDb link for the series via the external_ids endpoint
        imdb_url = None
        if confidence < validation_threshold:
            ext_resp = self.session.get(f"{self.BASE_URL}/tv/{series_id}/external_ids")
            if ext_resp.status_code == 200:
                imdb_id = ext_resp.json().get("imdb_id")
                if imdb_id:
                    imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        
        ep_response = self.session.get(f"{self.BASE_URL}/tv/{series_id}/season/{season}/episode/{episode}")
        episode_title = ep_response.json().get("name") if ep_response.status_code == 200 else None
            
        return TmdbMatch(
            tmdb_id=series_id,
            title=series_title,
            media_type=MediaType.TV_EPISODE,
            season=season,
            episode=episode,
            episode_title=episode_title,
            confidence=confidence,
            poster_path=best_series.get("poster_path"),
            imdb_url=imdb_url
        )