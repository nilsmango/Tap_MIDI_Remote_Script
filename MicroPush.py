# MicroPush

from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.MixerComponent import MixerComponent
from _Framework.TransportComponent import TransportComponent
from _Framework.EncoderElement import *
from _Framework.ButtonElement import ButtonElement
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_NOTE_TYPE, MIDI_NOTE_ON_STATUS, MIDI_NOTE_OFF_STATUS, MIDI_CC_TYPE
from _Framework.DeviceComponent import DeviceComponent
from ableton.v2.base import listens, liveobj_valid, liveobj_changed


mixer, transport, capture_button, quantize_button, duplicate_button, sesh_record_button, quantize_grid_button, quantize_strength_button, swing_amount_button = None, None, None, None, None, None, None, None, None
quantize_grid_value = 5
quantize_strength_value = 1.0
swing_amount_value = 0.0



class MicroPush(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            global mixer
            global transport
            track_count = 8
            return_count = 24  # Maximum of 12 Sends and 12 Returns
            mixer = MixerComponent(track_count, return_count)
            transport = TransportComponent()
            self._last_can_redo = self.song().can_redo
            self._last_can_undo = self.song().can_undo
            self.first_periodic_check = True
            self._initialize_mixer()
            self._initialize_buttons()
            self._update_mixer_and_tracks()
            self._set_selected_track_implicit_arm()
            self._on_selected_track_changed.subject = self.song().view
            # track = self.song().view.selected_track
            # track.view.add_selected_device_listener(self._on_selected_device_changed)
            self.song().add_tracks_listener(self._on_track_number_changed)  # hier für return tracks: .add_return_tracks_listener()
            self._setup_device_control()

    # def _on_selected_device_changed(self):
    #     self.log_message("device changed!!")

    def _setup_device_control(self):
        self._device = DeviceComponent()
        self._device.name = 'Device_Component'
        device_controls = []
        for index in range(8):
            control = EncoderElement(MIDI_CC_TYPE, index, 20, Live.MidiMap.MapMode.absolute)
            control.name = 'Ctrl_' + str(index)
            device_controls.append(control)
        self._device.set_parameter_controls(device_controls)
        nav_left_button = ButtonElement(1, MIDI_CC_TYPE, 0, 33)
        nav_right_button = ButtonElement(1, MIDI_CC_TYPE, 0, 32)
        self._device.set_bank_nav_buttons(nav_left_button, nav_right_button)
        self._on_device_changed.subject = self._device
        self.set_device_component(self._device)
        # Register button listeners for navigation buttons
        nav_left_button.add_value_listener(self._on_nav_button_pressed)
        nav_right_button.add_value_listener(self._on_nav_button_pressed)


    def _on_nav_button_pressed(self, value):
        if value:
            self._on_device_changed()

    @subject_slot('device')
    def _on_device_changed(self):
        if liveobj_valid(self._device):
            device = self._device.device()  # Retrieve the Device object
            # get and send name of bank and device
            selected_track = self.song().view.selected_track
            selected_device = selected_track.view.selected_device
            device_name = selected_device.name
            bank_name = self._device._bank_name
            bank_names_list = ','.join(str(name) for name in self._device._parameter_bank_names())
            # sending sysex of bank name, device name, bank names
            self._send_sys_ex_message(bank_name, 0x6D)
            self._send_sys_ex_message(bank_names_list, 0x5D)
            self._send_sys_ex_message(device_name, 0x4D)
            if hasattr(device, 'parameters') and device.parameters:
                
                # TODO: make this prettier!
                parameter_names = [control.mapped_parameter().name if control.mapped_parameter() else ""
                                for control in self._device._parameter_controls]
                parameter_names = [name for name in parameter_names if name]  # Remove empty names
                if parameter_names:
                    # Do something with the parameter names
                    self.log_message("Parameter Names: {}".format(parameter_names))
                    # send a MIDI SysEx message with the names
                    self._send_parameter_names(parameter_names)
                else:
                    self.log_message("No parameter names found in the device controls.")
            else:
                self.log_message("Device has no parameters.")
        else:
            self.log_message("Invalid device.")

    def _send_parameter_names(self, parameter_names):
        name_string = ','.join(parameter_names)
        self._send_sys_ex_message(name_string, 0x7D)

    def _send_sys_ex_message(self, name_string, manufacturer_id):
        status_byte = 0xF0  # SysEx message start
        # parameter names: 0x7D, bank name: 0x6D
        device_id = 0x01  
        data = name_string.encode('ascii')
        end_byte = 0xF7  # SysEx message end
        sys_ex_message = (status_byte, manufacturer_id, device_id) + tuple(data) + (end_byte, )
        self._send_midi(sys_ex_message)


    def _initialize_mixer(self):
        self.show_message("Loading Micro Push mappings")
        mixer.master_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, 8, 7))
        mixer.set_prehear_volume_control(EncoderElement(MIDI_CC_TYPE, 9, 7, Live.MidiMap.MapMode.absolute))

    def _initialize_buttons(self):
        transport.set_play_button(ButtonElement(1, MIDI_CC_TYPE, 0, 118))
        transport.set_stop_button(ButtonElement(1, MIDI_CC_TYPE, 0, 117))
        transport.set_metronome_button(ButtonElement(1, MIDI_CC_TYPE, 0, 58))
        capture_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 100)
        capture_button.add_value_listener(self._capture_button_value)
        quantize_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 99)
        quantize_button.add_value_listener(self._quantize_button_value)
        # duplicate the active clip to a free slot
        duplicate_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 98)
        duplicate_button.add_value_listener(self._duplicate_button_value)
        # a session recording button
        sesh_record_button = ButtonElement(1, MIDI_CC_TYPE, 0, 119)
        sesh_record_button.add_value_listener(self._sesh_record_value)
        # quantize grid size button
        quantize_grid_button = ButtonElement(1, MIDI_CC_TYPE, 1, 0)
        quantize_grid_button.add_value_listener(self._quantize_grid_value)
        # quantize strength
        quantize_strength_button = ButtonElement(1, MIDI_CC_TYPE, 1, 1)
        quantize_strength_button.add_value_listener(self._quantize_strength_value)
        # swing percentage button
        swing_amount_button = ButtonElement(1, MIDI_CC_TYPE, 1, 2)
        swing_amount_button.add_value_listener(self._swing_amount_value)
        # periodic check
        periodic_check_button = ButtonElement(True, MIDI_NOTE_TYPE, 15, 97)
        periodic_check_button.add_value_listener(self._periodic_check)
        # redo button
        redo_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 102)
        redo_button.add_value_listener(self._redo_button_value)
        # undo button
        undo_button = ButtonElement(1, MIDI_NOTE_TYPE, 15, 101)
        undo_button.add_value_listener(self._undo_button_value)

    def _periodic_check(self, value):
        if value != 0:
            can_redo = self.song().can_redo
            can_undo = self.song().can_undo
            if can_redo != self._last_can_redo or self.first_periodic_check is True:
                self._last_can_redo = can_redo
                if can_redo:
                    midi_event_bytes = (0x90 | 0x02, 0x02, 0x64)
                    self._send_midi(midi_event_bytes)
                else:
                    midi_event_bytes = (0x80 | 0x02, 0x02, 0x64)
                    self._send_midi(midi_event_bytes)
            if can_undo != self._last_can_undo or self.first_periodic_check is True:
                self._last_can_undo = can_undo
                if can_undo:
                    midi_event_bytes = (0x90 | 0x02, 0x00, 0x64)
                    self._send_midi(midi_event_bytes)
                else:
                    midi_event_bytes = (0x80 | 0x02, 0x00, 0x64)
                    self._send_midi(midi_event_bytes)
            self.first_periodic_check = False

    def _redo_button_value(self, value):
        if value != 0:
            song = self.song()
            if song.can_redo:
                song.redo()
                self._periodic_check(1)

    def _undo_button_value(self, value):
        if value != 0:
            song = self.song()
            if song.can_undo:
                song.undo()
                self._periodic_check(1)

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

    def _duplicate_clip(self):
        selected_track = self.song().view.selected_track

        if selected_track is None:
            return

        song = self.song()
        selected_scene = song.view.selected_scene
        all_scenes = song.scenes
        current_index = list(all_scenes).index(selected_scene)

        duplicated_id = selected_track.duplicate_clip_slot(current_index)

        duplicated_slot = self.song().scenes[duplicated_id]

        if self.song().view.highlighted_clip_slot.is_playing:
            # move to the duplicated clip_slot
            self.song().view.selected_scene = duplicated_slot

            if not self.song().view.highlighted_clip_slot.is_playing:
                # force legato ensures that the playing-position of the duplicated
                # loop is continued from the previous clip
                self.song().view.highlighted_clip_slot.fire(force_legato=True)
        else:
            self.song().view.selected_scene = duplicated_slot

    @subject_slot('selected_track')
    def _on_selected_track_changed(self):
        selected_track = self.song().view.selected_track
        if selected_track and selected_track.has_midi_input:
            self._set_selected_track_implicit_arm()
        self._set_other_tracks_implicit_arm()
        device_to_select = selected_track.view.selected_device
        if device_to_select == None and len(selected_track.devices) > 0:
            device_to_select = selected_track.devices[0]
        if device_to_select != None:
            self.song().view.select_device(device_to_select)
        self._device_component.set_device(device_to_select)

    def _set_selected_track_implicit_arm(self):
        selected_track = self.song().view.selected_track
        if selected_track:
            selected_track.implicit_arm = True
        else:
            self.song().tracks[0].implicit_arm = True

    def _set_other_tracks_implicit_arm(self):
        for track in self.song().tracks:
            if track != self.song().view.selected_track:
                track.implicit_arm = False

    def _on_track_number_changed(self):
        self._update_mixer_and_tracks()

    # Updating names and number of tracks
    def _update_mixer_and_tracks(self):
        track_count = len(self.song().tracks)
        # mixer.set_track_count(track_count)
        self.show_message("Track Count: {}".format(track_count))
        track_names = ", ".join([track.name for track in self.song().tracks])
        self.show_message("Track Count: {}\nTrack Names: {}".format(track_count, track_names))

        # Channels
        for index, track in enumerate(self.song().tracks):
            strip = mixer.channel_strip(index)
            # Configure strip controls for each channel track
            # strip.set_mute_button(...)
            # strip.set_solo_button(...)
            # strip.set_arm_button(...)
            # strip.set_shift_button(...)
            # strip.set_pan_control(...)
            # strip.set_volume_control(...)

    def disconnect(self):
        capture_button.remove_value_listener(self._capture_button_value)
        quantize_button.remove_value_listener(self._quantize_button_value)
        duplicate_button.remove_value_listener(self._duplicate_button_value)
        sesh_record_button.remove_value_listener(self._sesh_record_value)
        redo_button.remove_value_listener(self._redo_button_value)
        undo_button.remove_value_listener(self._undo_button_value)
        periodic_check_button.remove_value_listener(self._periodic_check)
        
        self.song().remove_tracks_listener(self._on_track_number_changed)
        # self.song().view.remove_selected_track_listener(self._on_selected_track_changed)
        self.remove_midi_listener(self._midi_listener)
        super(MicroPush, self).disconnect()
