import unittest

from folder_launcher.hierarchy import build_category_tree, is_same_or_descendant, suggest_category
from folder_launcher.models import Category, FolderEntry


class HierarchyTests(unittest.TestCase):
    def test_windows_paths_are_case_insensitive(self) -> None:
        self.assertTrue(is_same_or_descendant(r"D:\Claude\Project", r"d:\claude"))
        self.assertFalse(is_same_or_descendant(r"D:\Claude2", r"D:\Claude"))

    def test_longest_prefix_wins(self) -> None:
        categories = [
            Category("broad", "D drive", ["D:\\"]),
            Category("specific", "Work", [r"D:\work"]),
        ]
        self.assertEqual(suggest_category(r"D:\work\project", categories), "specific")

    def test_tree_uses_nearest_registered_parent(self) -> None:
        entries = [
            FolderEntry("root", "Claude", r"D:\claude", "cat"),
            FolderEntry("filter", "Filter", r"D:\claude\geektime\filter", "cat"),
            FolderEntry("mysql", "MySQL", r"D:\claude\geektime\filter\mysql", "cat"),
            FolderEntry("other", "Other", r"D:\other", "cat"),
        ]

        roots = build_category_tree(entries, "cat")

        self.assertEqual([item.entry.id for item in roots], ["root", "other"])
        self.assertEqual(roots[0].children[0].entry.id, "filter")
        self.assertEqual(roots[0].children[0].children[0].entry.id, "mysql")


if __name__ == "__main__":
    unittest.main()
