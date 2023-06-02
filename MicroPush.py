# MicroPush

from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.MixerComponent import MixerComponent
from _Framework.TransportComponent import TransportComponent
from _Framework.EncoderElement import *
from _Framework.ButtonElement import ButtonElement
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_NOTE_TYPE

# from ableton.v2.base import listens, liveobj_valid, liveobj_changed


mixer, transport, capture_button, quantize_button, duplicate_button = None, None, None, None, None


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
            # self._on_selected_track_changed.subject = self.song().tracks
            self.song().add_tracks_listener(self._on_track_number_changed)  # vielleicht noch einmal song davor. hier für return tracks: .add_return_tracks_listener()      

    def _initialize_mixer(self):
        self.show_message("Loading Micro Push mappings")
        mixer.master_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, 8, 7))
        mixer.set_prehear_volume_control(EncoderElement(MIDI_CC_TYPE, 9, 7, Live.MidiMap.MapMode.absolute))

    def _initialize_buttons(self):
        transport.set_record_button(ButtonElement(1, MIDI_CC_TYPE, 0, 119))
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

    def _capture_button_value(self, value):
        if value != 0:
            self.song().capture_midi()

    def _quantize_button_value(self, value):
        if value != 0:
            clip = self.song().view.detail_clip
            if clip:
                # grid (1 = 1/16), strength (0.5 = 50%)
                clip.quantize(2, 1.0)
                # add some groove if wanted, didn't work
                # clip.groove_amount = 0.5

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

        duplicated_id = selected_track.duplicate_clip_slot(
            current_index
        )

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

    # @subject_slot('selected_track')
    # def _on_selected_track_changed(self):
    #     pass #some track changed logic here

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
        self.song().remove_tracks_listener(self._on_track_number_changed)
        super(MicroPush, self).disconnect()
