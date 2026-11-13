import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from services.automation_service import AutomationService
from services.proxy_service import ProxyService
from services.api_service import ApiService
from services.system_service import SystemService

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("TSB WORKER - FB Automation Pro (Licensed)")
        self.root.geometry("1300x780")
        self.root.configure(bg="#0f1115")

        self.config = self.load_config()
        
        # সার্ভিসগুলো ইনিশিয়ালাইজ করা
        self.automation_service = AutomationService(self.config, self.append_log, self.update_table_row)
        self.proxy_service = ProxyService(self.config)
        self.api_service = ApiService(self.config)
        self.system_service = SystemService(self.config)

        self.setup_styles()
        self.build_top_nav()
        self.build_sub_header()
        self.build_config_panels()
        self.build_bottom_bar()

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self):
        # UI থেকে ভاتলু আপডেট করা
        self.config["threads"] = self.threads_var.get()
        self.config["vpn_regions"] = self.vpn_var.get()
        self.config["enable_2fa"] = self.chk_2fa.get()
        self.config["extract_cookie"] = self.chk_cookie.get()
        self.config["add_email"] = self.chk_email.get()
        self.config["delete_old_contact"] = self.chk_contact.get()
        self.config["enable_proxy"] = self.chk_proxy.get()
        self.config["reuse_gmail"] = self.chk_reuse_gmail.get()
        self.config["reuse_number"] = self.chk_reuse_num.get()

        self.config["proxy_type"] = self.proxy_type_cb.get()
        self.config["proxy_server"] = self.proxy_server_var.get()
        self.config["proxy_port"] = self.proxy_port_var.get()
        self.config["proxy_user"] = self.proxy_user_var.get()
        self.config["proxy_pass"] = self.proxy_pass_var.get()
        self.config["selected_country"] = self.country_cb.get()

        self.config["public_api_header_key"] = self.api_header_key_var.get()
        self.config["public_api_url"] = self.public_api_url_var.get()
        self.config["public_api_header"] = self.public_api_header_var.get()
        self.config["public_api_liveaccess_url"] = self.public_api_liveaccess_url_var.get()
        self.config["public_api_console_url"] = self.public_api_console_url_var.get()
        self.config["nez_range"] = self.nez_range_var.get()
        try:
            self.config["range_country_map"] = json.loads(
                self.range_country_map_var.get() or "{}"
            )
        except json.JSONDecodeError:
            self.append_log("Range country map must be valid JSON.")
            return
        self.config["iva_countries"] = self.iva_country_var.get()
        self.config["otp_timeout"] = self.otp_timeout_var.get()
        self.config["target_bot"] = self.target_bot_var.get()

        self.config["password"] = self.pass_var.get()
        self.config["fb_package"] = self.pkg_var.get()
        self.config["fail_limit"] = self.fail_limit_var.get()
        self.config["language"] = self.lang_cb.get()

        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)

        self.append_log("কনফিগারেশন সফলভাবে সেভ করা হয়েছে।")
        messagebox.showinfo("Saved", "Configuration saved successfully!")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#14171d",
            foreground="#e0e0e0",
            fieldbackground="#14171d",
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background="#1a1e26",
            foreground="#2ecc71",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map("Treeview", background=[("selected", "#1f3a2e")])

    def build_top_nav(self):
        top_frame = tk.Frame(self.root, bg="#14171d", height=60, padx=15)
        top_frame.pack(fill="x", side="top")
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="⚡ TSB WORKER", bg="#14171d", fg="#ffffff", font=("Segoe UI", 13, "bold")).pack(side="left")
        tk.Label(top_frame, text=" PRO ", bg="#2ecc71", fg="#0f1115", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(5, 15))

        self.status_label = tk.Label(top_frame, text="● SYSTEM READY", bg="#14171d", fg="#95a5a6", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(side="left", padx=10)

        btn_dash = tk.Button(top_frame, text="🏠 Dashboard", bg="#183629", fg="#2ecc71", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2")
        btn_dash.pack(side="left", padx=8)

        btn_settings = tk.Button(top_frame, text="⚙ Settings", bg="#1a1e26", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2")
        btn_settings.pack(side="left", padx=4)

        # Start & Stop Engine Buttons
        btn_stop = tk.Button(top_frame, text="■ STOP", bg="#38191b", fg="#ff6b6b", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6, cursor="hand2", command=self.stop_engine)
        btn_stop.pack(side="right", padx=(8, 0))

        btn_start = tk.Button(top_frame, text="▶ START ENGINE", bg="#27ae60", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=18, pady=6, cursor="hand2", command=self.start_engine)
        btn_start.pack(side="right")

        # License Box
        lic_frame = tk.Frame(top_frame, bg="#12151b", bd=1, relief="solid", padx=8, pady=3)
        lic_frame.pack(side="right", padx=15)
        tk.Label(lic_frame, text="ID: TSB-7B6C07EA15", bg="#12151b", fg="#8c95a1", font=("Consolas", 8)).pack(anchor="w")
        tk.Label(lic_frame, text="📅 2089-10-10 (22981 Days Left)", bg="#12151b", fg="#2ecc71", font=("Consolas", 8)).pack(anchor="w")

    def build_sub_header(self):
        sub_frame = tk.Frame(self.root, bg="#12151b", height=45, padx=15)
        sub_frame.pack(fill="x", side="top")
        sub_frame.pack_propagate(False)

        tk.Label(sub_frame, text="Gmail API:", bg="#12151b", fg="#8c95a1", font=("Segoe UI", 9)).pack(side="left")
        self.gmail_api_cb = ttk.Combobox(sub_frame, values=["https://tsbotp.site"], width=18, state="readonly")
        self.gmail_api_cb.set("https://tsbotp.site")
        self.gmail_api_cb.pack(side="left", padx=8)

        tk.Label(sub_frame, text="Phone API:", bg="#12151b", fg="#8c95a1", font=("Segoe UI", 9)).pack(side="left", padx=(15, 0))
        self.phone_api_cb = ttk.Combobox(sub_frame, values=["Facebook Create by Gmail"], width=22, state="readonly")
        self.phone_api_cb.set("Facebook Create by Gmail")
        self.phone_api_cb.pack(side="left", padx=8)

        tk.Label(sub_frame, text="Country:", bg="#12151b", fg="#8c95a1", font=("Segoe UI", 9)).pack(side="left", padx=(15, 0))
        self.country_cb = ttk.Combobox(
            sub_frame,
            values=["Canada", "USA", "UK"],
            width=16,
            state="readonly"
        )
        self.country_cb.set(self.config.get("selected_country", "Canada"))
        self.country_cb.pack(side="left", padx=8)
        self.country_cb.bind("<<ComboboxSelected>>", self.on_country_changed)

        btn_save_top = tk.Button(sub_frame, text="✔ Save", bg="#2ecc71", fg="#0f1115", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, command=self.save_config, cursor="hand2")
        btn_save_top.pack(side="right", padx=10)

        tk.Label(sub_frame, text="Stock: 1430 (Live API)", bg="#12151b", fg="#2ecc71", font=("Segoe UI", 9)).pack(side="right", padx=15)

    def build_config_panels(self):
        container = tk.Frame(self.root, bg="#0f1115", padx=12, pady=10)
        container.pack(fill="x")

        # ১. AUTOMATION PANEL
        p1 = tk.LabelFrame(container, text=" ⚙ AUTOMATION ", bg="#14171d", fg="#2ecc71", font=("Segoe UI", 9, "bold"), bd=1, relief="solid", padx=10, pady=8)
        p1.pack(side="left", fill="both", expand=True, padx=4)

        tk.Label(p1, text="Threads (e.g. 1,2,3):", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.threads_var = tk.StringVar(value=self.config.get("threads", "1,2"))
        tk.Entry(p1, textvariable=self.threads_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 8), ipady=3)

        tk.Label(p1, text="VPN Regions:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.vpn_var = tk.StringVar(value=self.config.get("vpn_regions", "UK - Docklands, UK"))
        tk.Entry(p1, textvariable=self.vpn_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 8), ipady=3)

        self.chk_2fa = tk.BooleanVar(value=self.config.get("enable_2fa", True))
        self.chk_cookie = tk.BooleanVar(value=self.config.get("extract_cookie", False))
        self.chk_email = tk.BooleanVar(value=self.config.get("add_email", False))
        self.chk_contact = tk.BooleanVar(value=self.config.get("delete_old_contact", True))
        self.chk_reuse_gmail = tk.BooleanVar(value=self.config.get("reuse_gmail", True))
        self.chk_reuse_num = tk.BooleanVar(value=self.config.get("reuse_number", False))

        for text, var in [("Enable 2FA", self.chk_2fa), ("Extract Cookie", self.chk_cookie), ("Add Email", self.chk_email), 
                          ("Delete Old Contact", self.chk_contact), ("Reuse Gmail", self.chk_reuse_gmail), ("Reuse Number", self.chk_reuse_num)]:
            tk.Checkbutton(p1, text=text, variable=var, bg="#14171d", fg="white", selectcolor="#1a1e26", activebackground="#14171d", activeforeground="white", font=("Segoe UI", 9)).pack(anchor="w", pady=1)

        # ২. SUPER PROXY PANEL
        p2 = tk.LabelFrame(container, text=" 🔵 SUPER PROXY ", bg="#14171d", fg="#3498db", font=("Segoe UI", 9, "bold"), bd=1, relief="solid", padx=10, pady=8)
        p2.pack(side="left", fill="both", expand=True, padx=4)

        self.chk_proxy = tk.BooleanVar(value=self.config.get("enable_proxy", True))
        tk.Checkbutton(p2, text="Enable Super Proxy Setup", variable=self.chk_proxy, bg="#14171d", fg="#3498db", selectcolor="#1a1e26", activebackground="#14171d", activeforeground="#3498db", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Label(p2, text="Type:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.proxy_type_cb = ttk.Combobox(p2, values=["other", "socks5", "http"], state="readonly")
        self.proxy_type_cb.set(self.config.get("proxy_type", "other"))
        self.proxy_type_cb.pack(fill="x", pady=(2, 6))

        tk.Label(p2, text="Server:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.proxy_server_var = tk.StringVar(value=self.config.get("proxy_server", "gw.dataimpulse.com"))
        tk.Entry(p2, textvariable=self.proxy_server_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p2, text="Port:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.proxy_port_var = tk.StringVar(value=self.config.get("proxy_port", "823"))
        tk.Entry(p2, textvariable=self.proxy_port_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p2, text="User:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.proxy_user_var = tk.StringVar(value=self.config.get("proxy_user", ""))
        tk.Entry(p2, textvariable=self.proxy_user_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p2, text="Pass:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.proxy_pass_var = tk.StringVar(value=self.config.get("proxy_pass", ""))
        tk.Entry(p2, textvariable=self.proxy_pass_var, show="*", bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        # ৩. EXTERNAL APIS PANEL
        p3 = tk.LabelFrame(container, text=" 🔑 EXTERNAL APIS ", bg="#14171d", fg="#9b59b6", font=("Segoe UI", 9, "bold"), bd=1, relief="solid", padx=10, pady=8)
        p3.pack(side="left", fill="both", expand=True, padx=4)

        tk.Label(p3, text="API Header Key:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.api_header_key_var = tk.StringVar(
            value=os.environ.get(
                "FB_WORKER_NEZ_KEY",
                self.config.get(
                    "public_api_header_key",
                    self.config.get("nez_key", "")
                )
            )
        )
        tk.Entry(p3, textvariable=self.api_header_key_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Public API URL:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.public_api_url_var = tk.StringVar(
            value=self.config.get(
                "public_api_url",
                ApiService.DEFAULT_PUBLIC_API_URL
            )
        )
        tk.Entry(p3, textvariable=self.public_api_url_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="API Header:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.public_api_header_var = tk.StringVar(
            value=self.config.get(
                "public_api_header",
                ApiService.DEFAULT_PUBLIC_API_HEADER
            )
        )
        tk.Entry(p3, textvariable=self.public_api_header_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Live Access URL:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.public_api_liveaccess_url_var = tk.StringVar(
            value=self.config.get(
                "public_api_liveaccess_url",
                ApiService.DEFAULT_LIVEACCESS_URL
            )
        )
        tk.Entry(p3, textvariable=self.public_api_liveaccess_url_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Console URL:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.public_api_console_url_var = tk.StringVar(
            value=self.config.get(
                "public_api_console_url",
                ApiService.DEFAULT_CONSOLE_URL
            )
        )
        tk.Entry(p3, textvariable=self.public_api_console_url_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Nez Range:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.nez_range_var = tk.StringVar(
            value=self.config.get(
                "nez_range",
                ApiService.DEFAULT_PUBLIC_API_RANGE
            )
        )
        range_entry = tk.Entry(
            p3,
            textvariable=self.nez_range_var,
            bg="#1a1e26",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Segoe UI", 9)
        )
        range_entry.pack(fill="x", pady=(2, 6), ipady=3)
        range_entry.bind("<KeyRelease>", self.on_range_changed)

        tk.Label(p3, text="Range Country Map (JSON):", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.range_country_map_var = tk.StringVar(
            value=json.dumps(
                self.config.get(
                    "range_country_map",
                    {}
                ),
                separators=(",", ":")
            )
        )
        tk.Entry(p3, textvariable=self.range_country_map_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Iva Countries:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.iva_country_var = tk.StringVar(value=self.config.get("iva_countries", "ALL"))
        tk.Entry(p3, textvariable=self.iva_country_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="OTP Timeout:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.otp_timeout_var = tk.StringVar(value=self.config.get("otp_timeout", "60"))
        tk.Entry(p3, textvariable=self.otp_timeout_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p3, text="Target Bot:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.target_bot_var = tk.StringVar(value=self.config.get("target_bot", "@SureSmsBot"))
        tk.Entry(p3, textvariable=self.target_bot_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        # ৪. SYSTEM & FORMAT PANEL
        p4 = tk.LabelFrame(container, text=" ⚙ SYSTEM & FORMAT ", bg="#14171d", fg="#e67e22", font=("Segoe UI", 9, "bold"), bd=1, relief="solid", padx=10, pady=8)
        p4.pack(side="left", fill="both", expand=True, padx=4)

        tk.Label(p4, text="Password:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.pass_var = tk.StringVar(value=self.config.get("password", ""))
        tk.Entry(p4, textvariable=self.pass_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p4, text="FB Package:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.pkg_var = tk.StringVar(value=self.config.get("fb_package", "com.facebook.lite"))
        tk.Entry(p4, textvariable=self.pkg_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p4, text="Fail Limit:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.fail_limit_var = tk.StringVar(value=self.config.get("fail_limit", "4"))
        tk.Entry(p4, textvariable=self.fail_limit_var, bg="#1a1e26", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 6), ipady=3)

        tk.Label(p4, text="Language:", bg="#14171d", fg="#8c95a1", font=("Segoe UI", 9)).pack(anchor="w")
        self.lang_cb = ttk.Combobox(p4, values=["English (US)", "English (UK)"], state="readonly")
        self.lang_cb.set(self.config.get("language", "English (US)"))
        self.lang_cb.pack(fill="x", pady=(2, 6))

        self.chk_clear_server = tk.BooleanVar(value=True)
        tk.Checkbutton(p4, text="Continuous Clear Server", variable=self.chk_clear_server, bg="#14171d", fg="white", selectcolor="#1a1e26", activebackground="#14171d", activeforeground="white", font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

    def build_bottom_bar(self):
        self.bottom_frame = tk.Frame(self.root, bg="#14171d", height=280, padx=15, pady=6)
        self.bottom_frame.pack(fill="both", expand=True, side="bottom")
        self.bottom_frame.pack_propagate(False)

        # Resizable handle bar (Drag with mouse to resize height)
        resize_bar = tk.Frame(self.bottom_frame, bg="#2b3038", height=5, cursor="sb_v_double_arrow")
        resize_bar.pack(side="top", fill="x", pady=(0, 4))

        def start_resize(event):
            self._drag_start_y = event.y_root
            self._drag_start_height = self.bottom_frame.winfo_height()

        def do_resize(event):
            if getattr(self, "console_collapsed", False):
                return
            delta_y = self._drag_start_y - event.y_root
            new_height = max(120, min(650, self._drag_start_height + delta_y))
            self.bottom_frame.config(height=new_height)
            self.bottom_frame.pack_propagate(False)

        resize_bar.bind("<Button-1>", start_resize)
        resize_bar.bind("<B1-Motion>", do_resize)

        # Header bar with Collapse/Expand toggle
        console_header = tk.Frame(self.bottom_frame, bg="#14171d")
        console_header.pack(side="top", fill="x", pady=(0, 4))

        self.log_label = tk.Label(console_header, text="Ready...", bg="#14171d", fg="#a0aab5", font=("Consolas", 9), anchor="w")
        self.log_label.pack(side="left", fill="x", expand=True)

        self.console_toggle_btn = tk.Button(
            console_header,
            text="▲ COLLAPSE",
            bg="#2b3038",
            fg="#ffffff",
            activebackground="#3a424d",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            command=self.toggle_console,
            cursor="hand2"
        )
        self.console_toggle_btn.pack(side="right", padx=(6, 0))

        # Main Bottom Notebook (Tabs: 1. Process Console, 2. Number & Verify, 3. ID Creation)
        self.console_content_frame = tk.Frame(self.bottom_frame, bg="#0f1115")
        self.console_content_frame.pack(side="top", fill="both", expand=True)

        style = ttk.Style()
        style.configure("Console.TNotebook", background="#0f1115", borderwidth=0)
        style.configure("Console.TNotebook.Tab", background="#1a1e26", foreground="#a0aab5", font=("Segoe UI", 8, "bold"), padding=[12, 6])
        style.map("Console.TNotebook.Tab", background=[("selected", "#2ecc71")], foreground=[("selected", "#0f1115")])

        self.bottom_notebook = ttk.Notebook(self.console_content_frame, style="Console.TNotebook")
        self.bottom_notebook.pack(fill="both", expand=True)

        # ---------------------------------------------
        # TAB 1: PROCESS CONSOLE
        # ---------------------------------------------
        console_tab = tk.Frame(self.bottom_notebook, bg="#0b0d10")
        self.bottom_notebook.add(console_tab, text=" 🖥️ PROCESS CONSOLE ")

        c_top_bar = tk.Frame(console_tab, bg="#0b0d10", padx=5, pady=4)
        c_top_bar.pack(fill="x", side="top")
        tk.Label(c_top_bar, text="System & Process Logs", bg="#0b0d10", fg="#2ecc71", font=("Segoe UI", 8, "bold")).pack(side="left")

        tk.Button(
            c_top_bar,
            text="CLEAR CONSOLE",
            bg="#2b3038",
            fg="#ffffff",
            activebackground="#3a424d",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            command=self.clear_console,
            cursor="hand2"
        ).pack(side="right")

        self.console_text = tk.Text(
            console_tab,
            bg="#0b0d10",
            fg="#d7dde5",
            insertbackground="#d7dde5",
            relief="flat",
            font=("Consolas", 8),
            state="disabled",
            wrap="word"
        )
        self.console_text.tag_configure("success", foreground="#2ecc71")
        self.console_text.tag_configure("error", foreground="#ff6b6b")
        self.console_text.tag_configure("warning", foreground="#f1c40f")
        self.console_text.tag_configure("info", foreground="#d7dde5")
        self.console_text.pack(side="top", fill="both", expand=True)

        # ---------------------------------------------
        # TAB 2: NUMBER & VERIFY CONSOLE
        # ---------------------------------------------
        number_tab = tk.Frame(self.bottom_notebook, bg="#0b0d10")
        self.bottom_notebook.add(number_tab, text=" 📱 NUMBER & VERIFY ")

        n_top_bar = tk.Frame(number_tab, bg="#0b0d10", padx=5, pady=4)
        n_top_bar.pack(fill="x", side="top")
        tk.Label(n_top_bar, text="Emulator Number Storage & OTP Verification Console", bg="#0b0d10", fg="#3498db", font=("Segoe UI", 8, "bold")).pack(side="left")

        self.number_text = tk.Text(
            number_tab,
            bg="#0b0d10",
            fg="#3498db",
            insertbackground="#3498db",
            relief="flat",
            font=("Consolas", 8),
            state="normal",
            wrap="word"
        )
        self.number_text.insert("1.0", "Waiting for number allocation and OTP polling...\n")
        self.number_text.config(state="disabled")
        self.number_text.pack(side="top", fill="both", expand=True)

        # ---------------------------------------------
        # TAB 3: ID CREATION (name_list.txt)
        # ---------------------------------------------
        id_tab = tk.Frame(self.bottom_notebook, bg="#0b0d10")
        self.bottom_notebook.add(id_tab, text=" 👥 ID CREATION (name_list.txt) ")

        id_top_bar = tk.Frame(id_tab, bg="#0b0d10", padx=5, pady=4)
        id_top_bar.pack(fill="x", side="top")
        tk.Label(id_top_bar, text="Loaded names from name_list.txt & Account Generation Status", bg="#0b0d10", fg="#e67e22", font=("Segoe UI", 8, "bold")).pack(side="left")

        table_frame = tk.Frame(id_tab, bg="#0b0d10")
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("ID", "NAME", "UID", "PASSWORD", "2FA", "EMAIL", "STATUS")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        col_widths = {"ID": 50, "NAME": 160, "UID": 140, "PASSWORD": 140, "2FA": 150, "EMAIL": 200, "STATUS": 180}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col], anchor="center")

        self.tree.pack(fill="both", expand=True)

        self.populate_name_list_data()
        self.console_collapsed = False

    def populate_name_list_data(self):
        names = []
        try:
            if os.path.exists("name_list.txt"):
                with open("name_list.txt", "r", encoding="utf-8") as f:
                    names = [line.strip() for line in f if line.strip()]
        except Exception:
            pass

        if not names:
            names = ["Ethan Sullivan", "Sophia Weaver", "Mason Caldwell", "Harper Hayes", "Logan Brooks"]

        for i, name in enumerate(names[:100], start=1):
            self.tree.insert("", "end", iid=str(i), values=(i, name, "Pending..", self.config.get("password", "AbirCvB1Yn@11"), "...", "...", "Waiting"))

    def start_engine(self):
        self.status_label.config(text="● ENGINE RUNNING", fg="#2ecc71")
        thread_input = self.threads_var.get()
        self.automation_service.start_automation(thread_input)

    def search_country(self):
        self.config["public_api_url"] = self.public_api_url_var.get().strip()
        self.config["public_api_header"] = self.public_api_header_var.get().strip()
        self.config["public_api_liveaccess_url"] = (
            self.public_api_liveaccess_url_var.get().strip()
        )
        self.config["public_api_console_url"] = (
            self.public_api_console_url_var.get().strip()
        )
        self.config["public_api_header_key"] = self.api_header_key_var.get().strip()
        range_id = self.nez_range_var.get().strip()
        self.config["nez_range"] = range_id
        self.config["proxy_user"] = self.proxy_user_var.get().strip()
        try:
            self.config["range_country_map"] = json.loads(
                self.range_country_map_var.get() or "{}"
            )
        except json.JSONDecodeError as error:
            self.append_log(f"Range country map error: {error}")
            return
        self.log_label.config(text="[LOG] Searching country from public API...")

        search_generation = getattr(self, "_range_search_generation", 0) + 1
        self._range_search_generation = search_generation

        def worker():
            try:
                details = self.api_service.resolve_range_details(range_id)
            except (OSError, RuntimeError, ValueError) as error:
                self.root.after(
                    0,
                    lambda message=str(error): self._report_range_search_error(
                        search_generation,
                        message,
                    )
                )
                return

            def update_country():
                if search_generation != self._range_search_generation:
                    return
                country = details["country"]
                values = list(self.country_cb["values"])
                if country not in values:
                    values.append(country)
                    self.country_cb["values"] = values
                self.country_cb.set(country)
                self.config["selected_country_code"] = details["country_code"]
                self.on_country_changed(details["country_code"])
                self.append_log(f"Country selected: {country}")

            self.root.after(0, update_country)

        threading.Thread(
            target=worker,
            daemon=True,
            name="country-search"
        ).start()

    def _report_range_search_error(self, search_generation, error_message):
        if search_generation == self._range_search_generation:
            self.append_log(f"Country search error: {error_message}")

    def on_range_changed(self, _event=None):
        if hasattr(self, "_range_search_job"):
            self.root.after_cancel(self._range_search_job)
        self._range_search_job = self.root.after(500, self.search_country)

    def on_country_changed(self, _event=None):
        country = self.country_cb.get().strip()
        if not country:
            return
        try:
            country_code = (
                _event
                if isinstance(_event, str)
                else self.config.get("selected_country_code")
                or self.api_service.country_code(country)
            )
            updated_user = self.proxy_service.update_region(country_code)
        except ValueError as error:
            self.append_log(f"Proxy region update error: {error}")
            return

        self.config["selected_country"] = country
        if updated_user:
            self.proxy_user_var.set(updated_user)
            self.config["proxy_user"] = updated_user
        with open("config.json", "w") as config_file:
            json.dump(self.config, config_file, indent=4)
        self.append_log(f"Proxy country updated: {country}")

    def stop_engine(self):
        self.status_label.config(text="● SYSTEM READY", fg="#95a5a6")
        self.automation_service.stop_automation()

    def toggle_console(self):
        if self.console_collapsed:
            self.bottom_notebook.pack(fill="both", expand=True)
            self.bottom_frame.config(height=280)
            self.bottom_frame.pack_propagate(False)
            self.console_toggle_btn.config(text="▲ COLLAPSE")
            self.console_collapsed = False
        else:
            self.bottom_notebook.pack_forget()
            self.bottom_frame.config(height=45)
            self.bottom_frame.pack_propagate(False)
            self.console_toggle_btn.config(text="▼ EXPAND")
            self.console_collapsed = True

    def append_log(self, message):
        def _append():
            self.log_label.config(text=f"[LOG] {message}")
            normalized_message = message.lower()
            if any(
                keyword in normalized_message
                for keyword in ("error", "failed", "timeout", "ব্যর্থ", "ত্রুটি")
            ):
                tag = "error"
            elif any(
                keyword in normalized_message
                for keyword in ("success", "successful", "সফল", "complete", "active")
            ):
                tag = "success"
            elif any(
                keyword in normalized_message
                for keyword in ("warning", "wait", "অপেক্ষা", "checking")
            ):
                tag = "warning"
            else:
                tag = "info"

            if hasattr(self, "console_text"):
                self.console_text.config(state="normal")
                self.console_text.insert("end", f"{message}\n", tag)
                self.console_text.see("end")
                self.console_text.config(state="disabled")

            if any(k in normalized_message for k in ("number", "otp", "allocat", "api", "range", "getnum", "phone", "sms")):
                if hasattr(self, "number_text"):
                    self.number_text.config(state="normal")
                    self.number_text.insert("end", f"{message}\n")
                    self.number_text.see("end")
                    self.number_text.config(state="disabled")

        self.root.after(0, _append)

    def clear_console(self):
        if hasattr(self, "console_text"):
            self.console_text.config(state="normal")
            self.console_text.delete("1.0", "end")
            self.console_text.config(state="disabled")
        self.log_label.config(text="Console cleared.")

    def update_table_row(self, row_id, col_name, new_value):
        def _update():
            item_id = str(row_id)
            if self.tree.exists(item_id):
                current_values = list(self.tree.item(item_id, "values"))
                col_index = self.tree["columns"].index(col_name)
                current_values[col_index] = new_value
                self.tree.item(item_id, values=current_values)
        self.root.after(0, _update)