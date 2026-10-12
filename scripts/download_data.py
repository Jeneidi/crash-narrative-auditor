from pathlib import Path
from urllib.request import Request, urlopen


URL = "https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Incident_Reports_ADS.csv"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/raw/SGO-2021-01_Incident_Reports_ADS.csv"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    request = Request(URL, headers={"User-Agent": "Crash-Narrative-Auditor/1.0"})
    with urlopen(request, timeout=60) as response:
        TARGET.write_bytes(response.read())
    print(f"downloaded_bytes={TARGET.stat().st_size}")


if __name__ == "__main__":
    main()
