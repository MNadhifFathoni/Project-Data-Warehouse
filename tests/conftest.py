import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


SAMPLE_FIRMS_CSV = """latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,brightness,brightness_t13,brightness_t31,bright_t14,bright_t15
-8.26581,140.63788,2025-12-02,404,N21,n,2.0NRT,3.69,D,0.39,0.36,,,,,
-4.01679,136.13356,2025-12-02,404,N21,n,2.0NRT,7.78,D,0.56,0.43,,,,,
-3.30858,135.55623,2025-12-02,404,N21,n,2.0NRT,4.32,D,0.4,0.44,,,,,
"""

SAMPLE_EQ_GEOJSON = {
    "type": "FeatureCollection",
    "metadata": {},
    "features": [
        {
            "type": "Feature",
            "id": "us7000rr5p",
            "properties": {
                "mag": 4.5,
                "magType": "mb",
                "place": "173 km NNE of Tobelo, Indonesia",
                "time": 1767134169826,
                "updated": 1767134169826,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000rr5p",
                "felt": None,
                "cdi": None,
                "mmi": None,
                "alert": None,
                "status": "reviewed",
                "tsunami": 0,
                "sig": 312,
                "net": "us",
                "code": "7000rr5p",
                "nst": 29,
                "dmin": 3.772,
                "rms": 0.62,
                "gap": 95,
                "type": "earthquake",
                "title": "M 4.5 - 173 km NNE of Tobelo, Indonesia",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [128.8654, 3.0448, 10.0],
            },
        },
        {
            "type": "Feature",
            "id": "us7000rlks",
            "properties": {
                "mag": 4.5,
                "magType": "mb",
                "place": "72 km NNE of Gorontalo, Indonesia",
                "time": 1767128106344,
                "updated": 1767128106344,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000rlks",
                "felt": None,
                "cdi": None,
                "mmi": None,
                "alert": None,
                "status": "reviewed",
                "tsunami": 0,
                "sig": 312,
                "net": "us",
                "code": "7000rlks",
                "nst": 57,
                "dmin": 4.163,
                "rms": 0.72,
                "gap": 83,
                "type": "earthquake",
                "title": "M 4.5 - 72 km NNE of Gorontalo, Indonesia",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [123.344, 1.1328, 10.0],
            },
        },
    ],
}
