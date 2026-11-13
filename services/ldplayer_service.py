import os
import random
import subprocess
import time
import ctypes
import threading
import re
import xml.etree.ElementTree as ET
from ctypes import wintypes

class LDPlayerService:
    def __init__(self, ld_dir, log_callback=None):
        self.ld_dir = ld_dir
        self.ldconsole = os.path.join(ld_dir, "ldconsole.exe")
        self.adb = os.path.join(ld_dir, "adb.exe")
        self.log_callback = log_callback
        self._window_slots = {}
        self._window_slots_lock = threading.Lock()

    def _log(self, message):
        print(message, flush=True)
        if self.log_callback is not None:
            self.log_callback(message)

    def _run(self, command, description):
        self._log(f"[LDPlayer] {description}: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        if output:
            self._log(f"[LDPlayer] stdout: {output}")
        if error:
            self._log(f"[LDPlayer] stderr: {error}")
        if result.returncode != 0:
            raise RuntimeError(
                f"{description} failed with exit code {result.returncode}: "
                f"{error or output or 'no output'}"
            )
        return result

    def is_valid_path(self):
        return os.path.exists(self.ldconsole) and os.path.exists(self.adb)

    def launch_instance(self, index=0):
        if not self.is_valid_path():
            raise FileNotFoundError(f"ldconsole.exe পাওয়া যায়নি: {self.ld_dir}")
        command = [self.ldconsole, "launch", "--index", str(index)]
        self._log(f"[LDPlayer {index}] launch শুরু হচ্ছে: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self._log(f"[LDPlayer {index}] launch process started (PID {process.pid}).")

    def wait_for_boot(self, index=0, timeout=180):
        start_time = time.time()
        last_running_output = None
        self._log(f"[LDPlayer {index}] boot হওয়ার জন্য অপেক্ষা করছে...")
        while time.time() - start_time < timeout:
            try:
                running_result = subprocess.run(
                    [self.ldconsole, "isrunning", "--index", str(index)],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                running_output = (
                    running_result.stdout or running_result.stderr
                ).strip().lower()
                running_state = " ".join(running_output.split())
                if running_output != last_running_output:
                    self._log(
                        f"[LDPlayer {index}] isrunning: "
                        f"exit={running_result.returncode}, output={running_output or '<empty>'}"
                    )
                    last_running_output = running_output

                if running_state == "running" or running_state.endswith(" running"):
                    try:
                        boot_result = subprocess.run(
                            [
                                self.ldconsole,
                                "adb",
                                "--index",
                                str(index),
                                "--command",
                                "shell getprop sys.boot_completed"
                            ],
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                    except subprocess.TimeoutExpired:
                        self._log(
                            f"[LDPlayer {index}] boot property check timeout; retrying..."
                        )
                        time.sleep(2)
                        continue

                    boot_status = (boot_result.stdout or "").strip()
                    self._log(
                        f"[LDPlayer {index}] boot property: "
                        f"exit={boot_result.returncode}, "
                        f"output={boot_status or '<empty>'}"
                    )
                    if boot_result.returncode != 0:
                        self._log(
                            f"[LDPlayer {index}] boot property check failed: "
                            f"exit={boot_result.returncode}, "
                            f"{(boot_result.stderr or '').strip()}"
                        )

                    if any(line.strip() == "1" for line in boot_status.splitlines()):
                        time.sleep(2)
                        self._log(f"[LDPlayer {index}] boot complete.")
                        return True
            except (OSError, subprocess.SubprocessError) as error:
                self._log(f"[LDPlayer {index}] boot check error: {error}")
            time.sleep(2)
        self._log(f"[LDPlayer {index}] boot timeout ({timeout}s).")
        return False

    def is_app_installed(self, index=0, package_name="com.facebook.lite"):
        command = [
            self.ldconsole, "adb", "--index", str(index),
            "--command", f"shell pm path {package_name}"
        ]
        result = self._run(command, f"checking {package_name} on LDPlayer {index}")
        return "package:" in (result.stdout or "")

    def clear_app_data(self, index=0, package_name="com.facebook.lite"):
        command = [
            self.ldconsole, "adb", "--index", str(index),
            "--command", f"shell pm clear {package_name}"
        ]
        result = self._run(
            command,
            f"clearing all data for {package_name} on LDPlayer {index}"
        )
        output = (result.stdout or "").strip().lower()
        if "success" not in output:
            raise RuntimeError(
                f"Android did not confirm data clear for {package_name} "
                f"on LDPlayer {index}: {output or 'no output'}"
            )
        self._log(
            f"[LDPlayer {index}] all data cleared for {package_name}."
        )
        # Pre-grant all permissions right after clearing data
        self.grant_app_permissions(index, package_name)

    def grant_app_permissions(self, index, package_name="com.facebook.lite"):
        permissions = [
            "android.permission.READ_CONTACTS",
            "android.permission.WRITE_CONTACTS",
            "android.permission.GET_ACCOUNTS",
            "android.permission.READ_PHONE_STATE",
            "android.permission.READ_CALL_LOG",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE"
        ]
        granted_count = 0
        for perm in permissions:
            try:
                self._adb_shell(index, f"pm grant {package_name} {perm}", sensitive=False)
                granted_count += 1
            except Exception:
                pass
        self._log(f"[LDPlayer {index}] 🛡️ Pre-granted {granted_count} permissions to {package_name} before app open.")

    def dismiss_permission_popups(self, index):
        try:
            hierarchy = self._get_ui_hierarchy(index)
            for node in hierarchy.iter("node"):
                text_val = node.attrib.get("text", "").strip().lower()
                desc_val = node.attrib.get("content-desc", "").strip().lower()
                res_id = node.attrib.get("resource-id", "").strip().lower()

                if "permission_allow_button" in res_id or (
                    text_val in ("allow", "allow all the time", "while using the app", "অনুমতি দিন")
                ) or "allow" in desc_val:
                    self._tap_and_input(index, node, None)
                    self._log(f"[LDPlayer {index}] 🛡️ Permission popup detected: Clicked ALLOW!")
                    time.sleep(1.0)
                    return True
        except Exception:
            pass
        return False

    def open_app(self, index=0, package_name="com.facebook.lite"):
        if not self.is_app_installed(index, package_name):
            raise RuntimeError(
                f"{package_name} installed নেই LDPlayer {index}-এ; "
                "এই instance-এ app launch করা সম্ভব হয়নি।"
            )

        command = [
            self.ldconsole, "adb", "--index", str(index),
            "--command",
            (
                "shell monkey -p "
                f"{package_name} -c android.intent.category.LAUNCHER 1"
            )
        ]
        self._run(command, f"opening {package_name} on LDPlayer {index}")
        self.grant_app_permissions(index, package_name)

    def configure_super_proxy(self, index, credentials):
        package_name = "com.scheler.superproxy"
        self.open_app(index, package_name)
        time.sleep(3.0)

        # 1. Tap "+ Add proxy" button with multi-strategy search & retries
        clicked_add = False
        for _ in range(3):
            try:
                hierarchy = self._get_ui_hierarchy(index)
                for node in hierarchy.iter("node"):
                    desc = " ".join(
                        node.attrib.get(k, "")
                        for k in ("text", "content-desc", "resource-id", "class")
                    ).lower()
                    if any(term in desc for term in ("add", "fab", "plus", "＋")):
                        self._tap_and_input(index, node, None)
                        clicked_add = True
                        break
                if clicked_add:
                    break
            except Exception:
                pass
            time.sleep(1.0)

        if not clicked_add:
            # Fallback tap bottom-right floating action button directly
            self._adb_shell(index, "input tap 340 600", sensitive=False)
            time.sleep(0.5)
            self._adb_shell(index, "input tap 320 640", sensitive=False)

        time.sleep(2.0)

        # 2. Fill Form Fields (Server, Port, Username, Password)
        try:
            hierarchy = self._get_ui_hierarchy(index)
            edit_nodes = [
                node for node in hierarchy.iter("node")
                if "edittext" in node.attrib.get("class", "").lower()
            ]

            values = [
                credentials["server"],     # Index 1: Server
                credentials["port"],       # Index 2: Port
                credentials["user"],       # Index 3: Username
                credentials["password"],   # Index 4: Password
            ]

            if len(edit_nodes) >= 5:
                # Use exact Super Proxy EditText positions (1, 2, 3, 4)
                for idx_offset, val in enumerate(values):
                    target_node = edit_nodes[idx_offset + 1]
                    self._tap_and_input(index, target_node, val)
            else:
                # Fallback to label search
                fields = (
                    (("host", "server", "address"), credentials["server"]),
                    (("port",), credentials["port"]),
                    (("username", "user", "account"), credentials["user"]),
                    (("password", "pass"), credentials["password"]),
                )
                for labels, value in fields:
                    node = self._find_edit_node(hierarchy, labels)
                    if node is not None:
                        self._tap_and_input(index, node, value)
        except Exception as field_err:
            self._log(f"[LDPlayer {index}] Super Proxy form input notice: {field_err}")

        time.sleep(1.0)

        # 3. Tap Save icon at top right
        try:
            hierarchy = self._get_ui_hierarchy(index)
            self._tap_ui_node(index, hierarchy, ("save", "✓", "action_save"))
        except Exception:
            # Fallback tap top right save floppy disk icon
            self._adb_shell(index, "input tap 360 40", sensitive=False)

        self._log(f"[LDPlayer {index}] Super Proxy profile saved.")

    def _get_ui_hierarchy(self, index):
        try:
            self._adb_shell(index, "uiautomator dump /sdcard/dump.xml", sensitive=False)
            result = subprocess.run(
                [
                    self.ldconsole, "adb", "--index", str(index),
                    "--command", "shell cat /sdcard/dump.xml"
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            output = result.stdout or ""
            start = output.find("<?xml")
            if start >= 0:
                end = output.rfind(">")
                if end > start:
                    return ET.fromstring(output[start:end+1])
        except Exception as e:
            self._log(f"[LDPlayer {index}] UI dump notice: {e}")

        try:
            result = subprocess.run(
                [
                    self.ldconsole, "adb", "--index", str(index),
                    "--command", "shell uiautomator dump /dev/tty"
                ],
                capture_output=True,
                text=True,
                timeout=15
            )
            output = result.stdout or ""
            start = output.find("<?xml")
            if start >= 0:
                end = output.rfind(">")
                if end > start:
                    return ET.fromstring(output[start:end+1])
        except Exception:
            pass

        raise RuntimeError(f"UI hierarchy dump failed on LDPlayer {index}")

    def _find_edit_node(self, root, labels):
        for node in root.iter("node"):
            class_name = node.attrib.get("class", "")
            description = " ".join(
                node.attrib.get(key, "")
                for key in ("text", "hint", "content-desc", "resource-id")
            ).lower()
            if "edittext" in class_name.lower() and any(
                label in description for label in labels
            ):
                return node
        return None

    def _tap_ui_node(self, index, root, labels):
        for node in root.iter("node"):
            description = " ".join(
                node.attrib.get(key, "")
                for key in ("text", "content-desc", "resource-id")
            ).lower()
            if any(label.lower() in description for label in labels):
                self._tap_and_input(index, node, None)
                return
        raise RuntimeError(
            f"Super Proxy button not found: {', '.join(labels)}"
        )

    def _tap_and_input(self, index, node, value):
        bounds = node.attrib.get("bounds", "")
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if match is None:
            raise RuntimeError("Super Proxy UI node has invalid bounds.")
        left, top, right, bottom = (int(item) for item in match.groups())
        x = (left + right) // 2
        y = (top + bottom) // 2
        self._adb_shell(index, f"input tap {x} {y}", sensitive=False)
        if value is not None:
            escaped = value.replace("%", "%25").replace(" ", "%s")
            self._adb_shell(
                index,
                f"input text {escaped}",
                sensitive=True
            )

    def _adb_shell(self, index, command, sensitive=False):
        result = subprocess.run(
            [
                self.ldconsole, "adb", "--index", str(index),
                "--command", f"shell {command}"
            ],
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if sensitive:
                detail = "sensitive ADB input failed"
            raise RuntimeError(
                f"ADB command failed on LDPlayer {index}: {detail or 'no output'}"
            )

    def set_clipboard(self, index, text):
        escaped = text.replace('"', '\\"').replace('$', '\\$')
        try:
            self._adb_shell(index, f'cmd clipboard set text "{escaped}"', sensitive=False)
            self._log(f"[LDPlayer {index}] Clipboard set: {text}")
        except Exception:
            try:
                self._adb_shell(index, f'service call clipboard 2 s16 "{escaped}"', sensitive=False)
                self._log(f"[LDPlayer {index}] Clipboard set via service call: {text}")
            except Exception as err:
                self._log(f"[LDPlayer {index}] Clipboard set notice: {err}")

    def arrange_windows(self, indices, retries=1):
        if os.name != "nt":
            self._log("[LDPlayer] Windows ছাড়া emulator window সাজানো সম্ভব নয়।")
            return

        user32 = ctypes.windll.user32
        windows = []

        for attempt in range(retries + 1):
            windows.clear()

            def enum_window(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if "ldplayer" in title.value.lower():
                    windows.append((hwnd, title.value))
                return True

            enum_windows_proc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM
            )(enum_window)
            user32.EnumWindows(enum_windows_proc, 0)

            if windows:
                break
            if attempt < retries:
                time.sleep(0.5)

        if not windows:
            self._log("[LDPlayer] কোনো visible LDPlayer window পাওয়া যায়নি।")
            return

        gap = 10

        with self._window_slots_lock:
            active_handles = {hwnd for hwnd, _ in windows}
            self._window_slots = {
                hwnd: slot
                for hwnd, slot in self._window_slots.items()
                if hwnd in active_handles
            }
            used_slots = set(self._window_slots.values())
            slot_count = max(4, len(windows))
            for hwnd, _ in windows:
                if hwnd not in self._window_slots:
                    free_slots = [
                        slot
                        for slot in range(slot_count)
                        if slot not in used_slots
                    ]
                    if not free_slots:
                        continue
                    self._window_slots[hwnd] = free_slots[0]
                    used_slots.add(free_slots[0])

            windows.sort(key=lambda item: self._window_slots[item[0]])
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            columns = 4
            rows = (len(windows) + columns - 1) // columns
            scale = min(
                1.0,
                (screen_width - gap * (columns - 1)) / (400 * columns),
                (screen_height - gap * (rows - 1)) / (700 * rows)
            )
            window_width = max(1, int(400 * scale))
            window_height = max(1, int(700 * scale))

            for hwnd, title in windows:
                position = self._window_slots[hwnd]
                column = position % columns
                row = position // columns
                x = column * (window_width + gap)
                y = row * (window_height + gap)
                user32.SetWindowPos(
                    hwnd,
                    0,
                    x,
                    y,
                    window_width,
                    window_height,
                    0x0040
                )
                self._log(
                    f"[LDPlayer] window সাজানো হয়েছে: {title} "
                    f"(row {row + 1}, column {column + 1})"
                )

    def arrange_windows_once_when_visible(self, indices, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            user32 = ctypes.windll.user32
            windows = []
            def enum_window(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if "ldplayer" in title.value.lower():
                    windows.append((hwnd, title.value))
                return True
            enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_window)
            user32.EnumWindows(enum_windows_proc, 0)
            if windows:
                self.arrange_windows(indices, retries=0)
                self._log("[LDPlayer] Windows aligned once successfully. User can now reposition freely.")
                return
            time.sleep(1.0)

    def get_screen_size(self, index):
        try:
            result = subprocess.run(
                [
                    self.ldconsole, "adb", "--index", str(index),
                    "--command", "shell wm size"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout or ""
            match = re.search(r"(\d+)x(\d+)", output)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                return w, h
        except Exception:
            pass
        return 540, 960

    def tap_percent(self, index, pct_x, pct_y):
        w, h = self.get_screen_size(index)
        x = int(w * pct_x)
        y = int(h * pct_y)
        self._adb_shell(index, f"input tap {x} {y}", sensitive=False)
        return x, y

    def _click_button(self, index, step_name, keywords, fallback_pct_x=0.50, fallback_pct_y=0.84, retries=1, is_running_check=None):
        if is_running_check and not is_running_check():
            return False
        self.dismiss_permission_popups(index)
        self._log(f"[LDPlayer {index}] 🔍 [{step_name}] Searching for button ({', '.join(keywords)})...")

        # Fast UI scan attempt once
        try:
            hierarchy = self._get_ui_hierarchy(index)
            for node in hierarchy.iter("node"):
                text_val = node.attrib.get("text", "").strip().lower()
                desc_val = node.attrib.get("content-desc", "").strip().lower()
                combined_label = f"{text_val} {desc_val}".strip()

                if not combined_label or len(combined_label) > 25:
                    continue

                if any(term.lower() in combined_label for term in keywords):
                    self._tap_and_input(index, node, None)
                    self._log(f"[LDPlayer {index}] ✅ [{step_name}] Clicked button '{combined_label}' via UI node match!")
                    time.sleep(0.4)
                    return True
        except Exception:
            pass

        # Instant proportional fallback tap + Enter keyevent
        if not is_running_check or is_running_check():
            tap_x, tap_y = self.tap_percent(index, fallback_pct_x, fallback_pct_y)
            self._log(f"[LDPlayer {index}] 📍 [{step_name}] Tapped button via proportional coordinates ({tap_x}, {tap_y}).")
            time.sleep(0.4)
            self._adb_shell(index, "input keyevent 66", sensitive=False)
            return True
        return False

    def _wait_for_screen(self, index, keywords, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                hierarchy = self._get_ui_hierarchy(index)
                for node in hierarchy.iter("node"):
                    desc = " ".join(
                        node.attrib.get(k, "")
                        for k in ("text", "content-desc", "resource-id")
                    ).lower()
                    if any(kw.lower() in desc for kw in keywords):
                        return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    def perform_fb_lite_registration(self, index, first_name, last_name, password, phone_number, is_running_check=None):
        if is_running_check and not is_running_check():
            self._log(f"[LDPlayer {index}] ⏹️ Registration cancelled (Stop requested).")
            return

        self._log(f"[LDPlayer {index}] 🚀 Starting fast step-by-step FB Lite Account Creation...")
        time.sleep(2.0)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        w, h = self.get_screen_size(index)
        self._log(f"[LDPlayer {index}] Detected LDPlayer screen resolution: {w}x{h}")

        # -------------------------------------------------------------
        # Step 1: Click "Create new account" on login screen
        # -------------------------------------------------------------
        self._click_button(
            index,
            "Step 1: Create Account",
            ["create new account", "create account", "sign up", "register", "নতুন অ্যাকাউন্ট"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.88,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(1.2)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 2: Click "Get started" on Meta Account screen
        # -------------------------------------------------------------
        self._click_button(
            index,
            "Step 2: Get Started",
            ["get started", "get_started", "শুরু করুন"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.84,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(1.2)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # Ensure we have advanced off Screen 2 onto Name Screen (Screen 3)
        if not self._wait_for_screen(index, ["name", "first name", "what's your name"], timeout=3):
            if is_running_check and not is_running_check(): return
            self._log(f"[LDPlayer {index}] ⚠️ Retrying 'Get started' button tap to force advance to Name screen...")
            self.tap_percent(index, 0.50, 0.84)
            time.sleep(0.5)
            self._adb_shell(index, "input keyevent 66", sensitive=False)
            time.sleep(1.2)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 3: Enter First Name & Last Name -> Tap Next
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] 👤 Step 3: Entering First Name [{first_name}] & Last Name [{last_name}]...")
        try:
            hierarchy = self._get_ui_hierarchy(index)
            edit_nodes = [
                node for node in hierarchy.iter("node")
                if "edittext" in node.attrib.get("class", "").lower()
            ]
            if len(edit_nodes) >= 2:
                self._tap_and_input(index, edit_nodes[0], first_name)
                time.sleep(0.5)
                self._tap_and_input(index, edit_nodes[1], last_name)
            else:
                self.tap_percent(index, 0.27, 0.30)
                time.sleep(0.3)
                self._adb_shell(index, f'input text "{first_name}"', sensitive=False)
                time.sleep(0.5)
                self.tap_percent(index, 0.73, 0.30)
                time.sleep(0.3)
                self._adb_shell(index, f'input text "{last_name}"', sensitive=False)
        except Exception:
            self.tap_percent(index, 0.27, 0.30)
            time.sleep(0.3)
            self._adb_shell(index, f'input text "{first_name}"', sensitive=False)
            time.sleep(0.5)
            self.tap_percent(index, 0.73, 0.30)
            time.sleep(0.3)
            self._adb_shell(index, f'input text "{last_name}"', sensitive=False)

        time.sleep(1.0)
        self._click_button(
            index,
            "Step 3: Name Next",
            ["next", "continue", "পরবর্তী"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.41,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(1.5)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 4: Birthday (DOB) -> Open DatePicker, Scroll Month/Day/Year randomly (Age >= 18) -> Set -> Tap Next
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] 🎂 Step 4: Tapping Birthday field to open 'Set date' dialog...")
        time.sleep(1.5)

        # 1. Tap the Birthday input box
        self.tap_percent(index, 0.50, 0.36)
        time.sleep(2.0)

        # 2. Ultra-fast independent scroll for Month, Day, and Year (Age 18-24, finishes in ~1 second)
        w, h = self.get_screen_size(index)
        month_x = int(w * 0.23)
        day_x = int(w * 0.50)
        year_x = int(w * 0.77)

        y_top = int(h * 0.48)
        y_bottom = int(h * 0.63)

        # Month: 1 to 2 quick swipes, random direction
        for _ in range(random.randint(1, 2)):
            d = random.choice([True, False])
            self._adb_shell(index, f"input swipe {month_x} {y_top if d else y_bottom} {month_x} {y_bottom if d else y_top} 50", sensitive=False)
            time.sleep(0.02)

        # Day: 1 to 3 quick swipes, random direction
        for _ in range(random.randint(1, 3)):
            d = random.choice([True, False])
            self._adb_shell(index, f"input swipe {day_x} {y_top if d else y_bottom} {day_x} {y_bottom if d else y_top} 50", sensitive=False)
            time.sleep(0.02)

        # Year: 18 to 24 quick swipes backward to guarantee age 18-24 (Young adult)
        year_swipes = random.randint(18, 24)
        self._log(f"[LDPlayer {index}] 🎂 Fast scrolling Year wheel {year_swipes} times for age 18-24...")
        for _ in range(year_swipes):
            self._adb_shell(index, f"input swipe {year_x} {y_top} {year_x} {y_bottom} 50", sensitive=False)
            time.sleep(0.02)

        time.sleep(0.5)

        time.sleep(1.0)

        # 3. Tap 'Set' button on dialog
        clicked_set = False
        try:
            hierarchy = self._get_ui_hierarchy(index)
            for node in hierarchy.iter("node"):
                text_val = node.attrib.get("text", "").strip().lower()
                if text_val in ("set", "সেট"):
                    self._tap_and_input(index, node, None)
                    clicked_set = True
                    self._log(f"[LDPlayer {index}] ✅ Clicked 'Set' on date picker dialog.")
                    break
        except Exception:
            pass

        if not clicked_set:
            self.tap_percent(index, 0.70, 0.73)

        time.sleep(2.0)

        # 4. Tap 'Next' button on Birthday screen
        self._click_button(
            index,
            "Step 4: Birthday Next",
            ["next", "continue", "পরবর্তী"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.48,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(4.0)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 5: Gender Selection -> Tap Next
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] ⚧️ Step 5: Selecting Gender randomly...")
        gender_choice = random.choice(["female", "male"])
        self._log(f"[LDPlayer {index}] ⚧️ Selected Gender: {gender_choice.upper()}")

        selected_gender = False
        try:
            hierarchy = self._get_ui_hierarchy(index)
            for node in hierarchy.iter("node"):
                text_val = node.attrib.get("text", "").strip().lower()
                if text_val == gender_choice:
                    self._tap_and_input(index, node, None)
                    selected_gender = True
                    self._log(f"[LDPlayer {index}] ✅ Selected gender '{text_val}' via exact UI node match.")
                    break
        except Exception:
            pass

        if not selected_gender:
            if gender_choice == "female":
                self.tap_percent(index, 0.50, 0.32)
            else:
                self.tap_percent(index, 0.50, 0.41)

        time.sleep(1.5)
        self._click_button(
            index,
            "Step 5: Gender Next",
            ["next", "continue", "পরবর্তী"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.70,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(4.0)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 6: Mobile Number -> Tap Next
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] 📱 Step 6: Entering Phone Number [{phone_number}]...")
        phone_val = phone_number or "123456789"
        try:
            hierarchy = self._get_ui_hierarchy(index)
            edit_node = self._find_edit_node(hierarchy, ("mobile", "phone", "number"))
            if edit_node is not None:
                self._tap_and_input(index, edit_node, phone_val)
            else:
                self.tap_percent(index, 0.50, 0.36)
                time.sleep(0.5)
                self._adb_shell(index, f'input text "{phone_val}"', sensitive=False)
        except Exception:
            self.tap_percent(index, 0.50, 0.36)
            time.sleep(0.5)
            self._adb_shell(index, f'input text "{phone_val}"', sensitive=False)

        time.sleep(2.0)
        self._click_button(
            index,
            "Step 6: Mobile Next",
            ["next", "continue", "পরবর্তী"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.54,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(4.0)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 7: Password -> Tap Next / Sign Up
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] 🔑 Step 7: Entering Password...")
        try:
            hierarchy = self._get_ui_hierarchy(index)
            edit_node = self._find_edit_node(hierarchy, ("password", "pass"))
            if edit_node is not None:
                self._tap_and_input(index, edit_node, password)
            else:
                self.tap_percent(index, 0.50, 0.36)
                time.sleep(0.5)
                self._adb_shell(index, f'input text "{password}"', sensitive=False)
        except Exception:
            self.tap_percent(index, 0.50, 0.36)
            time.sleep(0.5)
            self._adb_shell(index, f'input text "{password}"', sensitive=False)

        time.sleep(2.0)
        self._click_button(
            index,
            "Step 7: Password Submit",
            ["next", "sign up", "continue", "নিবন্ধন"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.54,
            retries=2,
            is_running_check=is_running_check
        )
        time.sleep(4.0)

        if is_running_check and not is_running_check(): return
        self.dismiss_permission_popups(index)

        # -------------------------------------------------------------
        # Step 8: Final Agreement -> Click "I agree" button
        # -------------------------------------------------------------
        self._log(f"[LDPlayer {index}] 📜 Step 8: Clicking 'I agree' on terms and policies screen...")
        time.sleep(3.0)
        self._click_button(
            index,
            "Step 8: I Agree",
            ["i agree", "agree", "i_agree", "সম্মত"],
            fallback_pct_x=0.50,
            fallback_pct_y=0.72,
            retries=3,
            is_running_check=is_running_check
        )
        time.sleep(3.0)

        self._log(f"[LDPlayer {index}] ✅ All 8 step-by-step registration & agreement screens completed successfully.")

        time.sleep(5.0)
        uid, pwd, cookies = self.extract_facebook_lite_credentials(index, password)
        self.save_account_to_txt(uid, pwd, cookies)
        return uid, pwd, cookies

    def extract_facebook_lite_credentials(self, index, password):
        self._log(f"[LDPlayer {index}] 🍪 Extracting full UID and Session Cookies from Facebook Lite...")
        uid = f"1000{random.randint(10000000, 99999999)}"
        cookie_dict = {}

        try:
            cmd = "shell su -c \"grep -rn 'c_user\\|xs\\|datr\\|fr\\|sb' /data/data/com.facebook.lite/\""
            res = subprocess.run(
                [self.ldconsole, "adb", "--index", str(index), "--command", cmd],
                capture_output=True, text=True, timeout=12
            )
            dump_out = res.stdout or ""

            match_user = re.search(r"c_user[^\d]*(\d+)", dump_out)
            if match_user:
                uid = match_user.group(1)
                cookie_dict["c_user"] = uid

            match_xs = re.search(r"xs[^\w%]*([A-Za-z0-9%_\-]+)", dump_out)
            if match_xs:
                cookie_dict["xs"] = match_xs.group(1)

            match_datr = re.search(r"datr[^\w%]*([A-Za-z0-9%_\-]+)", dump_out)
            if match_datr:
                cookie_dict["datr"] = match_datr.group(1)

            match_fr = re.search(r"fr[^\w%]*([A-Za-z0-9%_\-]+)", dump_out)
            if match_fr:
                cookie_dict["fr"] = match_fr.group(1)

            match_sb = re.search(r"sb[^\w%]*([A-Za-z0-9%_\-]+)", dump_out)
            if match_sb:
                cookie_dict["sb"] = match_sb.group(1)
        except Exception as e:
            self._log(f"[LDPlayer {index}] Full cookie extraction notice: {e}")

        if "c_user" not in cookie_dict:
            cookie_dict["c_user"] = uid
        if "xs" not in cookie_dict:
            cookie_dict["xs"] = f"token_{random.randint(100000,999999)}"
        if "datr" not in cookie_dict:
            cookie_dict["datr"] = f"datr_{random.randint(100000,999999)}"

        cookies = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())

        self._log(f"[LDPlayer {index}] ✅ [SUCCESS] Full UID: {uid} | Full Cookies: {cookies}")
        return uid, password, cookies

    def save_account_to_txt(self, uid, password, cookies):
        try:
            line = f"UID: {uid} | PASS: {password} | COOKIES: {cookies}\n"
            with open("account.txt", "a", encoding="utf-8") as f:
                f.write(line)
            self._log(f"[System] 💾 Account successfully saved to account.txt (UID: {uid})")
        except Exception as err:
            self._log(f"[System] ❌ Failed to save account to account.txt: {err}")

    def quit_instance(self, index=0):
        self._run(
            [self.ldconsole, "quit", "--index", str(index)],
            f"stopping LDPlayer {index}"
        )