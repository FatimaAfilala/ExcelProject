import dataclasses
import datetime
import html
import logging
import typing

import numpy as np

import json
import os

from cara import models
from cara import data
import cara.data.weather
import cara.monte_carlo as mc
from .. import calculator
from cara.monte_carlo.data import activity_distributions, activity_distributions2, virus_distributions, mask_distributions, mask_distributions2 


LOG = logging.getLogger(__name__)


minutes_since_midnight = typing.NewType('minutes_since_midnight', int)


# Used to declare when an attribute of a class must have a value provided, and
# there should be no default value used.
_NO_DEFAULT = object()
_DEFAULT_MC_SAMPLE_SIZE = 50000


@dataclasses.dataclass
class FormData:
    activity_type: str
    role_type: str
    role_type2: str
    air_changes: float
    air_supply: float
    ceiling_height: float
    exposed_coffee_break_option: str
    exposed_coffee_duration: int
    exposed_finish: minutes_since_midnight
    exposed_lunch_finish: minutes_since_midnight
    exposed_lunch_option: bool
    exposed_lunch_start: minutes_since_midnight
    exposed_start: minutes_since_midnight
    floor_area: float
    hepa_amount: float
    hepa_option: bool
    infected_coffee_break_option: str               #Used if infected_dont_have_breaks_with_exposed
    infected_coffee_duration: int                   #Used if infected_dont_have_breaks_with_exposed
    infected_dont_have_breaks_with_exposed: bool
    infected_finish: minutes_since_midnight
    infected_lunch_finish: minutes_since_midnight   #Used if infected_dont_have_breaks_with_exposed
    infected_lunch_option: bool                     #Used if infected_dont_have_breaks_with_exposed
    infected_lunch_start: minutes_since_midnight    #Used if infected_dont_have_breaks_with_exposed
    infected_people: int
    infected_start: minutes_since_midnight
    location_name: str
    location_latitude: float
    location_longitude: float
    mask_type: str
    mask_type2: str
    mask_wearing_option: str
    mask_wearing_option2: str
    mechanical_ventilation_type: str
    calculator_version: str
    opening_distance: float
    event_month: str
    room_heating_option: bool
    room_number: str
    room_volume: float
    simulation_name: str
    scenarios_alt: str  #"1;2;3"
    scenario_1: str
    scenario_2: str
    scenario_3: str
    total_people: int
    uv_device: str
    uv_speed: int
    ventilation_type: str
    virus_type: str
    volume_type: str
    windows_duration: float
    windows_frequency: float
    window_height: float
    window_type: str
    window_width: float
    windows_number: int
    window_opening_regime: str

    #: The default values for undefined fields. Note that the defaults here
    #: and the defaults in the html form must not be contradictory.
    _DEFAULTS: typing.ClassVar[typing.Dict[str, typing.Any]] = {
        'activity_type': 'office',
        'role_type':'Hospital_patient',
        'role_type2':'Hospital_patient2',
        'air_changes': 0.,
        'air_supply': 0.,
        'calculator_version': _NO_DEFAULT,
        'ceiling_height': 0.,
        'exposed_coffee_break_option': 'coffee_break_0',
        'exposed_coffee_duration': 5,
        'exposed_finish': '17:30',
        'exposed_lunch_finish': '13:30',
        'exposed_lunch_option': True,
        'exposed_lunch_start': '12:30',
        'exposed_start': '08:30',
        'event_month': 'January',
        'floor_area': 0.,
        'hepa_amount': 0.,
        'hepa_option': False,
        'infected_coffee_break_option': 'coffee_break_0',
        'infected_coffee_duration': 5,
        'infected_dont_have_breaks_with_exposed': False,
        'infected_finish': '17:30',
        'infected_lunch_finish': '13:30',
        'infected_lunch_option': True,
        'infected_lunch_start': '12:30',
        'infected_people': _NO_DEFAULT,
        'infected_start': '08:30',
        'location_latitude': _NO_DEFAULT,
        'location_longitude': _NO_DEFAULT,
        'location_name': _NO_DEFAULT,
        'mask_type': 'Type I',
        'mask_type2': 'Type I',
        'mask_wearing_option': 'mask_off',
        'mask_wearing_option2': 'mask_off',
        'mechanical_ventilation_type': 'not-applicable',
        'opening_distance': 0.,
        'room_heating_option': False,
        'room_number': _NO_DEFAULT,
        'room_volume': 0.,
        'simulation_name': _NO_DEFAULT,
        'scenarios_alt': "1;2;3",
        'scenario_1': '',
        'scenario_2': '',
        'scenario_3': '',
        'total_people': _NO_DEFAULT,
        'uv_device': "BR500",
        'uv_speed': 400,
        'ventilation_type': 'no_ventilation',
        'virus_type': 'SARS_CoV_2',
        'volume_type': _NO_DEFAULT,
        'window_type': 'window_sliding',
        'window_height': 0.,
        'window_width': 0.,
        'windows_duration': 0.,
        'windows_frequency': 0.,
        'windows_number': 0,
        'window_opening_regime': 'windows_open_permanently',
    }

    @classmethod
    def from_dict(cls, form_data: typing.Dict) -> "FormData":
        # Take a copy of the form data so that we can mutate it.
        form_data = form_data.copy()
        form_data.pop('_xsrf', None)

        # Don't let arbitrary unescaped HTML through the net.
        for key, value in form_data.items():
            if isinstance(value, str):
                form_data[key] = html.escape(value)

        for key, default_value in cls._DEFAULTS.items():
            if form_data.get(key, '') == '':
                if default_value is _NO_DEFAULT:
                    raise ValueError(f"{key} must be specified")
                form_data[key] = default_value

        for key, value in form_data.items():
            if key in _CAST_RULES_FORM_ARG_TO_NATIVE:
                form_data[key] = _CAST_RULES_FORM_ARG_TO_NATIVE[key](value)

            if key not in cls._DEFAULTS:
                raise ValueError(f'Invalid argument "{html.escape(key)}" given')
        instance = cls(**form_data)
        instance.validate()
        return instance

    @classmethod
    def to_dict(cls, form: "FormData", strip_defaults: bool = False) -> dict:
        form_dict = {
            field.name: getattr(form, field.name)
            for field in dataclasses.fields(form)
        }

        for attr, value in form_dict.items():
            if attr in _CAST_RULES_NATIVE_TO_FORM_ARG:
                form_dict[attr] = _CAST_RULES_NATIVE_TO_FORM_ARG[attr](value)

        if strip_defaults:
            del form_dict['calculator_version']

            for attr, value in list(form_dict.items()):
                default = cls._DEFAULTS.get(attr, _NO_DEFAULT)
                if default is not _NO_DEFAULT and value in [default, 'not-applicable']:
                    form_dict.pop(attr)
        return form_dict

    def validate(self):
        # Validate time intervals selected by user
        time_intervals = [
            ['exposed_start', 'exposed_finish'],
            ['infected_start', 'infected_finish'],
        ]
        if self.exposed_lunch_option:
            time_intervals.append(['exposed_lunch_start', 'exposed_lunch_finish'])
        if self.infected_dont_have_breaks_with_exposed and self.infected_lunch_option:
            time_intervals.append(['infected_lunch_start', 'infected_lunch_finish'])

        for start_name, end_name in time_intervals:
            start = getattr(self, start_name)
            end = getattr(self, end_name)
            if start > end:
                raise ValueError(
                    f"{start_name} must be less than {end_name}. Got {start} and {end}.")

        validation_tuples = [('activity_type', ACTIVITY_TYPES), 
                             ('role_type', ROLE_TYPE),  
                             ('role_type2', ROLE_TYPE2),   
                             ('exposed_coffee_break_option', COFFEE_OPTIONS_INT), 
                             ('infected_coffee_break_option', COFFEE_OPTIONS_INT),   
                             ('mechanical_ventilation_type', MECHANICAL_VENTILATION_TYPES),
                             ('mask_type', MASK_TYPES),
                             ('mask_type2', MASK_TYPES2),
                             ('mask_wearing_option', MASK_WEARING_OPTIONS),
                             ('mask_wearing_option2', MASK_WEARING_OPTIONS),
                             ('ventilation_type', VENTILATION_TYPES),
                             ('virus_type', VIRUS_TYPES),
                             ('volume_type', VOLUME_TYPES),
                             ('window_opening_regime', WINDOWS_OPENING_REGIMES),
                             ('window_type', WINDOWS_TYPES),
                             ('event_month', MONTH_NAMES)]
        for attr_name, valid_set in validation_tuples:
            if getattr(self, attr_name) not in valid_set:
                raise ValueError(f"{getattr(self, attr_name)} is not a valid value for {attr_name}")

        if self.ventilation_type == 'natural_ventilation':
            if self.window_type == 'not-applicable':
                raise ValueError(
                    "window_type cannot be 'not-applicable' if "
                    "ventilation_type is 'natural_ventilation'"
                )
            if self.window_opening_regime == 'not-applicable':
                raise ValueError(
                    "window_opening_regime cannot be 'not-applicable' if "
                    "ventilation_type is 'natural_ventilation'"
                )

        if (self.ventilation_type == 'mechanical_ventilation'
                and self.mechanical_ventilation_type == 'not-applicable'):
            raise ValueError("mechanical_ventilation_type cannot be 'not-applicable' if "
                             "ventilation_type is 'mechanical_ventilation'")

    def build_mc_model(self) -> mc.ExposureModel:
        # Initializes room with volume either given directly or as product of area and height
        if self.volume_type == 'room_volume_explicit':
            volume = self.room_volume
        else:
            volume = self.floor_area * self.ceiling_height
        if self.room_heating_option:
            humidity = 0.3
        else:
            humidity = 0.5
        room = models.Room(volume=volume, humidity=humidity)

        # Initializes and returns a model with the attributes defined above
        return mc.ExposureModel(
            concentration_model=mc.ConcentrationModel(
                room=room,
                ventilation=self.ventilation(),
                infected=self.infected_population(),
            ),
            exposed=self.exposed_population()
        )

    def build_model(self, sample_size=_DEFAULT_MC_SAMPLE_SIZE) -> models.ExposureModel:
        return self.build_mc_model().build_model(size=sample_size)

    def tz_name_and_utc_offset(self) -> typing.Tuple[str, float]:
        """
        Return the timezone name (e.g. CET), and offset, in hours, that need to
        be *added* to UTC to convert to the form location's timezone.

        """
        month = MONTH_NAMES.index(self.event_month) + 1
        timezone = cara.data.weather.timezone_at(
            latitude=self.location_latitude, longitude=self.location_longitude,
        )
        # We choose the first of the month for the current year.
        date = datetime.datetime(datetime.datetime.now().year, month, 1)
        name = timezone.tzname(date)
        assert isinstance(name, str)
        utc_offset_td = timezone.utcoffset(date)
        assert isinstance(utc_offset_td, datetime.timedelta)
        utc_offset_hours = utc_offset_td.total_seconds() / 60 / 60
        return name, utc_offset_hours

    def outside_temp(self) -> models.PiecewiseConstant:
        """
        Return the outside temperature as a PiecewiseConstant in the destination
        timezone.

        """
        month = MONTH_NAMES.index(self.event_month) + 1

        wx_station = self.nearest_weather_station()
        temp_profile = cara.data.weather.mean_hourly_temperatures(wx_station[0], month)

        _, utc_offset = self.tz_name_and_utc_offset()

        # Offset the source times according to the difference from UTC (as a
        # result the first data value may no longer be a midnight, and the hours
        # no longer ordered modulo 24).
        source_times = np.arange(24) + utc_offset
        times, temp_profile = cara.data.weather.refine_hourly_data(
            source_times,
            temp_profile,
            npts=24*10,  # 10 steps per hour => 6 min steps
        )
        outside_temp = models.PiecewiseConstant(
            tuple(float(t) for t in times), tuple(float(t) for t in temp_profile),
        )
        return outside_temp

    def ventilation(self) -> models._VentilationBase:
        always_on = models.PeriodicInterval(period=120, duration=120)
        # Initializes a ventilation instance as a window if 'natural_ventilation' is selected, or as a HEPA-filter otherwise
        if self.ventilation_type == 'natural_ventilation':
            if self.window_opening_regime == 'windows_open_periodically':
                window_interval = models.PeriodicInterval(self.windows_frequency, self.windows_duration, min(self.infected_start, self.exposed_start))
            else:
                window_interval = always_on

            outside_temp = self.outside_temp()
            inside_temp = models.PiecewiseConstant((0, 24), (293,))

            ventilation: models.Ventilation
            if self.window_type == 'window_sliding':
                ventilation = models.SlidingWindow(
                    active=window_interval,
                    inside_temp=inside_temp,
                    outside_temp=outside_temp,
                    window_height=self.window_height,
                    opening_length=self.opening_distance,
                    number_of_windows=self.windows_number,
                )
            elif self.window_type == 'window_hinged':
                ventilation = models.HingedWindow(
                    active=window_interval,
                    inside_temp=inside_temp,
                    outside_temp=outside_temp,
                    window_height=self.window_height,
                    window_width=self.window_width,
                    opening_length=self.opening_distance,
                    number_of_windows=self.windows_number,
                )

        elif self.ventilation_type == "no_ventilation":
            ventilation = models.AirChange(active=always_on, air_exch=0.)
        else:
            if self.mechanical_ventilation_type == 'mech_type_air_changes':
                ventilation = models.AirChange(active=always_on, air_exch=self.air_changes)
            else:
                ventilation = models.HVACMechanical(
                    active=always_on, q_air_mech=self.air_supply)

        # this is a minimal, always present source of ventilation, due
        # to the air infiltration from the outside.
        # See CERN-OPEN-2021-004, p. 12.
        infiltration_ventilation = models.AirChange(active=always_on, air_exch=0.25)

        accepted_devices = ["BR500","BR1000","BR5000","BR10000"]
        accepted_viruses = ["SarS-CoV-2"]
        if self.uv_device in accepted_devices:
            with open(os.getcwd()+'\\cara\\config_BR.json') as json_file:
                data = json.load(json_file)
                Q2 = data[self.uv_device]["Q2"]
                doseQ2 = data[self.uv_device]["Dose_Q2"]
            with open(os.getcwd()+'\\cara\\config_D90.json') as json_file:
                data = json.load(json_file)
                if self.virus_type in accepted_viruses:
                    D90 = data[self.virus_type]
                else:
                    D90 = data["SarS-CoV-2"]
            uv= models.UVFilter(active=always_on, device=self.uv_device, speed=self.uv_speed,q2 = Q2, dose_q2=doseQ2, d90 = D90)
            return models.MultipleVentilation((ventilation, uv, infiltration_ventilation))
        #elif self.hepa_option:
            hepa = models.HEPAFilter(active=always_on, q_air_mech=self.hepa_amount)
            return models.MultipleVentilation((ventilation, hepa, infiltration_ventilation))
        else:
            return models.MultipleVentilation((ventilation, infiltration_ventilation))

    def nearest_weather_station(self) -> cara.data.weather.WxStationRecordType:
        """Return the nearest weather station (which has valid data) for this form"""
        return cara.data.weather.nearest_wx_station(
            longitude=self.location_longitude, latitude=self.location_latitude
        )

    def mask(self) -> models.Mask:
        # Initializes the mask type if mask wearing is "continuous", otherwise instantiates the mask attribute as
        # the "No mask"-mask
        if self.mask_wearing_option == 'mask_on':
            mask = mask_distributions[self.mask_type]
        else:
            mask = models.Mask.types['No mask']
        return mask

    def mask2(self) -> models.Mask:
        # Initializes the mask type if mask wearing is "continuous", otherwise instantiates the mask attribute as
        # the "No mask"-mask
        if self.mask_wearing_option2 == 'mask_on':
            mask2 = mask_distributions2[self.mask_type2]
        else:
            mask2 = models.Mask.types['No mask']
        return mask2    

    def exposed_population(self) -> mc.Population:
        scenario_activity_and_expiration = {
            'Hospital_patient': (
                'Seated',
                {'Talking': 0.5, 'Breathing': 9.5}
            ),
            'Nurse_working': (
                'Light activity',
                {'Talking': 2, 'Breathing': 8}
            ),
            'Physician_working': (
                'Standing',
                {'Talking': 5, 'Breathing': 5}
            ),
            'Office_worker': (
                'Seated',
                {'Talking': 2, 'Breathing':8 }
            ),
            'Workshop_worker': (
                'Moderate activity',
                {'Talking':7, 'Breathing':1.5, 'Shouting':1.5}
                ),
            'Meeting_participant': (
                'Seated', 
                {'Talking':1.5, 'Breathing':8, 'Shouting': 0.5 }
                ),
            'Meeting_leader': (
                'Standing', 
                {'Breathing':6,'Talking':3,'Shouting':1}
                ),
            'Student_sitting': (
                'Seated',    
                {'Talking':0.5 , 'Breathing': 9.5}
                ),
            'Professor_teaching': (
                'Standing',
                {'Talking': 6, 'Breathing': 2, 'Shouting':2}
            ),
            'Professor_conferencing':(
                'Light activity', 
                {'Talking':2,'Breathing':2, 'Shouting':6}
                ),
            'Concert_musician_soft_music':(
                'Standing', 
                {'Talking':0.5,'Breathing':9.5}
                ),    
            'Concert_musician_rock':(
                'Moderate activity', 
                {'Talking':1,'Breathing':8, 'Shouting':1}
                ),      
            'Concert_singer':(
                'Moderate activity', 
                {'Talking':1,'Breathing':2, 'Shouting':7}
                ), 
            'Concert_spectator_standing':(
                'Light activity', 
                {'Talking':1,'Breathing':8, 'Shouting':1}
                ),      
            'Concert_spectator_sitting':(
                'Seated',
                {'Talking':0.5,'Breathing':9, 'Shouting':0.5}
                ), 
            'Museum_visitor':(
                'Standing',
                {'Talking':1,'Breathing':9}
                ),   
            'Theater_spectator' :(
                'Seated',
                {'Talking':0.5,'Breathing':9, 'Shouting':0.5}
                ),   
            'Theater_actor' :(
                'Moderate activity',
                {'Breathing':7, 'Shouting':3}
                ),   
            'Conferencer': (
                'Light activity',
                {'Talking':2, 'Breathing':2, 'Shouting':6}
            ),    
            'Conference_attendee' : (
                'Seated',
                {'Talking':0.5, 'Breathing':9.5}
            ),    
            'Guest_standing' : (
                'Standing',
                {'Talking':2, 'Breathing':6, 'Shouting':2}
            ),       
            'Guest_sitting' : (
                'Seated',
                {'Talking':4, 'Breathing':6}
            ), 
            'Server' : (
                'Light activity',
                {'Talking':2, 'Breathing':8}
            ),    
            'Barrista' : (
                'Standing',
                {'Talking':2, 'Breathing':6, 'Shouting':2}
            ),   
            'Nightclub_dancing' : (
                'Moderate activity',
                {'Breathing':9, 'Shouting':1}
            ),     
            'Nightclub_sitting' : (
                'Seated',
                {'Breathing':8, 'Shouting':2}
            ),        
            'Customer_standing' : (
                'Standing',
                {'Talking':1,'Breathing':9}
            ), 
            'Cashier_sitting' : (
                'Seated',
                {'Talking':5,'Breathing':5}
            ),  
            'Vendor_standing'  : (
                'Standing',
                {'Talking':5,'Breathing':5}
            ), 
            'Musculation':(
                'Heavy exercise',
                {'Talking':1,'Breathing':9}
            ),
            'Floor_gymnastics':(
                'Moderate activity',
                {'Talking':1,'Breathing':8, "Shouting":1}
            ),
            'Team_competition':(
                'Heavy exercise',
                {'Talking':0.5,'Breathing':8, "Shouting":1.5}
            ),
            'Trip_in_elevator':(
                'Standing',
                {'Talking':1,'Breathing':9}
            ),

        }

        
        [activity_defn, expiration_defn] = scenario_activity_and_expiration[self.role_type]
        activity = activity_distributions[activity_defn]

        infected_occupants = self.infected_people
        # The number of exposed occupants is the total number of occupants
        # minus the number of infected occupants.
        exposed_occupants = self.total_people - infected_occupants

        exposed = mc.Population(
            number=exposed_occupants,
            presence=self.exposed_present_interval(),
            activity=activity,
            mask=self.mask(),
        )
        return exposed

       

    def infected_population(self) -> mc.Population:
        # Initializes the virus
        virus = virus_distributions[self.virus_type]

        scenario_activity_and_expiration2 = {
            'Hospital_patient2': (
                'Seated',
                {'Talking': 0.5, 'Breathing': 9.5}
            ),
            'Nurse_working2': (
                'Light activity',
                {'Talking': 2, 'Breathing': 8}
            ),
            'Physician_working2': (
                'Standing',
                {'Talking': 5, 'Breathing': 5}
            ),
            'Office_worker2': (
                'Seated',
                {'Talking': 2, 'Breathing':8 }
            ),
            'Workshop_worker2': (
                'Moderate activity',
                {'Talking':7, 'Breathing':1.5, 'Shouting':1.5}
                ),
            'Meeting_participant2': (
                'Seated', 
                {'Talking':1.5, 'Breathing':8, 'Shouting': 0.5 }
                ),
            'Meeting_leader2': (
                'Standing', 
                {'Breathing':6,'Talking':3,'Shouting':1}
                ),
            'Student_sitting2': (
                'Seated',    
                {'Talking':0.5 , 'Breathing': 9.5}
                ),
            'Professor_teaching2': (
                'Standing',
                {'Talking': 6, 'Breathing': 2, 'Shouting':2}
            ),
            'Professor_conferencing2':(
                'Light activity', 
                {'Talking':2,'Breathing':2, 'Shouting':6}
                ),
            'Concert_musician_soft_music2':(
                'Standing', 
                {'Talking':0.5,'Breathing':9.5}
                ),    
            'Concert_musician_rock2':(
                'Moderate activity', 
                {'Talking':1,'Breathing':8, 'Shouting':1}
                ),      
            'Concert_singer2':(
                'Moderate activity', 
                {'Talking':1,'Breathing':2, 'Shouting':7}
                ), 
            'Concert_spectator_standing2':(
                'Light activity', 
                {'Talking':1,'Breathing':8, 'Shouting':1}
                ),      
            'Concert_spectator_sitting2':(
                'Seated',
                {'Talking':0.5,'Breathing':9, 'Shouting':0.5}
                ), 
            'Museum_visitor2':(
                'Standing',
                {'Talking':1,'Breathing':9}
                ),   
            'Theater_spectator2' :(
                'Seated',
                {'Talking':0.5,'Breathing':9, 'Shouting':0.5}
                ),   
            'Theater_actor2' :(
                'Moderate activity',
                {'Breathing':7, 'Shouting':3}
                ),   
            'Conferencer2': (
                'Light activity',
                {'Talking':2, 'Breathing':2, 'Shouting':6}
            ),    
            'Conference_attendee1' : (
                'Seated',
                {'Talking':0.5, 'Breathing':9.5}
            ),    
            'Guest_standing2' : (
                'Standing',
                {'Talking':2, 'Breathing':6, 'Shouting':2}
            ),       
            'Guest_sitting2' : (
                'Seated',
                {'Talking':4, 'Breathing':6}
            ), 
            'Server2' : (
                'Light activity',
                {'Talking':2, 'Breathing':8}
            ),    
            'Barrista2' : (
                'Standing',
                {'Talking':2, 'Breathing':6, 'Shouting':2}
            ),   
            'Nightclub_dancing2' : (
                'Moderate activity',
                {'Breathing':9, 'Shouting':1}
            ),     
            'Nightclub_sitting2' : (
                'Seated',
                {'Breathing':8, 'Shouting':2}
            ),        
            'Customer_standing2' : (
                'Standing',
                {'Talking':1,'Breathing':9}
            ), 
            'Cashier_sitting2' : (
                'Seated',
                {'Talking':5,'Breathing':5}
            ),  
            'Vendor_standing2'  : (
                'Standing',
                {'Talking':5,'Breathing':5}
            ), 
            'Musculation2':(
                'Heavy exercise',
                {'Talking':1,'Breathing':9}
            ),
            'Floor_gymnastics2':(
                'Moderate activity',
                {'Talking':1,'Breathing':8, "Shouting":1}
            ),
            'Team_competition2':(
                'Heavy exercise',
                {'Talking':0.5,'Breathing':8, "Shouting":1.5}
            ),
            'Trip_in_elevator2':(
                'Standing',
                {'Talking':1,'Breathing':9}
            ),

        }

        [activity_defn2, expiration_defn2] = scenario_activity_and_expiration2[self.role_type2]
        activity2 = activity_distributions2[activity_defn2]

        expiration2 = build_expiration(expiration_defn2)

        infected_occupants = self.infected_people

        infected = mc.InfectedPopulation(
            number=infected_occupants,
            virus=virus,
            presence=self.infected_present_interval(),
            mask=self.mask2(),
            activity=activity2,
            expiration=expiration2
        )
        return infected


    def _compute_breaks_in_interval(self, start, finish, n_breaks, duration) -> models.BoundarySequence_t:
        break_delay = ((finish - start) - (n_breaks * duration)) // (n_breaks+1)
        break_times = []
        end = start
        for n in range(n_breaks):
            begin = end + break_delay
            end = begin + duration
            break_times.append((begin, end))
        return tuple(break_times)

    def exposed_lunch_break_times(self) -> models.BoundarySequence_t:
        result = []
        if self.exposed_lunch_option:
            result.append((self.exposed_lunch_start, self.exposed_lunch_finish))
        return tuple(result)

    def infected_lunch_break_times(self) -> models.BoundarySequence_t:
        if self.infected_dont_have_breaks_with_exposed:
            result = []
            if self.infected_lunch_option:
                result.append((self.infected_lunch_start, self.infected_lunch_finish))
            return tuple(result)
        else:
            return self.exposed_lunch_break_times()

    def exposed_number_of_coffee_breaks(self) -> int:
        return COFFEE_OPTIONS_INT[self.exposed_coffee_break_option]

    def infected_number_of_coffee_breaks(self) -> int:
        return COFFEE_OPTIONS_INT[self.infected_coffee_break_option]

    def _coffee_break_times(self, activity_start, activity_finish, coffee_breaks, coffee_duration, lunch_start, lunch_finish) -> models.BoundarySequence_t:
        time_before_lunch = lunch_start - activity_start
        time_after_lunch = activity_finish - lunch_finish
        before_lunch_frac = time_before_lunch / (time_before_lunch + time_after_lunch)
        n_morning_breaks = round(coffee_breaks * before_lunch_frac)
        breaks = (
            self._compute_breaks_in_interval(
                activity_start, lunch_start, n_morning_breaks, coffee_duration
            )
            + self._compute_breaks_in_interval(
                lunch_finish, activity_finish, coffee_breaks - n_morning_breaks, coffee_duration
            )
        )
        return breaks

    def exposed_coffee_break_times(self) -> models.BoundarySequence_t:
        exposed_coffee_breaks = self.exposed_number_of_coffee_breaks()
        if exposed_coffee_breaks == 0:
            return ()
        if self.exposed_lunch_option:
            breaks = self._coffee_break_times(self.exposed_start, self.exposed_finish, exposed_coffee_breaks, self.exposed_coffee_duration, self.exposed_lunch_start, self.exposed_lunch_finish)
        else:
            breaks = self._compute_breaks_in_interval(self.exposed_start, self.exposed_finish, exposed_coffee_breaks, self.exposed_coffee_duration)
        return breaks

    def infected_coffee_break_times(self) -> models.BoundarySequence_t:
        if self.infected_dont_have_breaks_with_exposed:
            infected_coffee_breaks = self.infected_number_of_coffee_breaks()
            if infected_coffee_breaks == 0:
                return ()
            if self.infected_lunch_option:
                breaks = self._coffee_break_times(self.infected_start, self.infected_finish, infected_coffee_breaks, self.infected_coffee_duration, self.infected_lunch_start, self.infected_lunch_finish)
            else:
                breaks = self._compute_breaks_in_interval(self.infected_start, self.infected_finish, infected_coffee_breaks, self.infected_coffee_duration)
            return breaks
        else:
            return self.exposed_coffee_break_times()

    def present_interval(
            self,
            start: int,
            finish: int,
            breaks: typing.Optional[models.BoundarySequence_t] = None,
    ) -> models.Interval:
        """
        Calculate the presence interval given the start and end times (in minutes), and
        a number of monotonic, non-overlapping, but potentially unsorted, breaks (also in minutes).

        """
        if not breaks:
            # If there are no breaks, the interval is the start and end.
            return models.SpecificInterval(((start/60, finish/60),))

        # Order the breaks by their start-time, and ensure that they are monotonic
        # and that the start of one break happens after the end of another.
        break_boundaries: models.BoundarySequence_t = tuple(sorted(breaks, key=lambda break_pair: break_pair[0]))

        for break_start, break_end in break_boundaries:
            if break_start >= break_end:
                raise ValueError("Break ends before it begins.")

        prev_break_end = break_boundaries[0][1]
        for break_start, break_end in break_boundaries[1:]:
            if prev_break_end >= break_start:
                raise ValueError(f"A break starts before another ends ({break_start}, {break_end}, {prev_break_end}).")
            prev_break_end = break_end

        present_intervals = []

        # def add_interval(start, end):

        current_time = start
        LOG.debug(f"starting time march at {_hours2timestring(current_time/60)} to {_hours2timestring(finish/60)}")

        # As we step through the breaks. For each break there are 6 important cases
        # we must cover. Let S=start; E=end; Bs=Break start; Be=Break end:
        #  1. The interval is entirely before the break. S < E <= Bs < Be
        #  2. The interval straddles the start of the break. S < Bs < E <= Be
        #  3. The break is entirely inside the interval. S < Bs < Be <= E
        #  4. The interval is entirely inside the break. Bs <= S < E <= Be
        #  5. The interval straddles the end of the break. Bs <= S < Be <= E
        #  6. The interval is entirely after the break. Bs < Be <= S < E

        for current_break in break_boundaries:
            if current_time >= finish:
                break

            LOG.debug(f"handling break {_hours2timestring(current_break[0]/60)}-{_hours2timestring(current_break[1]/60)} "
                      f" (current time: {_hours2timestring(current_time/60)})")

            break_s, break_e = current_break
            case1 = finish <= break_s
            case2 = current_time < break_s < finish < break_e
            case3 = current_time < break_s < break_e <= finish
            case4 = break_s <= current_time < finish <= break_e
            case5 = break_s <= current_time < break_e < finish
            case6 = break_e <= current_time

            if case1:
                LOG.debug(f"case 1: interval entirely before break")
                present_intervals.append((current_time / 60, finish / 60))
                LOG.debug(f" + added interval {_hours2timestring(present_intervals[-1][0])} "
                          f"- {_hours2timestring(present_intervals[-1][1])}")
                current_time = finish
            elif case2:
                LOG.debug(f"case 2: interval straddles start of break")
                present_intervals.append((current_time / 60, break_s / 60))
                LOG.debug(f" + added interval {_hours2timestring(present_intervals[-1][0])} "
                          f"- {_hours2timestring(present_intervals[-1][1])}")
                current_time = break_e
            elif case3:
                LOG.debug(f"case 3: break entirely inside interval")
                # We add the bit before the break, but not the bit afterwards,
                # as it may hit another break.
                present_intervals.append((current_time / 60, break_s / 60))
                LOG.debug(f" + added interval {_hours2timestring(present_intervals[-1][0])} "
                          f"- {_hours2timestring(present_intervals[-1][1])}")
                current_time = break_e
            elif case4:
                LOG.debug(f"case 4: interval entirely inside break")
                current_time = finish
            elif case5:
                LOG.debug(f"case 5: interval straddles end of break")
                current_time = break_e
            elif case6:
                LOG.debug(f"case 6: interval entirely after the break")

        if current_time < finish:
            LOG.debug("trailing interval")
            present_intervals.append((current_time / 60, finish / 60))
        return models.SpecificInterval(tuple(present_intervals))

    def infected_present_interval(self) -> models.Interval:
        return self.present_interval(
            self.infected_start, self.infected_finish,
            breaks=self.infected_lunch_break_times() + self.infected_coffee_break_times(),
        )

    def exposed_present_interval(self) -> models.Interval:
        return self.present_interval(
            self.exposed_start, self.exposed_finish,
            breaks=self.exposed_lunch_break_times() + self.exposed_coffee_break_times(),
        )


def build_expiration(expiration_definition) -> models._ExpirationBase:
    if isinstance(expiration_definition, str):
        return models._ExpirationBase.types[expiration_definition]
    elif isinstance(expiration_definition, dict):
        return models.MultipleExpiration(
            tuple([build_expiration(exp) for exp in expiration_definition.keys()]),
            tuple(expiration_definition.values())
        )


def baseline_raw_form_data():
    # Note: This isn't a special "baseline". It can be updated as required.
    return {
        'activity_type': 'office',
        'role_type':'',
        'role_type2':'',
        'air_changes': '',
        'air_supply': '',
        'ceiling_height': '',
        'exposed_coffee_break_option': 'coffee_break_4',
        'exposed_coffee_duration': '10',
        'exposed_finish': '18:00',
        'exposed_lunch_finish': '13:30',
        'exposed_lunch_option': '1',
        'exposed_lunch_start': '12:30',
        'exposed_start': '09:00',
        'floor_area': '',
        'hepa_amount': '250',
        'hepa_option': '0',
        'infected_coffee_break_option': 'coffee_break_4',
        'infected_coffee_duration': '10',
        'infected_dont_have_breaks_with_exposed': '1',
        'infected_finish': '18:00',
        'infected_lunch_finish': '13:30',
        'infected_lunch_option': '1',
        'infected_lunch_start': '12:30',
        'infected_people': '1',
        'infected_start': '09:00',
        'location_latitude': 46.20833,
        'location_longitude': 6.14275,
        'location_name': 'Geneva',
        'mask_type': 'Type I',
        'mask_type2': 'Type I',
        'mask_wearing_option': 'mask_off',
        'mask_wearing_option2': 'mask_off',
        'mechanical_ventilation_type': '',
        'calculator_version': calculator.__version__,
        'opening_distance': '0.2',
        'event_month': 'January',
        'room_heating_option': '0',
        'room_number': '123',
        'room_volume': '75',
        'scenarios_alt': '1;2;3',
        'scenario_1': '',
        'scenario_2': '',
        'scenario_3': '',
        'simulation_name': 'Test',
        'total_people': '10',
        'uv_option': False,
        'uv_device': "BR500",
        'uv_speed': 400,
        'ventilation_type': 'natural_ventilation',
        'virus_type': 'SARS_CoV_2',
        'volume_type': 'room_volume_explicit',
        'windows_duration': '',
        'windows_frequency': '',
        'window_height': '2',
        'window_type': 'window_sliding',
        'window_width': '2',
        'windows_number': '1',
        'window_opening_regime': 'windows_open_permanently'
    }


ACTIVITY_TYPES = {'office', 'meeting', 'training', 'callcentre', 'controlroom-day', 'controlroom-night', 'library', 'workshop', 'lab', 'gym'}
ROLE_TYPE ={'Hospital_patient', 'Nurse_working', 'Physician_working', 'Office_worker', 'Workshop_worker', 'Meeting_participant', 'Meeting_leader', 'Student_sitting', 'Professor_teaching', 'Professor_conferencing', 'Concert_musician_soft_music','Concert_musician_rock', 'Concert_singer', 
        'Concert_spectator_standing', 'Concert_spectator_sitting', 'Museum_visitor', 'Theater_spectator', 'Theater_actor', 'Conferencer', 'Conference_attendee', 'Guest_standing', 'Guest_sitting', 'Server', 'Barrista', 'Nightclub_dancing', 'Nightclub_sitting', 
        'Customer_standing', 'Cashier_sitting', 'Vendor_standing', 'Musculation', 'Floor_gymnastics', 'Team_competition', 'Trip_in_elevator'}

ROLE_TYPE2 ={'Hospital_patient2', 'Nurse_working2', 'Physician_working2', 'Office_worker2', 'Workshop_worker2', 'Meeting_participant2', 'Meeting_leader2', 'Student_sitting2', 'Professor_teaching2', 'Professor_conferencing2', 'Concert_musician_soft_music2','Concert_musician_rock2', 'Concert_singer2', 
        'Concert_spectator_standing2', 'Concert_spectator_sitting2', 'Museum_visitor2', 'Theater_spectator2', 'Theater_actor2', 'Conferencer2', 'Conference_attendee2', 'Guest_standing2', 'Guest_sitting2', 'Server2', 'Barrista2', 'Nightclub_dancing2', 'Nightclub_sitting2', 
        'Customer_standing2', 'Cashier_sitting2', 'Vendor_standing2', 'Musculation2', 'Floor_gymnastics2', 'Team_competition2', 'Trip_in_elevator2'}

MECHANICAL_VENTILATION_TYPES = {'mech_type_air_changes', 'mech_type_air_supply', 'not-applicable'}
MASK_TYPES = {'Type I', 'FFP2'}
MASK_TYPES2 = {'Type I', 'FFP2'}
MASK_WEARING_OPTIONS = {'mask_on', 'mask_off'}
MASK_WEARING_OPTIONS2 = {'mask_on', 'mask_off'}
VENTILATION_TYPES = {'natural_ventilation', 'mechanical_ventilation', 'no_ventilation'}
VIRUS_TYPES = {'SARS_CoV_2', 'SARS_CoV_2_B117', 'SARS_CoV_2_B1351','SARS_CoV_2_P1', 'SARS_CoV_2_B16172', 'SARS_CoV_2_B11529'}
VOLUME_TYPES = {'room_volume_explicit', 'room_volume_from_dimensions'}
WINDOWS_OPENING_REGIMES = {'windows_open_permanently', 'windows_open_periodically', 'not-applicable'}
WINDOWS_TYPES = {'window_sliding', 'window_hinged', 'not-applicable'}

COFFEE_OPTIONS_INT = {'coffee_break_0': 0, 'coffee_break_1': 1, 'coffee_break_2': 2, 'coffee_break_4': 4}

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December',
]


def _hours2timestring(hours: float):
    # Convert times like 14.5 to strings, like "14:30"
    return f"{int(np.floor(hours)):02d}:{int(np.round((hours % 1) * 60)):02d}"


def time_string_to_minutes(time: str) -> minutes_since_midnight:
    """
    Converts time from string-format to an integer number of minutes after 00:00
    :param time: A string of the form "HH:MM" representing a time of day
    :return: The number of minutes between 'time' and 00:00
    """
    return minutes_since_midnight(60 * int(time[:2]) + int(time[3:]))


def time_minutes_to_string(time: int) -> str:
    """
    Converts time from an integer number of minutes after 00:00 to string-format
    :param time: The number of minutes between 'time' and 00:00
    :return: A string of the form "HH:MM" representing a time of day
    """
    return "{0:0=2d}".format(int(time/60)) + ":" + "{0:0=2d}".format(time%60)


def _safe_int_cast(value) -> int:
    if isinstance(value, int):
        return value
    elif isinstance(value, float) and int(value) == value:
        return int(value)
    elif isinstance(value, str) and value.isdecimal():
        return int(value)
    else:
        raise TypeError(f"Unable to safely cast {value} ({type(value)} type) to int")


#: Mapping of field name to a callable which can convert values from form
#: input (URL encoded arguments / string) into the correct type.
_CAST_RULES_FORM_ARG_TO_NATIVE: typing.Dict[str, typing.Callable] = {}

#: Mapping of field name to callable which can convert native type to values
#: that can be encoded to URL arguments.
_CAST_RULES_NATIVE_TO_FORM_ARG: typing.Dict[str, typing.Callable] = {}


for _field in dataclasses.fields(FormData):
    if _field.type is minutes_since_midnight:
        _CAST_RULES_FORM_ARG_TO_NATIVE[_field.name] = time_string_to_minutes
        _CAST_RULES_NATIVE_TO_FORM_ARG[_field.name] = time_minutes_to_string
    elif _field.type is int:
        _CAST_RULES_FORM_ARG_TO_NATIVE[_field.name] = _safe_int_cast
    elif _field.type is float:
        _CAST_RULES_FORM_ARG_TO_NATIVE[_field.name] = float
    elif _field.type is bool:
        _CAST_RULES_FORM_ARG_TO_NATIVE[_field.name] = lambda v: v == '1'
        _CAST_RULES_NATIVE_TO_FORM_ARG[_field.name] = int
