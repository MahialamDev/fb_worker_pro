class SystemService:
    def __init__(self, config):
        self.config = config

    def get_account_defaults(self):
        return {
            "password": self.config.get("password", ""),
            "package": self.config.get("fb_package", "com.facebook.lite"),
            "fail_limit": self.config.get("fail_limit", "4"),
            "language": self.config.get("language", "English (US)")
        }