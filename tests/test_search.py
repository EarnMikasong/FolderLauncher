import unittest

from folder_launcher.models import AppConfig, Category, FolderEntry
from folder_launcher.search import search_categories, search_folders


def build_config() -> AppConfig:
    return AppConfig(
        categories=[
            Category("java", "Java 项目", [r"D:\java"]),
            Category("web", "Web 前端", [r"D:\web"]),
            Category("tools", "工具", [r"D:\tools"]),
        ],
        folders=[
            FolderEntry("a", "Java Sandbox", r"D:\java\sandbox", "java"),
            FolderEntry("b", "MyJava Tool", r"D:\tools\myjava", "tools"),
            FolderEntry("c", "Notes", r"D:\java\docs\notes", "java"),
            FolderEntry("d", "Portal", r"D:\web\portal", "web"),
            FolderEntry("e", "Extra", r"D:\java\extra", "java"),
        ],
    )


class FolderSearchTests(unittest.TestCase):
    def test_name_substring_hit(self) -> None:
        results = search_folders(build_config(), "sand")
        self.assertEqual([entry.id for entry in results], ["a"])

    def test_case_insensitive(self) -> None:
        results = search_folders(build_config(), "JAVA")
        self.assertEqual([entry.id for entry in results], ["a", "b", "e", "c"])

    def test_multiple_tokens_require_all(self) -> None:
        self.assertEqual([entry.id for entry in search_folders(build_config(), "java notes")], ["c"])
        self.assertEqual(search_folders(build_config(), "java portal"), [])

    def test_path_only_hit(self) -> None:
        results = search_folders(build_config(), "docs")
        self.assertEqual([entry.id for entry in results], ["c"])

    def test_name_prefix_sorts_before_path_only(self) -> None:
        results = search_folders(build_config(), "java")
        self.assertEqual([entry.id for entry in results], ["a", "b", "e", "c"])

    def test_no_match_returns_empty(self) -> None:
        self.assertEqual(search_folders(build_config(), "kotlin"), [])

    def test_empty_query_returns_empty(self) -> None:
        self.assertEqual(search_folders(build_config(), ""), [])
        self.assertEqual(search_folders(build_config(), "   "), [])


class CategorySearchTests(unittest.TestCase):
    def test_search_categories_basic_hit(self) -> None:
        self.assertEqual([item.id for item in search_categories(build_config(), "java")], ["java"])
        self.assertEqual([item.id for item in search_categories(build_config(), "web")], ["web"])
        self.assertEqual([item.id for item in search_categories(build_config(), "tools")], ["tools"])
        self.assertEqual(search_categories(build_config(), "php"), [])

    def test_empty_query_returns_empty(self) -> None:
        self.assertEqual(search_categories(build_config(), "  "), [])


if __name__ == "__main__":
    unittest.main()
