import threading
import time
from services.ldplayer_service import LDPlayerService

class WorkerEngine:
    def __init__(self, config, status_callback, log_callback, table_update_callback):
        self.config = config
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.table_update_callback = table_update_callback
        self.is_running = False
        self.ld_service = LDPlayerService(
            config.get("ldplayer_dir", "C:\\LDPlayer\\LDPlayer9"),
            log_callback
        )

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        thread = threading.Thread(target=self.run_workflow, daemon=True)
        thread.start()

    def stop(self):
        self.is_running = False
        self.status_callback("SYSTEM READY", "#95a5a6")
        self.log_callback("ইঞ্জিন বন্ধ করা হয়েছে।")

    def run_workflow(self):
        try:
            self.status_callback("ENGINE RUNNING", "#2ecc71")
            self.log_callback("অটোমেশন ইঞ্জিন শুরু হয়েছে...")

            index = 0  # ডিফল্ট ইনস্ট্যান্স ইনডেক্স
            package_name = self.config.get("fb_package", "com.facebook.lite")

            # ধাপ ১: LDPlayer ওপেন করা
            self.table_update_callback(1, "STATUS", "Launching LDPlayer...")
            self.log_callback(f"LDPlayer (Index: {index}) চালু করা হচ্ছে...")
            self.ld_service.launch_instance(index)

            if not self.is_running:
                return

            # ধাপ ২: বুট হওয়া পর্যন্ত অপেক্ষা
            self.table_update_callback(1, "STATUS", "Booting Android...")
            self.log_callback("অ্যান্ড্রয়েড সিস্টেম বুট হওয়ার জন্য অপেক্ষা করা হচ্ছে...")
            booted = self.ld_service.wait_for_boot(index)

            if not booted:
                self.log_callback("Error: LDPlayer বুট হতে ব্যর্থ হয়েছে।")
                self.table_update_callback(1, "STATUS", "Boot Failed")
                self.stop_cleanup()
                return

            if not self.is_running:
                return

            # ধাপ ৩: Facebook Lite ওপেন করা
            self.table_update_callback(1, "STATUS", "Opening FB Lite...")
            self.log_callback(f"অ্যাপ ওপেন করা হচ্ছে: {package_name}")
            self.ld_service.open_app(index, package_name)
            time.sleep(3)

            self.table_update_callback(1, "STATUS", "FB Lite Opened")
            self.log_callback("সফলভাবে Facebook Lite ওপেন হয়েছে!")

        except Exception as e:
            self.log_callback(f"Error: {str(e)}")
            self.table_update_callback(1, "STATUS", "Error")
        finally:
            self.stop_cleanup()

    def stop_cleanup(self):
        self.is_running = False
        self.status_callback("SYSTEM READY", "#95a5a6")