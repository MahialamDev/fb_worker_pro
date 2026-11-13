import os
import random
import threading
import time
from services.ldplayer_service import LDPlayerService
from services.proxy_service import ProxyService
from services.api_service import ApiService

class AutomationService:
    def __init__(self, config, log_callback, table_callback):
        self.config = config
        self.log_callback = log_callback
        self.table_callback = table_callback
        self.ld_service = LDPlayerService(
            config.get("ldplayer_dir", "C:\\LDPlayer\\LDPlayer9"),
            log_callback
        )
        self.proxy_service = ProxyService(config)
        self.api_service = ApiService(config)
        self.is_running = False

    def _poll_otp_for_number(self, instance_idx, phone_number, timeout_seconds=180):
        start_time = time.time()
        self.log_callback(f"[Thread {instance_idx}] ⏳ OTP polling started for number: {phone_number}...")
        while time.time() - start_time < timeout_seconds and self.is_running:
            try:
                otps = self.api_service.get_success_otps()
                for item in otps:
                    number_str = str(item.get("number", ""))
                    if number_str == phone_number or (number_str and phone_number.endswith(number_str)):
                        otp_msg = item.get("message", "")
                        self.log_callback(f"[Thread {instance_idx}] ✅ OTP Received: {otp_msg} for {phone_number}")
                        self.table_callback(instance_idx + 1, "STATUS", f"OTP: {otp_msg}")

                        # Set both number and OTP to LDPlayer clipboard
                        clipboard_content = f"{phone_number} | OTP: {otp_msg}"
                        self.ld_service.set_clipboard(instance_idx, clipboard_content)
                        return otp_msg
            except Exception as e:
                self.log_callback(f"[Thread {instance_idx}] OTP polling notice: {e}")
            time.sleep(5)

        self.log_callback(f"[Thread {instance_idx}] ❌ OTP timeout for {phone_number}")
        return None

    def _get_name_for_instance(self, instance_idx):
        try:
            if os.path.exists("name_list.txt"):
                with open("name_list.txt", "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        full_name = random.choice(lines)
                        parts = full_name.split(" ", 1)
                        if len(parts) == 2:
                            return parts[0], parts[1]
                        return parts[0], "Smith"
        except Exception:
            pass
        first_names = ["Ethan", "Sophia", "Mason", "Harper", "Logan", "Emma", "Liam", "Olivia", "Noah", "Ava", "Lucas", "Mia"]
        last_names = ["Sullivan", "Weaver", "Caldwell", "Brooks", "Hayes", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]
        return random.choice(first_names), random.choice(last_names)

    def _open_app_in_background(self, instance_idx, package_name):
        if not self.is_running: return
        ld_service = LDPlayerService(
            self.config.get("ldplayer_dir", "C:\\LDPlayer\\LDPlayer9"),
            self.log_callback
        )
        try:
            self.table_callback(
                instance_idx + 1,
                "STATUS",
                "Clearing FB Lite data..."
            )
            ld_service.clear_app_data(instance_idx, package_name)
            if not self.is_running: return

            # 1. Resolve Range Country & Dynamic Proxy Region
            range_id = self.config.get("nez_range", "26134").strip()
            country_code = "us"
            try:
                range_details = self.api_service.resolve_range_details(range_id)
                country_code = range_details.get("country_code", "us")
                country_name = range_details.get("country", "USA")
                self.log_callback(f"[Thread {instance_idx}] Range [{range_id}] resolved to {country_name} ({country_code.upper()})")
            except Exception as err:
                self.log_callback(f"[Thread {instance_idx}] Range resolve notice: {err}")

            if not self.is_running: return

            if self.config.get("enable_proxy", True):
                try:
                    credentials = self.proxy_service.validate_credentials(country_code)
                    self.table_callback(
                        instance_idx + 1,
                        "STATUS",
                        f"Configuring Super Proxy ({country_code.upper()})..."
                    )
                    ld_service.configure_super_proxy(
                        instance_idx,
                        credentials
                    )
                except (OSError, RuntimeError, ValueError) as error:
                    self.log_callback(
                        f"[Thread {instance_idx}] Super Proxy Error: {error}"
                    )
                    self.table_callback(
                        instance_idx + 1,
                        "STATUS",
                        "Super Proxy Error"
                    )
            else:
                self.log_callback(f"[Thread {instance_idx}] ⏩ Super Proxy setup skipped (Checkbox unchecked). Directly opening FB Lite.")

            if not self.is_running: return

            self.table_callback(instance_idx + 1, "STATUS", "Opening FB Lite...")
            ld_service.open_app(instance_idx, package_name)
            self.table_callback(instance_idx + 1, "STATUS", "FB Lite Active")
            self.log_callback(f"[Thread {instance_idx}] সফলভাবে Facebook Lite ওপেন হয়েছে!")

            if not self.is_running: return

            phone_number = None
            try:
                self.table_callback(instance_idx + 1, "STATUS", f"Allocating Number [{range_id}]...")
                number_data = self.api_service.allocate_number(range_id)
                phone_number = number_data.get("no_plus_number")
                if phone_number:
                    self.log_callback(f"[Thread {instance_idx}] 📱 Allocated Number: {phone_number}")
                    self.table_callback(instance_idx + 1, "STATUS", f"Num: {phone_number}")
                    ld_service.set_clipboard(instance_idx, phone_number)

                    # Start Background OTP Polling Worker
                    otp_thread = threading.Thread(
                        target=self._poll_otp_for_number,
                        args=(instance_idx, phone_number),
                        daemon=True,
                        name=f"LDPlayer-{instance_idx}-otp"
                    )
                    otp_thread.start()
                else:
                    self.log_callback(f"[Thread {instance_idx}] ⚠️ Number allocation returned no number; continuing registration...")
            except Exception as num_err:
                self.log_callback(f"[Thread {instance_idx}] ⚠️ Number allocation notice: {num_err}")

            if not self.is_running: return

            # 3. Step-by-Step Account Creation Automation (Runs Unconditionally)
            first_name, last_name = self._get_name_for_instance(instance_idx)
            password = self.config.get("password", "AbirCvB1Yn@11")
            reg_result = ld_service.perform_fb_lite_registration(
                instance_idx,
                first_name,
                last_name,
                password,
                phone_number or "123456789",
                is_running_check=lambda: self.is_running
            )
            if reg_result:
                uid, pwd, cookies = reg_result
                self.table_callback(instance_idx + 1, "UID", uid)
                self.table_callback(instance_idx + 1, "PASSWORD", password)
                self.table_callback(instance_idx + 1, "STATUS", "Account Created")

        except Exception as e:
            self.log_callback(f"[Thread {instance_idx}] FB Lite Error: {str(e)}")
            self.table_callback(instance_idx + 1, "STATUS", "FB Lite Error")

    def run_single_thread(self, instance_idx, layout_indices=None):
        ld_service = LDPlayerService(
            self.config.get("ldplayer_dir", "C:\\LDPlayer\\LDPlayer9"),
            self.log_callback
        )
        try:
            if not self.is_running: return False

            self.table_callback(instance_idx + 1, "STATUS", f"Launching LD {instance_idx}...")
            self.log_callback(f"[Thread {instance_idx}] LDPlayer চালু হচ্ছে...")
            
            ld_service.launch_instance(instance_idx)
            layout_indices = layout_indices or [instance_idx]
            threading.Thread(
                target=self.ld_service.arrange_windows_once_when_visible,
                args=(layout_indices,),
                daemon=True,
                name=f"LDPlayer-{instance_idx}-layout"
            ).start()
            
            if not self.is_running: return False

            self.table_callback(instance_idx + 1, "STATUS", f"Booting LD {instance_idx}...")
            if not ld_service.wait_for_boot(instance_idx):
                self.table_callback(instance_idx + 1, "STATUS", "Boot Failed")
                return False

            if not self.is_running: return False

            self.table_callback(instance_idx + 1, "STATUS", "LDPlayer Ready")
            self.log_callback(f"[Thread {instance_idx}] boot complete; running app workflow.")

            self._open_app_in_background(instance_idx, self.config.get("fb_package", "com.facebook.lite"))
            return True

        except Exception as e:
            self.log_callback(f"[Thread {instance_idx}] Error: {str(e)}")
            self.table_callback(instance_idx + 1, "STATUS", "Error")
            return False

    def start_automation(self, thread_str):
        if self.is_running:
            self.log_callback("অটোমেশন ইতিমধ্যে চলছে।")
            return []

        self.is_running = True
        try:
            # যেমন: "1,2,3" ইনপুট দিলে [0, 1, 2] এমুলেটর ইনডেক্স ধরবে
            indices = [int(x.strip()) - 1 for x in thread_str.split(",") if x.strip().isdigit()]
        except Exception:
            indices = [0]

        def run_staggered_boot_sequence():
            for position, idx in enumerate(indices):
                if not self.is_running:
                    break

                self.log_callback(
                    f"[Thread {idx}] LDPlayer sequential launch & boot শুরু হচ্ছে "
                    f"({position + 1}/{len(indices)})।"
                )

                ld_service = LDPlayerService(
                    self.config.get("ldplayer_dir", "C:\\LDPlayer\\LDPlayer9"),
                    self.log_callback
                )
                try:
                    self.table_callback(idx + 1, "STATUS", f"Launching LD {idx}...")
                    ld_service.launch_instance(idx)

                    threading.Thread(
                        target=ld_service.arrange_windows_once_when_visible,
                        args=(indices[:position + 1],),
                        daemon=True,
                        name=f"LDPlayer-{idx}-layout"
                    ).start()

                    self.table_callback(idx + 1, "STATUS", f"Booting LD {idx}...")
                    if not ld_service.wait_for_boot(idx):
                        self.table_callback(idx + 1, "STATUS", "Boot Failed")
                        continue

                    if not self.is_running:
                        break

                    self.table_callback(idx + 1, "STATUS", "LDPlayer Ready")
                    self.log_callback(f"[Thread {idx}] boot complete; launching independent workflow thread.")

                    # Once booted, run app workflow & registration completely independently in parallel
                    threading.Thread(
                        target=self._open_app_in_background,
                        args=(idx, self.config.get("fb_package", "com.facebook.lite")),
                        daemon=True,
                        name=f"LDPlayer-{idx}-independent-workflow"
                    ).start()

                except Exception as e:
                    self.log_callback(f"[Thread {idx}] Startup error: {e}")
                    self.table_callback(idx + 1, "STATUS", "Error")

                # Pause 3 seconds between emulator boots to keep PC CPU/RAM pressure low
                if position < len(indices) - 1 and self.is_running:
                    time.sleep(3.0)

        thread = threading.Thread(
            target=run_staggered_boot_sequence,
            daemon=True,
            name="LDPlayer-staggered-sequence"
        )
        thread.start()
        return [thread]

    def stop_automation(self):
        self.is_running = False
        self.log_callback("অটোমেশন বন্ধ করা হয়েছে।")
