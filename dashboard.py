"""Desktop dashboard for the Anti-Performance Throttling Booster.

Run ``python dashboard.py`` on a Windows desktop.  The UI uses only Tkinter,
which is bundled with standard CPython, while all monitoring stays local.
"""

from __future__ import annotations

from collections import deque
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from detection.detector import detect_throttling, generate_recommendation, record_event
from logging_module.event_logger import EventLogger
from monitoring import NetworkMonitor, PerformanceMonitor
from optimization.optimization_engine import OptimizationEngine


BG = "#120d1f"
PANEL = "#20152f"
PANEL_ALT = "#2b1b40"
PURPLE = "#a855f7"
PURPLE_DARK = "#7133b3"
TEXT = "#f5efff"
MUTED = "#bca9d5"
WARNING = "#fbbf24"
ERROR = "#fb7185"
SUCCESS = "#6ee7b7"


class BoosterDashboard(tk.Tk):
    """Integrates SRS REQ-01 through REQ-23 in a local dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PulseBoost | Performance Monitor")
        self.geometry("1200x760")
        self.minsize(980, 650)
        self.configure(bg=BG)

        self.monitor = PerformanceMonitor(refresh_interval=1.0)
        self.network_monitor = NetworkMonitor()
        self.optimizer = OptimizationEngine()
        self.logger = EventLogger()
        self.cpu_history: deque[float] = deque(maxlen=5)
        self.memory_history: deque[float] = deque(maxlen=5)
        self.target_pid: int | None = None
        self.last_throttling_state = False
        self.rows_by_pid: dict[int, dict] = {}
        self.status_var = tk.StringVar(value="Monitoring stopped")
        self.cpu_var = tk.StringVar(value="--")
        self.memory_var = tk.StringVar(value="--")
        self.network_var = tk.StringVar(value="--")
        self.profile_var = tk.StringVar(value=self.optimizer.profile_manager.active_profile.name)
        self._configure_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabelframe", background=BG, foreground=TEXT, bordercolor=PURPLE_DARK)
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 10))
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 23))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Metric.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 24))
        style.configure("MetricTitle.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("TButton", background=PURPLE_DARK, foreground=TEXT, padding=(12, 7), font=("Segoe UI Semibold", 9))
        style.map("TButton", background=[("active", PURPLE)])
        style.configure("TCombobox", fieldbackground=PANEL_ALT, background=PURPLE_DARK, foreground=TEXT)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=27, borderwidth=0)
        style.configure("Treeview.Heading", background=PURPLE_DARK, foreground=TEXT, font=("Segoe UI Semibold", 9), relief="flat")
        style.map("Treeview", background=[("selected", PURPLE_DARK)], foreground=[("selected", TEXT)])

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="PulseBoost", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="Local performance monitoring and safe background-process optimization", style="Subtitle.TLabel").pack(anchor="w", pady=(0, 14))

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(0, 14))
        ttk.Button(actions, text="Start monitoring", command=self.start_monitoring).pack(side="left")
        ttk.Button(actions, text="Stop monitoring", command=self.stop_monitoring).pack(side="left", padx=8)
        self.status_label = ttk.Label(actions, textvariable=self.status_var, foreground=SUCCESS)
        self.status_label.pack(side="right")

        metrics = ttk.Frame(root)
        metrics.pack(fill="x", pady=(0, 14))
        for title, variable in (("CPU UTILIZATION", self.cpu_var), ("MEMORY UTILIZATION", self.memory_var), ("NETWORK DOWNLOAD", self.network_var)):
            card = ttk.Frame(metrics, style="Panel.TFrame", padding=16)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            ttk.Label(card, text=title, style="MetricTitle.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="Metric.TLabel").pack(anchor="w", pady=(7, 0))

        controls = ttk.Frame(root)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="Performance profile").pack(side="left")
        self.profile_box = ttk.Combobox(controls, textvariable=self.profile_var, state="readonly", width=18,
                                        values=[profile.name for profile in self.optimizer.profile_manager.list_profiles()])
        self.profile_box.pack(side="left", padx=8)
        self.profile_box.bind("<<ComboboxSelected>>", self._select_profile)
        ttk.Button(controls, text="Edit active profile", command=self.edit_profile).pack(side="left")
        ttk.Button(controls, text="Set selected as target", command=self.set_target).pack(side="right")
        ttk.Button(controls, text="Optimize selected", command=self.optimize_selected).pack(side="right", padx=8)

        tables = ttk.Panedwindow(root, orient="horizontal")
        tables.pack(fill="both", expand=True)
        process_panel = ttk.Labelframe(tables, text="  Processes  ", padding=8)
        alert_panel = ttk.Labelframe(tables, text="  Alerts and recent activity  ", padding=8)
        tables.add(process_panel, weight=3)
        tables.add(alert_panel, weight=2)
        columns = ("pid", "name", "cpu", "memory", "state")
        self.process_tree = ttk.Treeview(process_panel, columns=columns, show="headings", selectmode="browse")
        for column, heading, width in (("pid", "PID", 70), ("name", "Process", 180), ("cpu", "CPU %", 70), ("memory", "Memory MB", 95), ("state", "Status", 200)):
            self.process_tree.heading(column, text=heading)
            self.process_tree.column(column, width=width, anchor="w")
        self.process_tree.pack(fill="both", expand=True)
        self.activity = tk.Listbox(alert_panel, bg=PANEL, fg=TEXT, selectbackground=PURPLE_DARK, activestyle="none", borderwidth=0,
                                   font=("Segoe UI", 10), highlightthickness=0)
        self.activity.pack(fill="both", expand=True)
        self._refresh_logs()

    def start_monitoring(self) -> None:
        try:
            self.monitor.start_monitoring()
            self.network_monitor.start_monitoring()
        except RuntimeError as error:
            self._set_status(str(error), ERROR)
            return
        self.cpu_history.clear()
        self.memory_history.clear()
        self.last_throttling_state = False
        self._set_status("Monitoring active - refreshing every second", SUCCESS)
        self._refresh()

    def stop_monitoring(self) -> None:
        if not self.monitor.is_monitoring:
            self._set_status("Monitoring is already stopped", WARNING)
            return
        try:
            self.monitor.stop_monitoring()
            self.network_monitor.stop_monitoring()
        except RuntimeError as error:
            self._set_status(str(error), ERROR)
            return
        self._set_status("Monitoring stopped", MUTED)

    def _refresh(self) -> None:
        if not self.monitor.is_monitoring:
            return
        try:
            snapshot = self.monitor.collect_snapshot()
            network = self.network_monitor.get_network_stats()
            self.cpu_history.append(snapshot["cpu_percent"])
            self.memory_history.append(snapshot["memory_percent"])
            self.cpu_var.set(f"{snapshot['cpu_percent']:.1f}%")
            self.memory_var.set(f"{snapshot['memory_percent']:.1f}%")
            self.network_var.set(f"{network['download_speed_mb_per_second']:.2f} MB/s")
            self._render_processes(snapshot["processes"])
            self._evaluate_detection(snapshot)
            self._record_network_alerts(network["alerts"])
        except Exception as error:  # A dashboard must report monitoring errors, not silently stop.
            self._set_status(f"Monitoring error: {error}", ERROR)
        finally:
            if self.monitor.is_monitoring:
                self.after(int(self.monitor.refresh_interval * 1000), self._refresh)

    def _render_processes(self, processes: list[dict]) -> None:
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        rows = self.optimizer.get_process_analysis(processes, target_pid=self.target_pid)
        self.rows_by_pid = {row["pid"]: row for row in rows}
        for row in rows:
            state = "Target" if row["is_target"] else "Protected" if row["is_protected"] else "Eligible" if row["eligible_for_optimization"] else "Review"
            self.process_tree.insert("", "end", iid=str(row["pid"]), values=(row["pid"], row["name"], f"{row['cpu_percent']:.1f}", f"{row['memory_mb']:.0f}", state))

    def _evaluate_detection(self, snapshot: dict) -> None:
        throttled = len(self.cpu_history) == self.cpu_history.maxlen and detect_throttling(list(self.cpu_history), list(self.memory_history))
        if throttled and not self.last_throttling_state:
            process = max(snapshot["processes"], key=lambda row: row["cpu_percent"], default={"name": "Unknown", "cpu_percent": 0, "memory_mb": 0})
            event = record_event(list(self.cpu_history), list(self.memory_history), process["name"], process["cpu_percent"], process["memory_percent"])
            recommendation = generate_recommendation(snapshot["cpu_percent"], snapshot["memory_percent"])
            self.logger.log_throttling_event("Suspected performance throttling detected.", source="dashboard", details={"event": event, "recommendation": recommendation})
            self._add_activity(f"Warning: {recommendation}")
        self.last_throttling_state = throttled

    def _record_network_alerts(self, alerts: list[dict]) -> None:
        for alert in alerts:
            self.logger.log_event(alert["event_type"], alert["message"], source="network_monitor", details=alert)
            self._add_activity(f"Network alert: {alert['message']}")

    def _selected_pid(self) -> int | None:
        selection = self.process_tree.selection()
        return int(selection[0]) if selection else None

    def set_target(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            self._set_status("Select a process to use as the target workload", WARNING)
            return
        self.target_pid = pid
        self._set_status(f"Target workload set to {self.rows_by_pid[pid]['name']} ({pid})", SUCCESS)

    def optimize_selected(self) -> None:
        pid = self._selected_pid()
        if pid is None or pid not in self.rows_by_pid:
            self._set_status("Select a current process before optimizing", WARNING)
            return
        row = self.rows_by_pid[pid]
        if not messagebox.askyesno("Confirm safe optimization", f"Lower priority for {row['name']} (PID {pid})?\n\nThe target process and protected system processes cannot be changed."):
            return
        result = self.optimizer.optimize_process(pid, list(self.rows_by_pid.values()), confirmed=True, target_pid=self.target_pid)
        self.logger.log_optimization_action(result["message"], source="dashboard", details=result)
        color = SUCCESS if result["success"] else ERROR if result["status"] == "failed" else WARNING
        self._set_status(result["message"], color)
        self._add_activity(f"Optimization: {result['message']}")

    def _select_profile(self, _event=None) -> None:
        self.optimizer.profile_manager.select_profile(self.profile_var.get())
        self._set_status(f"Active profile: {self.profile_var.get()}", SUCCESS)

    def edit_profile(self) -> None:
        profile = self.optimizer.profile_manager.active_profile
        cpu = simpledialog.askfloat("CPU threshold", "CPU threshold (%)", initialvalue=profile.cpu_threshold_percent, minvalue=0.1, maxvalue=100.0, parent=self)
        if cpu is None:
            return
        memory = simpledialog.askfloat("Memory threshold", "Memory threshold (MB)", initialvalue=profile.memory_threshold_mb, minvalue=1.0, parent=self)
        if memory is None:
            return
        actions = simpledialog.askinteger("Action limit", "Maximum priority changes per session", initialvalue=profile.max_actions, minvalue=1, maxvalue=10, parent=self)
        if actions is None:
            return
        self.optimizer.profile_manager.update_profile(profile.name, cpu_threshold_percent=cpu, memory_threshold_mb=memory, max_actions=actions)
        self._set_status("Profile saved", SUCCESS)

    def _refresh_logs(self) -> None:
        self.activity.delete(0, tk.END)
        for item in self.logger.get_recent_logs(limit=12):
            self.activity.insert(tk.END, f"{item['event_type']}: {item['message']}")

    def _add_activity(self, message: str) -> None:
        self.activity.insert(tk.END, message)
        self.activity.yview_moveto(1)

    def _set_status(self, message: str, color: str) -> None:
        self.status_var.set(message)
        self.status_label.configure(foreground=color)

    def _on_close(self) -> None:
        if self.monitor.is_monitoring:
            self.stop_monitoring()
        self.destroy()


if __name__ == "__main__":
    BoosterDashboard().mainloop()
