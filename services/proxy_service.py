import re


class ProxyService:
    def __init__(self, config):
        self.config = config

    def get_proxy_string(self):
        if not self.config.get("enable_proxy", True):
            return "Proxy Disabled"
        
        ptype = self.config.get("proxy_type", "other")
        server = self.config.get("proxy_server", "")
        port = self.config.get("proxy_port", "")
        return f"{ptype}://{server}:{port}"

    def get_credentials(self, country_code=None):
        username = self.config.get("proxy_user", "").strip()
        if country_code:
            username = re.sub(
                r"(__cr\.)[a-z]{2}\b",
                rf"\g<1>{country_code.lower()}",
                username,
                flags=re.IGNORECASE,
            )
        return {
            "type": self.config.get("proxy_type", "other"),
            "server": self.config.get("proxy_server", "").strip(),
            "port": str(self.config.get("proxy_port", "")).strip(),
            "user": username,
            "password": self.config.get("proxy_pass", ""),
        }

    def validate_credentials(self, country_code=None):
        credentials = self.get_credentials(country_code)
        missing = [
            field for field in ("server", "port", "user", "password")
            if not credentials[field]
        ]
        if missing:
            raise ValueError(
                "Super Proxy credentials missing: " + ", ".join(missing)
            )
        return credentials

    def update_region(self, country_code):
        username = self.config.get("proxy_user", "").strip()
        if not username:
            return ""
        updated = re.sub(
            r"(__cr\.)[a-z]{2}\b",
            rf"\g<1>{country_code.lower()}",
            username,
            flags=re.IGNORECASE,
        )
        self.config["proxy_user"] = updated
        return updated