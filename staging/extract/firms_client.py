import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class FIRMSClient:
    def __init__(self, map_key: str, max_retries: int = 3, backoff: float = 2.0):
        self.map_key = map_key
        self.max_retries = max_retries
        self.backoff = backoff

    def fetch_area(
        self,
        source: str,
        bbox: str,
        day_range: int,
        ref_date: Optional[str] = None,
    ) -> str:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
            f"/{self.map_key}/{source}/{bbox}/{day_range}"
        )
        if ref_date:
            url += f"/{ref_date}"

        logger.info("GET FIRMS %s  day_range=%s  bbox=%s", source, day_range, bbox)

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, timeout=120)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code == 429:
                    wait = self.backoff * (2 ** (attempt - 1))
                    logger.warning("Rate limited — waiting %.0fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code in (400, 404):
                    logger.info("No data for %s (HTTP %s)", ref_date or "latest", resp.status_code)
                    return ""
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.error("Attempt %d/%d failed: %s", attempt, self.max_retries, e)
                if attempt == self.max_retries:
                    raise
                time.sleep(self.backoff * (2 ** (attempt - 1)))
        return ""
