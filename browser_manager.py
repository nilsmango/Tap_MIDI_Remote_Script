"""
BrowserManager Module
Handles navigation and state management for Ableton Live browser.
"""

from Live.Browser import Browser, BrowserItem
from ableton.v2.base import liveobj_valid

class BrowserManager:
    """
    Manages browser navigation state and Live API interactions.
    Object caching is intentionally omitted to prevent C++ destruction crashes.
    """

    def __init__(self, browser, log_message):
        self.browser = browser
        self.log_message = log_message

        self.current_item = None
        self.navigation_path = []
        self.selected_index = 0
        self.current_category = None

        self.category_roots = {
            'audio_effects': self.browser.audio_effects,
            'instruments': self.browser.instruments,
            'midi_effects': self.browser.midi_effects,
            'max_for_live': self.browser.max_for_live,
            'drums': self.browser.drums,
            'samples': self.browser.samples,
            'sounds': self.browser.sounds,
            'packs': self.browser.packs,
            'plugins': self.browser.plugins,
            'user_library': self.browser.user_library,
            'current_project': self.browser.current_project,
        }

    def select_category(self, category_name):
        """Switch to a root category, handling vectors safely."""
        self.current_category = category_name
        self.navigation_path = []
        self.selected_index = 0

        if category_name in ['user_folders', 'colors']:
            # For vectors, current_item remains None at the root level.
            # get_children() will return the vector list.
            self.current_item = None
            self.log_message(f"Selected vector category: {category_name}")
            return True

        if category_name in self.category_roots:
            self.current_item = self.category_roots[category_name]
            self.log_message(f"Selected standard category: {category_name}")
            return True

        self.log_message(f"Category not found: {category_name}")
        return False

    def navigate_up(self):
        if not self.navigation_path:
            # Already at root of category (or vector root)
            self.current_item = None
            self.selected_index = 0
            self.log_message("Already at root")
            return True

        self.navigation_path.pop()
        if self.navigation_path:
            self.current_item = self.navigation_path[-1]
        else:
            self.select_category(self.current_category)

        self.selected_index = 0
        return True

    def navigate_down(self, index):
        children = self.get_children()
        if index < 0 or index >= len(children):
            return False

        target_item = children[index]
        if not getattr(target_item, 'is_folder', False):
            return False

        if self.current_item:
            self.navigation_path.append(self.current_item)

        self.current_item = target_item
        self.selected_index = 0
        return True

    def navigate_next(self):
        children = self.get_children()
        if children:
            self.selected_index = min(self.selected_index + 1, len(children) - 1)
        return self.selected_index

    def navigate_prev(self):
        children = self.get_children()
        if children:
            self.selected_index = max(self.selected_index - 1, 0)
        return self.selected_index

    def get_children(self):
        """Dynamically fetch children to avoid dangling references."""
        if self.current_item is None:
            if self.current_category == 'user_folders':
                return list(self.browser.user_folders)
            elif self.current_category == 'colors':
                return list(self.browser.colors)
            elif self.current_category in self.category_roots:
                return list(self.category_roots[self.current_category].children)
            return []

        try:
            return list(self.current_item.children)
        except Exception as e:
            self.log_message(f"Error getting children: {e}")
            return []

    def get_selected_item(self):
        children = self.get_children()
        if 0 <= self.selected_index < len(children):
            return children[self.selected_index]
        return None

    def load_selected_item(self):
        selected = self.get_selected_item()
        if not selected or not getattr(selected, 'is_loadable', False):
            return False
        try:
            self.browser.load_item(selected)
            return True
        except Exception as e:
            self.log_message(f"Load error: {e}")
            return False

    def preview_selected_item(self):
        selected = self.get_selected_item()
        if selected and getattr(selected, 'is_loadable', False):
            try:
                self.browser.preview_item(selected)
                return True
            except:
                pass
        return False

    def stop_preview(self):
        try:
            self.browser.stop_preview()
        except:
            pass

    def navigate_to_path(self, category_name, path_names):
        """Instantly traverses a path requested by the iOS Shortcut system."""
        if not self.select_category(category_name):
            return False

        for folder_name in path_names:
            children = self.get_children()
            found = False
            for idx, child in enumerate(children):
                if liveobj_valid(child) and child.name == folder_name and getattr(child, 'is_folder', False):
                    self.selected_index = idx
                    self.navigate_down(idx)
                    found = True
                    break
            if not found:
                self.log_message(f"Path broken at {folder_name}")
                break
        return True

    def get_current_path_names(self):
        path = []
        for item in self.navigation_path:
            if liveobj_valid(item):
                path.append(item.name)
        if self.current_item and liveobj_valid(self.current_item) and getattr(self.current_item, 'is_folder', False):
            if self.current_category in ['user_folders', 'colors'] and self.current_item not in self.navigation_path:
                 path.append(self.current_item.name)
        return path

    def get_category_index_map(self):
        return {
            0: 'audio_effects', 1: 'instruments', 2: 'midi_effects',
            3: 'max_for_live', 4: 'drums', 5: 'samples', 6: 'sounds',
            7: 'packs', 8: 'plugins', 9: 'user_library', 10: 'current_project',
            11: 'user_folders', 12: 'colors'
        }
