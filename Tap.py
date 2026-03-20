# 7III Tap 1.5

from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.MixerComponent import MixerComponent
from _Framework.TransportComponent import TransportComponent
from _Framework.SessionComponent import SessionComponent
from _Framework.EncoderElement import *
from _Framework.ButtonElement import ButtonElement
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_NOTE_TYPE, MIDI_NOTE_ON_STATUS, MIDI_NOTE_OFF_STATUS, MIDI_CC_TYPE
from _Framework.DeviceComponent import DeviceComponent
from ableton.v2.base import listens, liveobj_valid, liveobj_changed
from Live.Clip import MidiNoteSpecification

import threading
import random
from itertools import zip_longest
import time

secret_version_number = 2

mixer, transport, session_component = None, None, None
quantize_grid_value = 5
quantize_strength_value = 1.0
swing_amount_value = 0.0


class Tap(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            global mixer
            global transport
            global session_component
            self.mixer_status = False
            self.mixer_reset = True
            self.visible_channels = (0, 3)
            self.device_status = True
            self.seq_status = False
            self.seq_clip_playing_status = 2
            track_count = 127
            return_count = 12  # Maximum of 12 Sends and 12 Returns
            max_clip_slots = 800  # Adjust this number based on your needs
            self.playing_position_listeners = [None] * max_clip_slots
            self.current_clip_notes = []
            self.last_selected_clip_slot = None
            self.last_raw_notes = None
            self.currently_playing_notes = [False] * 128
            self.last_playing_position = 0.0
            self.last_sent_out_playing_pos = 0.0
            self.clip_length_trick = 110.0
            mixer = MixerComponent(track_count, return_count)
            transport = TransportComponent()
            session_component = SessionComponent()
            self.old_clips_array = []
            self._drum_rack_device = None
            self.was_initialized = False
            self._track_level_listeners = {}
            self._return_level_listeners = {}
            self._master_level_listeners = {}
            self._disabled_parameter_listeners = {}
            self._disabled_parameters = []
            self._current_disabled_controls = []
            self._automation_state_listeners = {}
            self._automation_metadata_update_timer = None
            self._automation_metadata_retry_count = 0
            self._automation_metadata_retry_start = None
            self._last_automation_signature = None
            # browser pagination state
            self.browser_current_items = []
            self.browser_current_page = 0
            self.browser_pages_count = 0
            self.browser_items_per_page = 12
            # browser navigation history for back button
            self.browser_history = []
            self.browser_folder_mapping = {
                0: 'audio_effects',
                1: 'colors',
                2: 'current_project',
                3: 'drums',
                4: 'instruments',
                5: 'max_for_live',
                6: 'midi_effects',
                7: 'packs',
                8: 'plugins',
                9: 'sounds',
                10: 'user_folders',
                11: 'user_library'
            }
            self._metadata_recheck_timer = None
            self._last_sent_metadata = None
            self._last_drum_pad_metadata = None
            self._drum_pad_change_recheck_count = 0
            self._drum_pad_recheck_start = None
            self._last_drum_pad_note = None
            self._last_drum_pad_change_at = 0.0
            self._device_recheck_start = None
            self._device_recheck_count = 0
            self._debug_mode = False
            self._metadata_cache = {}
            self._metadata_send_seq = 0
            self._metadata_send_seq_by_device = {}
            self._automation_metadata_device_id = None
            self._automation_timer_lock = threading.Lock()
            self._mixer_disconnect_timer = None
            self._clip_slot_listeners = {}
            self._registered_track_ids = set()
            self._clip_color_listeners = {}
            self._clip_listener_track_slots = {}
            self._clip_slot_color_map = {}
            self._track_list_signature = None
            self._previous_selected_track = None
            self._periodic_timer_ref = None
            # connection check button
            connection_check_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 94)
            connection_check_button.add_value_listener(self._connection_established)
            # send project again button
            send_project_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 88)
            send_project_button.add_value_listener(self._send_project)

            # making a song instance
            self.song_instance = self.song()
            
            self._last_playing_pos_sent = 0.0

    def _setup_device_control(self):
        self._device = DeviceComponent()
        self._device.name = 'Device_Component'
        
        self._device_controls = []
        for index in range(8):
            control = EncoderElement(MIDI_CC_TYPE, 8, 72 + index, Live.MidiMap.MapMode.absolute)
            control.name = 'Ctrl_' + str(index)
            self._device_controls.append(control)
        
        nav_left_button = ButtonElement(1, MIDI_CC_TYPE, 0, 33)
        nav_right_button = ButtonElement(1, MIDI_CC_TYPE, 0, 32)
        self._device.set_bank_nav_buttons(nav_left_button, nav_right_button)
        
        # Set up device change listener
        self._on_device_changed.subject = self._device
        self.set_device_component(self._device)
        
        # Register button listeners for navigation buttons
        nav_left_button.add_value_listener(self._on_nav_button_pressed)
        nav_right_button.add_value_listener(self._on_nav_button_pressed)
        
        # Initially connect the controls (assuming we start in device mode)
        self._connect_device_controls()

    def _connect_device_controls(self):
        if hasattr(self, '_device_controls'):
            self._device.set_parameter_controls(self._device_controls)
        self._readd_disabled_parameter_listeners()
    
    def _disconnect_device_controls(self):
        if hasattr(self, '_device'):
            self._device.set_parameter_controls([])
        self._remove_disabled_parameter_listeners()
        self._remove_automation_state_listeners()

    def _on_nav_button_pressed(self, value):
        if value:
            self._on_device_changed()

    def _find_drum_rack_in_track(self, track):
        for device in track.devices:
            if device.can_have_drum_pads:
                return device
            elif isinstance(device, Live.RackDevice.RackDevice):
                # If the device is a RackDevice (e.g., Instrument Rack), recursively search inside its chains
                for chain in device.chains:
                    drum_rack = self._find_drum_rack_in_track(chain)
                    if drum_rack is not None:
                        return drum_rack
        return None
    
    def _setup_drum_pad_listeners(self):
        if self._drum_rack_device:
            self._send_all_drum_pad_names()
            self._send_selected_drum_pad_number()
            for pad in self._drum_rack_device.drum_pads:
                if not pad.name_has_listener(self._send_all_drum_pad_names):
                    pad.add_name_listener(self._send_all_drum_pad_names)
            if not self._drum_rack_device.view.selected_drum_pad_has_listener(self._send_selected_drum_pad_number):
                self._drum_rack_device.view.add_selected_drum_pad_listener(self._send_selected_drum_pad_number)

    def _remove_drum_pad_name_listeners(self):
        if self._drum_rack_device:
            for pad in self._drum_rack_device.drum_pads:
                if pad.name_has_listener(self._send_all_drum_pad_names):
                    pad.remove_name_listener(self._send_all_drum_pad_names)
            if self._drum_rack_device.view.selected_drum_pad_has_listener(self._send_selected_drum_pad_number):
                self._drum_rack_device.view.remove_selected_drum_pad_listener(self._send_selected_drum_pad_number)

    def _send_all_drum_pad_names(self):
        if not self._drum_rack_device:
            return
    
        pads = self._drum_rack_device.drum_pads
    
        # Find the first and last pad with chains using the .note property
        first_with_chain = None
        last_with_chain = None
    
        for pad in pads:
            if pad.chains:
                first_with_chain = pad
                break
    
        for pad in reversed(pads):
            if pad.chains:
                last_with_chain = pad
                break
                
        if first_with_chain and last_with_chain:
            first_index = first_with_chain.note
            last_index = last_with_chain.note
        
            pad_names = []
            
            # Add index of first chain pad
            pad_names.append(str(first_index))
            for pad in pads[first_index:last_index + 1]:
                if pad.chains:
                    pad_names.append(pad.name)
                else:
                    pad_names.append(str(pad.note))
            payload = ",".join(pad_names)
            self._send_sys_ex_message(payload, 0x11)
    
    def _update_tempo(self):
        new_tempo = round(self.song().tempo, 2)
        self._send_sys_ex_message(str(new_tempo), 0x12)
    
    def _is_bank_connected(self, device, bank_name):
        if not isinstance(device, Live.RackDevice.RackDevice):
            return True
        
        if bank_name not in ("Macros", "Macros 2"):
            return True
        
        if not hasattr(device, 'macros_mapped'):
            return True
        
        macro_ranges = {
            "Macros": (0, 8),
            "Macros 2": (8, 16)
        }
        
        if bank_name not in macro_ranges:
            return True
        
        start_idx, end_idx = macro_ranges[bank_name]
        return any(device.macros_mapped[start_idx:end_idx])
    
    def _build_parameter_metadata(self, selected_device):
        if not hasattr(selected_device, 'parameters'):
            return ""
        
        param_data = []
        device_parameters = list(selected_device.parameters)
        device_param_map = {}
        for dp in device_parameters:
            if hasattr(dp, 'name'):
                device_param_map[dp.name] = dp
        unmapped_encoder_indices = []
        
        for control_index in range(8):
            control = self._device_controls[control_index] if control_index < len(self._device_controls) else None
            mapped_param = control.mapped_parameter() if control and control.mapped_parameter() else None
            
            if mapped_param:
                device_param = mapped_param
                if device_param is None or not hasattr(device_param, 'name'):
                    device_param = device_param_map.get(mapped_param.name)
                
                if device_param:
                    if hasattr(device_param, 'is_enabled'):
                        if hasattr(device_param, 'automation_state') and device_param.automation_state != 0:
                            if device_param.automation_state == 1:
                                name = f"**{device_param.name}"
                            elif device_param.automation_state == 2:
                                name = f"*/{device_param.name}"
                        elif device_param.is_enabled:
                            name = device_param.name
                        else:
                            name = f"*-{device_param.name}"
                    else:
                        name = device_param.name
                    
                    min_val_str = None
                    max_val_str = None
                    default_val_str = None
                    
                    if min_val_str is None or max_val_str is None:
                        try:
                            if hasattr(device_param, 'str_for_value'):
                                if hasattr(device_param, 'min') and hasattr(device_param, 'max'):
                                    min_val_str = device_param.str_for_value(device_param.min)
                                    max_val_str = device_param.str_for_value(device_param.max)
                                else:
                                    min_val_str = device_param.str_for_value(0.0)
                                    max_val_str = device_param.str_for_value(1.0)
                        except Exception:
                            pass
                    
                    if min_val_str is None:
                        min_val_str = str(device_param.min) if hasattr(device_param, 'min') else "0.0"
                    if max_val_str is None:
                        max_val_str = str(device_param.max) if hasattr(device_param, 'max') else "1.0"
                    
                    raw_default_value = None
                    quarter_str = "0.0"
                    if (not device_param.is_quantized and hasattr(device_param, 'default_value')):
                        try:
                            raw_default_value = device_param.default_value
                            if hasattr(device_param, 'str_for_value'):
                                default_val_str = device_param.str_for_value(device_param.default_value)
                                try:
                                    num_val = float(default_val_str)
                                    default_val_str = str(round(num_val, 2))
                                except Exception:
                                    pass
                                if hasattr(device_param, 'min') and hasattr(device_param, 'max'):
                                    quarter_value = device_param.min + (device_param.max - device_param.min) * 32/127
                                    quarter_str = device_param.str_for_value(quarter_value)
                            else:
                                default_val_str = str(round(device_param.default_value, 2))
                            if hasattr(device_param, 'min') and hasattr(device_param, 'max') and device_param.max != device_param.min:
                                raw_default_value = round((raw_default_value - device_param.min) / (device_param.max - device_param.min), 3)
                        except Exception:
                            default_val_str = min_val_str
                            raw_default_value = device_param.min if hasattr(device_param, 'min') else 0.0
                    else:
                        default_val_str = min_val_str
                        raw_default_value = device_param.min if hasattr(device_param, 'min') else 0.0
                    
                    if hasattr(device_param, 'is_quantized') and device_param.is_quantized and hasattr(device_param, 'value_items'):
                        value_items = ';'.join(str(item) for item in device_param.value_items)
                    else:
                        value_items = ''
                    
                    default_raw_str = str(raw_default_value) if raw_default_value is not None else ""
                    param_str = f"{name.strip()}|{min_val_str.strip()}|{max_val_str.strip()}|{default_val_str.strip()}|{default_raw_str.strip()}|{quarter_str.strip()}|{value_items.strip()}"
                    param_data.append(param_str)
                else:
                    param_str = "*--&&-|0|127|0.0|0.0|32|"
                    param_data.append(param_str)
                    unmapped_encoder_indices.append(control_index)
            else:
                param_str = "*--&&-|0|127|0.0|0.0|32|"
                param_data.append(param_str)
                unmapped_encoder_indices.append(control_index)
        
        return ','.join(param_data)
    
    def _metadata_has_only_numbers(self, metadata):
        if not metadata:
            return False
        
        params = metadata.split(',')
        
        for param in params:
            fields = param.split('|')
            for field_index in [1, 2, 3, 5]:
                if field_index < len(fields):
                    field_value = fields[field_index].strip()
                    if field_value:
                        try:
                            float(field_value)
                        except ValueError:
                            return False
        
        return True

    def _metadata_has_raw_0_127(self, metadata):
        if not metadata:
            return False
        
        params = metadata.split(',')
        for param in params:
            fields = param.split('|')
            for field_index in [1, 2, 3, 5]:
                if field_index < len(fields):
                    field_value = fields[field_index].strip()
                    if field_value in ("0", "127"):
                        return True
        return False

    def _metadata_has_unmapped(self, metadata):
        if not metadata:
            return False
        
        return "*--&&-" in metadata

    def _metadata_needs_rack_recheck(self, metadata):
        return (
            self._metadata_has_unmapped(metadata)
            or self._metadata_has_only_numbers(metadata)
            or self._metadata_has_raw_0_127(metadata)
        )

    def _debug_log(self, message):
        if self._debug_mode:
            self.log_message(message)

    def _get_device_cache_key(self, device):
        if not device:
            return None
        return id(device)

    def _get_cached_metadata(self, device):
        key = self._get_device_cache_key(device)
        if key is None:
            return None
        return self._metadata_cache.get(key)

    def _set_cached_metadata(self, device, metadata):
        key = self._get_device_cache_key(device)
        if key is None:
            return
        self._metadata_cache[key] = metadata

    def _clear_cached_metadata(self, device):
        key = self._get_device_cache_key(device)
        if key is None:
            return
        if key in self._metadata_cache:
            del self._metadata_cache[key]

    def _mark_metadata_sent(self, device):
        key = self._get_device_cache_key(device)
        self._metadata_send_seq += 1
        if key is not None:
            self._metadata_send_seq_by_device[key] = self._metadata_send_seq
    
    def _recheck_parameter_metadata(self):
        self._metadata_recheck_timer = None
        
        if not liveobj_valid(self._device):
            return
        
        selected_track = self.song().view.selected_track
        selected_device = selected_track.view.selected_device
        metadata_device = selected_device
        
        if self._drum_rack_device and selected_device == self._drum_rack_device:
            mapped_device = self._find_mapped_device()
            if mapped_device and self._is_device_in_drum_pad(mapped_device):
                metadata_device = mapped_device
        
        is_rack_device = isinstance(metadata_device, Live.RackDevice.RackDevice)
        is_drum_rack = self._drum_rack_device and metadata_device == self._drum_rack_device
        is_drum_pad_device = self._drum_rack_device and self._is_device_in_drum_pad(metadata_device)
        
        if not is_rack_device and not is_drum_pad_device:
            return
        
        current_metadata = self._build_parameter_metadata(metadata_device)
        has_unmapped = self._metadata_has_unmapped(current_metadata)
        has_only_numbers = self._metadata_has_only_numbers(current_metadata)
        
        if self._drum_pad_recheck_start is None:
            self._drum_pad_recheck_start = time.time()
        
        elapsed = time.time() - self._drum_pad_recheck_start
        self._debug_log(
            "Recheck metadata: "
            f"iter={self._drum_pad_change_recheck_count} "
            f"elapsed={round(elapsed, 3)}s "
            f"device='{metadata_device.name if metadata_device else 'None'}' "
            f"rack={is_rack_device} drum_rack={bool(is_drum_rack)} drum_pad_device={bool(is_drum_pad_device)} "
            f"unmapped={has_unmapped} only_numbers={has_only_numbers}"
        )
        
        if elapsed >= 0.8:
            self._debug_log("Recheck metadata: reached max duration 0.8s, stopping")
            self._drum_pad_change_recheck_count = 0
            self._drum_pad_recheck_start = None
            return
        
        should_resend = False
        cached_metadata = self._get_cached_metadata(metadata_device)
        if current_metadata and cached_metadata != current_metadata:
            should_resend = True
        
        if should_resend:
            self._debug_log(f"Recheck metadata (iteration {getattr(self, '_drum_pad_change_recheck_count', 0)}): Resending changed metadata")
            self._send_sys_ex_message(current_metadata, 0x7D)
            self._set_cached_metadata(metadata_device, current_metadata)
            self._mark_metadata_sent(metadata_device)
            
            if is_drum_pad_device:
                self._last_drum_pad_metadata = current_metadata
            else:
                self._last_sent_metadata = current_metadata
            
            if hasattr(metadata_device, 'parameters') and metadata_device.parameters:
                device_parameters = list(metadata_device.parameters)
                
                for control_index in range(8):
                    control = self._device_controls[control_index] if control_index < len(self._device_controls) else None
                    mapped_param = control.mapped_parameter() if control and control.mapped_parameter() else None
                    
                    if mapped_param:
                        device_param = None
                        for dp in device_parameters:
                            if hasattr(dp, 'name') and dp.name == mapped_param.name:
                                device_param = dp
                                break
                        
                        if device_param:
                            cc_value = self._parameter_value_to_cc(device_param)
                            cc_number = 72 + control_index
                            self.send_cc(cc_number, 8, cc_value)
        
        max_iterations = 8
        should_continue = False
        if is_drum_pad_device or is_drum_rack:
            should_continue = has_unmapped
        elif is_rack_device:
            should_continue = has_only_numbers
        
        if should_continue:
            self._drum_pad_change_recheck_count += 1
            if self._drum_pad_change_recheck_count <= max_iterations:
                self._metadata_recheck_timer = threading.Timer(0.1, self._recheck_parameter_metadata)
                self._metadata_recheck_timer.start()
            else:
                if is_drum_pad_device:
                    self._debug_log(f"Drum pad recheck: Reached max iterations (0.8s), last metadata: {current_metadata[:100]}...")
                    self._last_drum_pad_metadata = None
                else:
                    if is_drum_rack:
                        self._debug_log(f"Drum rack recheck: Reached max iterations (0.8s), last metadata: {current_metadata[:100]}...")
                    else:
                        self._debug_log(f"Rack recheck: Reached max iterations (0.8s), last metadata: {current_metadata[:100]}...")
                self._drum_pad_change_recheck_count = 0
                self._drum_pad_recheck_start = None
                return
        else:
            self._drum_pad_change_recheck_count = 0
            self._drum_pad_recheck_start = None
    
    @subject_slot('device')
    def _on_device_changed(self):
        if self._drum_rack_device:
            self._remove_drum_pad_name_listeners()
            self._drum_rack_device = None
        self._remove_automation_state_listeners()
        self._automation_metadata_device_id = None
            
        if liveobj_valid(self._device):
            # get and send name of bank and device
            selected_track = self.song().view.selected_track
            selected_device = selected_track.view.selected_device
            
            # Get all available devices of the selected track, including nested devices
            all_devices, chain_info = self._get_all_nested_devices(selected_track.devices)
            
            # Convert device objects to names for display, adding chain markers
            all_device_names = []
            for i, device in enumerate(all_devices):
                name = device.name
                
                # collect all starts/ends for this index
                starts = [info for info in chain_info if info['start_index'] == i]
                ends   = [info for info in chain_info if info['end_index'] == i]
                
                # there should never be more than one rack or chain at the same index
                prefix = ""
                for s in starts:
                    if s['type'] == 'rack':
                        prefix += "||"
                    elif s['type'] == 'chain':
                        prefix += "|*"
            
                # make sure chains come first, racks after
                suffix = ""
                for e in [e for e in ends if e['type'] == 'chain']:
                    suffix += "*|"
                for e in [e for e in ends if e['type'] == 'rack']:
                    suffix += "||"
            
                all_device_names.append(prefix + name + suffix)
            
            available_devices_string = ','.join(all_device_names)
            
            # find out if track has a drum rack.
            track_has_drums = 0
            drum_rack_device = self._find_drum_rack_in_track(selected_track)
            if drum_rack_device is not None:
                track_has_drums = 1
                # set up drum pad names, with listener
                self._drum_rack_device = drum_rack_device
                self._setup_drum_pad_listeners()
                
            # CHANGE 2: Find index of selected device in our comprehensive nested devices list
            selected_device_index = "not found"
            for index, device in enumerate(all_devices):
                if device == selected_device:
                    selected_device_index = str(index)
                    break
            
            # bank names, list and if has drum
            current_bank_name = self._device._bank_name
            all_bank_names = self._device._parameter_bank_names()
            connected_bank_names = [name for name in all_bank_names if self._is_bank_connected(selected_device, name)]
            
            # Handle case where current bank was filtered out
            if current_bank_name and isinstance(selected_device, Live.RackDevice.RackDevice):
                if current_bank_name in all_bank_names and current_bank_name not in connected_bank_names:
                    # Current bank was filtered, navigate to first connected bank
                    if connected_bank_names:
                        # Simulate bank navigation to trigger device change with valid bank
                        self._device._bank_index = all_bank_names.index(connected_bank_names[0])
                    else:
                        current_bank_name = ""
            
            bank_name_drum = current_bank_name + ";" + str(track_has_drums)
            bank_names_list = ','.join(str(name) for name in connected_bank_names)
            
            # sending sysex of bank name, device name, bank names
            self._send_sys_ex_message(bank_name_drum, 0x6D)
            self._send_sys_ex_message(bank_names_list, 0x5D)
            # CHANGE 3: Send the index from our comprehensive device list
            self._send_sys_ex_message(selected_device_index, 0x4D)
            
            # Send the comprehensive list of available devices
            self._send_sys_ex_message(available_devices_string, 0x01)
            
            # In mixer mode, temporarily reconnect device controls so we can
            # build parameter metadata. Do this early so the framework has more
            # time to remap parameters to the new device before we read them.
            if self.mixer_status:
                self._connect_device_controls()
            
            if hasattr(selected_device, 'parameters') and selected_device.parameters:
                def _build_parameter_names():
                    names = []
                    for control in self._device._parameter_controls:
                        if control.mapped_parameter():
                            mapped_param = control.mapped_parameter()
                            
                            device_param = mapped_param
                            
                            if device_param and hasattr(device_param, 'is_enabled'):
                                if hasattr(device_param, 'automation_state') and device_param.automation_state != 0:
                                    if device_param.automation_state == 1:
                                        names.append(f"**{device_param.name}")
                                    elif device_param.automation_state == 2:
                                        names.append(f"*/{device_param.name}")
                                elif device_param.is_enabled:
                                    names.append(device_param.name)
                                else:
                                    names.append(f"*-{device_param.name}")
                            else:
                                # Fallback to mapped parameter name if DeviceParameter not found
                                names.append(mapped_param.name)
                        else:
                            names.append("")
                    return [name for name in names if name != ""]
                
                parameter_names = _build_parameter_names()
                if not parameter_names and self.mixer_status:
                    if hasattr(self._device, 'set_device'):
                        try:
                            self._device.set_device(selected_device)
                        except Exception:
                            pass
                    if connected_bank_names:
                        try:
                            if current_bank_name and current_bank_name in all_bank_names:
                                self._device._bank_index = all_bank_names.index(current_bank_name)
                            else:
                                self._device._bank_index = all_bank_names.index(connected_bank_names[0])
                        except Exception:
                            pass
                    if hasattr(self._device, 'update'):
                        try:
                            self._device.update()
                        except Exception:
                            pass
                    parameter_names = _build_parameter_names()
                
                # Filter out empty names but keep "-" for disabled parameters
                
                if parameter_names:
                    self._send_parameter_info(parameter_names)
                else:
                    # parameter_names empty — try building metadata directly from
                    # _build_parameter_metadata, which may succeed even when the
                    # device component's own remapping is still in progress
                    current_metadata = self._build_parameter_metadata(selected_device)
                    if current_metadata and not self._metadata_has_unmapped(current_metadata):
                        self._send_sys_ex_message(current_metadata, 0x7D)
                        self._set_cached_metadata(selected_device, current_metadata)
                        self._mark_metadata_sent(selected_device)
                    else:
                        # Truly unmapped — send placeholder
                        self._send_sys_ex_message("*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|", 0x7D)
                        
                        # Send CC 0 for all encoders
                        for control_index in range(8):
                            cc_number = 72 + control_index
                            self.send_cc(cc_number, 8, 0)
                self._refresh_automation_state_listeners_current_bank()
                self._last_automation_signature = self._get_automation_signature()
            
            self._remove_disabled_parameter_listeners()
            
            if hasattr(selected_device, 'parameters') and selected_device.parameters:
                for control_index, control in enumerate(self._device._parameter_controls):
                    if control.mapped_parameter():
                        mapped_param = control.mapped_parameter()
                        
                        device_param = mapped_param
                        
                        if device_param and hasattr(device_param, 'is_enabled') and not device_param.is_enabled:
                            listener = self._create_disabled_param_listener(device_param, control_index)
                            if not device_param.value_has_listener(listener):
                                device_param.add_value_listener(listener)
                            
                            self._disabled_parameter_listeners[(device_param, control_index)] = listener
                            self._disabled_parameters.append(device_param)
                            self._current_disabled_controls.append(control_index)
                            
                            cc_value = self._parameter_value_to_cc(device_param)
                            cc_number = 72 + control_index
                            self.send_cc(cc_number, 8, cc_value)
            else:
                # Device has no parameters - send not mapped for all controls
                self._send_sys_ex_message("*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|", 0x7D)
                
                # Send CC 0 for all encoders
                for control_index in range(8):
                    cc_number = 72 + control_index
                    self.send_cc(cc_number, 8, 0)

            # In mixer mode, disconnect device controls after a short delay
            # instead of immediately, so the framework has time to finish
            # remapping parameters to the new device.
            if self.mixer_status:
                if hasattr(self, '_mixer_disconnect_timer') and self._mixer_disconnect_timer:
                    self._mixer_disconnect_timer.cancel()
                self._mixer_disconnect_timer = threading.Timer(0.2, self._disconnect_device_controls)
                self._mixer_disconnect_timer.start()

        else:
            # no device
            # sending sysex of bank name, device name, bank names
            bank_name_drum = ";0"
            bank_names_list = ""
            available_devices_string = ""
            self._send_sys_ex_message(bank_name_drum, 0x6D)
            self._send_sys_ex_message(bank_names_list, 0x5D)
            self._send_sys_ex_message(available_devices_string, 0x01)
            # Send not mapped for all controls when no device is selected
            self._send_sys_ex_message("*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|,*--&&-|0|127|0.0|0.0|32|", 0x7D)
            
            # Send CC 0 for all encoders
            for control_index in range(8):
                cc_number = 72 + control_index
                self.send_cc(cc_number, 8, 0)
    
    def _get_all_nested_devices(self, devices):
        """
        Recursively collect all devices, including those inside instruments and drum racks.
        For drum racks, only include the selected drum pad chain (like Push behavior).
        Returns a tuple: (list of device objects, list of chain_info dicts)
        
        chain_info format: {'start_index': int, 'end_index': int, 'type': 'drum_rack'/'rack'}
        """
        all_devices = []
        chain_info = []
        
        for device in devices:
            if liveobj_valid(device):
                # Add the current device
                all_devices.append(device)
                
                # Check if device is a drum rack
                if hasattr(device, 'can_have_drum_pads') and device.can_have_drum_pads and hasattr(device, 'drum_pads') and device.drum_pads:
                    # For drum racks, only process the selected drum pad chain
                    selected_drum_pad = self._get_selected_drum_pad(device)
                    if selected_drum_pad and hasattr(selected_drum_pad, 'chains') and selected_drum_pad.chains:
                        for chain in selected_drum_pad.chains:
                            if liveobj_valid(chain) and hasattr(chain, 'devices'):
                                # Mark start of nested chain
                                start_index = len(all_devices)
                                
                                # Add devices from the selected drum pad chain
                                nested_devices, nested_chain_info = self._get_all_nested_devices(chain.devices)
                                all_devices.extend(nested_devices)
                                
                                # Mark end of nested chain (if any devices were added)
                                if nested_devices:
                                    end_index = len(all_devices) - 1
                                    chain_info.append({
                                        'start_index': start_index,
                                        'end_index': end_index,
                                        'type': 'rack'
                                    })
                                
                                # Add any nested chain info with adjusted indices
                                for info in nested_chain_info:
                                    chain_info.append({
                                        'start_index': info['start_index'] + start_index,
                                        'end_index': info['end_index'] + start_index,
                                        'type': info['type']
                                    })
                
                # Check if device is an instrument rack or effect rack (has chains)
                elif hasattr(device, 'chains') and device.chains:
                    num_chains = len([c for c in device.chains if liveobj_valid(c) and hasattr(c, 'devices')])
                    
                    for chain in device.chains:
                        if liveobj_valid(chain) and hasattr(chain, 'devices'):
                            # Mark start of nested chain
                            start_index = len(all_devices)
                            
                            # Add devices from this chain
                            nested_devices, nested_chain_info = self._get_all_nested_devices(chain.devices)
                            all_devices.extend(nested_devices)
                            
                            # Mark end of nested chain (if any devices were added)
                            # adding chain instead of rack if we have more than one chain
                            if nested_devices:
                                end_index = len(all_devices) - 1
                                chain_info.append({
                                    'start_index': start_index,
                                    'end_index': end_index,
                                    'type': 'chain' if num_chains > 1 else 'rack'
                                })
                            
                            # Add any nested chain info with adjusted indices
                            for info in nested_chain_info:
                                chain_info.append({
                                    'start_index': info['start_index'] + start_index,
                                    'end_index': info['end_index'] + start_index,
                                    'type': info['type']
                                })
                            
        return all_devices, chain_info
    
    def _get_selected_drum_pad(self, drum_rack):
        """
        Get the currently selected drum pad from a drum rack device.
        Returns the selected drum pad or None if none is selected.
        """
        if hasattr(drum_rack, 'view') and hasattr(drum_rack.view, 'selected_drum_pad'):
            return drum_rack.view.selected_drum_pad
        
        # Alternative: if the view approach doesn't work, we could try to find the 
        # currently playing pad or default to the first pad with a chain
        for pad in drum_rack.drum_pads:
            if liveobj_valid(pad) and hasattr(pad, 'chains') and pad.chains:
                return pad
                
        return None
    
    def _send_selected_drum_pad_number(self):
        """
        Gets the currently selected drum pad number and sends it as a MIDI note on message
        on channel 3, note number 3, with the pad number encoded in the velocity.
        """
        try:
            if self._drum_rack_device:
                selected_pad = self._drum_rack_device.view.selected_drum_pad
                if selected_pad:
                    pad_number = selected_pad.note
                    now = time.time()
                    if self._last_drum_pad_note == pad_number and (now - self._last_drum_pad_change_at) < 0.05:
                        return
                    self._last_drum_pad_note = pad_number
                    self._last_drum_pad_change_at = now
                    
                    channel = 3
                    midi_note_number = 3
                    self.send_note_on(midi_note_number, channel, pad_number)
                    
                    if hasattr(self, '_metadata_recheck_timer') and self._metadata_recheck_timer:
                        self._metadata_recheck_timer.cancel()
                    
                    self._drum_pad_change_recheck_count = 0
                    self._last_drum_pad_metadata = None
                    self._last_sent_metadata = None
                    self._drum_pad_recheck_start = time.time()
                    
                    # Only auto-follow pad if we're already on a pad device
                    self._select_device_in_selected_drum_pad()
                    
                    # Kick off a metadata recheck loop to wait for full pad loading
                    self._debug_log("Drum pad change: starting metadata recheck loop")
                    self._metadata_recheck_timer = threading.Timer(0.1, self._recheck_parameter_metadata)
                    self._metadata_recheck_timer.start()
            else:
                self._debug_log("No drum pad selected")
            
        except Exception as e:
            self._debug_log(f"Error sending drum pad number: {str(e)}")
    
    def _find_mapped_device(self):
        """
        Finds the device that controls are currently mapped to by checking
        the device that owns the mapped parameters.
        """
        if not hasattr(self, '_device_controls'):
            return None
        
        for control in self._device_controls:
            if control and control.mapped_parameter():
                mapped_param = control.mapped_parameter()
                if hasattr(mapped_param, 'canonical_parent'):
                    device = mapped_param.canonical_parent
                    if hasattr(device, 'canonical_parent') and hasattr(device.canonical_parent, 'canonical_parent'):
                        return device
        return None

    def _select_device_in_selected_drum_pad(self):
        if not self._drum_rack_device:
            return
        
        selected_track = self.song().view.selected_track
        current_device = selected_track.view.selected_device
        if not current_device or not self._is_device_in_any_drum_pad(current_device):
            return
        
        selected_drum_pad = self._get_selected_drum_pad(self._drum_rack_device)
        if not selected_drum_pad or not selected_drum_pad.chains:
            return
        
        target_device = None
        mapped_device = self._find_mapped_device()
        if mapped_device and self._is_device_in_drum_pad(mapped_device):
            target_device = mapped_device
        else:
            def _first_device_in_chain(chain):
                if not liveobj_valid(chain) or not hasattr(chain, 'devices'):
                    return None
                for chain_device in chain.devices:
                    if liveobj_valid(chain_device):
                        if hasattr(chain_device, 'parameters') and chain_device.parameters:
                            return chain_device
                        if hasattr(chain_device, 'chains') and chain_device.chains:
                            for inner_chain in chain_device.chains:
                                nested = _first_device_in_chain(inner_chain)
                                if nested:
                                    return nested
                        return chain_device
                return None
            
            for chain in selected_drum_pad.chains:
                target_device = _first_device_in_chain(chain)
                if target_device:
                    break
        
        if target_device and liveobj_valid(target_device):
            try:
                if hasattr(self.song().view, 'select_device'):
                    self.song().view.select_device(target_device)
                elif hasattr(self._device, 'set_device'):
                    self._device.set_device(target_device)
                else:
                    selected_track.view.selected_device = target_device
            except Exception as e:
                self._debug_log(f"Error selecting drum pad device: {str(e)}")

    def _is_device_in_any_drum_pad(self, device):
        if not self._drum_rack_device or not device:
            return False
        
        def _device_in_chain(chain):
            if not liveobj_valid(chain) or not hasattr(chain, 'devices'):
                return False
            for chain_device in chain.devices:
                if chain_device == device:
                    return True
                if hasattr(chain_device, 'chains') and chain_device.chains:
                    for inner_chain in chain_device.chains:
                        if _device_in_chain(inner_chain):
                            return True
            return False
        
        for pad in self._drum_rack_device.drum_pads:
            if liveobj_valid(pad) and hasattr(pad, 'chains') and pad.chains:
                for chain in pad.chains:
                    if _device_in_chain(chain):
                        return True
        
        return False

    def _is_device_in_rack_chain(self, device, track_devices):
        if not device or not track_devices:
            return False
        
        parent_chain, _ = self._find_parent_chain(track_devices, device)
        return parent_chain is not None
    
    def _is_device_in_drum_pad(self, device):
        """
        Checks if a device is inside a drum pad of the current drum rack.
        """
        if not self._drum_rack_device or not device:
            return False
        
        selected_drum_pad = self._get_selected_drum_pad(self._drum_rack_device)
        if not selected_drum_pad or not selected_drum_pad.chains:
            return False
        
        def _device_in_chain(chain):
            if not liveobj_valid(chain) or not hasattr(chain, 'devices'):
                return False
            for chain_device in chain.devices:
                if chain_device == device:
                    return True
                if hasattr(chain_device, 'chains') and chain_device.chains:
                    for inner_chain in chain_device.chains:
                        if _device_in_chain(inner_chain):
                            return True
            return False
        
        for chain in selected_drum_pad.chains:
            if _device_in_chain(chain):
                return True
        
        return False

    def _send_parameter_info(self, parameter_names):
        if parameter_names == "":
            self._send_sys_ex_message("", 0x7D)
        else:
            selected_track = self.song().view.selected_track
            selected_device = selected_track.view.selected_device
            
            current_metadata = self._build_parameter_metadata(selected_device)
            
            if current_metadata:
                cached_metadata = self._get_cached_metadata(selected_device)
                metadata_changed = cached_metadata != current_metadata
                if metadata_changed:
                    self._send_sys_ex_message(current_metadata, 0x7D)
                    self._set_cached_metadata(selected_device, current_metadata)
                    self._mark_metadata_sent(selected_device)
                
                if metadata_changed:
                    unmapped_encoder_indices = []
                    for control_index in range(8):
                        control = self._device_controls[control_index] if control_index < len(self._device_controls) else None
                        mapped_param = control.mapped_parameter() if control and control.mapped_parameter() else None
                        if not mapped_param:
                            unmapped_encoder_indices.append(control_index)
                    
                    for control_index in unmapped_encoder_indices:
                        cc_number = 72 + control_index
                        self.send_cc(cc_number, 8, 0)
                
                is_rack_device = isinstance(selected_device, Live.RackDevice.RackDevice)
                is_drum_rack = self._drum_rack_device and selected_device == self._drum_rack_device
                is_drum_pad_device = self._drum_rack_device and self._is_device_in_drum_pad(selected_device)
                is_rack_related = is_rack_device or self._is_device_in_rack_chain(selected_device, selected_track.devices)
                
                should_iterate = False
                if is_drum_rack or is_drum_pad_device:
                    should_iterate = self._metadata_has_unmapped(current_metadata)
                elif is_rack_related:
                    should_iterate = self._metadata_needs_rack_recheck(current_metadata)
                
                if should_iterate:
                    if is_drum_pad_device:
                        self._last_drum_pad_metadata = current_metadata
                    else:
                        self._last_sent_metadata = current_metadata
                    
                    if is_drum_rack or is_drum_pad_device:
                        self._drum_pad_change_recheck_count = 0
                        self._drum_pad_recheck_start = time.time()
                    else:
                        self._device_recheck_count = 0
                        self._device_recheck_start = time.time()
                    
                    if self._metadata_recheck_timer:
                        self._metadata_recheck_timer.cancel()
                    
                    self._metadata_recheck_timer = threading.Timer(0.1, self._recheck_parameter_metadata)
                    self._metadata_recheck_timer.start()
                else:
                    self._last_sent_metadata = None
                    self._last_drum_pad_metadata = None
                    self._drum_pad_change_recheck_count = 0

    def _send_sys_ex_message(self, name_string, manufacturer_id):
        status_byte = 0xF0  # SysEx message start
        end_byte = 0xF7  # SysEx message end
        device_id = 0x01
        data = name_string.encode('ascii', errors='ignore')
        max_chunk_length = 240
        if len(data) <= max_chunk_length:
            sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(data) + (end_byte, )
            self._send_midi(sys_ex_message)
        else:
            num_of_chunks = (len(data) + max_chunk_length - 1) // max_chunk_length
            for chunk_index in range(num_of_chunks):
                start_index = chunk_index * max_chunk_length
                end_index = start_index + max_chunk_length
                prefix = "$"
                if chunk_index == num_of_chunks - 1:
                    prefix = "_"
                chunk_data = prefix.encode('ascii') + data[start_index:end_index]

                sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(chunk_data) + (end_byte, )
                self._send_midi(sys_ex_message)

    def _initialize_buttons(self):
        transport.set_play_button(ButtonElement(1, MIDI_CC_TYPE, 0, 118))
        transport.set_stop_button(ButtonElement(1, MIDI_CC_TYPE, 0, 117))
        transport.set_metronome_button(ButtonElement(1, MIDI_CC_TYPE, 0, 58))
        session_component.set_stop_all_clips_button(ButtonElement(1, MIDI_NOTE_TYPE, 15, 96))
        self.capture_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 100)
        self.capture_button.add_value_listener(self._capture_button_value)
        self.quantize_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 99)
        self.quantize_button.add_value_listener(self._quantize_button_value)
        # duplicate the active clip to a free slot
        self.duplicate_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 98)
        self.duplicate_button.add_value_listener(self._duplicate_button_value)
        # duplicate scene
        self.duplicate_scene_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 95)
        self.duplicate_scene_button.add_value_listener(self._duplicate_scene_button_value)
        # a session recording button
        self.sesh_record_button = ButtonElement(1, MIDI_CC_TYPE, 0, 119)
        self.sesh_record_button.add_value_listener(self._sesh_record_value)
        # quantize grid size button
        quantize_grid_button = ButtonElement(1, MIDI_CC_TYPE, 1, 0)
        quantize_grid_button.add_value_listener(self._quantize_grid_value)
        # quantize strength
        quantize_strength_button = ButtonElement(1, MIDI_CC_TYPE, 1, 1)
        quantize_strength_button.add_value_listener(self._quantize_strength_value)
        # swing percentage button
        swing_amount_button = ButtonElement(1, MIDI_CC_TYPE, 1, 2)
        swing_amount_button.add_value_listener(self._swing_amount_value)
        # # periodic check
        # periodic_check_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 97)
        # periodic_check_button.add_value_listener(self._periodic_check)
        # redo button
        self.redo_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 102)
        self.redo_button.add_value_listener(self._redo_button_value)
        # undo button
        self.undo_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 101)
        self.undo_button.add_value_listener(self._undo_button_value)
        # device selection
        device_selection_button = ButtonElement(1, MIDI_CC_TYPE, 1, 3)
        device_selection_button.add_value_listener(self._select_device_by_index)
        # track selection
        track_selection_button = ButtonElement(1, MIDI_CC_TYPE, 1, 4)
        track_selection_button.add_value_listener(self._select_track_by_index)
        # return and master track selection
        return_track_selection_button = ButtonElement(1, MIDI_CC_TYPE, 1, 5)
        return_track_selection_button.add_value_listener(self._select_return_track_by_index)
        # scene launch
        scene_launch_button = ButtonElement(1, MIDI_CC_TYPE, 1, 14)
        scene_launch_button.add_value_listener(self._fire_scene)
        # clip / scene select
        clip_scene_select_button = ButtonElement(1, MIDI_CC_TYPE, 1, 15)
        clip_scene_select_button.add_value_listener(self._select_clip_scene)
        # scene delete
        scene_delete_button = ButtonElement(1, MIDI_CC_TYPE, 1, 16)
        scene_delete_button.add_value_listener(self._delete_scene)
        # random device add button
        random_device_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 93)
        random_device_button.add_value_listener(self._add_random_sound)
        # random audio effect button
        random_effect_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 92)
        random_effect_button.add_value_listener(self._add_random_effect)
        # random synth button
        random_synth_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 103)
        random_synth_button.add_value_listener(self._add_random_synth)
        # random drums button
        random_drums_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 104)
        random_drums_button.add_value_listener(self._add_random_drums)
        # delete device button
        delete_device_button = ButtonElement(1, MIDI_CC_TYPE, 1, 17)
        delete_device_button.add_value_listener(self._delete_device)
        # select drum pad button
        select_drum_pad_button = ButtonElement(1, MIDI_CC_TYPE, 1, 24)
        select_drum_pad_button.add_value_listener(self._select_drum_pad)
        # move device left
        move_device_left_button = ButtonElement(1, MIDI_CC_TYPE, 1, 18)
        move_device_left_button.add_value_listener(self._move_device_left)
        # move device right
        move_device_right_button = ButtonElement(1, MIDI_CC_TYPE, 1, 19)
        move_device_right_button.add_value_listener(self._move_device_right)
        # add midi track
        add_midi_track_button = ButtonElement(1, MIDI_CC_TYPE, 1, 21)
        add_midi_track_button.add_value_listener(self._add_midi_track)
        # delete midi track
        delete_midi_track_button = ButtonElement(1, MIDI_CC_TYPE, 1, 22)
        delete_midi_track_button.add_value_listener(self._delete_midi_track)
        # add return track
        add_return_track_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 91)
        add_return_track_button.add_value_listener(self._add_return_track)
        # delete return track
        delete_return_track_button = ButtonElement(1, MIDI_CC_TYPE, 1, 23)
        delete_return_track_button.add_value_listener(self._delete_return_track)
        # mixer view status
        mixer_view_status = ButtonElement(1, MIDI_NOTE_TYPE, 15, 90)
        mixer_view_status.add_value_listener(self._update_mixer_status)
        # device view status
        device_view_status = ButtonElement(1, MIDI_NOTE_TYPE, 15, 89)
        device_view_status.add_value_listener(self._update_device_status)
        # step seq status
        step_seq_status = ButtonElement(1, MIDI_NOTE_TYPE, 15, 87)
        step_seq_status.add_value_listener(self._update_step_seq)
        # adding empty clip
        add_empty_clip_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 86)
        add_empty_clip_button.add_value_listener(self._add_empty_clip)
        # creating new empty clip
        create_empty_clip_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 85)
        create_empty_clip_button.add_value_listener(self._create_new_empty_clip)
        # selecting playing clip
        select_playing_clip_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 84)
        select_playing_clip_button.add_value_listener(self._select_playing_clip)
        # cropping selected clip
        crop_clip_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 83)
        crop_clip_button.add_value_listener(self._crop_clip)
        # browser start button (CC channel 1, CC 25)
        self.browser_start_button = ButtonElement(1, MIDI_CC_TYPE, 1, 25)
        self.browser_start_button.add_value_listener(self._start_browser)
        # browser pagination button (MIDI note channel 15, note 82)
        self.browser_navigate_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 82)
        self.browser_navigate_button.add_value_listener(self._browser_navigate)
        # browser select item button (MIDI note channel 15, note 81)
        self.browser_open_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 81)
        self.browser_open_button.add_value_listener(self._browser_open_item)
        # browser load item button (MIDI note channel 15, note 80) - always loads, never opens children
        self.browser_load_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 80)
        self.browser_load_button.add_value_listener(self._browser_load_item)
        # browser go back button (MIDI note channel 15, note 79) - go one level back, remembers page
        self.browser_back_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 79)
        self.browser_back_button.add_value_listener(self._browser_go_back)


    def send_note_on(self, note_number, channel, velocity):
        channel_byte = channel & 0x7F
        note_byte = note_number & 0x7F
        velocity_byte = velocity & 0x7F
        midi_note_on_message = (0x90 | channel_byte, note_byte, velocity_byte)
        self._send_midi(midi_note_on_message)

    def send_note_off(self, note_number, channel, velocity):
        channel_byte = channel & 0x7F
        note_byte = note_number & 0x7F
        velocity_byte = velocity & 0x7F
        midi_note_off_message = (0x80 | channel_byte, note_byte, velocity_byte)
        self._send_midi(midi_note_off_message)

    def send_cc(self, cc_number, channel, value):
        channel_byte = channel & 0x7F
        cc_byte = cc_number & 0x7F
        value_byte = int(round(value)) & 0x7F
        midi_cc_message = (0xB0 | channel_byte, cc_byte, value_byte)
        self._send_midi(midi_cc_message)

    def _parameter_value_to_cc(self, device_param):
        if not hasattr(device_param, 'value') or not hasattr(device_param, 'min') or not hasattr(device_param, 'max'):
            return 0
        
        value = device_param.value
        min_val = device_param.min
        max_val = device_param.max
        
        if max_val == min_val:
            return 0
        
        normalized = (value - min_val) / (max_val - min_val)
        cc_value = int(round(normalized * 127))
        return max(0, min(127, cc_value))

    def _create_disabled_param_listener(self, device_param, control_index):
        def listener():
            cc_value = self._parameter_value_to_cc(device_param)
            cc_number = 72 + control_index
            channel = 8
            self.send_cc(cc_number, channel, cc_value)
        return listener

    def _create_automation_state_listener(self, device_param):
        def listener():
            self._refresh_parameter_metadata_on_automation_change()
        return listener

    def _refresh_automation_state_listeners_current_bank(self):
        self._remove_automation_state_listeners()
        if not hasattr(self, '_device') or not liveobj_valid(self._device):
            return
        for control in self._device._parameter_controls:
            if control.mapped_parameter():
                device_param = control.mapped_parameter()
                if device_param:
                    listener = self._create_automation_state_listener(device_param)
                    if device_param not in self._automation_state_listeners:
                        self._automation_state_listeners[device_param] = listener
                        if hasattr(device_param, 'add_automation_state_listener'):
                            device_param.add_automation_state_listener(listener)

    def _get_automation_signature(self):
        if not hasattr(self, '_device') or not liveobj_valid(self._device):
            return None
        signature = []
        for control in self._device._parameter_controls:
            mapped_param = control.mapped_parameter() if control else None
            if mapped_param and hasattr(mapped_param, 'automation_state'):
                signature.append(mapped_param.automation_state)
            else:
                signature.append(None)
        return tuple(signature)

    def _refresh_parameter_metadata_on_automation_change(self):
        if not liveobj_valid(self._device):
            return
        
        selected_track = self.song().view.selected_track
        selected_device = selected_track.view.selected_device
        
        if not selected_device or not hasattr(selected_device, 'parameters'):
            return

        current_signature = self._get_automation_signature()
        if current_signature is not None and current_signature == self._last_automation_signature:
            return
        
        # Update signature immediately so the same change doesn't re-trigger
        # while the timer is pending
        self._last_automation_signature = current_signature
        
        with self._automation_timer_lock:
            if self._automation_metadata_update_timer:
                self._automation_metadata_update_timer.cancel()
        
        self._automation_metadata_device_id = id(selected_device)
        self._automation_metadata_retry_count = 0
        self._automation_metadata_retry_start = time.time()
        seq_at_schedule = self._metadata_send_seq_by_device.get(id(selected_device), 0)
        new_timer = threading.Timer(
            0.05,
            self._send_refreshed_parameter_metadata,
            args=[selected_device, seq_at_schedule]
        )
        with self._automation_timer_lock:
            self._automation_metadata_update_timer = new_timer
        new_timer.start()

    def _send_refreshed_parameter_metadata(self, selected_device, seq_at_schedule=0):
        with self._automation_timer_lock:
            self._automation_metadata_update_timer = None
        if not selected_device or not liveobj_valid(selected_device):
            return
        if self._metadata_send_seq_by_device.get(id(selected_device), 0) != seq_at_schedule:
            return
        current_selected = self.song().view.selected_track.view.selected_device
        if current_selected != selected_device or id(selected_device) != self._automation_metadata_device_id:
            return
        current_metadata = self._build_parameter_metadata(selected_device)
        if current_metadata:
            cached_metadata = self._get_cached_metadata(selected_device)
            metadata_changed = cached_metadata != current_metadata
            if metadata_changed:
                self._send_sys_ex_message(current_metadata, 0x7D)
                self._set_cached_metadata(selected_device, current_metadata)
                self._mark_metadata_sent(selected_device)
                self._last_automation_signature = self._get_automation_signature()
            
            if metadata_changed and hasattr(selected_device, 'parameters') and selected_device.parameters:
                for control_index in range(8):
                    control = self._device_controls[control_index] if control_index < len(self._device_controls) else None
                    mapped_param = control.mapped_parameter() if control and control.mapped_parameter() else None
                    
                    if mapped_param:
                        device_param = mapped_param
                        
                        if device_param:
                            cc_value = self._parameter_value_to_cc(device_param)
                            cc_number = 72 + control_index
                            self.send_cc(cc_number, 8, cc_value)
            
            if not metadata_changed:
                elapsed = 0.0
                if self._automation_metadata_retry_start is not None:
                    elapsed = time.time() - self._automation_metadata_retry_start
                if self._automation_metadata_retry_count < 3 and elapsed < 0.3:
                    self._automation_metadata_retry_count += 1
                    new_timer = threading.Timer(
                        0.05,
                        self._send_refreshed_parameter_metadata,
                        args=[selected_device, seq_at_schedule]
                    )
                    with self._automation_timer_lock:
                        self._automation_metadata_update_timer = new_timer
                    new_timer.start()
                else:
                    self._automation_metadata_retry_count = 0
                    self._automation_metadata_retry_start = None
                    self._last_automation_signature = self._get_automation_signature()
            else:
                self._automation_metadata_retry_count = 0
                self._automation_metadata_retry_start = None

    def _remove_disabled_parameter_listeners(self):
        for (param, control_index), listener in self._disabled_parameter_listeners.items():
            if liveobj_valid(param) and hasattr(param, 'remove_value_listener'):
                if param.value_has_listener(listener):
                    param.remove_value_listener(listener)
        self._disabled_parameter_listeners.clear()
        self._disabled_parameters.clear()
        self._current_disabled_controls.clear()

    def _remove_automation_state_listeners(self):
        for param, listener in self._automation_state_listeners.items():
            if liveobj_valid(param) and hasattr(param, 'remove_automation_state_listener'):
                if hasattr(param, 'automation_state_has_listener') and param.automation_state_has_listener(listener):
                    param.remove_automation_state_listener(listener)
        self._automation_state_listeners.clear()
        self._automation_metadata_device_id = None
        self._automation_metadata_retry_count = 0
        self._automation_metadata_retry_start = None
        self._last_automation_signature = None
        
        if self._automation_metadata_update_timer:
            self._automation_metadata_update_timer.cancel()
            self._automation_metadata_update_timer = None

    def _readd_disabled_parameter_listeners(self):
        if not hasattr(self, '_device') or not liveobj_valid(self._device):
            return
        
        selected_track = self.song().view.selected_track
        selected_device = selected_track.view.selected_device
        
        if hasattr(selected_device, 'parameters') and selected_device.parameters:
            device_parameters = list(selected_device.parameters)
            
            for control_index, control in enumerate(self._device._parameter_controls):
                if control.mapped_parameter():
                    mapped_param = control.mapped_parameter()
                    
                    device_param = None
                    for dp in device_parameters:
                        if hasattr(dp, 'name') and dp.name == mapped_param.name:
                            device_param = dp
                            break
                    
                    if device_param and hasattr(device_param, 'is_enabled') and not device_param.is_enabled:
                        if (device_param, control_index) not in self._disabled_parameter_listeners:
                            listener = self._create_disabled_param_listener(device_param, control_index)
                            if not device_param.value_has_listener(listener):
                                device_param.add_value_listener(listener)
                            
                            self._disabled_parameter_listeners[(device_param, control_index)] = listener
                            self._disabled_parameters.append(device_param)
                            self._current_disabled_controls.append(control_index)
                            
                            cc_value = self._parameter_value_to_cc(device_param)
                            cc_number = 72 + control_index
                            self.send_cc(cc_number, 8, cc_value)

    def _connection_established(self, value):
        if value:            
            # self.log_message("Connection App to Ableton (still) works!")
            # send midi note on channel 3, note number 1 to confirm handshake
            midi_event_bytes = (0x90 | 0x03, 0x01, secret_version_number)
            self._send_midi(midi_event_bytes)
            
            # initializing everything else if this is not just the handshake
            if self.was_initialized is False:
                self.was_initialized = True
                self.old_clips_array = []
                self._on_tracks_changed()
                song = self.song()
                self._initialize_buttons()
                self._update_mixer_and_tracks()
                self._set_selected_track_implicit_arm()
                selected_track = song.view.selected_track
                self._send_selected_track_index(selected_track)
                self._on_selected_track_changed.subject = song.view
                # updating scale
                self._on_scale_changed()
                # track = self.song().view.selected_track
                # track.view.add_selected_device_listener(self._on_selected_device_changed)
                song.add_tracks_listener(self._on_tracks_changed)  # hier für return tracks: .add_return_tracks_listener()
                # self.song().view.add_selected_scene_listener(self._on_selected_scene_changed)
                song.add_scale_name_listener(self._on_scale_changed)
                song.add_root_note_listener(self._on_scale_changed)
                # add song tempo listener
                song.add_tempo_listener(self._update_tempo)
                # updating tempo
                self._update_tempo()
                # rest
                self._setup_device_control()
                self._register_clip_listeners()
                self.periodic_timer = 1
                self._periodic_execution()
            
            # hack to get new tracks if we have a new song.
            current_song = self.song()
            if current_song != self.song_instance:
               self._on_tracks_changed()
               self.song_instance = current_song
               current_song.add_tempo_listener(self._update_tempo)
               self._update_tempo()

    def _send_project(self, value):
        if value:
            self.old_clips_array = []
            self._update_mixer_and_tracks()
            self._update_clip_slots()
    
    def _periodic_execution(self):
        self._periodic_check()
        if self.periodic_timer == 1:
            self._periodic_timer_ref = threading.Timer(0.3, self._periodic_execution)
            self._periodic_timer_ref.start()

    def _periodic_check(self):
        # update clip slots
        # we only need to update clip slots periodically when we are in clip slots view
        # meaning not in the device view
        if self.device_status is False:
            self._update_clip_slots()

    def _redo_button_value(self, value):
        if value != 0:
            song = self.song()
            if song.can_redo:
                song.redo()
                # self._periodic_check()

    def _undo_button_value(self, value):
        if value != 0:
            song = self.song()
            if song.can_undo:
                song.undo()
                # self._periodic_check()

    def _sesh_record_value(self, value):
        if value != 0:
            record = self.song().session_record
            if record == False:
                self.song().session_record = True
            else:
                self.song().session_record = False

    def _capture_button_value(self, value):
        if value != 0:
            self.song().capture_midi()

    def _quantize_grid_value(self, value):
        global quantize_grid_value
        quantize_grid_value = value

    def _quantize_strength_value(self, value):
        global quantize_strength_value
        quantize_strength_value = value / 100.0

    def _swing_amount_value(self, value):
        global swing_amount_value
        # 100% swing amount did strange things, so I went down to 10% max
        swing_amount_value = value / 1000.0

    def _quantize_button_value(self, value):
        if value != 0:
            clip = self.song().view.detail_clip
            if clip:
                # need to set the swing amount first (0.00-1.00)
                self.song().swing_amount = swing_amount_value
                # grid (int 1 == 1/4, 2 == 1/8, 5 == 1/16, 8 = 1/32), strength (0.50 == 50%)
                clip.quantize(quantize_grid_value, quantize_strength_value)

    def _duplicate_button_value(self, value):
        if value != 0:
            self._duplicate_clip()

    def _duplicate_scene_button_value(self, value):
        if value != 0:
            song = self.song()
            selected_scene = song.view.selected_scene
            all_scenes = song.scenes
            current_index = list(all_scenes).index(selected_scene)
            song.duplicate_scene(current_index)

    def _add_empty_clip(self, value):
        """
        Adds an empty clip at the currently highlighted track and scene.
        The clip length matches the time signature numerator (one full bar).
        """
        if value != 0:
            song = self.song()
            selected_track = song.view.selected_track
    
            if selected_track is None:
                return
            
            selected_scene = song.view.selected_scene
            all_scenes = song.scenes
            scene_index = list(all_scenes).index(selected_scene)
        
            clip_slot = selected_track.clip_slots[scene_index]
            
            if clip_slot.has_clip:
                return  # Avoid overwriting an existing clip
            
            clip_length = song.signature_numerator  # Use the time signature numerator for one full bar
            clip_slot.create_clip(clip_length)
            
            # lil trick to get the clip metadata to fire
            if self.seq_status:
                if self.device_status:
                    self.start_step_seq()
    
    def _create_new_empty_clip(self, value):
        """
        Creates an empty clip at the next empty the slot in the currently highlighted track.
        The clip length matches the time signature numerator (one full bar).
        """
        if value != 0:
            song = self.song()
            selected_track = song.view.selected_track
    
            if selected_track is None:
                return
            
            selected_scene = song.view.selected_scene
            all_scenes = song.scenes
            scene_index = list(all_scenes).index(selected_scene)
            destination_scene_index = len(all_scenes)
    
            # check if there is a free clip slot after the current clip
            for index, clip_slot in enumerate(selected_track.clip_slots):
                if index <= scene_index:
                    continue
                if clip_slot.has_clip:
                    continue
                destination_scene_index = index
                break
    
            if destination_scene_index == len(all_scenes):
                # create a new scene if there is no free slot after the current slot
                song.create_scene(-1)
        
            # adding empty clip at next empty scene
            clip_slot = selected_track.clip_slots[destination_scene_index]
            clip_length = song.signature_numerator  # Use the time signature numerator for one full bar
            clip_slot.create_clip(clip_length)
            
            # selecting the empty scene
            song.view.selected_scene = song.scenes[destination_scene_index]
    
    def _select_playing_clip(self, value):
        if value != 0:
            song = self.song()
            selected_track = song.view.selected_track
    
            if selected_track is None:
                return
            
            for index, clip_slot in enumerate(selected_track.clip_slots):
                if clip_slot.is_playing:
                    song.view.selected_scene = song.scenes[index]
                    break
    
    def _crop_clip(self, value):
        if value != 0:
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            
            if clip_slot and clip_slot.has_clip:
                clip = clip_slot.clip
                clip.crop()
    
    def _duplicate_clip(self):
        song = self.song()
        selected_track = song.view.selected_track

        if selected_track is None:
            return

        selected_scene = song.view.selected_scene
        all_scenes = song.scenes
        scene_index = list(all_scenes).index(selected_scene)
        track_index = list(song.tracks).index(selected_track)
        destination_scene_index = len(all_scenes)

        # checking if clip was playing
        was_playing = song.view.highlighted_clip_slot.is_playing == 1

        # check if there is a free clip slot after the current clip
        for index, clip_slot in enumerate(selected_track.clip_slots):
            if index <= scene_index:
                continue
            if clip_slot.has_clip:
                continue
            destination_scene_index = index
            break

        if destination_scene_index == len(all_scenes):
            # create a new scene if there is no free slot after the current slot
            song.create_scene(-1)

        self._copy_paste_clip(track_index, scene_index, track_index, destination_scene_index)

        # select newly created clip
        song.view.selected_scene = song.scenes[destination_scene_index]
        # fire the new clip if the old clip was playing
        if was_playing:
            song.view.highlighted_clip_slot.fire(force_legato=True)
        
        # set up everything new
        self._on_selected_track_changed()

    @subject_slot('selected_track')
    def _on_selected_track_changed(self):
        if self.was_initialized:
            selected_track = self.song().view.selected_track
            track_has_midi_input = 0
            if selected_track and selected_track.has_midi_input:
                self._set_selected_track_implicit_arm()
                track_has_midi_input = 1
            self._set_up_notes_playing(selected_track)
            self._set_other_tracks_implicit_arm()
            # send new index of selected track
            self._send_selected_track_index(selected_track)
            self._on_selected_scene_changed()
            # send sys ex of track midi input status.
            self._send_sys_ex_message(str(track_has_midi_input), 0x0B)
            # TODO: this part doesn't seem to work? how can I make this work with master and return?
            device_to_select = selected_track.view.selected_device
            if device_to_select is None and len(selected_track.devices) > 0:
                device_to_select = selected_track.devices[0]
            if device_to_select is not None:
                self._track_change_in_progress = True
                self.song().view.select_device(device_to_select)
                self._track_change_in_progress = False
            self._device_component.set_device(device_to_select)
            # _on_device_changed is already called by select_device above via
            # the @subject_slot('device') listener. Only call it explicitly
            # when no device was selected (listener won't fire).
            if device_to_select is None:
                self._on_device_changed()
            self._check_clip_playing_status()
            if self.seq_status:
                if self.device_status:
                    self.start_step_seq()

    def _set_up_notes_playing(self, selected_track):
        if selected_track != "clip":
            # Only remove playing position listeners from the PREVIOUSLY selected track,
            # not from all tracks. This changes O(tracks * clips) to O(clips).
            if hasattr(self, '_previous_selected_track') and self._previous_selected_track is not None:
                old_track = self._previous_selected_track
                if liveobj_valid(old_track):
                    for (clip_index, clip_slot) in enumerate(old_track.clip_slots):
                        if clip_slot is not None and clip_slot.has_clip:
                            if clip_slot.clip.playing_position_has_listener(self.playing_position_listeners[clip_index]):
                                clip_slot.clip.remove_playing_position_listener(self.playing_position_listeners[clip_index])
            self._previous_selected_track = selected_track
        else:
            selected_track = self.song().view.selected_track

        if selected_track.has_midi_input:
            for (clip_index, clip_slot) in enumerate(selected_track.clip_slots):
                if clip_slot is not None and clip_slot.has_clip:
                    if not clip_slot.clip.playing_position_has_listener(self.playing_position_listeners[clip_index]):
                        # self.log_message("adding pos listener: {}".format(clip_index))
                        listener = lambda index=clip_index: self._clip_pos_changed(index)
                        self.playing_position_listeners[clip_index] = listener
                        clip_slot.clip.add_playing_position_listener(listener)

    def _check_clip_playing_status(self):
        song = self.song()
        selected_track = song.view.selected_track
        highlighted_clip_slot_playing = getattr(song.view.highlighted_clip_slot, 'is_playing', False)
        
        if highlighted_clip_slot_playing:
            # Ensure status is 0 if the highlighted clip is playing
            new_status = 0
        else:
            # Check if any other clip is playing
            another_clip_playing = any(clip_slot.is_playing for clip_slot in selected_track.clip_slots if clip_slot.has_clip)
            new_status = 1 if another_clip_playing else 2
        
        # Update status only if it has changed
        if self.seq_clip_playing_status != new_status:
            self.seq_clip_playing_status = new_status
            velocity_map = {0: 100, 1: 200, 2: 300}
            velocity = velocity_map[new_status] & 0x7F
            self.send_note_on(2, 3, velocity)

    def _clip_pos_changed(self, clip_index):
        # Only check and send things if we are in device view
        if self.device_status:
            song = self.song()
            selected_track = song.view.selected_track

            if clip_index < len(selected_track.clip_slots):
                clip_slot = selected_track.clip_slots[clip_index]

                if clip_slot is not None and clip_slot.has_clip:
                    clip_playing = clip_slot.clip
                    
                    clip_start = min(clip_playing.start_time, clip_playing.start_marker, clip_playing.loop_start) - self.clip_length_trick
                    time_span = (max(clip_playing.loop_end, clip_playing.end_marker, clip_playing.length) + self.clip_length_trick) - clip_start
                    loop_start = clip_playing.loop_start
                    
                    try:
                        # Get all the notes in the clip
                        current_raw_notes = clip_playing.get_notes_extended(0, 128, clip_start, time_span)
                        
                        # if the current clip has different notes save the new notes.
                        if current_raw_notes is not self.last_raw_notes:
                            self.last_raw_notes = current_raw_notes

                            # Reset the current clip notes array
                            self.current_clip_notes = []
                            # add all the notes to the array
                            for midi_note in current_raw_notes:
                                pitch = midi_note.pitch
                                duration = midi_note.duration
                                note_start_time = midi_note.start_time
                                # Process note properties as needed
                                # self.log_message("Note: Pitch {}, Start Time {}, Duration {}".format(pitch, start_time, duration))
                                end_time = note_start_time + duration
                                self.current_clip_notes.append([pitch, note_start_time, end_time])

                        # check which notes are playing at position
                        # if we detect changes send them out to app
                        clip_position = clip_playing.playing_position
                        
                        # clip status no mater the seq_status
                        self._check_clip_playing_status()
                        
                        if self.seq_status:
                            if song.view.highlighted_clip_slot.is_playing:
                                self.send_out_playing_pos(clip_position)
                                self.last_sent_out_playing_pos = clip_position
                            else:
                                # reseting the playing position
                                if self.last_sent_out_playing_pos != 0.0:
                                    self.last_sent_out_playing_pos = 0.0
                                    self.send_out_playing_pos(self.last_sent_out_playing_pos)
                                
                        else:
                            # making sure we have the right starting position, when jumping back to the start of clip or loop
                            if self.last_playing_position > clip_position:
                                if clip_position >= loop_start:
                                    self.last_playing_position = loop_start
                                else:
                                    self.last_playing_position = clip_playing.start_marker
    
                            # check if currently playing notes are still playing in this playing position
                            for (note_index, is_playing) in enumerate(self.currently_playing_notes):
                                if is_playing:
                                    # Initialize a flag to indicate if a playing note was found
                                    found_playing_note = False
    
                                    # Find the notes that stopped playing in since the last update
                                    for note in self.current_clip_notes:
                                        pitch, note_start_time, end_time = note
    
                                        if note_start_time <= self.last_playing_position and clip_position < end_time and pitch == note_index:
                                            # Note is still playing
                                            found_playing_note = True
                                            break
    
                                    # If no playing note was found, update the state
                                    if not found_playing_note:
                                        self.currently_playing_notes[note_index] = False
                                        # send note off for note_index note.
                                        # self.log_message("Note off: {}".format(note_index))
                                        self.send_note_off(note_index, 0, 100)
    
                            # check current clip notes array which notes are on for that playing position
                            for note in self.current_clip_notes:
                                pitch, note_start_time, end_time = note
                                if self.last_playing_position <= note_start_time <= clip_position:
                                    # note starts playing
                                    self.currently_playing_notes[pitch] = True
                                    # send midi note on
                                    # self.log_message("Note on: {}".format(pitch))
                                    self.send_note_on(pitch, 0, 100)
                            # update last playing position
                            self.last_playing_position = clip_position
                    except Exception as e:
                        self._debug_log(f"Exception for clip position changed: {str(e)}")
                        import traceback
                        self._debug_log(traceback.format_exc())
                        pass
                # else:
                    # self.log_message("No valid clip in the slot.")

    def _send_selected_track_index(self, selected_track):
        track_list = self.song().tracks
        track_index = self._find_track_index(selected_track, track_list)
        self._send_sys_ex_message(track_index, 0x03)
        if track_index == "not found":
            return_tracks_list = self.song().return_tracks
            return_track_index = self._find_track_index(selected_track, return_tracks_list)
            if return_track_index == "not found":
                return_track_index = str(len(return_tracks_list))
            self._send_sys_ex_message(return_track_index, 0x08)
        else:
            self._send_sys_ex_message("none selected", 0x08)

    def _find_track_index(self, track, track_list):
        for index, t in enumerate(track_list):
            if track == t:
                return str(index)
        return "not found" # Track not found

    def _select_device_by_index(self, value):
        selected_track = self.song().view.selected_track
        all_devices = self._get_all_nested_devices(selected_track.devices)[0]
        device_to_select = all_devices[value]
        self.song().view.select_device(device_to_select)

    def _select_track_by_index(self, track_index):
        # self.log_message("Getting track: {}".format(track_index))
        song = self.song()
        if track_index >= 0 and track_index < len(song.tracks):
            song.view.selected_track = song.tracks[track_index]
        else:
            self._debug_log("Invalid track index: {}".format(track_index))

    def _select_return_track_by_index(self, track_index):
        song = self.song()
        if track_index < len(song.return_tracks):
            return_track = song.return_tracks[track_index] 
            song.view.selected_track = return_track
        else:
            master_track = song.master_track 
            song.view.selected_track = master_track

    def _set_selected_track_implicit_arm(self):
        selected_track = self.song().view.selected_track
        if selected_track and selected_track.has_midi_input:
            try:
                selected_track.implicit_arm = True
            except Exception:
                pass
        # else:
        #     try:
        #         self.song().tracks[0].implicit_arm = True
        #     except Exception:
        #         pass

    def _set_other_tracks_implicit_arm(self):
        for track in self.song().tracks:
            if track != self.song().view.selected_track:
                try:
                    track.implicit_arm = False
                except Exception:
                    pass

    def _on_tracks_changed(self):
        if self._metadata_recheck_timer:
            self._metadata_recheck_timer.cancel()
            self._metadata_recheck_timer = None
        self._metadata_cache.clear()
        self._metadata_send_seq_by_device.clear()
        self._update_mixer_and_tracks()
        self._register_clip_listeners()
        self._update_clip_slots()

    def _make_color_string(self, color):
        red = (color >> 16) & 255
        green = (color >> 8) & 255
        blue = color & 255
        color_string = "({},{},{})".format(red, green, blue)
        return color_string

    def _on_color_name_changed(self):
        self._update_mixer_and_tracks()
        self._on_selected_track_changed()
    
    def _create_level_change_handler(self, index):
        """
        A factory that returns a handler function for a specific index.
        This guarantees the index is correctly captured.
        """
        def handler():
            self._on_output_level_changed(index)
        return handler
    
    # Updating names and number of tracks
    def _update_mixer_and_tracks(self):
        tracks = list(self.song().tracks)
        return_tracks = list(self.song().return_tracks)
        master_track = self.song().master_track

        track_signature = (tuple(id(t) for t in tracks), tuple(id(t) for t in return_tracks))
        tracks_changed = track_signature != self._track_list_signature
        
        if tracks_changed:
            # 1. Remove all old listeners to prevent leaks
            for track, (left_listener, right_listener) in self._track_level_listeners.items():
                if liveobj_valid(track) and hasattr(track, 'output_meter_left_has_listener') and track.output_meter_left_has_listener(left_listener):
                    track.remove_output_meter_left_listener(left_listener)
                if liveobj_valid(track) and hasattr(track, 'output_meter_right_has_listener') and track.output_meter_right_has_listener(right_listener):
                    track.remove_output_meter_right_listener(right_listener)
            self._track_level_listeners.clear()

            for track, (left_listener, right_listener) in self._return_level_listeners.items():
                if liveobj_valid(track) and hasattr(track, 'output_meter_left_has_listener') and track.output_meter_left_has_listener(left_listener):
                    track.remove_output_meter_left_listener(left_listener)
                if liveobj_valid(track) and hasattr(track, 'output_meter_right_has_listener') and track.output_meter_right_has_listener(right_listener):
                    track.remove_output_meter_right_listener(right_listener)
            self._return_level_listeners.clear()
            
            if self._master_level_listeners:
                left_listener, right_listener = self._master_level_listeners.get(master_track, (None, None))
                if left_listener and hasattr(master_track, 'output_meter_left_has_listener') and master_track.output_meter_left_has_listener(left_listener):
                    master_track.remove_output_meter_left_listener(left_listener)
                if right_listener and hasattr(master_track, 'output_meter_right_has_listener') and master_track.output_meter_right_has_listener(right_listener):
                    master_track.remove_output_meter_right_listener(right_listener)
                self._master_level_listeners.clear()
            self._track_list_signature = track_signature

            # 2. Build track names, types, colors and send via SysEx
            track_names = []
            track_is_audio = []
            track_colors = []
            
            for index, track in enumerate(tracks):
                track_names.append(track.name)
                if any(clip_slot.is_group_slot for clip_slot in track.clip_slots):
                    track_is_audio.append("2")
                elif track.is_grouped:
                    if track.has_audio_input:
                        track_is_audio.append("4")
                    else:
                        track_is_audio.append("3")
                elif track.has_audio_input:
                    track_is_audio.append("1")
                else:
                    track_is_audio.append("0")
                color_string = self._make_color_string(track.color)
                track_colors.append(color_string)

            self._send_sys_ex_message(",".join(track_names), 0x02)
            self._send_sys_ex_message(",".join(track_is_audio), 0x0C)
            self._send_sys_ex_message("-".join(track_colors), 0x04)

            return_track_names = []
            return_track_colors = []
            for index, return_track in enumerate(return_tracks):
                return_track_names.append(return_track.name)
                return_track_colors.append(self._make_color_string(return_track.color))

            color_string = self._make_color_string(master_track.color)
            return_track_colors.append(color_string)
            self._send_sys_ex_message(",".join(return_track_names), 0x06)
            self._send_sys_ex_message("-".join(return_track_colors), 0x07)
        
        # 3. Set up level meter listeners (idempotent, safe to call every time)
        for index, track in enumerate(tracks):
            if track.has_audio_output:
                if track not in self._track_level_listeners:
                    left_handler = self._create_level_change_handler(index)
                    right_handler = self._create_level_change_handler(index)
                    track.add_output_meter_left_listener(left_handler)
                    track.add_output_meter_right_listener(right_handler)
                    self._track_level_listeners[track] = (left_handler, right_handler)

            if not track.color_has_listener(self._on_color_name_changed):
                track.add_color_listener(self._on_color_name_changed)
            if not track.name_has_listener(self._on_color_name_changed):
                track.add_name_listener(self._on_color_name_changed)

        for index, return_track in enumerate(return_tracks):
            if hasattr(return_track, 'add_output_meter_left_listener'):
                return_index = index + len(tracks)
                if return_track not in self._return_level_listeners:
                    left_handler = self._create_level_change_handler(return_index)
                    right_handler = self._create_level_change_handler(return_index)
                    return_track.add_output_meter_left_listener(left_handler)
                    return_track.add_output_meter_right_listener(right_handler)
                    self._return_level_listeners[return_track] = (left_handler, right_handler)

        if hasattr(master_track, 'add_output_meter_left_listener'):
            master_index = 127
            if master_track not in self._master_level_listeners:
                left_handler = self._create_level_change_handler(master_index)
                right_handler = self._create_level_change_handler(master_index)
                master_track.add_output_meter_left_listener(left_handler)
                master_track.add_output_meter_right_listener(right_handler)
                self._master_level_listeners[master_track] = (left_handler, right_handler)

        self._set_up_mixer_controls()
        
    def _set_up_mixer_controls(self):
        song = self.song()
        tracks = song.tracks
        return_tracks = song.return_tracks
        # - 1 because visible_channels is starting at 0
        last_track_index = len(tracks) - 1
        
        number_of_return_tracks = len(return_tracks)
        number_of_return_tracks_visible = self.visible_channels[1] - last_track_index
        master_track_visible = number_of_return_tracks_visible > number_of_return_tracks
        # self.log_message(f"visible_channels[0]: {self.visible_channels[0]}")
        # self.log_message(f"visible_channels[1]: {self.visible_channels[1]}")
        # self.log_message(f"master_track_visible: {master_track_visible}")
        
        # if last is 9, and last track is 7 -> last visible return is 1
        last_visible_return_index = self.visible_channels[1] - len(tracks)
        # if first is 8, and last track is 7 -> first visible return is 0
        first_visible_return_index = self.visible_channels[0] - len(tracks)
        # self.log_message(f"first_visible_return_index: {first_visible_return_index}")
        # self.log_message(f"last_visible_return_index: {last_visible_return_index}")
        
        # Channels
        for index, track in enumerate(tracks):

            strip = mixer.channel_strip(index)

            # Configure strip controls for each channel track
            if self.mixer_status and index >= self.visible_channels[0] and index <= self.visible_channels[1]:
                strip.set_volume_control(SliderElement(MIDI_CC_TYPE, 2, index))
                strip.set_send_controls((
                    EncoderElement(MIDI_CC_TYPE, 3, index, Live.MidiMap.MapMode.absolute),
                    EncoderElement(MIDI_CC_TYPE, 4, index, Live.MidiMap.MapMode.absolute)
                ))
                strip.set_pan_control(EncoderElement(MIDI_CC_TYPE, 5, index, Live.MidiMap.MapMode.absolute))
                strip.set_mute_button(ButtonElement(1, MIDI_CC_TYPE, 6, index))
                strip.set_solo_button(ButtonElement(1, MIDI_CC_TYPE, 7, index))
                # reseting volume just in case
                self._on_output_level_changed(index)
            else:
                strip.set_volume_control(None)
                strip.set_send_controls(None)
                strip.set_pan_control(None)
                strip.set_mute_button(None)
                strip.set_solo_button(None)

            # Other strip controls can be configured similarly
            # strip.set_arm_button(...)
            # strip.set_shift_button(...)

        # Master / channel 7 cc 127
        if self.mixer_status and master_track_visible:
            mixer.master_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, 0, 127))
            mixer.set_prehear_volume_control(EncoderElement(MIDI_CC_TYPE, 0, 126, Live.MidiMap.MapMode.absolute))
            mixer.master_strip().set_pan_control(EncoderElement(MIDI_CC_TYPE, 0, 125, Live.MidiMap.MapMode.absolute))
            # reseting volume just in case
            self._on_output_level_changed(127)
        else:
            mixer.master_strip().set_volume_control(None)
            mixer.set_prehear_volume_control(None)
            mixer.master_strip().set_pan_control(None)

        # Return Tracks
        for index, returnTrack in enumerate(return_tracks):
            strip = mixer.return_strip(index)

            if self.mixer_status and index <= last_visible_return_index and index >= first_visible_return_index:
                strip.set_volume_control(SliderElement(MIDI_CC_TYPE, 8, index))
                strip.set_mute_button(ButtonElement(1, MIDI_CC_TYPE, 8, index + 12))
                strip.set_solo_button(ButtonElement(1, MIDI_CC_TYPE, 8, index + 24))
                strip.set_send_controls((
                    EncoderElement(MIDI_CC_TYPE, 8, index + 36, Live.MidiMap.MapMode.absolute),
                    EncoderElement(MIDI_CC_TYPE, 8, index + 48, Live.MidiMap.MapMode.absolute)
                ))
                strip.set_pan_control(EncoderElement(MIDI_CC_TYPE, 8, index + 60, Live.MidiMap.MapMode.absolute))
                # reseting volume just in case
                self._on_output_level_changed(index + len(tracks))
            else:
                strip.set_volume_control(None)
                strip.set_mute_button(None)
                strip.set_solo_button(None)
                strip.set_send_controls(None)
                strip.set_pan_control(None)
        
    def _on_output_level_changed(self, index):
        if self.mixer_status:
            if not self.mixer_reset:
                self.mixer_reset = True
            song = self.song()
            tracks = song.tracks
            return_tracks = song.return_tracks
            is_visible_track = index >= self.visible_channels[0] and index <= self.visible_channels[1]            
            is_visible_master = index == 127 and (len(tracks) + len(return_tracks) - 1) < self.visible_channels[1]
            
            if is_visible_track or is_visible_master:
                if index < len(tracks):
                    track = tracks[index]
                elif index - len(tracks) < len(return_tracks):
                    track = return_tracks[index - len(tracks)]
                else:
                    track = song.master_track
    
                if track.has_audio_output:
                    left_channel = track.output_meter_left
                    right_channel = track.output_meter_right
                else:
                    left_channel = 0.0
                    right_channel = 0.0
    
                value_left = int(round(left_channel * 100))
                value_right = int(round(right_channel * 100))
    
                # send midi cc left on channel 9, right on channel 10, cc == index, 
                # value == Int(left_channel * 100)
    
                status_byte_left = 0xB8 | 9  # MIDI CC message on channel 9
                midi_cc_message_left = (status_byte_left, index, value_left)
                self._send_midi(midi_cc_message_left)
                status_byte_right = 0xB8 | 10  # MIDI CC message on channel 10
                midi_cc_message_right = (status_byte_right, index, value_right)
                self._send_midi(midi_cc_message_right)

        elif self.mixer_reset:
            self.mixer_reset = False

            song = self.song()
            tracks = song.tracks
            return_tracks = song.return_tracks
            value = 0
            total_track_number = len(tracks) + len(return_tracks) + 1

            for index in range(total_track_number):
                status_byte_left = 0xB8 | 9  # MIDI CC message on channel 9
                midi_cc_message_left = (status_byte_left, index, value)
                self._send_midi(midi_cc_message_left)
                status_byte_right = 0xB8 | 10  # MIDI CC message on channel 10
                midi_cc_message_right = (status_byte_right, index, value)
                self._send_midi(midi_cc_message_right)

    def _get_track_index(self, track):
        if not track:
            return None
        try:
            return list(self.song().tracks).index(track)
        except ValueError:
            return None

    def _make_clip_has_clip_listener(self, track):
        def listener():
            self._on_clip_has_clip_changed(track)
        return listener

    def _make_clip_triggered_listener(self, track):
        def listener():
            self._on_clip_playing_status_changed(track)
        return listener

    def _make_clip_color_listener(self, track):
        def listener():
            self._on_clip_has_clip_changed(track)
        return listener

    def _sync_clip_color_listeners_for_track(self, track):
        for clip_slot in track.clip_slots:
            if clip_slot is None:
                continue
            if clip_slot.has_clip:
                current_clip = clip_slot.clip
                previous_clip = self._clip_slot_color_map.get(clip_slot)
                if previous_clip is not None and previous_clip != current_clip:
                    old_listener = self._clip_color_listeners.pop(previous_clip, None)
                    if old_listener and liveobj_valid(previous_clip) and previous_clip.color_has_listener(old_listener):
                        previous_clip.remove_color_listener(old_listener)
                if current_clip not in self._clip_color_listeners:
                    listener = self._make_clip_color_listener(track)
                    self._clip_color_listeners[current_clip] = listener
                    current_clip.add_color_listener(listener)
                self._clip_slot_color_map[clip_slot] = current_clip
            else:
                previous_clip = self._clip_slot_color_map.pop(clip_slot, None)
                if previous_clip is not None:
                    old_listener = self._clip_color_listeners.pop(previous_clip, None)
                    if old_listener and liveobj_valid(previous_clip) and previous_clip.color_has_listener(old_listener):
                        previous_clip.remove_color_listener(old_listener)

    # clipSlots
    def _register_clip_listeners(self):
        current_track_ids = set()
        for track in self.song().tracks:
            track_id = id(track)
            current_track_ids.add(track_id)
            
            # Skip tracks that already have all their listeners registered
            if track_id in self._registered_track_ids:
                continue
            
            for clip_slot in track.clip_slots:

                if clip_slot == None:
                    continue

                listener_key = (clip_slot, 'has_clip')
                if listener_key not in self._clip_slot_listeners:
                    listener = self._make_clip_has_clip_listener(track)
                    self._clip_slot_listeners[listener_key] = listener
                    clip_slot.add_has_clip_listener(listener)

                listener_key = (clip_slot, 'is_triggered')
                if listener_key not in self._clip_slot_listeners:
                    listener = self._make_clip_triggered_listener(track)
                    self._clip_slot_listeners[listener_key] = listener
                    clip_slot.add_is_triggered_listener(listener)
            
            self._registered_track_ids.add(track_id)
        
        # Clean up stale entries for tracks that no longer exist
        self._registered_track_ids &= current_track_ids
        
        # Sync color listeners for all tracks
        for track in self.song().tracks:
            self._sync_clip_color_listeners_for_track(track)

    def _unregister_clip_and_audio_listeners(self):
        for track in self.song().tracks:
            for clip_slot in track.clip_slots:
                listener_key = (clip_slot, 'is_triggered')
                listener = self._clip_slot_listeners.pop(listener_key, None)
                if listener:
                    clip_slot.remove_is_triggered_listener(listener)
                else:
                    clip_slot.remove_is_triggered_listener(self._on_clip_playing_status_changed)
                
                listener_key = (clip_slot, 'has_clip')
                listener = self._clip_slot_listeners.pop(listener_key, None)
                if listener:
                    clip_slot.remove_has_clip_listener(listener)
                else:
                    clip_slot.remove_has_clip_listener(self._on_clip_has_clip_changed)
                
                if clip_slot.has_clip:
                    listener = self._clip_color_listeners.pop(clip_slot.clip, None)
                    if listener:
                        clip_slot.clip.remove_color_listener(listener)
                    else:
                        clip_slot.clip.remove_color_listener(self._on_clip_has_clip_changed)
                # if clip_slot.has_clip:
                #     # clip_slot.clip.remove_playing_status_listener(self._on_clip_playing_status_changed)
                #     clip_slot.clip.remove_playing_position_listener(self._on_playing_position_changed)
            # output meter listeners - use stored handler references
            if track in self._track_level_listeners:
                left_listener, right_listener = self._track_level_listeners[track]
                if liveobj_valid(track) and hasattr(track, 'output_meter_left_has_listener') and track.output_meter_left_has_listener(left_listener):
                    track.remove_output_meter_left_listener(left_listener)
                if liveobj_valid(track) and hasattr(track, 'output_meter_right_has_listener') and track.output_meter_right_has_listener(right_listener):
                    track.remove_output_meter_right_listener(right_listener)

        for return_track, (left_listener, right_listener) in self._return_level_listeners.items():
            if liveobj_valid(return_track) and hasattr(return_track, 'output_meter_left_has_listener') and return_track.output_meter_left_has_listener(left_listener):
                return_track.remove_output_meter_left_listener(left_listener)
            if liveobj_valid(return_track) and hasattr(return_track, 'output_meter_right_has_listener') and return_track.output_meter_right_has_listener(right_listener):
                return_track.remove_output_meter_right_listener(right_listener)
        
        self._track_level_listeners.clear()
        self._return_level_listeners.clear()
        self._clip_listener_track_slots.clear()
        self._clip_slot_listeners.clear()
        self._clip_color_listeners.clear()
        self._clip_slot_color_map.clear()

    # def _on_playing_position_changed(self):
    #     # self.log_message("trying to log the playing position")
    #     self._update_clip_slots()

    def find_different_indexes(self, arrays1, arrays2):
        different_indexes = []

        for index, (array1, array2) in enumerate(zip_longest(arrays1, arrays2)):
            if array1 != array2:
                different_indexes.append(index)

        return different_indexes

    def _on_clip_playing_status_changed(self, track=None):
        # self.log_message("clip playing status changed")
        self._refresh_parameter_metadata_on_automation_change()
        if track:
            track_index = self._get_track_index(track)
            if track_index is not None:
                self._update_clip_slots(track_index)
                return
        self._update_clip_slots()

    def _on_clip_has_clip_changed(self, track=None):
        # self.log_message("has clip status changed")
        self._refresh_parameter_metadata_on_automation_change()
        if track:
            track_index = self._get_track_index(track)
            if track_index is not None:
                self._update_clip_slots(track_index)
                self._sync_clip_color_listeners_for_track(track)
                self._set_up_notes_playing("clip")
                return
        self._update_clip_slots()
        self._set_up_notes_playing("clip")

    def _update_clip_slots(self, only_track_index=None):
        try:
            track_clips = []
            tracks = self.song().tracks
            if only_track_index is not None and len(self.old_clips_array) != len(tracks):
                only_track_index = None
            for track_index, track in enumerate(tracks):
                if only_track_index is not None and track_index != only_track_index:
                    track_clips.append(self.old_clips_array[track_index] if track_index < len(self.old_clips_array) else "")
                    continue
                try:
                    is_armed = track.arm
                    has_audio = track.has_audio_input
                except Exception:
                    is_armed = False
                    has_audio = False
                # track clip slots
                clip_slots = []
                try:
                    for clip_slot in track.clip_slots:
                        clip_value = "0"
                        try:
                            if clip_slot.is_triggered:
                                clip_value = "4"
                            elif clip_slot.is_recording:
                                clip_value = "3"
                            elif clip_slot.is_playing:
                                clip_value = "2"
                            elif clip_slot.has_clip:
                                clip_value = "1"
                            elif is_armed and has_audio:
                                clip_value = "5"
                        except Exception:
                            clip_value = "0"

                        color_string_value = "0"
                        
                        # this could also just be made to if value == "1", but does not hurt this way
                        if clip_value != "0" and clip_slot.has_clip:
                            # extra test if has clip because group channels don't have a clip but might be triggered etc
                            try:
                                if clip_slot.clip.color is not None:
                                    color_string_value = self._make_color_string(clip_slot.clip.color)
                            except Exception:
                                color_string_value = "0"
                        #     playing_position = clip_slot.clip.playing_position
                        #     length = clip_slot.clip.length
                        #     self.log_message("playing: {} triggering {}".format(is_playing_value, is_triggered_value))
                        # else:
                        #     playing_position = 0.0
                        #     length = 0.0

                        clip_string = "{}:{}".format(clip_value, color_string_value)
                        clip_slots.append(clip_string)
                except Exception as e:
                    pass
                clip_slots_string = "-".join(clip_slots)
                track_clips.append(clip_slots_string)

            # compare old track clips with new
            clips_difference = self.find_different_indexes(track_clips, self.old_clips_array)
            
            # safe new values
            self.old_clips_array = track_clips

            # send different tracks out
            # TODO: now this still does send out each track. not sure why. also it should only send out the clip that is changed and not the whole track I would say.
            if clips_difference != []:
                for track_index in clips_difference:
                    if int(track_index) < len(track_clips):
                        string_prefix = str(track_index) + "%"
                        track_string = string_prefix + str(track_clips[track_index])
                        self._send_sys_ex_message(track_string, 0x05)
                    else:
                        delete_clips = "DEL" + str(track_index)
                        self._send_sys_ex_message(delete_clips, 0x05)
        except Exception as e:
            # need to stop threading or we get a fatal error.
            # self.periodic_timer = 0
            pass

    def _on_scale_changed(self):
        song = self.song()
        scale = song.scale_name
        root = song.root_note
        scale_string = "{};{}".format(scale, root)
        self._send_sys_ex_message(scale_string, 0x0A)

    def handle_sysex(self, message):
        """
        Handles incoming SysEx messages, including multi-part (chunked) ones.
        Chunks start with '$' (more coming) or '_' (final chunk).
        Only for manufacturer ID 16, 15, 14 (Modify Notes).
        """
        # Ensure we have a buffer for assembling chunks
        if not hasattr(self, "_sysex_buffer"):
            self._sysex_buffer = []
    
        # Basic validity check
        if len(message) < 3:
            self._sysex_buffer = []
            return
        
        manufacturer_id = message[1]
        prefix = message[2]
    
        # Check if this message is chunked (when manufacturer_id == 16)
        if manufacturer_id == 16 or manufacturer_id == 15 or manufacturer_id == 14:
            if prefix == 36:
                # Intermediate chunk
                self._sysex_buffer.extend(message[3:-1])  # skip F0, manuf, prefix, F7
                return
        
            elif prefix == 95:
                # Final chunk — assemble full message
                self._sysex_buffer.extend(message[3:-1])
                full_message = [0xF0, manufacturer_id] + self._sysex_buffer + [0xF7]
                self._sysex_buffer = []  # reset buffer
        
                # Now call the original handler
                self._handle_full_sysex(full_message)
                return
            
            else:
                # Cancel chunking, something went wrong
                self._sysex_buffer = []
                return
        
        else:
            if self._sysex_buffer != []:
                # Cancel chunking, something went wrong
                self._sysex_buffer = []
                return
                
            else:
                # Non-chunked message → handle directly
                self._handle_full_sysex(message)

    def _handle_full_sysex(self, message):
        # start stop clip
        if len(message) >= 2 and message[1] == 9:
            values = self.extract_values_from_sysex_message(message)
            if len(values) == 3:
                self._fire_clip(values[0], values[1], values[2])
        # delete clip
        if len(message) >= 2 and message[1] == 10:
            values = self.extract_values_from_sysex_message(message)
            if len(values) == 2:
                self._delete_clip(values[0], values[1])
        # copy paste clip
        if len(message) >= 2 and message[1] == 11:
            values = self.extract_values_from_sysex_message(message)
            if len(values) == 4:
                self._copy_paste_clip(values[0], values[1], values[2], values[3])
        # scale and rootnote
        if len(message) >= 2 and message[1] == 12:
            values = self.decode_sys_ex_scale_root(message)
            if len(values) == 2:
                self._set_scale_root_note(values[0], values[1])
        # duplicate loop
        if len(message) >= 2 and message[1] == 13:
            values = self.extract_values_from_sysex_message(message)
            if len(values) == 2:
                self._duplicate_loop(values[0], values[1])
        
        # add MULTIPLE notes
        if len(message) >= 2 and message[1] == 14:
            index = 2
            new_notes = []

            # Decode all notes in the message
            while index < (len(message) - 1):
                # Decode the pitch of the note
                note_pitch = message[index]
                index += 1

                # Decode the start time (3 bytes, 7-bit packed)
                if index + 3 > len(message):
                    break
                start_time = self._from_3_7bit_bytes(message, index)
                index += 3

                # Decode the duration (3 bytes, 7-bit packed)
                if index + 3 > len(message):
                    break
                duration = self._from_3_7bit_bytes(message, index)
                index += 3

                # Decode velocity
                if index >= len(message):
                    break
                velocity = message[index]
                index += 1

                # Decode mute and probability
                if index >= len(message):
                    break
                mute_and_probability = message[index]
                mute = (mute_and_probability & 0x80) != 0
                probability = (mute_and_probability & 0x7F) / 127.0
                index += 1

                # Create a MidiNoteSpecification object
                note_spec = MidiNoteSpecification(
                    pitch=note_pitch,
                    start_time=start_time / 1000.0,
                    duration=duration / 1000.0,
                    velocity=velocity,
                    mute=mute,
                    probability=probability
                )

                new_notes.append(note_spec)

            # Add all decoded notes to the current clip
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            if clip_slot is not None and clip_slot.has_clip and len(new_notes) > 0:
                clip = clip_slot.clip
                clip.add_new_notes(new_notes)
        
        # remove note (also multiple)
        if len(message) >= 2 and message[1] == 15:
            note_ids = []
            index = 2
            while index < (len(message) - 1):
                note_id = message[index] | (message[index + 1] << 7)
                note_ids.append(note_id)
                index += 2
        
            # Get the selected clip
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            if clip_slot is not None and clip_slot.has_clip:
                clip = clip_slot.clip
        
                # Remove the note by ID
                clip.remove_notes_by_id(note_ids)
        
        # modify MULTIPLE notes
        if len(message) >= 3 and message[1] == 16:
            index = 2
        
            # Get the selected clip
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            if clip_slot is not None and clip_slot.has_clip:
                clip = clip_slot.clip
                
                # Fetch existing notes from the clip
                clip_start = min(clip.start_time, clip.start_marker, clip.loop_start) - self.clip_length_trick
                clip_length = (max(clip.loop_end, clip.end_marker, clip.length) + self.clip_length_trick) - clip_start
                notes = clip.get_notes_extended(0, 128, clip_start, clip_length)
        
                # Modify the matching notes
                while index < (len(message) - 1):
                    note_id = message[index] | (message[index + 1] << 7)
                    pitch = message[index + 2]
                    index += 3
        
                    start_time_raw = self._from_3_7bit_bytes(message, index)
                    start_time = start_time_raw / 1000.0
                    index += 3
        
                    duration_raw = self._from_3_7bit_bytes(message, index)
                    duration = duration_raw / 1000.0
                    index += 3
        
                    velocity = message[index]
                    index += 1
        
                    mute = bool(message[index] & 0x80)
                    probability = (message[index] & 0x7F) / 127.0
                    index += 1
        
                    for note in notes:
                        if note.note_id == note_id:
                            note.pitch = pitch
                            note.start_time = start_time
                            note.duration = duration
                            note.velocity = velocity
                            note.mute = mute
                            note.probability = probability
                            break
        
                # Apply the modified notes back to the clip
                clip.apply_note_modifications(notes)
        
        # markers
        if len(message) >= 2 and message[1] == 17:
            # Decode the note ID and data
            marker_id = message[2]
            
            # Decode start time (variable-length value)
            index = 3
            marker_time_raw = self._from_3_7bit_bytes(message, index)
            marker_time = marker_time_raw / 1000.0
            
            # Get the selected clip
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            if clip_slot is not None and clip_slot.has_clip:
                clip = clip_slot.clip
                if marker_id == 0:
                    clip.start_marker = marker_time
                elif marker_id == 1:
                    clip.end_marker = marker_time
                elif marker_id == 2:
                    clip.loop_start = marker_time
                else:
                    clip.loop_end = marker_time
        
        # visible channel and mixer status true
        if len(message) >= 2 and message[1] == 18:
            start = message[2]
            end = message[3]
            self.visible_channels = (start, end)
            self.mixer_status = True
            self._set_up_mixer_controls()
            
        # combine clips
        if len(message) >= 2 and message[1] == 19:
            values = self.extract_values_from_sysex_message(message)
            if len(values) == 4:
                self._append_and_remove_clip(values[0], values[1], values[2], values[3])
        
        # toggle arm for audio tracks
        if len(message) >= 2 and message[1] == 20:
            track_index = message[2]
            track = self.song().tracks[track_index]
            track.arm = not track.arm
        
        # select next clip
        if len(message) >= 2 and message[1] == 21:
            upValue = message[2]
            track = self.song().view.selected_track
            current_clip_slot = self.song().view.highlighted_clip_slot
            # Find current index
            current_index = list(track.clip_slots).index(current_clip_slot)
            
            if upValue == 0:  # Move down to next clip
                # Search for next clip slot with a clip
                for i in range(current_index + 1, len(track.clip_slots)):
                    if track.clip_slots[i].has_clip:
                        self.song().view.highlighted_clip_slot = track.clip_slots[i]
                        break
                        
            elif upValue == 1:  # Move up to previous clip
                # Search for previous clip slot with a clip (in reverse)
                for i in range(current_index - 1, -1, -1):
                    if track.clip_slots[i].has_clip:
                        self.song().view.highlighted_clip_slot = track.clip_slots[i]
                        break
        if len(message) >= 2 and message[1] == 22:
            tempo_bytes = message[2:-1]
            try:
                tempo_string = bytes(tempo_bytes).decode('ascii')
                new_tempo = float(tempo_string)
                self.song().tempo = new_tempo
                # Optional: print for debugging
                # self.canonical_parent.log_message("Tempo set to " + tempo_string)
            except Exception as e:
                # Optional: log error
                # self.canonical_parent.log_message("Tempo decode error: " + str(e))
                pass
            

            


    def decode_sys_ex_scale_root(self, message):
        scale_name_bytes = message[2:-2]
        scale_name_bytes = bytes(message[2:-2])
        scale_name = scale_name_bytes.decode('utf-8')
        root_note_index = message[-2]
        return scale_name, root_note_index

    def extract_values_from_sysex_message(self, message):
        # Extract the values from the SysEx message based on the message format
        # Replace this with your own logic to extract the desired values
        # For example, if your message is [0xF0, 0x09, value1, value2, ..., 0xF7]
        # you can extract values starting from index 2: values = message[2:-1]
        values = message[2:-1]
        return values

    def _fire_clip(self, fire, track_index, clip_index):
        track = self.song().tracks[track_index]
        clip_slot = track.clip_slots[clip_index]
        if fire == 1:
            if clip_slot.is_playing:
                clip_slot.stop()
            else:
                clip_slot.set_fire_button_state(1)
        else:
            clip_slot.set_fire_button_state(1)

    def _delete_clip(self, track_index, clip_index):
        track = self.song().tracks[track_index]
        clip_slot = track.clip_slots[clip_index]
        clip_slot.delete_clip()

    def _duplicate_loop(self, track_index, clip_index):
        track = self.song().tracks[track_index]
        clip_slot = track.clip_slots[clip_index]
        if clip_slot.has_clip:
            clip_slot.clip.duplicate_loop()

    def _copy_paste_clip(self, from_track, from_clip, to_track, to_clip):
        tracks = self.song().tracks

        copy_track = tracks[from_track]
        copy_clip_slot = copy_track.clip_slots[from_clip]

        paste_track = tracks[to_track]
        paste_clip_slot = paste_track.clip_slots[to_clip]

        copy_clip_slot.duplicate_clip_to(paste_clip_slot)
        
        # set up new clip listeners
        self._register_clip_listeners()

    def _append_and_remove_clip(self, from_track, from_clip, to_track, to_clip):
        """
        Appends notes from one MIDI clip to the end of another, then removes the source clip.
        
        Args:
            from_track: Index of the track containing the clip to append
            from_clip: Index of the clip slot to append from
            to_track: Index of the track containing the destination clip
            to_clip: Index of the clip slot to append to
        """
        tracks = self.song().tracks
        source_track = tracks[from_track]
        source_clip_slot = source_track.clip_slots[from_clip]
        dest_track = tracks[to_track]
        dest_clip_slot = dest_track.clip_slots[to_clip]
        
        # Check if both clips exist and are MIDI clips
        if not source_clip_slot.has_clip or not dest_clip_slot.has_clip:
            return
        
        source_clip = source_clip_slot.clip
        dest_clip = dest_clip_slot.clip
        
        if not source_clip.is_midi_clip or not dest_clip.is_midi_clip:
            return
        
        # Get source clip looped region only
        source_loop_start = source_clip.loop_start
        source_loop_end = source_clip.loop_end
        source_looped_length = source_loop_end - source_loop_start
        source_notes = source_clip.get_notes_extended(0, 128, source_loop_start, source_looped_length)
        
        # Get destination clip loop end position
        dest_clip_loop_end = dest_clip.loop_end
        
        # Remove any notes in destination clip that are after loop_end
        # Get ALL notes in the clip (use clip length to ensure we capture everything)
        dest_clip_full_length = max(dest_clip.loop_end, dest_clip.end_marker, dest_clip.length, 110)
        dest_clip_notes = dest_clip.get_notes_extended(0, 128, 0, dest_clip_full_length)
        
        # Collect note IDs to delete (notes at or after loop_end)
        note_ids_to_delete = []
        for note in dest_clip_notes:
            if note.start_time >= dest_clip_loop_end:
                note_ids_to_delete.append(note.note_id)
        
        # Delete all notes in one call using note IDs
        if note_ids_to_delete:
            dest_clip.remove_notes_by_id(tuple(note_ids_to_delete))
        
        # Calculate offset for appending notes (append after destination's loop_end)
        time_offset = dest_clip_loop_end - source_loop_start
        
        # Offset source notes to append at the end of destination
        if source_notes:
            new_notes = []
            for note in source_notes:
                pitch = int(note.pitch)
                start_time = note.start_time + time_offset
                duration = note.duration
                velocity = int(note.velocity)
                mute = note.mute
                probability = note.probability
                
                note_spec = MidiNoteSpecification(
                    pitch=pitch,
                    start_time=start_time,
                    duration=duration,
                    velocity=velocity,
                    mute=mute,
                    probability=probability
                )
                new_notes.append(note_spec)
            
            # Add offset notes to destination clip
            dest_clip.add_new_notes(tuple(new_notes))
            
            # Update destination clip loop_end and end_marker to include new notes
            new_end = dest_clip_loop_end + source_looped_length
            dest_clip.loop_end = new_end
            dest_clip.end_marker = new_end
        
        # Remove the source clip
        source_clip_slot.delete_clip()

    def _set_scale_root_note(self, scale, root):
        song = self.song()
        song.scale_name = scale
        song.root_note = root

        if scale.lower() == 'chromatic':
            song.scale_mode = False
        else:
            song.scale_mode = True

    def _fire_scene(self, value):
        scenes = self.song().scenes
        if value < len(scenes):
            scene = scenes[value]
            scene.fire()

    def _select_clip_scene(self, value):
        scenes = self.song().scenes
        if value < len(scenes):
            self.song().view.selected_scene = scenes[value]
        track = self.song().view.selected_track
        if value < len(track.clip_slots):
            self.song().view.highlighted_clip_slot = track.clip_slots[value]
        self._send_selected_clip_slot(value)

    def _delete_scene(self, value):
        self.song().delete_scene(value)

    def _on_selected_scene_changed(self):
        selected_scene = self.song().view.selected_scene
        scenes_list = self.song().scenes
        new_index = self._find_track_index(selected_scene, scenes_list)
        self._send_selected_clip_slot(new_index)
        if self.seq_status:
            self.start_step_seq()

    def _send_selected_clip_slot(self, clip_index):
        self._send_sys_ex_message(str(clip_index), 0x10)

    def _delete_device(self, value):
        selected_track = self.song().view.selected_track
        all_devices = self._get_all_nested_devices(selected_track.devices)[0]
        device_to_delete = all_devices[value]

        # Try to find it in top-level devices first
        if device_to_delete in selected_track.devices:
            original_index = list(selected_track.devices).index(device_to_delete)
            selected_track.delete_device(original_index)
        else:
            # Device is nested, find its parent chain
            parent_chain, device_idx = self._find_parent_chain(selected_track.devices, device_to_delete)
            if parent_chain:
                parent_chain.delete_device(device_idx)
        self._on_device_changed()
        
        
    def _find_parent_chain(self, devices, target_device):
        """Find the parent chain and device index for a nested device"""
        for rack in devices:
            if hasattr(rack, 'chains'):
                for chain in rack.chains:
                    if target_device in chain.devices:
                        device_idx = list(chain.devices).index(target_device)
                        return chain, device_idx
                    # Recursively check nested racks
                    result = self._find_parent_chain(chain.devices, target_device)
                    if result[0]:
                        return result
        return None, None
        
    
    def _select_drum_pad(self, value):
        if self._drum_rack_device:
            drum_pad = self._drum_rack_device.drum_pads[value]
            self._drum_rack_device.view.selected_drum_pad = drum_pad

    def _move_device_left(self, value):
        song = self.song()
        selected_track = song.view.selected_track
        all_devices = self._get_all_nested_devices(selected_track.devices)[0]
        device_to_move = all_devices[value]
        
        # Check if it's a top-level device
        if device_to_move in selected_track.devices:
            real_index = list(selected_track.devices).index(device_to_move)
            if real_index > 0:
                song.move_device(device_to_move, selected_track, real_index - 1)
        else:
            # Device is inside a rack, move within its chain
            parent_chain, device_idx = self._find_parent_chain(selected_track.devices, device_to_move)
            if parent_chain and device_idx > 0:
                song.move_device(device_to_move, parent_chain, device_idx - 1)
    
    def _move_device_right(self, value):
        song = self.song()
        selected_track = song.view.selected_track
        all_devices = self._get_all_nested_devices(selected_track.devices)[0]
        device_to_move = all_devices[value]
        
        # Check if it's a top-level device
        if device_to_move in selected_track.devices:
            real_index = list(selected_track.devices).index(device_to_move)
            if real_index < len(selected_track.devices) - 1:
                song.move_device(device_to_move, selected_track, real_index + 2)
        else:
            # Device is inside a rack, move within its chain
            parent_chain, device_idx = self._find_parent_chain(selected_track.devices, device_to_move)
            if parent_chain and device_idx < len(parent_chain.devices) - 1:
                song.move_device(device_to_move, parent_chain, device_idx + 2)

    def _add_midi_track(self, value):
        song = self.song()
        song.create_midi_track(value)

    def _delete_midi_track(self, value):
        song = self.song()
        song.delete_track(value)

    def _add_return_track(self, value):
        if value:
            self.song().create_return_track()
    
    def _update_mixer_status(self, value):
        if value:
            self._disconnect_device_controls()
        else:
            if hasattr(self, '_mixer_disconnect_timer') and self._mixer_disconnect_timer:
                self._mixer_disconnect_timer.cancel()
                self._mixer_disconnect_timer = None
            self.mixer_status = False
            self._set_up_mixer_controls()
            self._connect_device_controls()

    def _update_device_status(self, value):
        if value:
            self.device_status = True
            self._check_clip_playing_status()
        else:
            self.device_status = False
    
    def _update_step_seq(self, value):
        if value:
            self.seq_status = True
            self.start_step_seq()
        else:
           self.seq_status = False
           self.stop_step_seq()
    
    def start_step_seq(self):
        # getting the highlighted clip
        song = self.song()
        selected_clip_slot = song.view.highlighted_clip_slot
        self.send_selected_clip_metadata()
        self.send_selected_clip_notes()
        # self.log_message("Starting step seq")
        if self.last_selected_clip_slot is not selected_clip_slot:
            if self.last_selected_clip_slot is not None and self.last_selected_clip_slot.has_clip:
                clip = self.last_selected_clip_slot.clip
                
                if clip.notes_has_listener(self.send_selected_clip_notes):
                    # self.log_message("removing notes listener")
                    clip.remove_notes_listener(self.send_selected_clip_notes)

                if self.last_selected_clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                    self.last_selected_clip_slot.remove_has_clip_listener(self.on_highlighted_slot_changed)
                
                self.remove_clip_metadata_listeners(clip)
            
            # updating last selected clip
            self.last_selected_clip_slot = selected_clip_slot
            if selected_clip_slot is not None:
                if selected_clip_slot.has_clip:
                    # add notes listener
                    # self.log_message("adding notes listener")
                    if not selected_clip_slot.clip.notes_has_listener(self.send_selected_clip_notes):
                        selected_clip_slot.clip.add_notes_listener(self.send_selected_clip_notes)
                    
                    self.add_clip_metadata_listeners(selected_clip_slot.clip)
                else:
                    # create a clip slot listener that listens to clip changes
                    if not selected_clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                        selected_clip_slot.add_has_clip_listener(self.on_highlighted_slot_changed)
                        # self.log_message("added a has clip listener")
    
    def add_clip_metadata_listeners(self, clip):
        if not clip.end_marker_has_listener(self.send_selected_clip_metadata):
            clip.add_end_marker_listener(self.send_selected_clip_metadata)
        if not clip.start_marker_has_listener(self.send_selected_clip_metadata):
            clip.add_start_marker_listener(self.send_selected_clip_metadata)
        if not clip.loop_end_has_listener(self.send_selected_clip_metadata):
            clip.add_loop_end_listener(self.send_selected_clip_metadata)
        if not clip.loop_start_has_listener(self.send_selected_clip_metadata):
            clip.add_loop_start_listener(self.send_selected_clip_metadata)
        if not clip.signature_denominator_has_listener(self.send_selected_clip_metadata):
            clip.add_signature_denominator_listener(self.send_selected_clip_metadata)
        if not clip.signature_numerator_has_listener(self.send_selected_clip_metadata):
            clip.add_signature_numerator_listener(self.send_selected_clip_metadata)
        
    def remove_clip_metadata_listeners(self, clip):
        if clip.end_marker_has_listener(self.send_selected_clip_metadata):
            clip.remove_end_marker_listener(self.send_selected_clip_metadata)
        if clip.start_marker_has_listener(self.send_selected_clip_metadata):
            clip.remove_start_marker_listener(self.send_selected_clip_metadata)
        if clip.loop_end_has_listener(self.send_selected_clip_metadata):
            clip.remove_loop_end_listener(self.send_selected_clip_metadata)
        if clip.loop_start_has_listener(self.send_selected_clip_metadata):
            clip.remove_loop_start_listener(self.send_selected_clip_metadata)
        if clip.signature_denominator_has_listener(self.send_selected_clip_metadata):
            clip.remove_signature_denominator_listener(self.send_selected_clip_metadata)
        if clip.signature_numerator_has_listener(self.send_selected_clip_metadata):
            clip.remove_signature_numerator_listener(self.send_selected_clip_metadata)
    
    def on_highlighted_slot_changed(self):
        """
        Adding note listener on a slot has clip listener slot once it gets a clip
        """
        song = self.song()
        selected_clip_slot = song.view.highlighted_clip_slot
        if selected_clip_slot.has_clip:
            self.send_selected_clip_metadata()
            self.send_selected_clip_notes()
            # add notes listener
            # self.log_message("slot now has a clip adding notes listener")
            selected_clip_slot.clip.add_notes_listener(self.send_selected_clip_notes)
            if selected_clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                selected_clip_slot.remove_has_clip_listener(self.on_highlighted_slot_changed)
    
    def stop_step_seq(self):
        song = self.song()
        selected_clip_slot = song.view.highlighted_clip_slot
        if selected_clip_slot is not None:
            if selected_clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                selected_clip_slot.remove_has_clip_listener(self.on_highlighted_slot_changed)
            if selected_clip_slot.has_clip:
                # remove notes listener
                if selected_clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                    selected_clip_slot.clip.remove_notes_listener(self.send_selected_clip_notes)
                # remove metadata listeners
                self.remove_clip_metadata_listeners(selected_clip_slot.clip)
            
        # reseting last selected clip
        self.last_selected_clip_slot = None
    
    # Use 7-bit encoding for multi-byte values below 1000
    def _to_2_7bit_bytes(self, value):
        return [
            value & 0x7F,           # Low 7 bits
            (value >> 7) & 0x7F     # High 7 bits
        ]
    
    def _to_3_7bit_bytes(self, value):
        """
        Convert an integer into 3 MIDI 7-bit bytes.
        Uses the highest bit of the first byte as a sign indicator.
        """
        is_negative = value < 0
        value = abs(value)
        
        if value > 0x1FFFFF:  # Cap at 2,097,151
            value = 0x1FFFFF
    
        first_byte = (value >> 14) & 0x7F
        if is_negative:
            first_byte |= 0x40  # Set the sign bit for negative numbers
    
        return [first_byte, (value >> 7) & 0x7F, value & 0x7F]
    
    def _from_3_7bit_bytes(self, bytes_list, start_index=0):
        """
        Convert 3 MIDI 7-bit bytes back into an integer.
        The highest bit of the first byte is used as a sign indicator.
        """
        if len(bytes_list) < start_index + 3:
            return 0
    
        first_byte = bytes_list[start_index]
        is_negative = (first_byte & 0x40) != 0  # Check if the sign bit is set
        value = ((first_byte & 0x3F) << 14) | (bytes_list[start_index + 1] << 7) | bytes_list[start_index + 2]
    
        return -value if is_negative else value
    
    def send_selected_clip_metadata(self):
        """
        Encode clip metadata into a compact SysEx message and send it out.
        """
        if self.seq_status:
            # self.log_message("sending clip metadata")
            status_byte = 0xF0
            end_byte = 0xF7
            manufacturer_id = 0x0E
            device_id = 0x01
            
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            if clip_slot is not None:
                if clip_slot.has_clip:
                    selected_clip = clip_slot.clip
                    # Extract clip metadata, make ints
                    start_marker = int(selected_clip.start_marker * 1000)
                    end_marker = int(selected_clip.end_marker * 1000)
                    loop_start = int(selected_clip.loop_start * 1000)
                    loop_end = int(selected_clip.loop_end * 1000)
                    signature_denominator = int(selected_clip.signature_denominator)
                    signature_numerator = int(selected_clip.signature_numerator)
                    
                    note_data = [
                        *self._to_3_7bit_bytes(start_marker),
                        *self._to_3_7bit_bytes(end_marker),
                        *self._to_3_7bit_bytes(loop_start),
                        *self._to_3_7bit_bytes(loop_end),
                        signature_denominator,
                        signature_numerator
                    ]
                    
                    # Send the SysEx message
                    sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(note_data) + (end_byte,)
                    self._send_midi(sys_ex_message)
    
    def send_selected_clip_notes(self):
        """
        Encode a full clip with all notes into a compact SysEx message and send it out.
        """
        if self.seq_status:
            status_byte = 0xF0
            end_byte = 0xF7
            manufacturer_id = 0x0D
            device_id = 0x01
            max_chunk_length = 240
            data = bytearray()
                
            song = self.song()
            clip_slot = song.view.highlighted_clip_slot
            
            if clip_slot is not None:
                if clip_slot.has_clip:
                    selected_clip = clip_slot.clip
                
                    # Extract clip metadata
                    clip_start = min(selected_clip.start_time, selected_clip.start_marker, selected_clip.loop_start) - self.clip_length_trick
                    clip_length = (max(selected_clip.loop_end, selected_clip.end_marker, selected_clip.length) + self.clip_length_trick) - clip_start
                    
                    # Get notes
                    notes = selected_clip.get_notes_extended(0, 128, clip_start, clip_length)
                    # self.log_message(f"Number of notes found: {len(notes)}")
                    for note in notes:
                        note_id = int(note.note_id)
                        pitch = int(note.pitch)
                        start_time = int(note.start_time * 1000)
                        duration = int(note.duration * 1000)
                        velocity = int(note.velocity)
                        mute = 1 if note.mute else 0
                        probability = int(note.probability * 127)
                    
                        note_data = [
                            *self._to_2_7bit_bytes(note_id),   # 2 bytes, 7-bit encoded
                            pitch,                      # 1 byte
                            *self._to_3_7bit_bytes(start_time),# 3 bytes, 7-bit encoded
                            *self._to_3_7bit_bytes(duration),  # 3 bytes, 7-bit encoded
                            velocity,  
                            (mute << 7) | probability
                        ]
                    
                        data.extend(note_data)
                else:
                    # Indicate no clip selected by adding a recognizable marker
                    data.extend([0x7F, 0x7F, 0x7F])
                    if not clip_slot.has_clip_has_listener(self.on_highlighted_slot_changed):
                        clip_slot.add_has_clip_listener(self.on_highlighted_slot_changed)
                
            # Split data if it's too large for a single SysEx message
            num_of_chunks = max(1, (len(data) + max_chunk_length - 1) // max_chunk_length)
                    
            for chunk_index in range(num_of_chunks):
                start_index = chunk_index * max_chunk_length
                end_index = start_index + max_chunk_length
                chunk_data = data[start_index:end_index]
                
                # Add prefix and suffix to chunks
                prefix = "_" if chunk_index == num_of_chunks - 1 else "$"
                chunk_data = prefix.encode('ascii') + chunk_data
            
                # Send the SysEx message
                sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(chunk_data) + (end_byte,)
                # self.log_message("Sending SysEx chunk")
                self._send_midi(sys_ex_message)
    
    def send_out_playing_pos(self, value):
        now = time.time()
        if now - self._last_playing_pos_sent < 1.0 / 60.0:
            return
        self._last_playing_pos_sent = now
    
        status_byte = 0xF0
        end_byte = 0xF7
        manufacturer_id = 0x0F
        device_id = 0x01
            
        playing_pos_in_ms = int(value * 1000)
        
        pos_data = self._to_3_7bit_bytes(playing_pos_in_ms)
        
        sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(pos_data) + (end_byte,)
        self._send_midi(sys_ex_message)
            
    
    def _delete_return_track(self, value):
        song = self.song()
        song.delete_return_track(value)

    def _add_random_synth(self, value):
        if value:
            browser = self.application().browser
            # selecting an instrument from the instrument folder
            found_instrument = False
            instruments = browser.instruments
            inst_children = instruments.children

            while not found_instrument:
                random_number = random.randint(0, len(inst_children) - 1)
                rand_instrument = inst_children[random_number]
                if rand_instrument.name not in ["CV Instrument", "CV Triggers", "External Instrument", "Ext. Instrument", "Drum Rack", "Instrument Rack", "Sampler", "Simpler", "Impulse"]:
                    if rand_instrument.is_device:
                        found_instrument = True
                    else:
                        # open folder (Drum Synth)
                        children = rand_instrument.children
                        rand_index = random.randint(0, len(children) - 1)
                        rand_instrument = children[rand_index]
                        found_instrument = True

            browser.load_item(rand_instrument)
            self._on_tracks_changed()
            self._on_device_changed()

    def _add_random_drums(self, value):
        if value:
            browser = self.application().browser
            # selecting a drum rack
            drums = browser.drums.children
            number_of_drums = len(drums)
            found_drum = False
            while not found_drum:
                random_index = random.randint(0, number_of_drums - 1)
                random_drum = drums[random_index]
                if random_drum.name not in ["Drum Hits", "Drum Rack"]:
                    found_drum = True
            browser.load_item(random_drum)
            self._on_tracks_changed()
            self._on_device_changed()

    def _add_random_sound(self, value):
        if value:
            browser = self.application().browser
            # selecting a random device from the sounds folder
            sounds = browser.sounds
            number_of_sounds = len(sounds.children)
            random_index = random.randint(0, number_of_sounds - 1)
            selected_sounds_folder = sounds.children[random_index]
            number_of_sounds = len(selected_sounds_folder.children)
            random_sound_index = random.randint(0, number_of_sounds - 1)
            selected_sound = selected_sounds_folder.children[random_sound_index]
            browser.load_item(selected_sound)
            self._on_tracks_changed()
            self._on_device_changed()

    def _add_random_effect(self, value):
        if value:
            browser = self.application().browser
            # Tried loading max for live effects but gave up
            # random_index = random.randint(0, 1)
            # if random_index == 0:
            #     max_effects = browser.max_for_live.children
            #     max_number = len(max_effects)
            #     random_max = random.randint(0, max_number - 1)
            #     selected_folder = max_effects[random_max].children
            #     max_number = len(selected_folder)
            #     finished = False
            #     number_of_tries = 0
            #     if max_number == 0:
            #         selected_effect = selected_folder
            #         finished = True
            #     while not finished and number_of_tries < 10:
            #         random_max = random.randint(0, max_number - 1)
            #         selected_effect = selected_folder[random_max]
            #         number_of_tries += 1
            #         self.log_message("Selected Device: {}".format(selected_effect.name))
            #         if not any(selected_effect.name.lower().startswith(substring.lower()) for substring in ["IR", "Api", "Map8", "Max Audio Effect"]):
            #             finished = True

            # else:
            effects = browser.audio_effects
            effect_children = effects.children
            number_of_effects = len(effect_children)
            # check if effects are in folders or not
            if number_of_effects >= 10:
                random_effect_index = random.randint(0, number_of_effects - 1)
                selected_effect = effect_children[random_effect_index]
            else:
                finished = False
                while not finished:
                    random_folder_index = random.randint(0, number_of_effects - 1)
                    selected_folder = effect_children[random_folder_index]
                    self._debug_log("Selected FOlder: {}".format(selected_folder.name))
                    if selected_folder.name != "Utilities":
                        finished = True

                folder_children = selected_folder.children
                number_folder_children = len(folder_children)
                random_folder_child_index = random.randint(0, number_folder_children - 1)
                selected_effect = folder_children[random_folder_child_index]
            browser.load_item(selected_effect)
            self._on_tracks_changed()
            self._on_device_changed()

    def _start_browser(self, folder_index):
        """
        Start browsing a specific browser folder.

        Triggered by MIDI CC on channel 1, CC 25. The value corresponds to a folder mapping:
        0 = audio_effects, 1 = colors, 2 = current_project, 3 = drums,
        4 = instruments, 5 = max_for_live, 6 = midi_effects, 7 = packs,
        8 = plugins, 9 = sounds, 10 = user_folders, 11 = user_library

        Collects all items from the requested folder, resets pagination, and sends the first page
        via SysEx with manufacturer ID 0x13.

        Args:
            folder_index: Integer (0-11) corresponding to the folder to browse
        """
        browser = self.application().browser

        if folder_index not in self.browser_folder_mapping:
            return

        folder_name = self.browser_folder_mapping[folder_index]

        try:
            # Clear history when starting fresh
            self.browser_history = []

            # Get the browser item for the requested folder
            if folder_name in ['colors', 'user_folders']:
                # These return lists instead of BrowserItem
                folder_items = getattr(browser, folder_name)
                self.browser_current_items = list(folder_items)
            else:
                # These return a BrowserItem with children
                folder_item = getattr(browser, folder_name)
                if hasattr(folder_item, 'children'):
                    self.browser_current_items = list(folder_item.children)
                else:
                    self.browser_current_items = [folder_item]

            # Reset pagination and send first page
            self.browser_current_page = 0
            self.browser_pages_count = (len(self.browser_current_items) + self.browser_items_per_page - 1) // self.browser_items_per_page
            self._send_browser_page(self.browser_current_page)

        except Exception as e:
            self._debug_log(f"Error starting browser: {str(e)}")

    def _get_browser_item_type(self, item):
        """
        Determine the type suffix for a browser item.

        Checks the browser item's properties and returns the appropriate suffix for display
        in the app. The type can be inferred from which folder was requested.

        Args:
            item: A BrowserItem object from Live's browser

        Returns:
            String suffix: '//' for folders, '||<' for devices with children, '||' for devices without children,
            '<' for items with children that are neither folders nor devices, empty string otherwise
        """
        if hasattr(item, 'is_folder') and item.is_folder:
            return '//'
        elif hasattr(item, 'is_device') and item.is_device:
            if hasattr(item, 'children') and item.children:
                return '||<'
            else:
                return '||'
        elif hasattr(item, 'children') and item.children:
            return '<'
        else:
            return ''

    def _send_browser_page(self, page_number):
        """
        Send a paginated list of browser items via SysEx.

        Sends up to 12 items (browser_items_per_page) from the current browser folder.
        Items are formatted with type suffixes: '//' for folders, '||<' for devices with children,
        '||' for devices without children, '<' for non-folder non-device items with children.

        SysEx message format (manufacturer ID 0x13):
            current_page^total_pages^item1//,item2||<,item3||,item4<,...

        Args:
            page_number: The page number to send (0-indexed)
        """
        if page_number < 0 or page_number >= self.browser_pages_count:
            return

        self.browser_current_page = page_number

        start_index = page_number * self.browser_items_per_page
        end_index = min(start_index + self.browser_items_per_page, len(self.browser_current_items))
        page_items = self.browser_current_items[start_index:end_index]

        # Build item strings with type suffixes
        item_strings = []
        for item in page_items:
            if hasattr(item, 'name'):
                item_name = item.name
                item_type = self._get_browser_item_type(item)
                item_strings.append(f"{item_name}{item_type}")

        # Format: current_page^total_pages^item1//,item2||,item3||,...
        items_string = ','.join(item_strings)
        message = f"{self.browser_current_page}^{self.browser_pages_count}^{items_string}"

        # Send using manufacturer ID 0x13
        self._send_sys_ex_message(message, 0x13)

    def _browser_navigate(self, value):
        """
        Navigate between browser pages using a MIDI note button.

        Triggered by MIDI note on channel 15, note 82.
        - Note on (value != 0): Go to next page
        - Note off (value == 0): Go to previous page

        Validates boundaries and only sends pages that exist.

        Args:
            value: MIDI note velocity (0-127). Non-zero = note on, zero = note off
        """
        if not self.browser_current_items:
            return

        if value != 0:
            # Note on: go to next page
            if self.browser_current_page < self.browser_pages_count - 1:
                self._send_browser_page(self.browser_current_page + 1)
        else:
            # Note off: go to previous page
            if self.browser_current_page > 0:
                self._send_browser_page(self.browser_current_page - 1)

    def _browser_open_item(self, value):
        """
        Open and action on a browser item based on MIDI note velocity.

        Triggered by MIDI note on channel 15, note 81. The velocity is sent as
        (index + 1) to avoid velocity 0 issues.

        The actual item index is calculated as: (current_page * items_per_page) + (value - 1)

        Action depends on item type:
        - Folder (is_folder): Load folder contents and send new browser page
        - Has children but not a folder: Try to display children
        - Other (no children or can't display): Attempt to load the item

        After loading a device, updates track and device views to reflect changes.

        Args:
            value: MIDI note velocity (1-12), sent as index + 1
        """
        if not self.browser_current_items:
            return

        index = (self.browser_current_page * self.browser_items_per_page) + (value - 1)
        if index >= len(self.browser_current_items):
            return

        item = self.browser_current_items[index]
        browser = self.application().browser

        if hasattr(item, 'is_folder') and item.is_folder:
            if hasattr(item, 'children'):
                # Save current state to history before navigating
                self.browser_history.append({
                    'items': self.browser_current_items,
                    'page': self.browser_current_page,
                    'pages_count': self.browser_pages_count
                })
                self.browser_current_items = list(item.children)
                self.browser_current_page = 0
                self.browser_pages_count = (len(self.browser_current_items) + self.browser_items_per_page - 1) // self.browser_items_per_page
                self._send_browser_page(self.browser_current_page)
        elif hasattr(item, 'children'):
            try:
                children = list(item.children)
                if children:
                    # Save current state to history before navigating
                    self.browser_history.append({
                        'items': self.browser_current_items,
                        'page': self.browser_current_page,
                        'pages_count': self.browser_pages_count
                    })
                    self.browser_current_items = children
                    self.browser_current_page = 0
                    self.browser_pages_count = (len(self.browser_current_items) + self.browser_items_per_page - 1) // self.browser_items_per_page
                    self._send_browser_page(self.browser_current_page)
                else:
                    browser.load_item(item)
                    self._on_tracks_changed()
                    self._on_device_changed()
            except Exception:
                browser.load_item(item)
                self._on_tracks_changed()
                self._on_device_changed()
        else:
            browser.load_item(item)
            self._on_tracks_changed()
            self._on_device_changed()

    def _browser_load_item(self, value):
        """
        Load a browser item based on MIDI note velocity, never opening children.

        Triggered by MIDI note on channel 15, note 80. The velocity is sent as
        (index + 1) to avoid velocity 0 issues.

        The actual item index is calculated as: (current_page * items_per_page) + (value - 1)

        Always attempts to load the item, regardless of whether it's a folder, device with children, etc.
        After loading, updates track and device views to reflect changes.

        Args:
            value: MIDI note velocity (1-12), sent as index + 1
        """
        if not self.browser_current_items:
            return

        index = (self.browser_current_page * self.browser_items_per_page) + (value - 1)
        if index >= len(self.browser_current_items):
            return

        item = self.browser_current_items[index]
        browser = self.application().browser
        browser.load_item(item)
        self._on_tracks_changed()
        self._on_device_changed()

    def _browser_go_back(self, value):
        """
        Go back one or more levels in the browser history, restoring the page state.

        Triggered by MIDI note on channel 15, note 79.

        The velocity determines how many steps to go back:
        - Velocity 1 = go back 1 step
        - Velocity 2 = go back 2 steps
        - etc.

        Restores the previous level's items and page number from the history stack.
        Only works if there's history available.

        Args:
            value: MIDI note velocity (1-127). Determines number of steps to go back.
        """
        if value == 0 or not self.browser_history:
            return

        # Determine number of steps to go back
        steps = min(value, len(self.browser_history))

        # Pop the last state(s) from history
        for _ in range(steps - 1):
            self.browser_history.pop()

        previous_state = self.browser_history.pop()

        # Restore the previous state
        self.browser_current_items = previous_state['items']
        self.browser_current_page = previous_state['page']
        self.browser_pages_count = previous_state['pages_count']

        # Send the page we were at
        self._send_browser_page(self.browser_current_page)

    def disconnect(self):
        # Cancel all pending timers
        if self._metadata_recheck_timer:
            self._metadata_recheck_timer.cancel()
            self._metadata_recheck_timer = None
        if self._automation_metadata_update_timer:
            self._automation_metadata_update_timer.cancel()
            self._automation_metadata_update_timer = None
        if hasattr(self, '_mixer_disconnect_timer') and self._mixer_disconnect_timer:
            self._mixer_disconnect_timer.cancel()
            self._mixer_disconnect_timer = None
        if hasattr(self, '_periodic_timer_ref') and self._periodic_timer_ref:
            self._periodic_timer_ref.cancel()
            self._periodic_timer_ref = None
        
        # Stop periodic execution
        self.periodic_timer = 0
        
        # Clear caches
        self._metadata_cache.clear()
        self._metadata_send_seq_by_device.clear()
        
        self._remove_disabled_parameter_listeners()
        self._remove_automation_state_listeners()
#        self.quantize_button.remove_value_listener(self._quantize_button_value)
        if hasattr(self, 'duplicate_button'):
            self.duplicate_button.remove_value_listener(self._duplicate_button_value)
        if hasattr(self, 'duplicate_scene_button'):
            self.duplicate_scene_button.remove_value_listener(self._duplicate_scene_button_value)
        if hasattr(self, 'sesh_record_button'):
            self.sesh_record_button.remove_value_listener(self._sesh_record_value)
        if hasattr(self, 'redo_button'):
            self.redo_button.remove_value_listener(self._redo_button_value)
        if hasattr(self, 'undo_button'):
            self.undo_button.remove_value_listener(self._undo_button_value)
        # browser buttons cleanup
        if hasattr(self, 'browser_start_button'):
            self.browser_start_button.remove_value_listener(self._start_browser)
        if hasattr(self, 'browser_navigate_button'):
            self.browser_navigate_button.remove_value_listener(self._browser_navigate)
        if hasattr(self, 'browser_open_button'):
            self.browser_open_button.remove_value_listener(self._browser_open_item)
        if hasattr(self, 'browser_load_button'):
            self.browser_load_button.remove_value_listener(self._browser_load_item)
        if hasattr(self, 'browser_back_button'):
            self.browser_back_button.remove_value_listener(self._browser_go_back)
        song = self.song()
        # periodic_check_button.remove_value_listener(self._periodic_check)
        song.remove_tracks_listener(self._on_tracks_changed)
        # self.song().view.remove_selected_track_listener(self._on_selected_track_changed)
        # self._unregister_clip_and_audio_listeners()
        # self.remove_midi_listener(self._midi_listener)
        # self.song().view.remove_selected_scene_listener(self._on_selected_scene_changed)
        song.remove_scale_name_listener(self._on_scale_changed)
        song.remove_root_note_listener(self._on_scale_changed)
        # Clean up level listeners
        for track, (left_listener, right_listener) in self._track_level_listeners.items():
            if liveobj_valid(track) and hasattr(track, 'output_meter_left_has_listener') and track.output_meter_left_has_listener(left_listener):
                track.remove_output_meter_left_listener(left_listener)
            if liveobj_valid(track) and hasattr(track, 'output_meter_right_has_listener') and track.output_meter_right_has_listener(right_listener):
                track.remove_output_meter_right_listener(right_listener)

        for track, (left_listener, right_listener) in self._return_level_listeners.items():
            if liveobj_valid(track) and hasattr(track, 'output_meter_left_has_listener') and track.output_meter_left_has_listener(left_listener):
                track.remove_output_meter_left_listener(left_listener)
            if liveobj_valid(track) and hasattr(track, 'output_meter_right_has_listener') and track.output_meter_right_has_listener(right_listener):
                track.remove_output_meter_right_listener(right_listener)

        if self._master_level_listeners:
            master_track = self.song().master_track
            left_listener, right_listener = self._master_level_listeners.get(master_track, (None, None))
            if left_listener and liveobj_valid(master_track) and hasattr(master_track, 'output_meter_left_has_listener') and master_track.output_meter_left_has_listener(left_listener):
                master_track.remove_output_meter_left_listener(left_listener)
            if right_listener and liveobj_valid(master_track) and hasattr(master_track, 'output_meter_right_has_listener') and master_track.output_meter_right_has_listener(right_listener):
                master_track.remove_output_meter_right_listener(right_listener)
        
        super(Tap, self).disconnect()
