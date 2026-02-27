import unittest
from unittest.mock import Mock, MagicMock
from browser_manager import BrowserManager

class TestBrowserManager(unittest.TestCase):

    def setUp(self):
        self.mock_browser = Mock()
        self.mock_log = Mock()
        self.manager = BrowserManager(self.mock_browser, self.mock_log)

    def test_select_standard_category(self):
        """Test selecting a standard category like audio_effects"""
        self.mock_browser.audio_effects = Mock()
        result = self.manager.select_category('audio_effects')
        self.assertTrue(result)
        self.assertEqual(self.manager.current_category, 'audio_effects')
        self.assertIsNotNone(self.manager.current_item)
        self.mock_log.assert_called()

    def test_select_vector_category(self):
        """Test selecting a vector category like user_folders"""
        # user_folders shouldn't set a current_item, it's a list directly handled by get_children
        result = self.manager.select_category('user_folders')
        self.assertTrue(result)
        self.assertEqual(self.manager.current_category, 'user_folders')
        self.assertIsNone(self.manager.current_item)
        self.mock_log.assert_called()

    def test_select_colors_vector_category(self):
        """Test selecting the colors vector category"""
        result = self.manager.select_category('colors')
        self.assertTrue(result)
        self.assertEqual(self.manager.current_category, 'colors')
        self.assertIsNone(self.manager.current_item)

    def test_navigate_up_at_root(self):
        """Test navigating up when already at root"""
        self.manager.current_item = None
        self.manager.navigation_path = []
        result = self.manager.navigate_up()
        self.assertTrue(result)
        self.mock_log.assert_called_with("Already at root")

    def test_navigate_up_from_subfolder(self):
        """Test navigating up from a subfolder"""
        parent_item = Mock()
        child_item = Mock()
        self.manager.navigation_path = [parent_item]
        self.manager.current_item = child_item
        self.manager.selected_index = 5

        result = self.manager.navigate_up()

        self.assertTrue(result)
        self.assertEqual(self.manager.current_item, parent_item)
        self.assertEqual(len(self.manager.navigation_path), 0)
        self.assertEqual(self.manager.selected_index, 0)

    def test_navigate_next(self):
        """Test navigating to next item"""
        self.manager.selected_index = 0
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [Mock(), Mock(), Mock()]
        self.manager.select_category('audio_effects')

        new_index = self.manager.navigate_next()

        self.assertEqual(new_index, 1)
        self.assertEqual(self.manager.selected_index, 1)

    def test_navigate_next_at_end(self):
        """Test navigating next when already at last item"""
        self.manager.selected_index = 2
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [Mock(), Mock(), Mock()]
        self.manager.select_category('audio_effects')

        new_index = self.manager.navigate_next()

        self.assertEqual(new_index, 2)  # Should stay at last item

    def test_navigate_prev(self):
        """Test navigating to previous item"""
        self.manager.selected_index = 2
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [Mock(), Mock(), Mock()]
        self.manager.select_category('audio_effects')

        new_index = self.manager.navigate_prev()

        self.assertEqual(new_index, 1)
        self.assertEqual(self.manager.selected_index, 1)

    def test_navigate_prev_at_start(self):
        """Test navigating prev when already at first item"""
        self.manager.selected_index = 0
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [Mock(), Mock(), Mock()]
        self.manager.select_category('audio_effects')

        new_index = self.manager.navigate_prev()

        self.assertEqual(new_index, 0)  # Should stay at first item

    def test_navigate_down_to_folder(self):
        """Test navigating down into a folder"""
        parent_item = Mock()
        folder_item = Mock()
        folder_item.is_folder = True

        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [folder_item]
        self.manager.select_category('audio_effects')
        self.manager.selected_index = 0

        result = self.manager.navigate_down(0)

        self.assertTrue(result)
        self.assertEqual(self.manager.current_item, folder_item)
        self.assertEqual(self.manager.selected_index, 0)

    def test_navigate_down_to_device(self):
        """Test navigating down to a device (should fail)"""
        device_item = Mock()
        device_item.is_folder = False

        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [device_item]
        self.manager.select_category('audio_effects')

        result = self.manager.navigate_down(0)

        self.assertFalse(result)

    def test_get_children_standard_category(self):
        """Test getting children from standard category"""
        mock_child1 = Mock()
        mock_child2 = Mock()
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [mock_child1, mock_child2]
        self.manager.select_category('audio_effects')

        children = self.manager.get_children()

        self.assertEqual(len(children), 2)
        self.assertIn(mock_child1, children)
        self.assertIn(mock_child2, children)

    def test_get_children_vector_category(self):
        """Test getting children from vector category"""
        mock_folder1 = Mock()
        mock_folder2 = Mock()
        self.mock_browser.user_folders = [mock_folder1, mock_folder2]
        self.manager.select_category('user_folders')

        children = self.manager.get_children()

        self.assertEqual(len(children), 2)
        self.assertIn(mock_folder1, children)
        self.assertIn(mock_folder2, children)

    def test_get_children_subfolder(self):
        """Test getting children from a subfolder"""
        parent_item = Mock()
        child1 = Mock()
        child2 = Mock()
        parent_item.children = [child1, child2]

        self.manager.current_item = parent_item
        self.manager.navigation_path = []

        children = self.manager.get_children()

        self.assertEqual(len(children), 2)
        self.assertIn(child1, children)
        self.assertIn(child2, children)

    def test_get_selected_item(self):
        """Test getting the currently selected item"""
        mock_item1 = Mock()
        mock_item2 = Mock()
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [mock_item1, mock_item2]
        self.manager.select_category('audio_effects')
        self.manager.selected_index = 1

        selected = self.manager.get_selected_item()

        self.assertEqual(selected, mock_item2)

    def test_get_selected_item_out_of_range(self):
        """Test getting selected item when index is out of range"""
        mock_item = Mock()
        self.mock_browser.audio_effects = Mock()
        self.mock_browser.audio_effects.children = [mock_item]
        self.manager.select_category('audio_effects')
        self.manager.selected_index = 5

        selected = self.manager.get_selected_item()

        self.assertIsNone(selected)

    def test_get_category_index_map(self):
        """Test the category index map"""
        category_map = self.manager.get_category_index_map()

        self.assertEqual(category_map[0], 'audio_effects')
        self.assertEqual(category_map[1], 'instruments')
        self.assertEqual(category_map[11], 'user_folders')
        self.assertEqual(category_map[12], 'colors')

    def test_shortcut_traversal(self):
        """Test shortcut traversal to a specific path"""
        root = Mock()
        folder1 = Mock()
        folder1.name = "Dynamics"
        folder1.is_folder = True

        folder2 = Mock()
        folder2.name = "Compressor"
        folder2.is_folder = True

        root.children = [folder1]
        folder1.children = [folder2]

        self.mock_browser.audio_effects = root

        # Action
        result = self.manager.navigate_to_path('audio_effects', ['Dynamics', 'Compressor'])

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.manager.current_item, folder2)
        self.assertEqual(self.manager.current_category, 'audio_effects')

    def test_shortcut_traversal_invalid_category(self):
        """Test shortcut traversal with invalid category"""
        result = self.manager.navigate_to_path('invalid_category', [])

        self.assertFalse(result)

    def test_get_current_path_names(self):
        """Test getting current path names"""
        folder1 = Mock()
        folder1.name = "Effects"
        folder2 = Mock()
        folder2.name = "Dynamics"

        self.manager.navigation_path = [folder1, folder2]
        self.manager.current_item = Mock()

        path_names = self.manager.get_current_path_names()

        self.assertEqual(len(path_names), 2)
        self.assertEqual(path_names[0], "Effects")
        self.assertEqual(path_names[1], "Dynamics")

    def test_load_selected_item_success(self):
        """Test loading selected item"""
        mock_item = Mock()
        mock_item.is_loadable = True
        self.mock_browser.load_item = Mock()

        self.manager.current_item = mock_item
        self.manager.selected_index = 0
        self.manager.get_children = Mock(return_value=[mock_item])

        result = self.manager.load_selected_item()

        self.assertTrue(result)
        self.mock_browser.load_item.assert_called_once_with(mock_item)

    def test_load_selected_item_not_loadable(self):
        """Test loading non-loadable item"""
        mock_item = Mock()
        mock_item.is_loadable = False

        self.manager.current_item = mock_item
        self.manager.get_children = Mock(return_value=[mock_item])

        result = self.manager.load_selected_item()

        self.assertFalse(result)

    def test_preview_selected_item(self):
        """Test previewing selected item"""
        mock_item = Mock()
        mock_item.is_loadable = True
        self.mock_browser.preview_item = Mock()

        self.manager.current_item = mock_item
        self.manager.get_children = Mock(return_value=[mock_item])

        result = self.manager.preview_selected_item()

        self.assertTrue(result)
        self.mock_browser.preview_item.assert_called_once_with(mock_item)

    def test_stop_preview(self):
        """Test stopping preview"""
        self.mock_browser.stop_preview = Mock()

        self.manager.stop_preview()

        self.mock_browser.stop_preview.assert_called_once()


if __name__ == '__main__':
    unittest.main()
