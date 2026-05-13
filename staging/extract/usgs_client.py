import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class USGSClient:
    def __init__(self, max_retries: int = 3, backoff: float = 2.0):
        self.max_retries = max_retries
        self.backoff = backoff

    def fetch_events(
        self,
        starttime: str,
        endtime: str,
        minlatitude: float = -11.0,
        maxlatitude: float = 6.0,
        minlongitude: float = 95.0,
        maxlongitude: float = 141.0,
        minmagnitude: float = 0.0,
        limit: int = 20000,
        offset: int = 1,
    ) -> dict:
        params = {
            "format": "geojson",
            "starttime": starttime,
            "endtime": endtime,
            "minlatitude": minlatitude,
            "maxlatitude": maxlatitude,
            "minlongitude": minlongitude,
            "maxlongitude": maxlongitude,
            "minmagnitude": minmagnitude,
            "limit": min(limit, 20000),
            "offset": offset,
            "orderby": "time",
        }
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

        logger.info("GET USGS  %s – %s  mag>=%s", starttime, endtime, minmagnitude)

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=120)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429:
                    wait = self.backoff * (2 ** (attempt - 1))
                    logger.warning("Rate limited — waiting %.0fs", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.error("Attempt %d/%d failed: %s", attempt, self.max_retries, e)
                if attempt == self.max_retries:
                    raise
                time.sleep(self.backoff * (2 ** (attempt - 1)))
        return {}
