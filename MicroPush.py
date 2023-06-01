# MicroPush

from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.MixerComponent import MixerComponent
from _Framework.TransportComponent import TransportComponent
from _Framework.EncoderElement import *
from _Framework.ButtonElement import ButtonElement
from _Framework.SliderElement import SliderElement
from ableton.v2.base import listens, liveobj_valid, liveobj_changed


mixer, transport = None, None

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
            self._initialize_transport()
            self._update_mixer_track_count()
            # self._on_selected_track_changed.subject = self.song().tracks

            self.song().add_tracks_listener(self._on_track_number_changed) # vielleicht noch einmal song davor. hier für return tracks: .add_return_tracks_listener()
            



    def _initialize_mixer(self):
        self.show_message("Loading Micro Push mappings")
        mixer.master_strip().set_volume_control(SliderElement(MIDI_CC_TYPE, 8, 7))
        mixer.set_prehear_volume_control(EncoderElement(MIDI_CC_TYPE, 9, 7, Live.MidiMap.MapMode.absolute))

    def _initialize_transport(self):
        transport.set_record_button(ButtonElement(1, MIDI_CC_TYPE, 0, 119))
        transport.set_play_button(ButtonElement(1, MIDI_CC_TYPE, 0, 118))
        transport.set_stop_button(ButtonElement(1, MIDI_CC_TYPE, 0, 117))
        transport.set_metronome_button(ButtonElement(1, MIDI_CC_TYPE, 0, 58))

    # @subject_slot('selected_track')
    # def _on_selected_track_changed(self):
    #     pass #some track changed logic here


    def _on_track_number_changed(self):
        self._update_mixer_track_count()

    # Updating names and number of tracks
    def _update_mixer_track_count(self):
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
        self.song().remove_tracks_listener(self._on_track_number_changed)
        self._on_track_number_changed.subject = None
        super(MicroPush, self).disconnect()
