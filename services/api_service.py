import json
import os
from pathlib import Path
from urllib import error, request


COUNTRY_DATA_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "country_calling_codes.json"
)


def _load_country_records():
    try:
        with COUNTRY_DATA_PATH.open(encoding="utf-8-sig") as country_file:
            payload = json.load(country_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Country calling-code data could not be loaded: {COUNTRY_DATA_PATH}"
        ) from exc

    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Country calling-code data has an invalid records list.")

    valid_records = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("iso2")
        and record.get("name")
        and str(record.get("dial_code", "")).isdigit()
    ]
    if not valid_records:
        raise RuntimeError("Country calling-code data contains no valid records.")
    return valid_records


COUNTRY_RECORDS = _load_country_records()


class ApiService:
    DEFAULT_PUBLIC_API_URL = (
        "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/getnum"
    )
    DEFAULT_PUBLIC_API_HEADER = "mauthapi"
    DEFAULT_PUBLIC_API_RANGE = "26134"
    DEFAULT_LIVEACCESS_URL = (
        "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/liveaccess"
    )
    DEFAULT_CONSOLE_URL = (
        "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/console"
    )

    COUNTRY_CODES = {
        "canada": "ca",
        "united states": "us",
        "usa": "us",
        "united kingdom": "gb",
        "uk": "gb",
        "great britain": "gb",
        "australia": "au",
        "germany": "de",
        "france": "fr",
        "italy": "it",
        "spain": "es",
        "netherlands": "nl",
        "sweden": "se",
        "norway": "no",
        "denmark": "dk",
        "finland": "fi",
        "poland": "pl",
        "india": "in",
        "bangladesh": "bd",
        "singapore": "sg",
        "japan": "jp",
        "south korea": "kr",
        "brazil": "br",
        "mexico": "mx",
    }

    def __init__(self, config):
        self.config = config

    def get_public_api_config(self):
        base_url = self.config.get(
            "public_api_url",
            self.DEFAULT_PUBLIC_API_URL
        ).strip().rstrip("/")
        if not base_url.lower().endswith("/getnum"):
            base_url = f"{base_url}/getnum"
        return {
            "base_url": base_url,
            "header": self.config.get(
                "public_api_header",
                self.DEFAULT_PUBLIC_API_HEADER
            ).strip(),
            "token": os.environ.get(
                "FB_WORKER_NEZ_KEY",
                self.config.get(
                    "public_api_header_key",
                    self.config.get("nez_key", "")
                )
            ).strip(),
            "range_id": self.config.get(
                "nez_range",
                self.DEFAULT_PUBLIC_API_RANGE
            ).strip(),
            "liveaccess_url": self.config.get(
                "public_api_liveaccess_url",
                self.DEFAULT_LIVEACCESS_URL
            ).strip().rstrip("/"),
            "console_url": self.config.get(
                "public_api_console_url",
                self.DEFAULT_CONSOLE_URL
            ).strip().rstrip("/"),
        }

    def _get_json(self, url, description):
        api_config = self.get_public_api_config()
        missing = [name for name in ("header", "token") if not api_config[name]]
        if missing:
            raise ValueError(
                f"{description} API settings missing: " + ", ".join(missing)
            )

        http_request = request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                api_config["header"]: api_config["token"],
            },
            method="GET",
        )
        try:
            with request.urlopen(http_request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"{description} API request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{description} API returned invalid JSON."
            ) from exc

        if body.get("meta", {}).get("code") != 200:
            raise RuntimeError(
                f"{description} API rejected request: "
                f"{body.get('message') or body.get('meta', {}).get('status')}"
            )
        return body

    def get_live_ranges(self):
        api_config = self.get_public_api_config()
        if not api_config["liveaccess_url"]:
            raise ValueError("Live access API URL is required.")
        body = self._get_json(api_config["liveaccess_url"], "Live access")
        return (body.get("data") or {}).get("ranges") or []

    def get_console_stats(self):
        api_config = self.get_public_api_config()
        if not api_config["console_url"]:
            raise ValueError("Console API URL is required.")
        body = self._get_json(api_config["console_url"], "Console")
        return (body.get("data") or {})

    @staticmethod
    def normalize_range(value):
        normalized = str(value).strip().upper()
        if normalized.endswith("XXX"):
            normalized = normalized[:-3]
        if not normalized.isdigit():
            return ""
        return normalized

    def resolve_range_country(self, range_id):
        return self.resolve_range_details(range_id)["country"]

    def resolve_range_details(self, range_id):
        normalized_range = self.normalize_range(range_id)
        if not normalized_range:
            raise ValueError("Range must contain digits, optionally ending in XXX.")
        custom_map = self.config.get("range_country_map", {})
        custom_code = custom_map.get(normalized_range.lower())
        if custom_code:
            return {
                "country": self.country_name(custom_code),
                "country_code": custom_code.lower(),
                "range": normalized_range,
            }

        api_config = self.get_public_api_config()
        if api_config["liveaccess_url"] and api_config["header"] and api_config["token"]:
            live_ranges = self.get_live_ranges()
            for item in live_ranges:
                live_range = self.normalize_range(item.get("range", ""))
                if live_range == normalized_range:
                    country = item.get("country")
                    code = item.get("country_code")
                    if not country or not code:
                        raise RuntimeError(
                            f"Live access record for range {normalized_range} "
                            "is missing country or country_code."
                        )
                    return {
                        "country": country,
                        "country_code": code.lower(),
                        "range": normalized_range,
                    }

        static_details = self._resolve_calling_code_range(normalized_range)
        if static_details:
            return static_details
        raise RuntimeError(
            f"No country found for range {normalized_range}."
        )

    @classmethod
    def _resolve_calling_code_range(cls, range_id):
        records = sorted(
            COUNTRY_RECORDS,
            key=lambda record: len(str(record["dial_code"])),
            reverse=True,
        )
        for record in records:
            dial_code = str(record["dial_code"])
            if range_id.startswith(dial_code):
                return {
                    "country": record["name"],
                    "country_code": record["iso2"].lower(),
                    "range": range_id,
                    "source": "offline_calling_code_map",
                }
        return None

    def search_country(self):
        api_config = self.get_public_api_config()
        missing = [
            name for name in ("base_url", "header", "token", "range_id")
            if not api_config[name]
        ]
        if missing:
            raise ValueError(
                "Public API settings missing: " + ", ".join(missing)
            )

        url = api_config["base_url"]
        payload = json.dumps({"rid": api_config["range_id"]}).encode("utf-8")
        http_request = request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                api_config["header"]: api_config["token"],
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Public API request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Public API returned invalid JSON.") from exc

        meta = body.get("meta", {})
        if meta.get("code") != 200:
            raise RuntimeError(
                f"Public API rejected range: "
                f"{body.get('message') or meta.get('status') or 'unknown error'}"
            )
        country = (body.get("data") or {}).get("country")
        if not country:
            raise RuntimeError("Public API response did not include a country.")
        return country

    def allocate_number(self, range_id=None):
        api_config = self.get_public_api_config()
        selected_range = self.normalize_range(
            range_id if range_id is not None else api_config["range_id"]
        )
        missing = [
            name for name in ("base_url", "header", "token")
            if not api_config[name]
        ]
        if not selected_range:
            missing.append("range_id")
        if missing:
            raise ValueError(
                "Public API settings missing: " + ", ".join(missing)
            )

        payload = json.dumps({"rid": selected_range}).encode("utf-8")
        http_request = request.Request(
            api_config["base_url"],
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                api_config["header"]: api_config["token"],
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Number allocation API request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Number allocation API returned invalid JSON.") from exc

        meta = body.get("meta", {})
        if meta.get("code") != 200:
            raise RuntimeError(
                "Number allocation rejected: "
                f"{body.get('message') or meta.get('status') or 'unknown error'}"
            )
        number = (body.get("data") or {}).get("no_plus_number")
        if not number:
            raise RuntimeError(
                "Number allocation response did not include data.no_plus_number."
            )
        return body["data"]

    @classmethod
    def country_code(cls, country):
        normalized = " ".join(country.strip().lower().split())
        for record in COUNTRY_RECORDS:
            if " ".join(record["name"].strip().lower().split()) == normalized:
                return record["iso2"].lower()
        try:
            return cls.COUNTRY_CODES[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported proxy country for dynamic region: {country}"
            ) from exc

    @classmethod
    def country_name(cls, code):
        normalized_code = code.strip().lower()
        for record in COUNTRY_RECORDS:
            if record["iso2"].lower() == normalized_code:
                return record["name"]
        for country, country_code in cls.COUNTRY_CODES.items():
            if country_code == normalized_code:
                return country.title()
        raise ValueError(
            f"Unsupported country code for proxy region: {code}"
        )

    def get_otp_config(self):
        return {
            "timeout": self.config.get("otp_timeout", "60"),
            "target_bot": self.config.get("target_bot", "@SureSmsBot"),
            "nez_key": self.config.get("nez_key", "")
        }

    def get_success_otps(self):
        api_config = self.get_public_api_config()
        url = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/success-otp"
        http_request = request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                api_config["header"]: api_config["token"],
            },
            method="GET",
        )
        try:
            with request.urlopen(http_request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        if body.get("meta", {}).get("code") != 200:
            return []
        return (body.get("data") or {}).get("otps") or []