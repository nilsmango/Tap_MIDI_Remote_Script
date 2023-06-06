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
            self._initialize_mixer()
            self._initialize_buttons()
            self._update_mixer_and_tracks()
            self._set_selected_track_implicit_arm()
            self._on_selected_track_changed.subject = self.song().view
            self.song().add_tracks_listener(self._on_track_number_changed)  # hier für return tracks: .add_return_tracks_listener()
            self._setup_device_control()

    def _setup_device_control(self):
        self._device = DeviceComponent()
        self._device.name = 'Device_Component'
        device_controls = []
        for index in range(16):
            control = EncoderElement(MIDI_CC_TYPE, index, 20, Live.MidiMap.MapMode.absolute)
            control.name = 'Ctrl_' + str(index)
            device_controls.append(control)
        self._device.set_parameter_controls(device_controls)
        self._on_device_changed.subject = self._device
        self.set_device_component(self._device)

    @subject_slot('device')
    def _on_device_changed(self):
        pass

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
        self.song().remove_tracks_listener(self._on_track_number_changed)
        # self.song().view.remove_selected_track_listener(self._on_selected_track_changed)
        self.remove_midi_listener(self._midi_listener)
        super(MicroPush, self).disconnect()
