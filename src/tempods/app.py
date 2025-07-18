from cosmicds.utils import load_template
from glue_jupyter.view import Viewer
import ipyvuetify as v
from ipyvuetify.VuetifyTemplate import VuetifyTemplate
from ipywidgets import DOMWidget, widget_serialization
from traitlets import Dict, Instance

from os import getenv
import json
import glue_jupyter as gj
from glue_map.data import RemoteGeoData_ArcGISImageServer, Data
from glue_map.map.state import MapViewerState
from tempods.components.subset_control_widget import SubsetControlWidget

from glue.config import colormaps
from ipyleaflet import Map, Marker, LayersControl, TileLayer, WidgetControl, GeoJSON
from datetime import date, datetime, timezone, timedelta
from ipywidgets import SelectionSlider, Layout, Label, VBox, Dropdown, DatePicker, HTML, AppLayout, widgets, FloatSlider
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
        asdc_url = "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/"
        tempo_data = RemoteGeoData_ArcGISImageServer(asdc_url,
                                                     name='TEMPO')

        power_data = self.glue_app.load_data("Power_Plants.csv")
        self.glue_app.add_data(tempo_data)

        # Our remote dataset does not have real components representing latitude and longitude. We link to the only components
        # it does have so that we can display this on the same viewer without trigger and IncompatibleAttribute error
        self.glue_app.add_link(self.glue_app.data_collection["Power_Plants"], 'Longitude',  self.glue_app.data_collection["TEMPO"], 'Pixel Axis 0')
        self.glue_app.add_link(self.glue_app.data_collection["Power_Plants"], 'Latitude', self.glue_app.data_collection["TEMPO"], 'TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN')

        big = (power_data['Install_MW'] > 100)
        med = (power_data['Install_MW'] > 10) & (power_data['Install_MW'] <= 100)
        small = (power_data['Install_MW'] <= 10)
        power_data.add_component(big*9 + med*4 + small*1, label='Size_binned')

        with open('coastlines.geojson', 'r') as f:
            coastdata = json.load(f)
        geo_json = GeoJSON(
            data=coastdata,
            style={
                'color': 'black',
                'opacity': 1,
                'fillOpacity': 0,
                'weight': 0.5
            },
        )

        stadia_base_url = "https://tiles.stadiamaps.com/tiles/stamen_toner_lines/{z}/{x}/{y}{r}.png"
        stadia_labels_url="https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}{r}.png"

        stadia_api_key = getenv("STADIA_API_KEY")
        if stadia_api_key is not None:
            stadia_base_url += f"?api_key={stadia_api_key}"
            stadia_labels_url += f"?api_key={stadia_api_key}"
        map_state = MapViewerState(basemap=TileLayer(url=stadia_base_url), center=(40, -100), zoom_level=4)
        map_viewer = self.glue_app.new_data_viewer("map", data=tempo_data, state=map_state, show=False)
        map_viewer.figure_widget.layout = {"width": "800px", "height": "450px"}
        map_viewer.map.panes = {"labels": {"zIndex": 650}}

        _ = map_viewer.map.add(TileLayer(url=stadia_labels_url, pane='labels'))
        _ = map_viewer.map.add(geo_json)

        powerplant_widget = SubsetControlWidget(power_data, map_viewer)

        self.add_widget(powerplant_widget, "powerplant")
        self.add_viewer(map_viewer, "map")

        timeseries_viewer = self.glue_app.new_data_viewer('timeseries', data=tempo_data, show=False)
        timeseries_viewer.figure_widget.layout = {"height": "400px"}
        timeseries_viewer.figure.axes[1].label_offset = "-50"
        timeseries_viewer.figure.axes[1].tick_format = ".0f"
        timeseries_viewer.figure.axes[1].label = "Average NO2 within region (10^14 molecules/cm^2)"

        timeseries_viewer.figure.axes[0].label_offset = "40"
        timeseries_viewer.figure.axes[0].label = "Time (UTC)"

        timeseries_viewer.figure.axes[0].label_color = "white"
        timeseries_viewer.figure.axes[1].label_color = "white"

        timeseries_viewer.state.y_min = 0
        timeseries_viewer.state.y_max *= 1.1

        timeseries_viewer.figure.axes[0].tick_style = {"stroke": "white"}
        timeseries_viewer.figure.axes[1].tick_style = {"stroke": "white"}


        timeseries_viewer.figure.axes[0].tick_format = "%H:%M"

        self.add_viewer(timeseries_viewer, "timeseries")
        
        def convert_from_milliseconds(milliseconds_since_epoch):
            """Converts milliseconds since epoch to a date-time string in 'YYYY-MM-DDTHH:MM:SSZ' format."""
            dt = datetime.fromtimestamp((milliseconds_since_epoch)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
            date_time_str = dt.strftime('%H:%M')
            return date_time_str
        
        time_values = tempo_data.get_time_steps(timeseries_viewer.state.t_date)
        time_strings = [convert_from_milliseconds(t) for t in time_values]  
        time_options = [(time_strings[i], time_values[i]) for i in range(len(time_values))]
        
        slider = SelectionSlider(description='Time (UTC):', options=time_options, layout=Layout(width='600px', height='25px'))
        dt = datetime.fromtimestamp((slider.value)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        timeseries_viewer.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')
        
        date_chooser = DatePicker(description='Pick a Date')
        date_chooser.value = date(2024, 11, 13)
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
        
        opacity_slider = FloatSlider(description='', value=1, min=0, max=1, orientation='vertical', readout=False)
        opacity_slider.layout = {"width":"28px"}

        # Doing the link this simple way does not work, and causes the opacity to be reset
        # as we scrub through timesteps. Instead, we need to do a callback on the glue state attribute
        # mylink = widgets.jslink((opacity_slider, 'value'), (map_viewer.map.layers[1], 'opacity'))

        def update_opacity(change):
            if change.new != change.old:
                map_viewer.layers[0].state.opacity = change.new
        opacity_slider.observe(update_opacity, 'value')

        opacity_label = WidgetControl(widget=widgets.Label('Opacity:'), position='topleft')
        opacity_control = WidgetControl(widget=opacity_slider, position='topleft')
        map_viewer.map.add(opacity_label)
        map_viewer.map.add(opacity_control)
        map_viewer.map.add(WidgetControl(widget=date_chooser, position='bottomleft'))

        def update_slider_value(event):
            if 'domain' in event and 'x' in event['domain']:
                value = event['domain']['x']
                t = [i[1] for i in slider.options]
                smax = max(t)
                smin = min(t)
                t = [abs(((i - smin) / (smax - smin)) - value) for i in t]
                min_index = min(range(len(t)), key = t.__getitem__)
                slider.value = slider.options[min_index][1]

        timeseries_viewer.add_event_callback(callback = update_slider_value, events=['click'])

    def add_viewer(self, viewer: Viewer, label: str):
        current_viewers = {k: v for k, v in self.viewers.items()}
        current_viewers.update({label: viewer._layout})
        self.viewers = current_viewers

    def add_widget(self, component: VuetifyTemplate, label: str):
        current_widgets = {k: v for k, v in self.extra_widgets.items()}
        current_widgets.update({label: component})
        self.extra_widgets = current_widgets
