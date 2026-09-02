import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("MediaOrganizer.Watcher")

# Allowed extensions to process
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}

# Temporary extensions to explicitly ignore
IGNORED_EXTENSIONS = {".crdownload", ".part", ".tmp", ".qb", ".nbr", ".part.met"}

class MediaFileHandler(FileSystemEventHandler):
    def __init__(self, workflow, organizer, config):
        self.workflow = workflow
        self.organizer = organizer
        self.config = config

    def _should_process(self, filepath: Path) -> bool:
        if filepath.is_dir():
            return False
        
        # Ignore temporary files
        if filepath.suffix.lower() in IGNORED_EXTENSIONS:
            return False
            
        # Check for double extensions (e.g., file.mkv.crdownload)
        if any(filepath.name.lower().endswith(ext) for ext in IGNORED_EXTENSIONS):
            return False

        return filepath.suffix.lower() in VIDEO_EXTENSIONS

    def _process_file(self, file_path_str: str):
        filepath = Path(file_path_str)
        if not self._should_process(filepath):
            return

        logger.info(f"New file detected: {filepath.name}")
        
        # File accessibility check (safety lock)
        if not self._is_file_ready(filepath):
            logger.warning(f"File {filepath.name} is still locked by another process. Skipping.")
            return

        # Execute workflow
        job_id = f"job_{abs(hash(str(filepath) + str(time.time())))}"
        job = self.workflow.process_file(str(filepath), job_id)
        
        if job.status == "approved" and job.match:
            destination = self.organizer.plan_destination(job.match, filepath.name)
            
            # Prevent endless loop in in_place mode if the file is already correctly placed
            if destination.resolve() == filepath.resolve():
                logger.info(f"File {filepath.name} is already in the correct path. No action needed.")
                return

            logger.info(f"Executing operation: {filepath} -> {destination}")
            try:
                self.organizer.apply_operation(filepath, destination)
            except Exception as e:
                logger.error(f"Failed to move file {filepath.name}: {e}")

    def _is_file_ready(self, filepath: Path, retries: int = 3, delay: float = 2.0) -> bool:
        """Verifies if the file is completely written and no longer locked."""
        for _ in range(retries):
            try:
                # Attempt exclusive access mode check
                with open(filepath, "a+"):
                    return True
            except IOError:
                time.sleep(delay)
        return False

    def on_created(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

    def on_moved(self, event):
        # Triggered when Chrome renames .crdownload to .mkv
        if not event.is_directory:
            self._process_file(event.dest_path)


class MediaWatcher:
    def __init__(self, paths_to_watch: list, workflow, organizer, config):
        self.paths_to_watch = paths_to_watch
        self.workflow = workflow
        self.organizer = organizer
        self.config = config
        self.observer = Observer()

    def start(self):
        event_handler = MediaFileHandler(self.workflow, self.organizer, self.config)
        for path_str in self.paths_to_watch:
            path = Path(path_str)
            if path.exists():
                logger.info(f"Starting watchdog observer on: {path}")
                self.observer.schedule(event_handler, str(path), recursive=True)
            else:
                logger.warning(f"Path does not exist, watchdog skipped for: {path}")
        
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()