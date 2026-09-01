# Media Organizer

A lightweight, deterministic Python service designed to automatically organize movie and TV show libraries for Plex and Jellyfin. It runs within a single Docker container on a personal NAS, prioritizing reliability and human validation over blind automation.

## Core Principles

* **Non-Destructive**: Never deletes, overwrites, or moves files blindly. Ambiguous matches require manual validation.
* **Strict Separation**: Analysis and identification are strictly decoupled from file moving and renaming.
* **Dry Run Support**: Simulates all operations without altering the file system.

## Processing Pipeline

```text
INPUT → PARSE → IDENTIFY → VALIDATE → PLAN → APPLY → VERIFY

```

1. **Input**: Monitors `/downloads` or scans existing `/movies` and `/series` libraries.
2. **Parse**: Extracts clean titles, years, seasons, episodes, and technical tags.
3. **Identify**: Queries The Movie Database (TMDB) and supports manual overrides via IMDb URLs (`ttXXXXXXX`).
4. **Validate**: Automatically applies changes for high confidence ($\ge 95\%$), holds for review ($70\% - 94.99\%$), or rejects ($< 70\%$).
5. **Plan & Apply**: Executes safe copy/move operations, checks for duplicates, and fetches missing subtitles (English prioritized over French).

## Configuration

Settings are managed via `config/config.yaml`. You can configure paths, your TMDB API key, confidence thresholds, operation modes (`move` or `copy`), and subtitle language preferences.

## Deployment

The service is containerized via Docker and orchestrated using Docker Compose. Ensure your local volume paths for downloads, libraries, config, and logs are correctly mapped in your Compose file before starting the container.