from __future__ import absolute_import, print_function, unicode_literals

import re
import Live
from _Framework.DeviceComponent import DeviceComponent
from ableton.v2.base import liveobj_valid
try:
    from ableton.v2.control_surface import SimplerDeviceDecorator
except ImportError:
    SimplerDeviceDecorator = None
try:
    # Push decorator exposes all of Drift API-backed selectors.
    from Push2.drift import DriftDeviceDecorator
    from ableton.v2.control_surface.drift_decoration import DriftDeviceDecorator as BaseDriftDeviceDecorator
except ImportError:
    try:
        from ableton.v2.control_surface.drift_decoration import DriftDeviceDecorator
        BaseDriftDeviceDecorator = DriftDeviceDecorator
    except ImportError:
        DriftDeviceDecorator = None
        BaseDriftDeviceDecorator = None
try:
    from Push2.meld import MeldDeviceDecorator
except ImportError:
    MeldDeviceDecorator = None
try:
    from Push2.hybrid_reverb import HybridReverbDeviceDecorator
except ImportError:
    HybridReverbDeviceDecorator = None
try:
    from ableton.v2.control_surface import BankingInfo, DescribedDeviceParameterBank
    from Push2.custom_bank_definitions import BANK_DEFINITIONS as PUSH_BANK_DEFINITIONS
    from Push2.device_decorator_factory import DeviceDecoratorFactory as PushDeviceDecoratorFactory
except ImportError:
    BankingInfo = None
    DescribedDeviceParameterBank = None
    PUSH_BANK_DEFINITIONS = {}
    PushDeviceDecoratorFactory = None
try:
    from Push2.device_parameter_bank_with_options import DescribedDeviceParameterBankWithOptions
except ImportError:
    DescribedDeviceParameterBankWithOptions = None
try:
    from Move.custom_bank_definitions import CUSTOM_BANK_DEFINITIONS as MOVE_BANK_DEFINITIONS
except ImportError:
    MOVE_BANK_DEFINITIONS = {}

class TapDeviceComponent(DeviceComponent):
    SAFE_PARAMETER_BANK_SIZE = 8
    CURATED_PUSH_BANK_CLASSES = frozenset((
        'Chorus2',
        'Tube',
        'PhaserNew',
        'Reverb',
        'Roar',
        'Shifter',
        'Transmute',
        'Spectral',
        'Saturator',
        'MidiRandom',
        'MidiScale',
        'Eq8',
    ))
    CURATED_MOVE_BANK_CLASSES = frozenset((
        'AutoPan2',
        'AutoShift',
        'FilterEQ3',
        'Redux2',
        'Resonator',
        'Vinyl',
    ))
    AUTO_SHIFT_DETAILS_BANK_NAME = "Shift"
    AUTO_PAN_MODE_BANK_NAME = "Mode"
    CHORUS_MODE_BANK_NAME = "Mode"
    CHORD_SHIFT_SCALE_BANK_NAME = "Shift Scale"
    CHORD_STRUM_BANK_NAME = "Strum"
    CURATED_OPTIONS_BANK_NAME = "Options"
    OPERATOR_WAVES_BANK_NAME = "Waveforms"
    OPERATOR_FILTER_PLUS_BANK_NAME = "Filter +"
    OPERATOR_LFO_PLUS_BANK_NAME = "LFO +"
    WAVETABLE_OSC_BANK_NAME = "Waves"
    WAVETABLE_ENV_2_BANK_NAME = "Envelope 2"
    WAVETABLE_ENV_3_BANK_NAME = "Envelope 3"
    SIMPLER_MAIN_BANK_NAME = "Main"
    SIMPLER_ACTIONS_BANK_NAME = "Actions"
    SIMPLER_WARP_BANK_NAME = "Controls"
    SIMPLER_CONTROLS_2_BANK_NAME = "Controls 2"
    SIMPLER_BROWSE_BANK_NAME = "Browse"
    SIMPLER_BROWSE_PLUS_BANK_NAME = "Browse +"
    SIMPLER_AMP_BANK_NAME = "Volume"
    SIMPLER_SLICE_DETAIL_BANK_NAME = "Pitch & Fade"
    SIMPLER_AMP_BANK_INDEX = 3
    DRUMCELL_SAMPLE_BANK_NAME = "Sample"
    DRUMCELL_FX_FILTER_BANK_NAME = "FX & Filter"
    DRUMCELL_REST_BANK_NAME = "Main & Mod"
    DRUMCELL_FX_2_BANK_NAME = "FX P"
    DRUMCELL_FX_3_BANK_NAME = "FX P2"
    DELAY_BANK_NAMES = ("Main", "Time / Flt", "Flt / LFO", "LFO Wave")
    GRAIN_DELAY_BANK_NAMES = ("Pitch", "Time")
    AUTO_FILTER_BANK_NAMES = ("Main", "Envelope", "LFO", "Sidechain")
    AUTO_FILTER_2_BANK_NAMES = ("Main", "LFO", "Envelope", "Quantization")
    BEAT_REPEAT_BANK_NAMES = ("Main", "Filt/Mix", "Repeat Rate")
    HYBRID_REVERB_BANK_NAMES = (
        "Main", "Convolution", "Algorithm Pg1", "Algorithm Pg2",
        "EQ Pg1", "EQ Pg2", "Global",
    )
    DRIFT_BANK_NAMES = (
        "Main", "Oscillators", "Osc 2 / Noise", "Osc Mod", "Filters", "Filter Mod",
        "Envelope 1", "Envelope 2", "Envelope 2 Cyc", "LFO", "Mod 1 & 2", "Mod 3",
        "Global", "Global / Out",
    )
    MELD_ENGINE_BANK_NAME = "A | B"
    MELD_BANK_NAMES = (
        MELD_ENGINE_BANK_NAME,
        "Main",
        "Osc / Mix",
        "Filter",
        "Amp Envelope",
        "Mod Envelope",
        "Envelope Setup",
        "LFO 1 Generator",
        "LFO 1 FX",
        "LFO 2",
        "Global / Out",
    )
    ANALOG_OSC_1_BANK_NAME = "OSC 1"
    ANALOG_OSC_2_BANK_NAME = "OSC 2"
    ANALOG_NOISE_BANK_NAME = "Noise"
    ANALOG_OSC_PLUS_BANK_NAME = "OSC +"
    ANALOG_MIX_LFO_BANK_NAME = "Mix / LFO"
    ANALOG_LFO_PLUS_BANK_NAME = "LFO +"
    ANALOG_LOOPS_FILTER_BANK_NAME = "Loops / Filter"

    def __init__(self, *a, **k):
        DeviceComponent.__init__(self, *a, **k)
        self._use_safe_parameter_banks = False
        self._parameter_bank_cache = None
        self._parameter_bank_cache_device = None
        self._curated_parameter_display_names = ()
        self._curated_bank_names_cache = None
        self._curated_option_pages_cache = None
        self._curated_dynamic_parameter_keys_cache = None
        self._drift_decorator = None
        self._drift_decorator_device = None
        self._drift_base_decorator = None
        self._meld_decorator = None
        self._meld_decorator_device = None
        self._hybrid_reverb_decorator = None
        self._hybrid_reverb_decorator_device = None
        self._simpler_bank_decorator = None
        self._simpler_bank_decorator_device = None
        self._curated_decorator_factory = None
        if PushDeviceDecoratorFactory is not None:
            try:
                self._curated_decorator_factory = PushDeviceDecoratorFactory()
            except Exception:
                pass

    def invalidate_parameter_bank_cache(self):
        self._parameter_bank_cache = None
        self._parameter_bank_cache_device = None
        self._curated_parameter_display_names = ()
        self._curated_bank_names_cache = None
        self._curated_option_pages_cache = None
        self._curated_dynamic_parameter_keys_cache = None

    def set_device(self, device):
        if device != getattr(self, '_device', None):
            self._disconnect_drift_decorator()
            self._disconnect_meld_decorator()
            self._disconnect_hybrid_reverb_decorator()
            self._disconnect_simpler_bank_decorator()
            self._sync_curated_decorators(device)
        self.invalidate_parameter_bank_cache()
        self._use_safe_parameter_banks = False
        try:
            result = DeviceComponent.set_device(self, device)
            if self._is_meld() and self._bank_index == 0:
                self._bank_index = 1
                self.update()
            return result
        except IndexError:
            self._use_safe_parameter_banks = True
            self._bank_index = 1 if self._is_meld() else 0
            try:
                self.update()
            except Exception:
                pass
            try:
                self.notify_device()
            except Exception:
                pass

    def disconnect(self):
        self._disconnect_drift_decorator()
        self._disconnect_meld_decorator()
        self._disconnect_hybrid_reverb_decorator()
        self._disconnect_simpler_bank_decorator()
        factory = self._curated_decorator_factory
        self._curated_decorator_factory = None
        if factory:
            try:
                factory.disconnect()
            except Exception:
                pass
        DeviceComponent.disconnect(self)

    def update(self):
        try:
            return DeviceComponent.update(self)
        except IndexError:
            self._use_safe_parameter_banks = True
            self._clamp_bank_index_to_safe_banks()
            try:
                return DeviceComponent.update(self)
            except IndexError:
                pass

    def _current_bank_details(self):
        try:
            return DeviceComponent._current_bank_details(self)
        except IndexError:
            self._use_safe_parameter_banks = True
            self._clamp_bank_index_to_safe_banks()
            try:
                return DeviceComponent._current_bank_details(self)
            except IndexError:
                return '', tuple([None] * self.SAFE_PARAMETER_BANK_SIZE)

    def _parameter_banks(self):
        device = getattr(self, '_device', None)
        uses_curated_banks = self._uses_curated_banks()
        uses_cache = (
            self._is_operator() or self._is_chord() or self._is_drift() or self._is_meld() or
            self._is_hybrid_reverb() or uses_curated_banks
        )
        if (uses_cache and self._parameter_bank_cache is not None and
                self._parameter_bank_cache_device == device):
            return list(self._parameter_bank_cache)

        if uses_curated_banks:
            curated_banks = self._curated_parameter_banks()
            if curated_banks:
                self._parameter_bank_cache = tuple(curated_banks)
                self._parameter_bank_cache_device = device
                return list(curated_banks)
            try:
                return list(DeviceComponent._parameter_banks(self))
            except IndexError:
                self._use_safe_parameter_banks = True
                return self._safe_parameter_banks()

        base_names = self._base_parameter_bank_names()
        if self._use_safe_parameter_banks:
            banks = self._safe_parameter_banks()
        else:
            try:
                banks = DeviceComponent._parameter_banks(self)
            except IndexError:
                self._use_safe_parameter_banks = True
                base_names = self._safe_parameter_bank_names_base()
                banks = self._safe_parameter_banks()
        banks = self._add_tap_custom_banks(banks, base_names)
        if uses_cache:
            self._parameter_bank_cache = tuple(banks)
            self._parameter_bank_cache_device = device
        return banks

    def _parameter_bank_names(self):
        if self._uses_curated_banks():
            curated_names = self._curated_bank_names()
            if curated_names:
                return curated_names
        return self._add_tap_custom_bank_names(self._base_parameter_bank_names())

    def _best_of_parameter_bank(self):
        if self._use_safe_parameter_banks:
            return []
        try:
            return DeviceComponent._best_of_parameter_bank(self)
        except IndexError:
            self._use_safe_parameter_banks = True
            return []

    def _number_of_parameter_banks(self):
        return len(self._parameter_banks())

    def _base_parameter_bank_names(self):
        if self._use_safe_parameter_banks:
            # Simpler's native parameter lookup can briefly fail while its
            # sample mode is changing.  Keep Live's curated names even when
            # the safer parameter lookup is needed; otherwise the fallback
            # leaks unstable "Bank 1" ... "Bank 7" labels to Tap.
            if self._is_simpler():
                try:
                    return tuple(DeviceComponent._parameter_bank_names(self))
                except IndexError:
                    pass
            return self._safe_parameter_bank_names_base()
        try:
            return tuple(DeviceComponent._parameter_bank_names(self))
        except IndexError:
            self._use_safe_parameter_banks = True
            return self._safe_parameter_bank_names_base()

    def _safe_parameter_bank_names_base(self):
        bank_count = len(self._safe_parameter_banks())
        device = getattr(self, '_device', None)
        names = []
        for index in range(bank_count):
            name = None
            if device and hasattr(device, 'get_bank_name'):
                try:
                    name = device.get_bank_name(index)
                except Exception:
                    pass
            if name:
                name = ''.join(char for char in str(name) if ord(char) < 128)
            names.append(name or "Bank {}".format(index + 1))
        return tuple(names)

    def _device_class_name(self):
        try:
            return str(self._device.class_name)
        except Exception:
            return ""

    def _is_operator(self):
        return self._device_class_name() == 'Operator'

    def _is_chord(self):
        return self._device_class_name() == 'MidiChord'

    def _is_wavetable(self):
        device = getattr(self, '_device', None)
        try:
            return (
                self._device_class_name() in ('Wavetable', 'InstrumentVector') or
                str(device.class_display_name) == 'Wavetable' or
                hasattr(device, 'oscillator_1_wavetables')
            )
        except Exception:
            return False

    def _is_simpler(self):
        return self._device_class_name() == 'OriginalSimpler'

    def _simpler_uses_native_banks(self):
        if not self._is_simpler():
            return False
        try:
            return bool(self._device.multi_sample_mode)
        except Exception:
            # If this Live version cannot expose multisample mode, a missing
            # sample is ambiguous. Keep the normal parameter banks instead of
            # presenting Simpler as empty; Browse remains available in its own
            # bank.
            try:
                return not liveobj_valid(self._device.sample)
            except Exception:
                return True

    def _is_drumcell(self):
        return self._device_class_name() == 'DrumCell'

    def _is_delay(self):
        return self._device_class_name() == 'Delay'

    def _is_grain_delay(self):
        return self._device_class_name() == 'GrainDelay'

    def _is_analog(self):
        return self._device_class_name() == 'UltraAnalog'

    def _is_auto_filter(self):
        try:
            return (
                self._device_class_name() == 'AutoFilter' or
                (str(self._device.class_display_name) == 'Auto Filter' and
                 not self._is_auto_filter_2())
            )
        except Exception:
            return False

    def _is_auto_filter_2(self):
        return self._device_class_name() == 'AutoFilter2'

    def _is_beat_repeat(self):
        try:
            return (
                self._device_class_name() == 'BeatRepeat' or
                str(self._device.class_display_name) == 'Beat Repeat'
            )
        except Exception:
            return False

    def _is_hybrid_reverb(self):
        try:
            return (
                self._device_class_name() in ('Hybrid', 'HybridReverb') or
                str(self._device.class_display_name) == 'Hybrid Reverb'
            )
        except Exception:
            return False

    def _is_drift(self):
        try:
            return self._device_class_name() == 'Drift' or str(self._device.class_display_name) == 'Drift'
        except Exception:
            return False

    def _is_meld(self):
        device = getattr(self, '_device', None)
        try:
            return (
                self._device_class_name() in ('InstrumentMeld', 'Meld') or
                str(device.class_display_name) == 'Meld' or
                hasattr(device, 'selected_engine')
            )
        except Exception:
            return False

    def _curated_bank_source(self):
        class_name = self._device_class_name()
        if class_name in self.CURATED_MOVE_BANK_CLASSES and class_name in MOVE_BANK_DEFINITIONS:
            return MOVE_BANK_DEFINITIONS
        if class_name in self.CURATED_PUSH_BANK_CLASSES and class_name in PUSH_BANK_DEFINITIONS:
            return PUSH_BANK_DEFINITIONS
        return None

    def _curated_bank_definition(self):
        source = self._curated_bank_source()
        return source.get(self._device_class_name()) if source else None

    def _curated_dynamic_parameter_keys(self):
        cached = self._curated_dynamic_parameter_keys_cache
        if cached is not None:
            return cached

        condition_names = set()
        definitions = []
        for definition in (
                self._curated_bank_definition(),
                PUSH_BANK_DEFINITIONS.get(self._device_class_name())):
            if definition and not any(definition is existing for existing in definitions):
                definitions.append(definition)
        for definition in definitions:
            for bank_definition in definition.values():
                for slots in bank_definition.values():
                    if not isinstance(slots, (tuple, list)):
                        continue
                    for slot in slots:
                        for condition in getattr(slot, '_conditions', ()) or ():
                            condition_list = condition.get('ConditionsListName', ())
                            for subcondition in condition_list:
                                name = subcondition.get('ConditionName')
                                if name:
                                    condition_names.add(str(name))

        # These custom pages switch parameter identity with the device mode.
        if self._device_class_name() in ('AutoPan2', 'Chorus2'):
            condition_names.add('Mode')

        self._curated_dynamic_parameter_keys_cache = frozenset(
            re.sub(r'[^a-z0-9]+', '', name.lower())
            for name in condition_names
        )
        return self._curated_dynamic_parameter_keys_cache

    def curated_parameter_drives_bank(self, parameter):
        if parameter is None or not self._uses_curated_banks():
            return False
        names = (
            str(getattr(parameter, 'name', '')),
            str(getattr(parameter, 'original_name', '')),
        )
        parameter_keys = set(
            re.sub(r'[^a-z0-9]+', '', name.lower())
            for name in names
        )
        return bool(parameter_keys.intersection(self._curated_dynamic_parameter_keys()))

    def _uses_curated_banks(self):
        return (
            BankingInfo is not None and
            DescribedDeviceParameterBank is not None and
            self._curated_bank_definition() is not None
        )

    def _sync_curated_decorators(self, device):
        factory = self._curated_decorator_factory
        if not factory:
            return
        try:
            factory.sync_decorated_objects([device] if liveobj_valid(device) else [])
        except Exception:
            pass

    def _curated_decorated_device(self):
        device = getattr(self, '_device', None)
        factory = self._curated_decorator_factory
        if not factory or not liveobj_valid(device):
            return device
        try:
            return factory.decorate(device)
        except Exception:
            return device

    def _curated_bank_names(self):
        if self._curated_bank_names_cache is not None:
            return self._curated_bank_names_cache
        definition = self._curated_bank_definition()
        names = list(definition.keys()) if definition else []
        if self._device_class_name() == 'AutoShift' and names:
            names.append(self.AUTO_SHIFT_DETAILS_BANK_NAME)
        elif self._device_class_name() == 'AutoPan2' and names:
            names.append(self.AUTO_PAN_MODE_BANK_NAME)
        elif self._device_class_name() == 'Chorus2' and names:
            names.append(self.CHORUS_MODE_BANK_NAME)
        option_page_count = len(self._curated_option_pages())
        if option_page_count == 1:
            names.append(self.CURATED_OPTIONS_BANK_NAME)
        elif option_page_count > 1:
            names.extend(
                "{} {}".format(self.CURATED_OPTIONS_BANK_NAME, index + 1)
                for index in range(option_page_count)
            )
        self._curated_bank_names_cache = tuple(names)
        return self._curated_bank_names_cache

    def _set_curated_shift_state(self, bank, shifted):
        has_shift_slots = False
        for slot in getattr(bank, '_dynamic_slots', ()):
            setter = getattr(slot, 'set_shifted_state', None)
            if callable(setter):
                has_shift_slots = True
                try:
                    setter(bool(shifted))
                except Exception:
                    pass
        if has_shift_slots:
            try:
                bank._update_parameters()
            except Exception:
                pass

    def _curated_bank_parameters(self, bank, index, shifted=False):
        bank.index = index
        self._set_curated_shift_state(bank, shifted)
        parameters = []
        display_names = []
        for item in getattr(bank, 'parameters', ()) or ():
            if isinstance(item, (tuple, list)):
                parameters.append(item[0] if item else None)
                display_names.append(item[1] if len(item) > 1 and item[1] else None)
            else:
                parameters.append(item)
                display_names.append(None)
        parameters.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(parameters)))
        display_names.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(display_names)))
        return (
            tuple(parameters[:self.SAFE_PARAMETER_BANK_SIZE]),
            tuple(display_names[:self.SAFE_PARAMETER_BANK_SIZE]),
        )

    def _curated_option_parameter(self, option):
        parameter = getattr(option, '_parameter', None)
        if parameter is None:
            parameter = getattr(option, '_property_host', None)
        return parameter

    def _curated_option_pages(self):
        if self._curated_option_pages_cache is not None:
            return self._curated_option_pages_cache
        definition = PUSH_BANK_DEFINITIONS.get(self._device_class_name())
        has_option_slots = bool(definition) and any(
            any(bool(slot) for slot in bank_definition.get('Options', ()))
            for bank_definition in definition.values()
        )
        if not has_option_slots:
            self._curated_option_pages_cache = ()
            return ()
        device = self._curated_decorated_device()
        if (
            not liveobj_valid(device) or
            BankingInfo is None or
            DescribedDeviceParameterBankWithOptions is None
        ):
            self._curated_option_pages_cache = ()
            return ()
        banking_info = BankingInfo({self._device_class_name(): definition})
        bank = None
        try:
            bank = DescribedDeviceParameterBankWithOptions(
                device=device,
                size=self.SAFE_PARAMETER_BANK_SIZE,
                banking_info=banking_info,
            )
            option_parameters = []
            option_names = []
            seen_parameters = set()
            for index in range(len(definition)):
                bank.index = index
                for option in getattr(bank, 'options', ()) or ():
                    if option is None:
                        continue
                    parameter = self._curated_option_parameter(option)
                    if parameter is None:
                        continue
                    parameter_key = id(parameter)
                    if parameter_key in seen_parameters:
                        continue
                    seen_parameters.add(parameter_key)
                    option_parameters.append(parameter)
                    name = str(getattr(option, 'name', '') or getattr(parameter, 'name', ''))
                    if name == 'frequency_dial_mode_opt':
                        name = 'Frequency Mode'
                    option_names.append(name)
            pages = []
            for start in range(0, len(option_parameters), self.SAFE_PARAMETER_BANK_SIZE):
                parameters = option_parameters[start:start + self.SAFE_PARAMETER_BANK_SIZE]
                display_names = option_names[start:start + self.SAFE_PARAMETER_BANK_SIZE]
                parameters.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(parameters)))
                display_names.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(display_names)))
                pages.append((tuple(parameters), tuple(display_names)))
            self._curated_option_pages_cache = tuple(pages)
            return self._curated_option_pages_cache
        except Exception:
            self._curated_option_pages_cache = ()
            return ()
        finally:
            if bank:
                try:
                    bank.disconnect()
                except Exception:
                    pass

    def _curated_auto_pan_mode_bank(self):
        mode = self._parameter_by_names('Mode')
        mode_name = self._parameter_display(mode).strip().lower()
        is_tremolo = 'tremolo' in mode_name
        is_panning = 'panning' in mode_name or 'pan' in mode_name
        parameters = (
            mode,
            self._parameter_by_names('Vintage') if is_tremolo else None,
            self._parameter_by_names('Stereo Mode') if is_panning else None,
        ) + tuple([None] * 5)
        display_names = ('Mode', 'Vintage' if is_tremolo else None,
                         'Stereo Mode' if is_panning else None) + tuple([None] * 5)
        return parameters, display_names

    def _curated_chorus_mode_bank(self):
        mode = self._parameter_by_names('Mode')
        mode_name = self._parameter_display(mode).strip().lower()
        is_chorus = 'classic' in mode_name or 'chorus' in mode_name
        parameters = (
            mode,
            self._parameter_by_names('Delay Time') if is_chorus else None,
            self._parameter_by_names('Delay Taps') if is_chorus else None,
            self._parameter_by_names('HP Enabled', 'HP On'),
            self._parameter_by_names('HP Freq'),
            None,
            None,
            self._parameter_by_names('Dry/Wet'),
        )
        display_names = (
            'Mode',
            'Delay Time' if is_chorus else None,
            'Delay Taps' if is_chorus else None,
            'HP On',
            'HP Freq',
            None,
            None,
            None,
        )
        return parameters, display_names

    def _add_internal_scale_parameter(self, resolved_banks):
        if self._device_class_name() != 'MidiScale' or not resolved_banks:
            return
        internal_scale = self._parameter_by_names('Internal Scale', 'InternalScale', 'Scale')
        if internal_scale is None:
            return
        parameters, display_names = resolved_banks[0]
        parameters = tuple((parameters[0], internal_scale) + parameters[1:7])
        display_names = tuple((display_names[0], 'Internal Scale') + display_names[1:7])
        resolved_banks[0] = parameters, display_names

    def _curated_parameter_banks(self):
        definition = self._curated_bank_definition()
        device = self._curated_decorated_device()
        if not definition or not liveobj_valid(device):
            return ()
        banking_info = BankingInfo({self._device_class_name(): definition})
        bank = None
        try:
            bank = DescribedDeviceParameterBank(
                device=device,
                size=self.SAFE_PARAMETER_BANK_SIZE,
                banking_info=banking_info,
            )
            resolved_banks = [
                self._curated_bank_parameters(bank, index)
                for index in range(len(definition))
            ]
            if self._device_class_name() == 'AutoShift' and resolved_banks:
                resolved_banks.append(self._curated_bank_parameters(bank, 0, shifted=True))
            elif self._device_class_name() == 'AutoPan2' and resolved_banks:
                resolved_banks.append(self._curated_auto_pan_mode_bank())
            elif self._device_class_name() == 'Chorus2' and resolved_banks:
                resolved_banks.append(self._curated_chorus_mode_bank())
            self._add_internal_scale_parameter(resolved_banks)
            resolved_banks.extend(self._curated_option_pages())
            self._curated_parameter_display_names = tuple(
                display_names for _, display_names in resolved_banks
            )
            return tuple(parameters for parameters, _ in resolved_banks)
        except Exception:
            self._curated_parameter_display_names = ()
            return ()
        finally:
            if bank:
                try:
                    bank.disconnect()
                except Exception:
                    pass

    def curated_parameter_display_name(self, parameter):
        try:
            bank_index = self._bank_index
            display_names = self._curated_parameter_display_names[bank_index]
            parameter_bank = self._parameter_bank_cache[bank_index]
            for index, candidate in enumerate(parameter_bank):
                if candidate is parameter and index < len(display_names):
                    return display_names[index]
        except Exception:
            pass
        return None

    def _disconnect_drift_decorator(self):
        decorator = self._drift_decorator
        base_decorator = self._drift_base_decorator
        self._drift_decorator = None
        self._drift_decorator_device = None
        self._drift_base_decorator = None
        if decorator:
            try:
                decorator.disconnect()
            except Exception:
                pass
        if base_decorator and base_decorator is not decorator:
            try:
                base_decorator.disconnect()
            except Exception:
                pass

    def _disconnect_meld_decorator(self):
        decorator = self._meld_decorator
        self._meld_decorator = None
        self._meld_decorator_device = None
        if decorator:
            try:
                decorator.disconnect()
            except Exception:
                pass

    def _disconnect_hybrid_reverb_decorator(self):
        decorator = self._hybrid_reverb_decorator
        self._hybrid_reverb_decorator = None
        self._hybrid_reverb_decorator_device = None
        if decorator:
            try:
                decorator.disconnect()
            except Exception:
                pass

    def _disconnect_simpler_bank_decorator(self):
        decorator = self._simpler_bank_decorator
        self._simpler_bank_decorator = None
        self._simpler_bank_decorator_device = None
        if decorator:
            try:
                decorator.disconnect()
            except Exception:
                pass

    def simpler_decorator(self):
        """Return the bank decorator so Simpler support does not create a duplicate."""
        if not self._is_simpler() or SimplerDeviceDecorator is None:
            return None
        self._decorated_parameters()
        return self._simpler_bank_decorator

    def _decorated_parameters(self):
        device = getattr(self, '_device', None)
        if self._uses_curated_banks():
            decorated = self._curated_decorated_device()
            return tuple(getattr(decorated, 'parameters', getattr(device, 'parameters', ())))
        if self._is_hybrid_reverb() and HybridReverbDeviceDecorator is not None:
            if (self._hybrid_reverb_decorator is None or
                    self._hybrid_reverb_decorator_device != device):
                self._disconnect_hybrid_reverb_decorator()
                try:
                    self._hybrid_reverb_decorator = HybridReverbDeviceDecorator(live_object=device)
                    self._hybrid_reverb_decorator_device = device
                except TypeError:
                    try:
                        self._hybrid_reverb_decorator = HybridReverbDeviceDecorator(
                            live_object=device, additional_properties={}
                        )
                        self._hybrid_reverb_decorator_device = device
                    except Exception:
                        self._hybrid_reverb_decorator = None
                except Exception:
                    self._hybrid_reverb_decorator = None
            if self._hybrid_reverb_decorator:
                return tuple(self._hybrid_reverb_decorator.parameters)
        if self._is_simpler():
            decorated = []
            if SimplerDeviceDecorator is not None:
                if self._simpler_bank_decorator is None or self._simpler_bank_decorator_device != device:
                    self._disconnect_simpler_bank_decorator()
                    try:
                        self._simpler_bank_decorator = SimplerDeviceDecorator(
                            live_object=device, additional_properties={}
                        )
                        self._simpler_bank_decorator_device = device
                    except Exception:
                        self._simpler_bank_decorator = None
                if self._simpler_bank_decorator:
                    decorated.extend(self._simpler_bank_decorator.parameters)

            decorated_ids = set(id(parameter) for parameter in decorated)
            decorated.extend(
                parameter for parameter in getattr(device, 'parameters', ())
                if id(parameter) not in decorated_ids
            )
            # In multisample mode Simpler exposes the actual Sampler as a
            # nested device. Parameters such as "F On" and "Pe On" live there
            # rather than in OriginalSimpler's parameter list.
            sampler = getattr(device, 'sampler', None)
            if sampler and liveobj_valid(sampler):
                decorated_ids.update(id(parameter) for parameter in decorated)
                decorated.extend(
                    parameter for parameter in getattr(sampler, 'parameters', ())
                    if id(parameter) not in decorated_ids
                )
            return tuple(decorated)
        if self._is_drift() and DriftDeviceDecorator is not None:
            if self._drift_decorator is None or self._drift_decorator_device != device:
                self._disconnect_drift_decorator()
                try:
                    voice_mode = None
                    if BaseDriftDeviceDecorator is not None:
                        self._drift_base_decorator = BaseDriftDeviceDecorator(live_object=device)
                        voice_mode = next(
                            (parameter for parameter in self._drift_base_decorator.parameters
                             if str(getattr(parameter, 'name', '')) == 'Voice Mode'),
                            None
                        )
                    additional_properties = {'voice_mode': voice_mode} if voice_mode else {}
                    self._drift_decorator = DriftDeviceDecorator(
                        live_object=device, additional_properties=additional_properties
                    )
                    self._drift_decorator_device = device
                except Exception:
                    self._drift_decorator = None
            if self._drift_decorator:
                parameters = list(self._drift_decorator.parameters)
                if self._drift_base_decorator:
                    voice_mode = next(
                        (parameter for parameter in self._drift_base_decorator.parameters
                         if str(getattr(parameter, 'name', '')) == 'Voice Mode'),
                        None
                    )
                    if voice_mode:
                        parameters.append(voice_mode)
                return tuple(parameters)
        if self._is_meld() and MeldDeviceDecorator is not None:
            if self._meld_decorator is None or self._meld_decorator_device != device:
                self._disconnect_meld_decorator()
                try:
                    self._meld_decorator = MeldDeviceDecorator(live_object=device)
                    self._meld_decorator_device = device
                except Exception:
                    self._meld_decorator = None
            if self._meld_decorator:
                return tuple(self._meld_decorator.parameters)
        return tuple(getattr(device, 'parameters', ()))

    def _simpler_is_classic(self):
        try:
            return self._is_simpler() and int(self._device.playback_mode) == 0
        except Exception:
            return False

    def _simpler_is_slice(self):
        try:
            return self._is_simpler() and int(self._device.playback_mode) == 2
        except Exception:
            return False

    def _simpler_is_warped(self):
        try:
            sample = self._device.sample
            return liveobj_valid(sample) and bool(sample.warping)
        except Exception:
            return False

    def _simpler_browse_bank_name(self):
        return (
            self.SIMPLER_BROWSE_PLUS_BANK_NAME
            if self._simpler_uses_native_banks()
            else self.SIMPLER_BROWSE_BANK_NAME
        )

    def _custom_bank_insert_index(self, bank_names, anchor_name):
        anchor_name = re.sub(r'[^a-z0-9]+', '', anchor_name.lower())
        for index, name in enumerate(bank_names):
            normalized_name = re.sub(r'[^a-z0-9]+', '', str(name).lower())
            if anchor_name in normalized_name:
                return index + 1
        return len(bank_names)

    def _operator_waves_insert_index(self, bank_names):
        for index, name in enumerate(bank_names):
            normalized = re.sub(r'[^a-z0-9]+', '', str(name).lower())
            if normalized in ('oscd', 'oscillatord') or normalized.endswith('oscillatord'):
                return index + 1
        return len(bank_names)

    def _add_tap_custom_bank_names(self, bank_names):
        names = list(bank_names)
        if self._uses_curated_banks():
            names = list(self._curated_bank_names())
        elif self._is_auto_filter_2():
            names = list(self.AUTO_FILTER_2_BANK_NAMES)
        elif self._is_auto_filter():
            names = list(self.AUTO_FILTER_BANK_NAMES)
        elif self._is_beat_repeat():
            names = list(self.BEAT_REPEAT_BANK_NAMES)
        elif self._is_hybrid_reverb():
            names = list(self.HYBRID_REVERB_BANK_NAMES)
        elif self._is_drift():
            names = list(self.DRIFT_BANK_NAMES)
        elif self._is_meld():
            names = list(self.MELD_BANK_NAMES)
        elif self._is_chord():
            names.extend((
                self.CHORD_SHIFT_SCALE_BANK_NAME,
                self.CHORD_STRUM_BANK_NAME,
            ))
        elif self._is_operator():
            index = self._operator_waves_insert_index(names)
            names.insert(index, self.OPERATOR_WAVES_BANK_NAME)
            filter_index = self._operator_filter_bank_insert_index(names)
            names.insert(filter_index, self.OPERATOR_FILTER_PLUS_BANK_NAME)
            lfo_index = self._operator_lfo_bank_insert_index(names)
            names.insert(lfo_index, self.OPERATOR_LFO_PLUS_BANK_NAME)
        elif self._is_wavetable():
            self._replace_wavetable_envelope_bank_names(names)
            index = self._wavetable_waves_insert_index(names)
            names.insert(index, self.WAVETABLE_OSC_BANK_NAME)
        elif self._is_simpler():
            if not self._simpler_uses_native_banks():
                # Keep Live's native bank count and indices intact. Tap's
                # Push-like page replaces bank zero in place instead of
                # inserting a bank.
                if names:
                    names[0] = self.SIMPLER_MAIN_BANK_NAME
                else:
                    names.append(self.SIMPLER_MAIN_BANK_NAME)
                if self._simpler_is_classic() and len(names) > self.SIMPLER_AMP_BANK_INDEX:
                    names[self.SIMPLER_AMP_BANK_INDEX] = self.SIMPLER_AMP_BANK_NAME
                elif self._simpler_is_slice() and len(names) > self.SIMPLER_AMP_BANK_INDEX:
                    names[self.SIMPLER_AMP_BANK_INDEX] = self.SIMPLER_SLICE_DETAIL_BANK_NAME
                self._configure_simpler_control_bank_names(names)
                names.insert(1, self.SIMPLER_ACTIONS_BANK_NAME)
            else:
                # Multisample Simpler uses Live's native banks, but its Warp
                # As parameter is still a quantized encoder. Replace the
                # native control pages so Tap can expose Warp As as a real
                # momentary action here as well.
                self._configure_simpler_control_bank_names(names)
            names.append(self._simpler_browse_bank_name())
        elif self._is_analog():
            names = self._analog_bank_names(names)
        elif self._is_drumcell():
            custom_names = (
                self.DRUMCELL_SAMPLE_BANK_NAME,
                self.DRUMCELL_FX_FILTER_BANK_NAME,
                self.DRUMCELL_REST_BANK_NAME,
            )
            while len(names) < len(custom_names):
                names.append('Bank {}'.format(len(names) + 1))
            names[:len(custom_names)] = custom_names
            if len(names) > 3:
                names[3] = self.DRUMCELL_FX_2_BANK_NAME
            if len(names) > 4:
                names[4] = self.DRUMCELL_FX_3_BANK_NAME
        elif self._is_grain_delay():
            names = list(self.GRAIN_DELAY_BANK_NAMES)
        elif self._is_delay():
            names = list(self.DELAY_BANK_NAMES)
        return tuple(names)

    def _add_tap_custom_banks(self, banks, base_names):
        banks = list(banks)
        names = list(base_names)
        if self._uses_curated_banks():
            curated_banks = self._curated_parameter_banks()
            if curated_banks:
                banks = list(curated_banks)
        elif self._is_auto_filter_2():
            banks = list(self._auto_filter_2_parameter_banks())
        elif self._is_auto_filter():
            banks = list(self._auto_filter_parameter_banks())
        elif self._is_beat_repeat():
            banks = list(self._beat_repeat_parameter_banks())
        elif self._is_hybrid_reverb():
            banks = list(self._hybrid_reverb_parameter_banks())
        elif self._is_drift():
            banks = list(self._drift_parameter_banks())
        elif self._is_meld():
            banks = list(self._meld_parameter_banks())
        elif self._is_chord():
            banks.extend((
                self._chord_shift_scale_parameters(),
                self._chord_strum_parameters(),
            ))
        elif self._is_operator():
            self._replace_operator_lfo_bank(banks, names)
            waves = self._operator_wave_parameters(banks)
            index = self._operator_waves_insert_index(names)
            banks.insert(index, tuple(waves + [None] * (self.SAFE_PARAMETER_BANK_SIZE - len(waves))))
            names.insert(index, self.OPERATOR_WAVES_BANK_NAME)
            filter_index = self._operator_filter_bank_insert_index(names)
            banks.insert(filter_index, self._operator_filter_plus_parameters())
            names.insert(filter_index, self.OPERATOR_FILTER_PLUS_BANK_NAME)
            lfo_index = self._operator_lfo_bank_insert_index(names)
            banks.insert(lfo_index, self._operator_lfo_plus_parameters())
        elif self._is_wavetable():
            self._replace_wavetable_envelope_banks(banks, names)
            # These are Live.WavetableDevice properties, not DeviceParameters.
            # Tap handles their MIDI mapping and feedback directly.
            index = self._wavetable_waves_insert_index(names)
            banks.insert(index, tuple([None] * self.SAFE_PARAMETER_BANK_SIZE))
        elif self._is_simpler():
            uses_native_banks = self._simpler_uses_native_banks()
            if not uses_native_banks:
                if not banks:
                    banks.append(tuple([None] * self.SAFE_PARAMETER_BANK_SIZE))
                banks[0] = tuple([None] * self.SAFE_PARAMETER_BANK_SIZE)
                if self._simpler_is_classic() and len(banks) > self.SIMPLER_AMP_BANK_INDEX:
                    banks[self.SIMPLER_AMP_BANK_INDEX] = self._simpler_amp_parameters()
                elif self._simpler_is_slice() and len(banks) > self.SIMPLER_AMP_BANK_INDEX:
                    banks[self.SIMPLER_AMP_BANK_INDEX] = self._simpler_slice_detail_parameters()
                self._replace_simpler_lfo_bank(banks, names)
                self._configure_simpler_control_banks(banks, names)
                banks.insert(1, tuple([None] * self.SAFE_PARAMETER_BANK_SIZE))
            else:
                self._configure_simpler_control_banks(banks, names)
                # DeviceComponent can expose more resolved C++ banks than its
                # stable curated name table. Keep only the banks represented by
                # that table, then add Browse + at the matching final index.
                visible_bank_count = len(names)
                banks = banks[:visible_bank_count]
                while len(banks) < visible_bank_count:
                    banks.append(tuple([None] * self.SAFE_PARAMETER_BANK_SIZE))
            banks.append(self._simpler_browse_parameters())
        elif self._is_analog():
            banks = self._analog_parameter_banks(banks, names)
        elif self._is_drumcell():
            custom_banks = (
                self._drumcell_sample_parameters(),
                self._drumcell_fx_filter_parameters(),
                self._drumcell_rest_parameters(),
            )
            while len(banks) < len(custom_banks):
                banks.append(tuple([None] * self.SAFE_PARAMETER_BANK_SIZE))
            banks[:len(custom_banks)] = custom_banks
        elif self._is_grain_delay():
            banks = list(self._grain_delay_parameter_banks())
        elif self._is_delay():
            banks = list(self._delay_parameter_banks())
        return banks

    def _normalized_bank_name(self, name):
        return re.sub(r'[^a-z0-9]+', '', str(name).lower())

    def _bank_index_named(self, bank_names, *wanted_names):
        wanted = set(self._normalized_bank_name(name) for name in wanted_names)
        return next(
            (index for index, name in enumerate(bank_names)
             if self._normalized_bank_name(name) in wanted),
            None,
        )

    def _replace_simpler_lfo_bank(self, banks, bank_names):
        index = self._bank_index_named(bank_names, 'LFO')
        if index is None or index >= len(banks):
            return
        bank = list(banks[index])
        bank.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(bank)))
        sync = self._parameter_by_names('L Sync')
        sync_on = False
        if sync:
            try:
                display = str(sync.str_for_value(sync.value)).strip().lower()
                sync_on = display in ('on', 'yes', 'true', 'sync', 'synced')
                if display in ('off', 'no', 'false', 'free'):
                    sync_on = False
            except Exception:
                try:
                    sync_on = float(sync.value) > float(sync.min)
                except Exception:
                    pass
        rate = self._parameter_by_names('L Sync Rate' if sync_on else 'L Rate')
        for control_index, parameter in enumerate(bank):
            key = self._normalized_bank_name(getattr(parameter, 'name', '')) if parameter else ''
            original_key = self._normalized_bank_name(getattr(parameter, 'original_name', '')) if parameter else ''
            if key == 'lrate' or original_key == 'lrate':
                bank[control_index] = rate
            elif key == 'lrkey' or original_key == 'lrkey':
                bank[control_index] = sync
        banks[index] = tuple(bank[:self.SAFE_PARAMETER_BANK_SIZE])

    def _simpler_warp_mode_name(self):
        try:
            value = int(self._device.sample.warp_mode)
            modes = (
                (Live.Clip.WarpMode.beats, 'beats'),
                (Live.Clip.WarpMode.tones, 'tones'),
                (Live.Clip.WarpMode.texture, 'texture'),
                (Live.Clip.WarpMode.repitch, 'repitch'),
                (Live.Clip.WarpMode.complex, 'complex'),
                (Live.Clip.WarpMode.complex_pro, 'complexpro'),
            )
            return next((name for mode, name in modes if int(mode) == value), '')
        except Exception:
            return ''

    def _simpler_control_parameters(self):
        mode = self._simpler_warp_mode_name() if self._simpler_is_warped() else ''
        mode_parameters = {
            'beats': ('Preserve', 'Loop Mode', 'Envelope'),
            'tones': ('Grain Size Tones',),
            'texture': ('Grain Size Texture', 'Flux'),
            'complexpro': ('Formants', 'Envelope Complex Pro'),
        }.get(mode, ())
        parameters = [None]
        parameters.extend(self._parameter_by_names(name) for name in mode_parameters)
        parameters.append(self._parameter_by_names('Filter Drive'))
        parameters.extend([None] * max(0, 5 - len(parameters)))
        parameters.extend((
            self._parameter_by_names('Pe < Env'),
            self._parameter_by_names('Pe Attack'),
            self._parameter_by_names('Pe Decay'),
        ))
        return tuple(parameters[:self.SAFE_PARAMETER_BANK_SIZE])

    def _simpler_controls_2_parameters(self):
        return (
            self._parameter_by_names('Transpose'),
            self._parameter_by_names('Detune'),
            self._parameter_by_names('Glide Mode', 'Glide', 'Glide On'),
            self._parameter_by_names('Glide Time'),
            self._parameter_by_names('L R < Key'),
            self._parameter_by_names('L Retrig'),
            # Live 12.4 exposes Simpler's filter switch as "F On".
            self._parameter_by_names('F On', 'Filter On', 'Filter On/Off', 'Filter Enable'),
            self._parameter_by_names('Pe On', 'Pitch Envelope On'),
        )

    def _simpler_browse_parameters(self):
        if not self._simpler_uses_native_banks():
            return tuple([None] * self.SAFE_PARAMETER_BANK_SIZE)
        return (
            None,  # Browse Samples is handled as a Tap action.
            self._parameter_by_names('F On', 'Filter On', 'Filter On/Off', 'Filter Enable'),
            self._parameter_by_names('Filter Type', 'Filter Type (Legacy)'),
            self._parameter_by_names('Pe On', 'Pitch Envelope On'),
            self._parameter_by_names('Pe < Env', 'Pitch Envelope Amount'),
            self._parameter_by_names('Transpose'),
            self._parameter_by_names('Detune'),
            self._parameter_by_names('Volume'),
        )

    def _simpler_control_bank_indices(self, bank_names):
        wanted = {
            self._normalized_bank_name(self.SIMPLER_WARP_BANK_NAME),
            self._normalized_bank_name(self.SIMPLER_CONTROLS_2_BANK_NAME),
            self._normalized_bank_name('Pitch Env'),
            self._normalized_bank_name('Controls 3'),
            self._normalized_bank_name('Options'),
            self._normalized_bank_name('Warp'),
        }
        return [
            index for index, name in enumerate(bank_names)
            if self._normalized_bank_name(name) in wanted
        ]

    def _configure_simpler_control_bank_names(self, bank_names):
        indices = self._simpler_control_bank_indices(bank_names)
        insertion_index = min(indices) if indices else min(1, len(bank_names))
        for index in reversed(indices):
            bank_names.pop(index)
        bank_names.insert(insertion_index, self.SIMPLER_WARP_BANK_NAME)
        bank_names.insert(insertion_index + 1, self.SIMPLER_CONTROLS_2_BANK_NAME)

    def _configure_simpler_control_banks(self, banks, bank_names):
        indices = self._simpler_control_bank_indices(bank_names)
        insertion_index = min(indices) if indices else min(1, len(banks))
        for index in reversed(indices):
            bank_names.pop(index)
            if index < len(banks):
                banks.pop(index)
        bank_names.insert(insertion_index, self.SIMPLER_WARP_BANK_NAME)
        banks.insert(insertion_index, self._simpler_control_parameters())
        bank_names.insert(insertion_index + 1, self.SIMPLER_CONTROLS_2_BANK_NAME)
        banks.insert(insertion_index + 1, self._simpler_controls_2_parameters())

    def _analog_bank_names(self, bank_names):
        names = list(bank_names)
        oscillator_index = self._bank_index_named(names, 'Oscillators')
        custom = [
            self.ANALOG_OSC_1_BANK_NAME,
            self.ANALOG_OSC_2_BANK_NAME,
            self.ANALOG_NOISE_BANK_NAME,
            self.ANALOG_OSC_PLUS_BANK_NAME,
        ]
        if oscillator_index is None:
            names = custom + names
        else:
            names[oscillator_index:oscillator_index + 1] = custom
        mix_index = self._bank_index_named(names, 'Mix')
        if mix_index is not None:
            names[mix_index] = self.ANALOG_MIX_LFO_BANK_NAME
            names.insert(mix_index + 1, self.ANALOG_LFO_PLUS_BANK_NAME)
        else:
            names.extend((self.ANALOG_MIX_LFO_BANK_NAME, self.ANALOG_LFO_PLUS_BANK_NAME))
        names.append(self.ANALOG_LOOPS_FILTER_BANK_NAME)
        return tuple(names)

    def _analog_parameter_banks(self, banks, bank_names):
        result = list(banks)
        oscillator_index = self._bank_index_named(bank_names, 'Oscillators')
        custom = [
            self._parameter_bank(
                'OSC1 Level', 'OSC1 Octave', 'OSC1 Semi', 'OSC1 Detune',
                'OSC1 Shape', 'PEG1 Amount', 'PEG1 Time', 'Volume',
            ),
            self._parameter_bank(
                'OSC2 Level', 'OSC2 Octave', 'OSC2 Semi', 'OSC2 Detune',
                'OSC2 Shape', 'PEG2 Amount', 'PEG2 Time', 'Volume',
            ),
            self._parameter_bank(
                'Noise On/Off', 'Noise Level', 'Noise Balance', 'Noise Color',
                None, None, None, None,
            ),
            self._parameter_bank(
                'OSC1 Mode', 'O1 Sub/Sync', 'OSC1 PW', 'O1 PW < LFO',
                'OSC2 Mode', 'O2 Sub/Sync', 'OSC2 PW', 'O2 PW < LFO',
            ),
        ]
        if oscillator_index is None:
            result = custom + result
            working_names = [
                self.ANALOG_OSC_1_BANK_NAME, self.ANALOG_OSC_2_BANK_NAME,
                self.ANALOG_NOISE_BANK_NAME, self.ANALOG_OSC_PLUS_BANK_NAME,
            ] + list(bank_names)
        else:
            result[oscillator_index:oscillator_index + 1] = custom
            working_names = list(bank_names)
            working_names[oscillator_index:oscillator_index + 1] = [
                self.ANALOG_OSC_1_BANK_NAME, self.ANALOG_OSC_2_BANK_NAME,
                self.ANALOG_NOISE_BANK_NAME, self.ANALOG_OSC_PLUS_BANK_NAME,
            ]

        mix_index = self._bank_index_named(working_names, 'Mix')
        mix_bank = self._parameter_bank(
            'AMP1 Level', 'AMP1 Pan', 'AMP2 Level', 'AMP2 Pan',
            'LFO1 Shape', 'LFO1 Speed', 'LFO1 SncRate', 'LFO1 Sync',
        )
        lfo_plus_bank = self._parameter_bank(
            'LFO2 Shape', 'LFO2 Speed', 'LFO2 SncRate', 'LFO2 Sync',
            'LFO1 On/Off', 'LFO2 On/Off', None, None,
        )
        if mix_index is None:
            result.extend((mix_bank, lfo_plus_bank))
            working_names.extend((self.ANALOG_MIX_LFO_BANK_NAME, self.ANALOG_LFO_PLUS_BANK_NAME))
        else:
            result[mix_index] = mix_bank
            result.insert(mix_index + 1, lfo_plus_bank)
            working_names[mix_index] = self.ANALOG_MIX_LFO_BANK_NAME
            working_names.insert(mix_index + 1, self.ANALOG_LFO_PLUS_BANK_NAME)

        output_index = self._bank_index_named(working_names, 'Output')
        if output_index is not None and output_index < len(result):
            result[output_index] = self._parameter_bank(
                'Volume', 'Glide On/Off', 'Glide Time', 'Glide Legato',
                'Unison On/Off', 'Unison Detune', 'Vib On/Off', 'Vib Amount',
            )
        result.append(self._parameter_bank(
            'FEG1 Loop', 'F1 Drive', 'FEG2 Loop', 'F2 Drive',
            'AEG1 Loop', 'AEG2 Loop', 'F1 On/Off', 'F2 On/Off',
        ))
        return result

    def _parameter_bank(self, *specifications):
        parameters = []
        for specification in specifications:
            if not specification:
                parameters.append(None)
            elif isinstance(specification, (tuple, list)):
                parameters.append(self._parameter_by_names(*specification))
            elif isinstance(specification, str):
                parameters.append(self._parameter_by_names(specification))
            else:
                parameters.append(specification)
        parameters.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(parameters)))
        return tuple(parameters[:self.SAFE_PARAMETER_BANK_SIZE])

    def _auto_filter_2_parameter_banks(self):
        filter_type = self._parameter_value_text('Filter Type')
        filter_type_key = re.sub(r'[^a-z0-9]+', '', filter_type)
        uses_morph = any(
            name in filter_type_key
            for name in ('morph', 'comb', 'notchlp', 'notchlowpass', 'vowel')
        )
        slope = self._parameter_by_names('Slope', 'Filter Slope')
        morph_or_slope = self._parameter_by_names('Filter Morph') if uses_morph else slope
        if 'dj' in filter_type:
            frequency = self._parameter_by_names('Control')
        elif 'vowel' in filter_type:
            frequency = self._parameter_by_names('Pitch')
        else:
            frequency = self._parameter_by_names('Frequency')
        resonance = self._parameter_by_names('Formant') if 'vowel' in filter_type else self._parameter_by_names('Resonance')

        lfo_time_mode = self._parameter_value_text('LFO T Mode')
        if 'sixteenth' in lfo_time_mode or '16' in lfo_time_mode:
            lfo_rate = self._parameter_by_names('LFO 16th')
        elif 'time' in lfo_time_mode:
            lfo_rate = self._parameter_by_names('LFO Time')
        elif lfo_time_mode == 'rate':
            lfo_rate = self._parameter_by_names('LFO Freq')
        else:
            lfo_rate = self._parameter_by_names('LFO Rate')
        lfo_spatial_mode = self._parameter_value_text('LFO S Mode')
        lfo_phase_or_spin = self._parameter_by_names('LFO Phase') if 'phase' in lfo_spatial_mode else self._parameter_by_names('LFO Spin')

        sidechain_eq_type = self._parameter_value_text('S/C EQ Type')
        sidechain_q_or_gain = self._parameter_by_names('S/C EQ Q') if 'pass' in sidechain_eq_type else self._parameter_by_names('S/C EQ Gain')
        quantize_mode = self._parameter_value_text('LFO Q Mode')
        quantize_amount = self._parameter_by_names('LFO Steps') if 'step' in quantize_mode else self._parameter_by_names('LFO S&H')

        return (
            self._parameter_bank(
                'Filter Type', frequency, resonance, morph_or_slope,
                'Circuit', 'Drive', 'Output', ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'LFO Wave', 'LFO Amount', 'LFO T Mode', lfo_rate,
                'LFO S Mode', lfo_phase_or_spin, 'LFO Offset', 'LFO Morph',
            ),
            self._parameter_bank(
                'Env Amount', 'Env Hold On', 'Env Attack', 'Env Release',
                'S/C EQ On', 'S/C EQ Type', 'S/C EQ Freq', sidechain_q_or_gain,
            ),
            self._parameter_bank(
                'LFO Q Mode', quantize_amount, 'Env S&H On', 'Env S&H',
                None, None, None, None,
            ),
        )

    def _auto_filter_parameter_banks(self):
        filter_type_text = self._parameter_value_text('Filter Type', 'Filter Type (Legacy)')
        filter_type_key = re.sub(r'[^a-z0-9]+', '', filter_type_text)
        if 'lowpass' in filter_type_key or 'highpass' in filter_type_key:
            circuit = self._parameter_by_names('Filter Circuit - LP/HP')
        else:
            circuit = self._parameter_by_names('Filter Circuit - BP/NO/Morph')
        morph_or_drive = self._parameter_by_names('Morph') if 'morph' in filter_type_key else self._parameter_by_names('Drive')

        lfo_sync_text = self._parameter_value_text('LFO Sync')
        lfo_rate = self._parameter_by_names('LFO Frequency') if 'free' in lfo_sync_text else self._parameter_by_names('LFO Sync Rate')
        lfo_is_synced = 'sync' in lfo_sync_text and 'free' not in lfo_sync_text
        stereo_mode_text = self._parameter_value_text('LFO Stereo Mode')
        lfo_stereo = self._parameter_by_names('LFO Offset') if lfo_is_synced else self._parameter_by_names('LFO Stereo Mode')
        lfo_phase = self._parameter_by_names('LFO Phase') if lfo_is_synced or 'phase' in stereo_mode_text else self._parameter_by_names('LFO Spin')

        return (
            self._parameter_bank(
                ('Filter Type', 'Filter Type (Legacy)'), 'Frequency',
                ('Resonance', 'Resonance (Legacy)'), circuit, morph_or_drive,
                'LFO Amount', 'LFO Sync', lfo_rate,
            ),
            self._parameter_bank(
                ('Filter Type', 'Filter Type (Legacy)'), 'Frequency',
                ('Resonance', 'Resonance (Legacy)'), morph_or_drive, 'Slope',
                'Env. Attack', 'Env. Release', 'Env. Modulation',
            ),
            self._parameter_bank(
                'LFO Amount', 'LFO Waveform', 'LFO Sync', lfo_rate,
                lfo_stereo, lfo_phase, 'LFO Quantize On', 'LFO Quantize Rate',
            ),
            self._parameter_bank(
                'S/C On', 'S/C Mix', 'S/C Gain', None, None, None, None, None,
            ),
        )

    def _beat_repeat_parameter_banks(self):
        return (
            self._parameter_bank(
                'Grid', 'Interval', 'Offset', 'Gate',
                'Pitch', 'Pitch Decay', 'Variation', 'Chance',
            ),
            self._parameter_bank(
                'Filter On', 'Filter Freq', 'Filter Width', None,
                'Mix Type', 'Volume', 'Decay', 'Chance',
            ),
            self._parameter_bank(
                'Repeat', 'Interval', 'Offset', 'Gate',
                'Grid', 'Block Triplets', 'Variation', 'Variation Type',
            ),
        )

    def _hybrid_algorithm_type_key(self):
        return re.sub(r'[^a-z0-9]+', '', self._parameter_value_text('Algo Type'))

    def _hybrid_algorithm_modulation_parameter(self, algorithm):
        if 'prism' in algorithm:
            return None
        if 'tides' in algorithm:
            return self._parameter_by_names('Ti Waveform')
        return self._parameter_by_names('Modulation')

    def _hybrid_algorithm_page_one_parameters(self, algorithm):
        if 'darkhall' in algorithm:
            character_one = self._parameter_by_names('DH Shape')
            character_two = self._parameter_by_names('DH BassMult', 'DH Bass Mult')
        elif 'quartz' in algorithm:
            character_one = self._parameter_by_names('Qz Low Damp')
            character_two = self._parameter_by_names('Qz Distance')
        elif 'shimmer' in algorithm:
            character_one = self._parameter_by_names('Sh Pitch Shift')
            character_two = self._parameter_by_names('Sh Shimmer')
        elif 'tides' in algorithm:
            character_one = self._parameter_by_names('Ti Tide')
            character_two = self._parameter_by_names('Ti Rate')
        elif 'prism' in algorithm:
            character_one = self._parameter_by_names('Pr High Mult')
            character_two = self._parameter_by_names('Pr X Over')
        else:
            character_one = None
            character_two = None
        return character_one, character_two

    def _hybrid_algorithm_page_two_character(self, algorithm):
        if 'darkhall' in algorithm:
            return self._parameter_by_names('DH Bass X')
        if 'quartz' in algorithm or 'shimmer' in algorithm:
            return self._parameter_by_names('Diffusion')
        if 'tides' in algorithm:
            return self._parameter_by_names('Ti Phase')
        return None

    def _hybrid_predelay_is_synced(self):
        text = self._parameter_value_text('P.Dly Sync', 'Predelay Sync')
        return 'sync' in text or text == 'on'

    def _hybrid_reverb_parameter_banks(self):
        algorithm = self._hybrid_algorithm_type_key()
        algorithm_one, algorithm_two = self._hybrid_algorithm_page_one_parameters(algorithm)
        algorithm_modulation = self._hybrid_algorithm_modulation_parameter(algorithm)
        damping_or_low_mult = self._parameter_by_names('Pr Low Mult') if 'prism' in algorithm else self._parameter_by_names('Damping')

        low_type = self._parameter_value_text('EQ Low Type', 'EQ Lo Type')
        low_gain_or_slope = self._parameter_by_names(
            'EQ Low Slope', 'EQ Lo Slope'
        ) if 'cut' in low_type else self._parameter_by_names('EQ Low Gain', 'EQ Lo Gain')
        high_type = self._parameter_value_text('EQ High Type', 'EQ Hi Type')
        high_gain_or_slope = self._parameter_by_names(
            'EQ High Slope', 'EQ Hi Slope'
        ) if 'cut' in high_type else self._parameter_by_names('EQ High Gain', 'EQ Hi Gain')
        predelay_synced = self._hybrid_predelay_is_synced()
        predelay = self._parameter_by_names(
            'P.Dly 16th', 'Predelay 16th'
        ) if predelay_synced else self._parameter_by_names('P.Dly Time', 'Predelay')
        predelay_feedback = self._parameter_by_names(
            'P.Dly Fb 16th', 'Predel. FB 16th', 'Predelay FB 16th'
        ) if predelay_synced else self._parameter_by_names('P.Dly Fb Time', 'Predelay FB')

        return (
            self._parameter_bank(
                ('Send Gain', 'Send'), 'Routing', 'Blend', 'Algo Type',
                'Decay', 'Size', algorithm_modulation, ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'IR Category', 'IR', 'Ir Attack Time', 'Ir Decay Time',
                'Ir Size Factor', 'Blend', 'Routing', ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'Algo Type', 'Decay', 'Size', algorithm_one,
                algorithm_two, algorithm_modulation, 'Width', ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'Algo Type', damping_or_low_mult,
                self._hybrid_algorithm_page_two_character(algorithm), 'EQ Pre Algo',
                ('Send Gain', 'Send'), 'Blend', 'Routing', ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'EQ Pre Algo', ('EQ Low Type', 'EQ Lo Type'),
                ('EQ Low Freq', 'EQ Lo Freq'), low_gain_or_slope,
                ('EQ High Type', 'EQ Hi Type'), ('EQ High Freq', 'EQ Hi Freq'),
                high_gain_or_slope, ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'EQ Pre Algo', ('EQ P1 Freq', 'EQ Peak 1 Freq'),
                ('EQ P1 Q', 'EQ Peak 1 Q'), ('EQ P1 Gain', 'EQ Peak 1 Gain'),
                ('EQ P2 Freq', 'EQ Peak 2 Freq'), ('EQ P2 Q', 'EQ Peak 2 Q'),
                ('EQ P2 Gain', 'EQ Peak 2 Gain'), ('Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                ('Send Gain', 'Send'), ('P.Dly Sync', 'Predelay Sync'),
                predelay, predelay_feedback, ('Vintage', 'Vintage Copy'),
                'Width', 'Blend', ('Dry/Wet', 'Dry Wet'),
            ),
        )

    def _drift_parameter_banks(self):
        envelope_2 = self._drift_envelope_2_parameters()
        return (
            self._parameter_bank(
                'Osc 1 Wave', 'Osc 1 Shape', 'Osc 1 Gain', 'Osc 2 Gain',
                'LP Freq', 'LP Res', 'LP Mod Amt 1', 'LP Mod Amt 2',
            ),
            self._parameter_bank(
                'Osc 1 Wave', 'Osc 1 Shape', 'Osc 1 Oct', 'Osc 1 Gain',
                'Osc 2 Wave', 'Osc 2 Oct', 'Osc 2 Detune', 'Osc 2 Gain',
            ),
            self._parameter_bank(
                'Osc Retrig On', None, 'Noise Gain', 'Noise On',
                'Noise Flt On', None, None, None,
            ),
            self._parameter_bank(
                'Pitch Mod Src 1', 'Pitch Mod Amt 1', 'Pitch Mod Src 2', 'Pitch Mod Amt 2',
                'Shape Mod Src', 'Osc 1 Shape Mod Amt', 'Osc Retrig On', 'Noise Gain',
            ),
            self._parameter_bank(
                'LP Freq', 'LP Res', 'LP Type', 'HP Freq',
                'Osc 1 Flt On', 'Osc 2 Flt On', 'Noise Flt On', 'Noise On',
            ),
            self._parameter_bank(
                'Key > LPF', 'LP Mod Src 1', 'LP Mod Amt 1', 'LP Mod Src 2',
                'LP Mod Amt 2', None, None, None,
            ),
            self._parameter_bank(
                'Env 1 Attack', 'Env 1 Decay', 'Env 1 Sustain', 'Env 1 Release',
                None, None, None, None,
            ),
            envelope_2,
            self._parameter_bank(
                'Env 2 Cyc On', ('Cyc Env Tilt', 'Cyc Tilt'), ('Cyc Env Hold', 'Cyc Hold'),
                ('Cyc Env Time Mode', 'Cyc Mode'), ('Cyc Env Rate', 'Cyc Rate'),
                ('Cyc Env Ratio', 'Cyc Ratio'), ('Cyc Env Time', 'Cyc Time'),
                ('Cyc Env Synced', 'Cyc Synced'),
            ),
            self._parameter_bank(
                'LFO Wave', 'LFO Time Mode', self._drift_lfo_rate_parameter(),
                'LFO Amt', 'LFO Retrig On', 'LFO Mod Src', 'LFO Mod Amt', None,
            ),
            self._parameter_bank(
                'Mod Source 1', 'Mod Dest 1', 'Mod Matrix Amt 1',
                'Mod Source 2', 'Mod Dest 2', 'Mod Matrix Amt 2', None, None,
            ),
            self._parameter_bank(
                'Mod Source 3', 'Mod Dest 3', 'Mod Matrix Amt 3', 'Vel > Vol',
                None, None, None, None,
            ),
            self._parameter_bank(
                'Voice Mode', 'Voice Count', 'Thickness', 'Spread',
                'Strength', 'Legato On', 'Glide Time', 'Drift',
            ),
            self._parameter_bank(
                'Transpose', 'Volume', 'PB Range', 'Note Pitch Bend On',
                None, None, None, None,
            ),
        )

    def _drift_envelope_2_parameters(self):
        cycle_enabled = self._parameter_by_names('Env 2 Cyc On')
        try:
            is_cycling = cycle_enabled.value > cycle_enabled.min
        except Exception:
            is_cycling = 'on' in self._parameter_display(cycle_enabled).lower()
        if is_cycling:
            return self._parameter_bank(
                'Env 2 Cyc On', ('Cyc Env Tilt', 'Cyc Tilt'), ('Cyc Env Hold', 'Cyc Hold'),
                ('Cyc Env Time Mode', 'Cyc Mode'), ('Cyc Env Rate', 'Cyc Rate'),
                ('Cyc Env Ratio', 'Cyc Ratio'), ('Cyc Env Time', 'Cyc Time'),
                ('Cyc Env Synced', 'Cyc Synced'),
            )
        return self._parameter_bank(
            'Env 2 Attack', 'Env 2 Decay', 'Env 2 Sustain', 'Env 2 Release',
            'Env 2 Cyc On', None, None, None,
        )

    def _parameter_value_text(self, *names):
        return self._parameter_display(self._parameter_by_names(*names)).lower()

    def _drift_lfo_rate_parameter(self):
        mode = self._parameter_value_text('LFO Time Mode')
        if 'ratio' in mode:
            return self._parameter_by_names('LFO Ratio')
        if 'time' in mode:
            return self._parameter_by_names('LFO Time')
        if 'sync' in mode:
            return self._parameter_by_names('LFO Synced')
        return self._parameter_by_names('LFO Rate')

    def _drift_voice_mode_parameter(self):
        mode = self._parameter_value_text('Voice Mode')
        if 'mono' in mode:
            return self._parameter_by_names('Thickness')
        if 'stereo' in mode:
            return self._parameter_by_names('Spread')
        if 'unison' in mode:
            return self._parameter_by_names('Strength')
        return None

    def _meld_engine_letter(self):
        try:
            return 'B' if int(self._device.selected_engine) == 1 else 'A'
        except Exception:
            return 'A'

    def _meld_original_name(self, suffix):
        return 'MeldVoice_Engine{}_{}'.format(self._meld_engine_letter(), suffix)

    def _meld_parameter(self, suffix, *aliases):
        return self._parameter_by_names(self._meld_original_name(suffix), *aliases)

    def _meld_parameter_banks(self):
        engine = self._meld_engine_letter()
        sync_1 = self._parameter_by_names('LFO 1 {} Sync'.format(engine), self._meld_original_name('Lfo1_Sync'))
        retrigger_1 = self._meld_parameter('Lfo1_Retrigger', 'LFO 1 {} Retrigger'.format(engine))
        sync_2 = self._parameter_by_names('LFO 2 {} Sync'.format(engine), self._meld_original_name('Lfo2_Sync'))
        retrigger_2 = self._meld_parameter('Lfo2_Retrigger', 'LFO 2 {} Retrigger'.format(engine))
        glide_mode = self._parameter_by_names('Glide {}'.format(engine))
        mono_poly = self._parameter_by_names('Mono Poly')
        try:
            mono_voice_parameter = self._parameter_by_names('Legato', 'MonoLegato') if int(mono_poly.value) == 0 else self._parameter_by_names('Poly Voices')
        except Exception:
            mono_voice_parameter = self._parameter_by_names('Poly Voices')
        envelope_delay_aliases = ('MeldVoice_EngineBDelay',) if engine == 'B' else ()
        return (
            tuple([None] * self.SAFE_PARAMETER_BANK_SIZE),
            self._parameter_bank(
                (self._meld_original_name('Oscillator_OscillatorType'),),
                (self._meld_original_name('Oscillator_Macro1'),),
                (self._meld_original_name('Oscillator_Macro2'),),
                (self._meld_original_name('Filter_Frequency'),),
                (self._meld_original_name('Filter_Macro1'),),
                (self._meld_original_name('ToneFilter'),),
                (self._meld_original_name('Pan'),),
                (self._meld_original_name('Volume'),),
            ),
            self._parameter_bank(
                (self._meld_original_name('Oscillator_OscillatorType'),),
                (self._meld_original_name('Oscillator_Pitch_Transpose'),),
                (self._meld_original_name('Oscillator_Pitch_Detune'),),
                (self._meld_original_name('Oscillator_Macro1'),),
                (self._meld_original_name('Oscillator_Macro2'),),
                (self._meld_original_name('ToneFilter'),),
                (self._meld_original_name('Pan'),),
                (self._meld_original_name('Volume'),),
            ),
            self._parameter_bank(
                (self._meld_original_name('Filter_FilterType'),),
                (self._meld_original_name('Filter_Frequency'),),
                (self._meld_original_name('Filter_Macro1'),),
                (self._meld_original_name('Filter_Macro2'),),
                (self._meld_original_name('ToneFilter'),),
                (self._meld_original_name('Pan'),),
                (self._meld_original_name('Volume'),),
                None,
            ),
            self._parameter_bank(
                (self._meld_original_name('AmpEnvelope_Times_Attack'),),
                (self._meld_original_name('AmpEnvelope_Slopes_Attack'),),
                (self._meld_original_name('AmpEnvelope_Times_Decay'),),
                (self._meld_original_name('AmpEnvelope_Slopes_Decay'),),
                (self._meld_original_name('AmpEnvelope_Sustain'),),
                (self._meld_original_name('AmpEnvelope_Times_Release'),),
                (self._meld_original_name('AmpEnvelope_Slopes_Release'),),
                (self._meld_original_name('AmpEnvelope_LoopMode'),),
            ),
            self._parameter_bank(
                (self._meld_original_name('FilterEnvelope_Times_Attack'),),
                (self._meld_original_name('FilterEnvelope_Slopes_Attack'),),
                (self._meld_original_name('FilterEnvelope_Times_Decay'),),
                (self._meld_original_name('FilterEnvelope_Slopes_Decay'),),
                (self._meld_original_name('FilterEnvelope_Values_Sustain'),),
                (self._meld_original_name('FilterEnvelope_Times_Release'),),
                (self._meld_original_name('FilterEnvelope_Values_Peak'),),
                (self._meld_original_name('FilterEnvelope_LoopMode'),),
            ),
            self._parameter_bank(
                (self._meld_original_name('EnvelopeDelay'),) + envelope_delay_aliases,
                ('Link Envelopes',), None, None, None, None, None, None,
            ),
            (
                self._meld_parameter('Lfo1_GeneratorType'),
                sync_1,
                self._meld_parameter('Lfo1_SyncedRate'),
                self._meld_parameter('Lfo1_Rate'),
                self._meld_parameter('Lfo1_PhaseOffset'),
                self._meld_parameter('Lfo1_GeneratorMacro1'),
                self._meld_parameter('Lfo1_GeneratorMacro2'),
                retrigger_1,
            ),
            self._parameter_bank(
                (self._meld_original_name('Lfo1_Transformer1Type'),),
                (self._meld_original_name('Lfo1_Transformer1Macro'),),
                (self._meld_original_name('Lfo1_Transformer2Type'),),
                (self._meld_original_name('Lfo1_Transformer2Macro'),),
                None, None, None, None,
            ),
            (
                self._meld_parameter('Lfo2_Waveform'),
                sync_2,
                self._meld_parameter('Lfo2_SyncedRate'),
                self._meld_parameter('Lfo2_Rate'),
                retrigger_2,
                self._meld_parameter('Lfo2_PhaseOffset'),
                None, None,
            ),
            (
                self._parameter_by_names('Stack Voices'),
                self._parameter_by_names('MeldVoice_VoiceSpreadAmount'),
                mono_poly,
                mono_voice_parameter,
                self._meld_parameter('GlideTime'),
                glide_mode,
                self._parameter_by_names('MeldVoice_Drive'),
                self._parameter_by_names('Volume'),
            ),
        )

    def _delay_parameter_banks(self):
        main = tuple(self._parameter_by_names(*names) for names in (
            ('Feedback',),
            ('Dry/Wet', 'Dry Wet'),
            ('Smoothing', 'Delay Smoothing Mode'),
            ('Link', 'Stereo Time Link'),
            ('Ping Pong',),
            ('Freeze',),
            ('L Sync', 'L Delay Sync'),
            ('R Sync', 'R Delay Sync'),
        ))
        time_bank = tuple(self._parameter_by_names(*names) for names in (
            ('L Time', 'L Delay Time'),
            ('R Time', 'R Delay Time'),
            ('L 16th', 'L Delay 16th'),
            ('R 16th', 'R Delay 16th'),
            ('L Offset', 'L Delay Offset'),
            ('R Offset', 'R Delay Offset'),
            ('Filter Freq', 'Filter Frequency'),
            ('Filter Width', 'Filter Bandwidth'),
        ))

        filter_lfo_bank = tuple(self._parameter_by_names(*names) for names in (
            ('Filter On', 'Filter On/Off'),
            ('LFO Mode', 'LF Mode', 'Mod LFO Mode', 'LFO Time Mode'),
            ('LFO Freq', 'Mod LFO Freq', 'Modulation Frequency', 'LFO Rate'),
            ('LFO Time', 'Mod LFO Time', 'Modulation Time'),
            ('LFO Synced', 'LFO Sync', 'Mod LFO Synced', 'Modulation Synced Rate', 'LFO Synced Rate'),
            ('LFO 16th', 'Mod LFO 16th', 'Modulation 16th'),
            ('LFO > Delay', 'Delay < Modulation'),
            ('LFO > Filter', 'Filter < Modulation'),
        ))
        lfo_wave_bank = (
            self._parameter_by_names('LFO Wave', 'Mod LFO Wave', 'Modulation Waveform', 'LFO Waveform'),
            self._parameter_by_names('LFO Morph', 'Mod LFO Morph', 'Modulation Morph'),
        ) + tuple([None] * 6)
        return (
            main,
            time_bank,
            filter_lfo_bank,
            lfo_wave_bank,
        )

    def _grain_delay_uses_beat_delay(self):
        mode = self._parameter_by_names('Delay Mode')
        display = self._parameter_display(mode).lower()
        if display in ('off', 'no', 'false', 'time'):
            return False
        if display in ('on', 'yes', 'true', 'sync', 'beat'):
            return True
        try:
            return float(mode.value) > float(mode.min)
        except Exception:
            return False

    def _grain_delay_parameter_banks(self):
        delay_time = (
            self._parameter_by_names('Beat Delay')
            if self._grain_delay_uses_beat_delay()
            else self._parameter_by_names('Time Delay')
        )
        return (
            self._parameter_bank(
                'Frequency', 'Pitch', 'Delay Mode', delay_time,
                'Random', 'Spray', 'Feedback', ('DryWet', 'Dry/Wet', 'Dry Wet'),
            ),
            self._parameter_bank(
                'Delay Mode', delay_time, 'Beat Swing', 'Feedback',
                None, None, None, ('DryWet', 'Dry/Wet', 'Dry Wet'),
            ),
        )

    def _simpler_amp_parameters(self):
        names = (
            'Ve Attack', 'Ve Decay', 'Ve Sustain', 'Ve Release',
            'Glide Time', 'Spread', 'Pan', 'Volume',
        )
        return tuple(self._parameter_by_names(name) for name in names)

    def _simpler_slice_detail_parameters(self):
        names = ('Transpose', 'Detune', 'Fade In', 'Fade Out')
        parameters = [self._parameter_by_names(name) for name in names]
        return tuple(parameters + [None] * (self.SAFE_PARAMETER_BANK_SIZE - len(parameters)))

    def _parameter_display(self, parameter):
        if not parameter:
            return ''
        try:
            return str(parameter.str_for_value(parameter.value)).strip()
        except Exception:
            pass
        try:
            display_value = parameter.display_value
            if display_value is not None:
                return str(display_value).strip()
        except Exception:
            pass
        return str(getattr(parameter, 'value', '')).strip()

    def _drumcell_sample_parameters(self):
        env_mode = self._parameter_by_names('Env Mode')
        hold = self._parameter_by_names('Hold') if 'trigger' in self._parameter_display(env_mode).lower() else None
        return (
            self._parameter_by_names('Start'),
            self._parameter_by_names('Length'),
            self._parameter_by_names('Attack'),
            hold,
            self._parameter_by_names('Decay'),
            self._parameter_by_names('Transpose'),
            self._parameter_by_names('Detune'),
            env_mode,
        )

    def _drumcell_effect_parameter_names(self):
        fx_type = self._parameter_display(self._parameter_by_names('FX Type')).lower()
        if 'pitch' in fx_type:
            return 'Pitch Env Amt', 'Pitch Env Decay'
        if 'sub' in fx_type:
            return 'Sub Amt', 'Sub Freq'
        if 'noise' in fx_type:
            return 'Noise Amt', 'Noise Color'
        if 'loop' in fx_type:
            return 'Loop Offset', 'Loop Length'
        if 'stretch' in fx_type:
            return 'Stretch Factor', 'Grain Size'
        if 'punch' in fx_type:
            return 'Punch Amt', 'Punch Release'
        if '8-bit' in fx_type or '8 bit' in fx_type:
            return '8-Bit Rate', '8-Bit Flt Decay'
        if fx_type == 'fm' or 'frequency mod' in fx_type:
            return 'FM Amt', 'FM Freq'
        return 'RM Amt', 'RM Freq'

    def _drumcell_filter_gain_or_resonance(self):
        filter_type = self._parameter_display(self._parameter_by_names('Filter Type')).lower()
        return self._parameter_by_names('Filter Gain') if 'peak' in filter_type else self._parameter_by_names('Filter Res')

    def _drumcell_fx_filter_parameters(self):
        effect_one, effect_two = self._drumcell_effect_parameter_names()
        return (
            self._parameter_by_names('FX On'),
            self._parameter_by_names('FX Type'),
            self._parameter_by_names(effect_one),
            self._parameter_by_names(effect_two),
            self._parameter_by_names('Filter On'),
            self._parameter_by_names('Filter Type'),
            self._parameter_by_names('Filter Freq'),
            self._drumcell_filter_gain_or_resonance(),
        )

    def _drumcell_rest_parameters(self):
        return (
            self._parameter_by_names('Volume'),
            self._parameter_by_names('Pan'),
            self._parameter_by_names('Vel > Vol'),
            self._parameter_by_names('Mod Src', 'Mod Source', 'Modulation Source'),
            self._parameter_by_names('Mod Dest'),
            self._parameter_by_names('Mod Amt'),
            None,
            None,
        )

    def _chord_shift_scale_parameters(self):
        parameters = [
            self._parameter_by_names(
                'Shift{} Scale Degrees'.format(index),
                'ShiftScaleDegrees{}'.format(index),
            )
            for index in range(1, 7)
        ]
        return tuple(parameters + [None, None])

    def _chord_strum_parameters(self):
        return (
            self._parameter_by_names('Strum'),
            self._parameter_by_names('Tension', 'Strum Tension', 'StrumTension'),
            self._parameter_by_names('Crescendo', 'Strum Crescendo', 'StrumCrescendo'),
            None,
            None,
            None,
            None,
            None,
        )

    def _parameter_by_names(self, *names):
        wanted = set(re.sub(r'[^a-z0-9]+', '', name.lower()) for name in names)
        fallback = None
        for parameter in self._decorated_parameters():
            parameter_names = (str(getattr(parameter, 'name', '')), str(getattr(parameter, 'original_name', '')))
            if any(re.sub(r'[^a-z0-9]+', '', name.lower()) in wanted for name in parameter_names):
                if self._operator_parameter_is_active(parameter):
                    return parameter
                if fallback is None:
                    fallback = parameter
        return fallback

    def _operator_filter_bank_insert_index(self, bank_names):
        for index, name in enumerate(bank_names):
            if re.sub(r'[^a-z0-9]+', '', str(name).lower()) == 'filter':
                return index + 1
        return self._custom_bank_insert_index(bank_names, 'filter')

    def _operator_lfo_bank_insert_index(self, bank_names):
        for index, name in enumerate(bank_names):
            if re.sub(r'[^a-z0-9]+', '', str(name).lower()) == 'lfo':
                return index + 1
        return len(bank_names)

    def _operator_filter_plus_parameters(self):
        filter_type = self._parameter_by_names('Filter Type', 'Filter Type (Legacy)')
        circuit_candidates = (
            self._parameter_by_names('Filter Circuit - LP/HP'),
            self._parameter_by_names('Filter Circuit - BP/NO/Morph'),
        )
        filter_type_display = self._operator_filter_type_display(filter_type)
        preferred_circuit_index = 0 if any(name in filter_type_display for name in ('lowpass', 'highpass')) else 1
        circuit = circuit_candidates[preferred_circuit_index]
        if not circuit:
            circuit = next((parameter for parameter in circuit_candidates if parameter and self._operator_parameter_is_active(parameter)), None)
        circuit = circuit or next((parameter for parameter in circuit_candidates if parameter), None)
        slope = self._parameter_by_names('Filter Slope')
        # Live's Operator schema calls these AntiAlias and Interpolation, but
        # some versions do not expose either one as a DeviceParameter.
        quality = (
            self._parameter_by_names('AntiAlias', 'Antialias', 'Anti Alias') or
            self._parameter_by_names('Interpolation', 'Interpol', 'UseLinearInterpolation') or
            self._parameter_by_names('Fe Amount')
        )
        return (
            filter_type,
            circuit,
            slope,
            self._parameter_by_names('Filter Drive'),
            self._parameter_by_names('LFO Retrigger'),
            self._parameter_by_names('Filter On'),
            quality,
            self._parameter_by_names('Pe On'),
        )

    def _operator_filter_type_display(self, filter_type):
        try:
            return str(filter_type.str_for_value(filter_type.value)).strip().lower()
        except Exception:
            return ''

    def _operator_lfo_plus_parameters(self):
        return tuple(self._parameter_by_names(name) for name in (
            'Osc-A < LFO',
            'Osc-B < LFO',
            'Osc-C < LFO',
            'Osc-D < LFO',
            'Filt < LFO',
            'LFO Dst B',
            'LFO Amt B',
            'LFO On',
        ))

    def _wavetable_waves_insert_index(self, bank_names):
        for index, name in enumerate(bank_names):
            normalized = re.sub(r'[^a-z0-9]+', '', str(name).lower())
            if normalized in ('osc2', 'oscillator2') or normalized.endswith('oscillator2'):
                return index + 1
        return min(2, len(bank_names))

    def _wavetable_envelope_bank_index(self, bank_names):
        for index, name in enumerate(bank_names):
            normalized = re.sub(r'[^a-z0-9]+', '', str(name).lower())
            if normalized in ('env23', 'envelope23', 'envelopes23'):
                return index
        return None

    def _replace_wavetable_envelope_bank_names(self, bank_names):
        index = self._wavetable_envelope_bank_index(bank_names)
        if index is not None:
            bank_names[index] = self.WAVETABLE_ENV_2_BANK_NAME
            bank_names.insert(index + 1, self.WAVETABLE_ENV_3_BANK_NAME)

    def _wavetable_envelope_parameters(self, envelope_number):
        prefix = 'Env {}'.format(envelope_number)
        return tuple(self._parameter_by_names(name) for name in (
            '{} Attack'.format(prefix),
            '{} Decay'.format(prefix),
            '{} Sustain'.format(prefix),
            '{} Release'.format(prefix),
            '{} Peak'.format(prefix),
            '{} Loop Mode'.format(prefix),
            '{} A Slope'.format(prefix),
            'LFO {} Retrigger'.format(envelope_number - 1),
        ))

    def _replace_wavetable_envelope_banks(self, banks, bank_names):
        index = self._wavetable_envelope_bank_index(bank_names)
        if index is not None and index < len(banks):
            banks[index] = self._wavetable_envelope_parameters(2)
            banks.insert(index + 1, self._wavetable_envelope_parameters(3))
            bank_names[index] = self.WAVETABLE_ENV_2_BANK_NAME
            bank_names.insert(index + 1, self.WAVETABLE_ENV_3_BANK_NAME)

    def _operator_lfo_is_synced(self, range_parameter):
        try:
            return str(range_parameter.str_for_value(range_parameter.value)).strip().lower() == 'sync'
        except Exception:
            return False

    def _replace_operator_lfo_bank(self, banks, bank_names):
        if banks is None:
            return
        for index, name in enumerate(bank_names):
            if re.sub(r'[^a-z0-9]+', '', str(name).lower()) != 'lfo' or index >= len(banks):
                continue
            bank = list(banks[index])
            bank.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(bank)))
            lfo_range = self._parameter_by_names('LFO Range')
            lfo_rate = self._parameter_by_names('LFO Sync' if self._operator_lfo_is_synced(lfo_range) else 'LFO Rate')
            bank[4] = lfo_rate
            bank[7] = lfo_range
            banks[index] = tuple(bank[:self.SAFE_PARAMETER_BANK_SIZE])
            return

    def _operator_source_parameters(self, raw_banks=None):
        parameters = list(getattr(self._device, 'parameters', ()))
        identities = set(id(parameter) for parameter in parameters)
        for bank in raw_banks or ():
            for parameter in bank or ():
                if parameter is not None and id(parameter) not in identities:
                    identities.add(id(parameter))
                    parameters.append(parameter)
        return parameters

    def _operator_wave_parameters(self, raw_banks=None):
        try:
            by_name = {}
            parameters = self._operator_source_parameters(raw_banks)
            for parameter in parameters:
                by_name[parameter.name] = parameter
                try:
                    by_name[parameter.original_name] = parameter
                except Exception:
                    pass
            feedback_by_oscillator = self._operator_feedback_parameters(parameters, by_name)
            parameters = []
            for oscillator in ('A', 'B', 'C', 'D'):
                wave = by_name.get('Osc-{} Wave'.format(oscillator))
                feedback = feedback_by_oscillator.get(oscillator)
                parameters.extend((wave, feedback))
            return parameters
        except Exception:
            return []

    def _operator_feedback_parameters(self, parameters=None, by_name=None):
        parameters = list(parameters if parameters is not None else self._operator_source_parameters())
        by_name = by_name or {}
        if not by_name:
            for parameter in parameters:
                by_name[parameter.name] = parameter
                try:
                    by_name[parameter.original_name] = parameter
                except Exception:
                    pass

        result = {}
        feedback_parameters = []
        for index, parameter in enumerate(parameters):
            names = [str(getattr(parameter, 'name', ''))]
            try:
                names.append(str(parameter.original_name))
            except Exception:
                pass
            normalized_names = [re.sub(r'[^a-z0-9]+', '', name.lower()) for name in names]
            if any(
                    'feedback' in name or 'feedb' in name or 'fdbk' in name or 'feedbk' in name or
                    name.endswith('fb') for name in normalized_names):
                feedback_parameters.append((index, parameter, normalized_names))

        for oscillator in ('A', 'B', 'C', 'D'):
            key = oscillator.lower()
            for _, parameter, normalized_names in feedback_parameters:
                if any(name in (
                        '{}feedback'.format(key), 'osc{}feedback'.format(key),
                        'oscillator{}feedback'.format(key),
                        '{}feedb'.format(key), 'osc{}feedb'.format(key),
                        'oscillator{}feedb'.format(key),
                        '{}fdbk'.format(key), 'osc{}fdbk'.format(key),
                        'oscillator{}fdbk'.format(key),
                        '{}feedbk'.format(key), 'osc{}feedbk'.format(key),
                        'oscillator{}feedbk'.format(key),
                        '{}fb'.format(key), 'osc{}fb'.format(key),
                        'oscillator{}fb'.format(key),
                        'feedback{}'.format(key), 'fdbk{}'.format(key),
                        'feedbk{}'.format(key), 'fb{}'.format(key),
                ) for name in normalized_names):
                    result[oscillator] = parameter
                    break

        wave_positions = {}
        for index, parameter in enumerate(parameters):
            names = (str(getattr(parameter, 'name', '')), str(getattr(parameter, 'original_name', '')))
            for oscillator in ('A', 'B', 'C', 'D'):
                normalized_wave_name = 'osc{}wave'.format(oscillator.lower())
                if any(re.sub(r'[^a-z0-9]+', '', name.lower()) == normalized_wave_name for name in names):
                    wave_positions[oscillator] = index

        unassigned = [(index, parameter) for index, parameter, _ in feedback_parameters if parameter not in result.values()]
        for oscillator_index, oscillator in enumerate(('A', 'B', 'C', 'D')):
            if oscillator in result or oscillator not in wave_positions:
                continue
            start = wave_positions[oscillator]
            next_positions = [wave_positions[name] for name in ('A', 'B', 'C', 'D')[oscillator_index + 1:] if name in wave_positions]
            end = min(next_positions) if next_positions else len(parameters)
            for parameter_index, parameter in unassigned:
                if start <= parameter_index < end:
                    result[oscillator] = parameter
                    unassigned.remove((parameter_index, parameter))
                    break

        unresolved = [oscillator for oscillator in ('A', 'B', 'C', 'D') if oscillator not in result]
        if len(unassigned) == len(unresolved):
            for oscillator, (_, parameter) in zip(unresolved, unassigned):
                result[oscillator] = parameter
        return result

    def _operator_parameter_is_active(self, parameter):
        try:
            if hasattr(parameter, 'is_enabled') and not parameter.is_enabled:
                return False
            if hasattr(parameter, 'state'):
                return parameter.state == Live.DeviceParameter.ParameterState.enabled
        except Exception:
            return False
        return True

    def tap_custom_bank_kind(self):
        names = self._parameter_bank_names()
        try:
            name = names[self._bank_index]
        except Exception:
            return None
        if name == self.WAVETABLE_OSC_BANK_NAME:
            return 'wavetable_osc'
        if name == self.OPERATOR_WAVES_BANK_NAME:
            return 'operator_waves'
        if name == self.OPERATOR_FILTER_PLUS_BANK_NAME:
            return 'operator_filter_plus'
        if name == self.OPERATOR_LFO_PLUS_BANK_NAME:
            return 'operator_lfo_plus'
        custom_simpler = self._is_simpler() and not self._simpler_uses_native_banks()
        if name == self.SIMPLER_MAIN_BANK_NAME and custom_simpler:
            return 'simpler_main'
        if name == self.SIMPLER_ACTIONS_BANK_NAME and custom_simpler:
            return 'simpler_actions'
        if name == self.SIMPLER_WARP_BANK_NAME and self._is_simpler():
            return 'simpler_warp'
        if (
                name in (self.SIMPLER_BROWSE_BANK_NAME, self.SIMPLER_BROWSE_PLUS_BANK_NAME)
                and self._is_simpler()):
            return 'simpler_browse'
        if self._is_drumcell():
            if name == self.DRUMCELL_SAMPLE_BANK_NAME:
                return 'drumcell_sample'
            if name == self.DRUMCELL_FX_FILTER_BANK_NAME:
                return 'drumcell_fx_filter'
            if name == self.DRUMCELL_REST_BANK_NAME:
                return 'drumcell_rest'
        return None

    def _clamp_bank_index_to_safe_banks(self):
        bank_count = len(self._parameter_banks())
        if bank_count == 0:
            self._bank_index = 0
        else:
            self._bank_index = max(0, min(self._bank_index, bank_count - 1))

    def _safe_parameter_banks(self):
        device = getattr(self, '_device', None)
        if not device or not liveobj_valid(device) or not hasattr(device, 'parameters'):
            return []

        parameters = list(device.parameters)
        if not parameters:
            return []

        live_banks = self._safe_live_parameter_banks(device, parameters)
        if live_banks:
            return live_banks

        parameters = parameters[1:]
        if not parameters:
            return []

        banks = []
        for index in range(0, len(parameters), self.SAFE_PARAMETER_BANK_SIZE):
            bank = list(parameters[index:index + self.SAFE_PARAMETER_BANK_SIZE])
            bank.extend([None] * (self.SAFE_PARAMETER_BANK_SIZE - len(bank)))
            banks.append(tuple(bank))
        return banks

    def _safe_live_parameter_banks(self, device, parameters):
        if not hasattr(device, 'get_bank_count') or not hasattr(device, 'get_bank_parameters'):
            return []

        try:
            bank_count = int(device.get_bank_count())
        except Exception:
            bank_count = 0

        if bank_count <= 0:
            return []

        banks = []
        empty_bank = tuple([None] * self.SAFE_PARAMETER_BANK_SIZE)
        for bank_index in range(bank_count):
            try:
                parameter_indices = list(device.get_bank_parameters(bank_index))
            except Exception:
                parameter_indices = []

            if len(parameter_indices) != self.SAFE_PARAMETER_BANK_SIZE:
                banks.append(empty_bank)
                continue

            bank = []
            for parameter_index in parameter_indices:
                if parameter_index == -1:
                    bank.append(None)
                elif 0 <= parameter_index < len(parameters):
                    bank.append(parameters[parameter_index])
                else:
                    bank.append(None)
            banks.append(tuple(bank))

        return banks

    def _safe_parameter_bank_names(self):
        return self._safe_parameter_bank_names_base()
