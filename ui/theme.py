class Theme:
    DARK = {
        "bg_root": "#0f1115",
        "bg_top": "#14171d",
        "bg_sub": "#12151b",
        "bg_panel": "#14171d",
        "bg_card": "#1a1e26",
        "bg_input": "#1a1e26",
        "bg_console": "#0b0d10",
        "fg_primary": "#ffffff",
        "fg_secondary": "#a0aab5",
        "fg_muted": "#8c95a1",
        "accent_green": "#2ecc71",
        "accent_blue": "#3498db",
        "accent_purple": "#9b59b6",
        "accent_orange": "#e67e22",
        "btn_bg": "#2b3038",
        "btn_fg": "#ffffff",
        "btn_hover": "#3a424d",
        "success": "#2ecc71",
        "error": "#ff6b6b",
        "warning": "#f1c40f",
        "border": "#21262d"
    }

    LIGHT = {
        "bg_root": "#f4f6f9",
        "bg_top": "#ffffff",
        "bg_sub": "#eef2f6",
        "bg_panel": "#ffffff",
        "bg_card": "#f8fafc",
        "bg_input": "#ffffff",
        "bg_console": "#ffffff",
        "fg_primary": "#1e293b",
        "fg_secondary": "#475569",
        "fg_muted": "#64748b",
        "accent_green": "#16a34a",
        "accent_blue": "#2563eb",
        "accent_purple": "#7c3aed",
        "accent_orange": "#ea580c",
        "btn_bg": "#e2e8f0",
        "btn_fg": "#0f172a",
        "btn_hover": "#cbd5e1",
        "success": "#16a34a",
        "error": "#dc2626",
        "warning": "#d97706",
        "border": "#cbd5e1"
    }

    def __init__(self, mode="dark"):
        self.mode = mode
        self.colors = self.DARK if mode == "dark" else self.LIGHT

    def toggle(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.colors = self.DARK if self.mode == "dark" else self.LIGHT
        return self.mode
