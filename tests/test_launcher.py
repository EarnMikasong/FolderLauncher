import tempfile
import unittest
from pathlib import Path

from folder_launcher.launcher import FolderLauncher, command_line
from folder_launcher.models import AppConfig, Category, CommandProfile, FolderEntry


class LauncherTests(unittest.TestCase):
    def test_continue_argument_is_optional(self) -> None:
        profile = CommandProfile("claude", "Claude", "claude", ["--debug"], True)
        self.assertEqual(command_line(profile, False), "claude --debug")
        self.assertEqual(command_line(profile, True), "claude --debug --continue")

    def test_launch_opens_explorer_and_terminal(self) -> None:
        start_calls: list[str] = []
        process_calls: list[tuple[tuple, dict]] = []

        def fake_startfile(path: str) -> None:
            start_calls.append(path)

        def fake_popen(*args, **kwargs):
            process_calls.append((args, kwargs))
            return object()

        with tempfile.TemporaryDirectory() as directory:
            entry = FolderEntry(
                "folder",
                "Project",
                directory,
                "category",
                command_id="agy",
                continue_session=True,
            )
            config = AppConfig(
                categories=[Category("category", "Work")],
                commands=[CommandProfile("agy", "Agy", "agy", supports_continue=True)],
                folders=[entry],
            )
            message = FolderLauncher(fake_startfile, fake_popen).launch(entry, config)

        self.assertEqual(start_calls, [str(Path(directory))])
        self.assertEqual(process_calls[0][0][0][-1], "agy --continue")
        self.assertIn("Agy --continue", message)


if __name__ == "__main__":
    unittest.main()
