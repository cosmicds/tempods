from cosmicds.utils import load_template
from glue_jupyter.view import Viewer
import ipyvuetify as v
from ipyvuetify.VuetifyTemplate import VuetifyTemplate
from ipywidgets import DOMWidget, widget_serialization
from traitlets import Dict, Instance

from os import getenv
import glue_jupyter as gj
from glue_map.data import RemoteGeoData_ArcGISImageServer, Data
from glue_map.map.state import MapViewerState
from tempods.components.subset_control_widget import SubsetControlWidget

from glue.config import colormaps
from ipyleaflet import Map, Marker, LayersControl, TileLayer, WidgetControl
from datetime import date, datetime, timezone, timedelta
from ipywidgets import SelectionSlider, Layout, Label, VBox, Dropdown, DatePicker, HTML, AppLayout
import pandas as pd
import numpy as np


v.theme.dark = True


class TempoApp(v.VuetifyTemplate):
    template = load_template("app.vue", __file__, traitlet=True).tag(sync=True)
    viewers = Dict().tag(sync=True, **widget_serialization)
    # Calling this just "widgets" or "components" caused problems - must be some name clashes with ipyvuetify
    extra_widgets = Dict().tag(sync=True, **widget_serialization)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.glue_app = gj.jglue()
        tempo_data = RemoteGeoData_ArcGISImageServer("https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/",
                                            name='TEMPO')

        power_data = self.glue_app.load_data("Power_Plants.csv")
        self.glue_app.add_data(tempo_data)

        # Our remote dataset does not have real components representing latitude and longitude. We link to the only components
        # it does have so that we can display this on the same viewer without trigger and IncompatibleAttribute error
        self.glue_app.add_link(self.glue_app.data_collection["Power_Plants"], 'Longitude',  self.glue_app.data_collection["TEMPO"], 'Pixel Axis 0')
        self.glue_app.add_link(self.glue_app.data_collection["Power_Plants"], 'Latitude', self.glue_app.data_collection["TEMPO"], 'TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN_BETA')

        big = (power_data['Install_MW'] > 100)
        med = (power_data['Install_MW'] > 10) & (power_data['Install_MW'] <= 100)
        small = (power_data['Install_MW'] <= 10)
        power_data.add_component(big*9 + med*4 + small*1, label='Size_binned')

        stadia_url = "https://tiles.stadiamaps.com/tiles/stamen_toner_lines/{z}/{x}/{y}{r}.png"
        stadia_api_key = getenv("STADIA_API_KEY")
        if stadia_api_key is not None:
            stadia_url += f"?api_key={stadia_api_key}"
        map_state = MapViewerState(basemap=TileLayer(url=stadia_url))
        map_viewer = self.glue_app.new_data_viewer("map", data=tempo_data, state=map_state, show=False)
        powerplant_widget = SubsetControlWidget(power_data, map_viewer)

        self.add_widget(powerplant_widget, "powerplant")
        self.add_viewer(map_viewer, "map")

        timeseries_viewer = self.glue_app.new_data_viewer('timeseries', data=tempo_data, show=False)
        timeseries_viewer.figure.axes[1].label_offset = "-50"
        timeseries_viewer.figure.axes[1].tick_format = ".0f"
        timeseries_viewer.figure.axes[1].label = "Amount of NO2 (10^14 molecules/cm^2)"

        timeseries_viewer.figure.axes[0].label_offset = "40"
        timeseries_viewer.figure.axes[0].label = "Time (UTC)"

        self.add_viewer(timeseries_viewer, "timeseries")
        
        def convert_from_milliseconds(milliseconds_since_epoch):
            """Converts milliseconds since epoch to a date-time string in 'YYYY-MM-DDTHH:MM:SSZ' format."""
            dt = datetime.fromtimestamp((milliseconds_since_epoch)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
            date_time_str = dt.strftime('%H:%M')
            return date_time_str
        
        time_values = tempo_data.get_time_steps(timeseries_viewer.state.t_date)
        time_strings = [convert_from_milliseconds(t) for t in time_values]  
        time_options = [(time_strings[i], time_values[i]) for i in range(len(time_values))]
        
        slider = SelectionSlider(description='', options=time_options,layout=Layout(width='700px', height='20px'))
        dt = datetime.fromtimestamp((slider.value)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        timeseries_viewer.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')
        
        date_chooser = DatePicker(description='Pick a Date')
        date_chooser.value = date(2024, 10, 15)
        def update_image(change):
            map_viewer.layers[0].state.timestep = change.new
            dt = datetime.fromtimestamp((change.new)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
            timeseries_viewer.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')
        
        def update_date(change):
            time_values = tempo_data.get_time_steps(change.new.isoformat())
            time_strings = [convert_from_milliseconds(t) for t in time_values]  
            time_options = [(time_strings[i], time_values[i]) for i in range(len(time_values))]
            slider.options = time_options
            timeseries_viewer.state.t_date = change.new.isoformat()
            
        date_chooser.observe(update_date, 'value')
        
        slider.observe(update_image, 'value')
        control = WidgetControl(widget=slider, position='bottomleft')
        map_viewer.map.add(control)

    def add_viewer(self, viewer: Viewer, label: str):
        current_viewers = {k: v for k, v in self.viewers.items()}
        current_viewers.update({label: viewer._layout})
        self.viewers = current_viewers

    def add_widget(self, component: VuetifyTemplate, label: str):
        current_widgets = {k: v for k, v in self.extra_widgets.items()}
        current_widgets.update({label: component})
        self.extra_widgets = current_widgets
