import logging
import threading
import time
import importlib
import os
import traceback
from typing import Any, Dict, List
from Matrix.models.Commands import CommandEntry, CommandExecutionLog, ScheduleModel
from Matrix.driver.base_executor import BaseCommandExecutor, synchronized_method
from Matrix.driver.scheduler import Scheduler
from Matrix.driver.ipc.server import IPCServer
from Matrix.driver.utilz import configure_log, CYAN
from Matrix.config import is_ipc_enabled
from Matrix.driver import power
from Matrix.driver.monitor import cpu_governor
from Matrix.driver.commands.msg_stack import get_message_stack
from Matrix.driver.monitor import probe

MAX_AUDIT_SIZE = 100
BUSY_WAIT = 0.1
WATCHDOG_WAIT = 120

logger: logging.Logger = logging.getLogger(__name__)
configure_log(logger, CYAN, "CmdExec", level=logging.INFO)

DISPLAY_SPLASH: bool = True
WATCHDOG_ON: bool = True


class CommandExecutor(BaseCommandExecutor, IPCServer):
    def __init__(self, schedule_file: str | None = "schedule.json", no_watchdog: bool = False, no_splash: bool = False) -> None:
        # Turn on the LED Panel power supply
        power.on()

        # Load commands (now fixed)
        self.commands: dict[str, Any] = self._load_commands()

        # Initialize scheduler and load playlists
        self.scheduler = Scheduler(schedule_file=schedule_file)

        if DISPLAY_SPLASH and not no_splash:
            self.scheduler.append_next(
                CommandEntry(command_name="splash", duration=6, args=[], kwargs={})
            )

        self.stop_current = threading.Event()
        self.stop_scheduler = threading.Event()
        self.stop_watchdog = threading.Event()

        logger.info("starting schedule thread")
        # self.schedule_thread: threading.Thread | None = threading.Thread(target=self._scheduler_loop, args=())
        self.schedule_thread.start()

        self.sleep_mode_activated: bool = False
        if WATCHDOG_ON and not no_watchdog:
            logger.info("starting watchdog thread")
            self.watchdog_thread: threading.Thread | None = threading.Thread(target=self._watchdog_loop, args=())
            self.watchdog_thread.start()

        self.audit_log: list[CommandExecutionLog] = []
        self.execution_counter = 0
        self.current_command: CommandEntry | None = None

    def _load_commands(self) -> dict:
        """
        Dynamically loads all commands from the 'commands' directory.
        """
        commands: dict[str, Any] = {}
        current_directory: str = self.get_current_directory()
        commands_dir = os.path.join(current_directory, "commands")

        for file in os.listdir(commands_dir):
            if file.endswith("_cmd.py") and file != "base.py":
                try:
                    module_name: str = file[:-3]
                    module = importlib.import_module(f"Matrix.driver.commands.{module_name}")
                    class_name: str = f"{file[:-7].capitalize()}Cmd"
                    command_class = getattr(module, class_name)
                    command_instance = command_class()
                    commands[command_instance.name] = command_instance
                except Exception as e:
                    logger.error(f"ERROR >> Unable to load command {module_name}: {e}")
                    logger.error(traceback.format_exc())

        return commands

    # ✅ Implement missing abstract methods with placeholders
    def connected(self) -> bool:
        return True

    def list_commands(self) -> list[str]:
        return list(self.commands.keys())

    def get_commands(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for name in self.commands:
            res: dict[str, Any] | None = self.get_command(name)
            if res:
                result.append(res)
        return result

    def get_command(self, name: str) -> dict[str, Any] | None:
        cmd = self.commands.get(name, None)
        if cmd:
            return {
                "name": cmd.name,
                "description": cmd.description,
                "screenshots": cmd.get_screenshots(),
                "recommended_duration": cmd.get_recommended_duration()
            }
        return None

    def get_command_screenshot(self, name: str, screenshot_name: str) -> str:
        return ""

    def list_schedules(self) -> list[str]:
        return self.scheduler.get_playlist_names()

    def get_schedule(self, playlist_name: str | None = None) -> ScheduleModel | None:
        if playlist_name is None:
            return self.scheduler.get_current_stack()
        else:
            return self.scheduler.get_playlist(playlist_name)

    def set_schedule(self, schedule: ScheduleModel, playlist_name: str | None = None) -> None:
        if playlist_name is not None:
            self.scheduler.save_playlist(schedule, playlist_name)
        else:
            self.scheduler.update_current_stack(schedule)

    def get_current_command(self) -> str | None:
        return self.current_command.command_name if self.current_command else None

    def play_schedule(self, playlist_name: str | None) -> None:
        self.scheduler.load_playlist(playlist_name)

    def send_command_message(self, command_name: str, message: str) -> str | None:
        msg: dict[str, str] = {"command_name": command_name, "message": message}
        get_message_stack().push(msg)
        return None

    def execute_now(
        self,
        command_name: str,
        duration: float,
        interrupt: bool = False,
        args: list = [],
        kwargs: dict = {},
    ) -> None:
        try:
            self.scheduler.append_next(
                CommandEntry(command_name=command_name, duration=duration, args=args, kwargs=kwargs)
            )
            if interrupt:
                self.stop_current.set()
        except Exception as e:
            logger.error(f"Error executing {command_name}: {str(e)}")
            logger.error(traceback.format_exc())

    def save_schedule(self) -> None:
        pass

    def stop(self, interrupt: bool = False) -> None:
        logger.info("Stop request received")
        self.stop_scheduler.set()
        self.stop_watchdog.set()
        time.sleep(BUSY_WAIT * 5)
        if interrupt:
            self.stop_current.set()
            time.sleep(BUSY_WAIT * 5)

        if self.schedule_thread and self.schedule_thread.is_alive():
            self.schedule_thread.join(timeout=2)
        logger.info("Scheduler shutdown completed, exiting")

    def sleep(self) -> None:
        logger.info("Entering Sleep mode")
        self.stop_scheduler.set()
        time.sleep(BUSY_WAIT * 5)
        self.stop_current.set()
        time.sleep(BUSY_WAIT * 5)

        if self.schedule_thread and self.schedule_thread.is_alive():
            self.schedule_thread.join(timeout=2)
        self.schedule_thread = None

        from Matrix.driver.commands.base import release_matrix_singleton
        release_matrix_singleton()
        power.off()
        cpu_governor.set_cpu_sleep_mode()
        self.sleep_mode_activated = True

    def wakeup(self) -> None:
        if not self.sleep_mode_activated:
            logger.error("Calling Wakeup while Sleep mode is not active...")
        power.on()
        cpu_governor.set_cpu_normal_mode()
        self.stop_scheduler.clear()
        self.stop_current.clear()

        if not self.schedule_thread:
            self.schedule_thread = threading.Thread(target=self._scheduler_loop, args=())
            self.schedule_thread.start()

        self.sleep_mode_activated = False

    def get_metrics(self) -> dict[str, Any] | None:
        metrics: dict[str, Any] = probe.all_metrics()
        metrics["watchdog_on"] = WATCHDOG_ON
        metrics["sleeping"] = self.sleep_mode_activated
        return metrics

    def watchdog(self, expected_state: bool | None = None) -> bool:
        global WATCHDOG_ON
        if expected_state is not None:
            WATCHDOG_ON = expected_state
        return WATCHDOG_ON


