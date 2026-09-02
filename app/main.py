import os
import time
import yaml
import logging
from pathlib import Path

from app.services.tmdb import TMDBClient
from app.workflow import MediaWorkflow
from app.organiser import MediaOrganizer
from app.watcher import MediaWatcher, VIDEO_EXTENSIONS, IGNORED_EXTENSIONS

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MediaOrganizer")


def load_config() -> dict:
    config_path = Path("config/config.yaml")
    if config_path.exists():
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    logger.warning("config.yaml not found. Falling back to environment variables.")
    return {
        "downloads_path": os.getenv("DOWNLOADS_PATH", "/downloads"),
        "movies_path": os.getenv("MOVIES_PATH", "/movies"),
        "series_path": os.getenv("SERIES_PATH", "/series"),
        "tmdb_api_key": os.getenv("TMDB_API_KEY", ""),
        "confidence": {
            "automatic": float(os.getenv("CONFIDENCE_AUTOMATIC", 95.0)),
            "validation": float(os.getenv("CONFIDENCE_VALIDATION", 70.0))
        },
        "operation_mode": os.getenv("OPERATION_MODE", "move"),  # "move" or "in_place"
        "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
    }


def run_full_scan(paths: list, workflow: MediaWorkflow, organizer: MediaOrganizer):
    """Executes a full initial scan of the specified paths (used for in_place mode)."""
    logger.info("Starting initial full library scan...")
    processed_count = 0

    for path_str in paths:
        root_path = Path(path_str)
        if not root_path.exists():
            continue

        for file_path in root_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
                if any(file_path.name.lower().endswith(ext) for ext in IGNORED_EXTENSIONS):
                    continue

                job_id = f"job_scan_{abs(hash(str(file_path)))}"
                job = workflow.process_file(str(file_path), job_id)

                if job.status == "approved" and job.match:
                    destination = organizer.plan_destination(job.match, file_path.name)
                    
                    if destination.resolve() != file_path.resolve():
                        logger.info(f"[SCAN] Relocating misplaced file: {file_path} -> {destination}")
                        try:
                            organizer.apply_operation(file_path, destination)
                            processed_count += 1
                        except Exception as e:
                            logger.error(f"[SCAN] Failed to move {file_path.name}: {e}")

    logger.info(f"Initial scan completed. {processed_count} files reorganized.")


def main():
    config = load_config()

    if not config.get("tmdb_api_key"):
        logger.error("TMDB API key is missing! Please configure it in config.yaml.")
        return

    workflow = MediaWorkflow(
        tmdb_api_key=config["tmdb_api_key"],
        validation_threshold=config["confidence"]["automatic"],
        min_confidence=config["confidence"]["validation"]
    )

    organizer = MediaOrganizer(
        movies_path=config["movies_path"],
        series_path=config["series_path"],
        operation_mode=config["operation_mode"],
        dry_run=config["dry_run"]
    )

    op_mode = config.get("operation_mode", "move")

    # Determine paths to watch based on mode
    if op_mode == "in_place":
        paths_to_watch = [config["movies_path"], config["series_path"]]
        # Step 1: Run full scan for existing files
        run_full_scan(paths_to_watch, workflow, organizer)
    else:
        paths_to_watch = [config["downloads_path"]]

    # Step 2: Start Watchdog for continuous monitoring
    watcher = MediaWatcher(paths_to_watch, workflow, organizer, config)
    watcher.start()

    logger.info(f"Service running in '{op_mode}' mode. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        watcher.stop()


if __name__ == "__main__":
    main()