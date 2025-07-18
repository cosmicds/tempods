import solara
import reacton.ipyvuetify as rv
from glue_jupyter.view import Viewer
import ipyvuetify as v



from os import getenv
import json
import glue_jupyter as gj
from glue_map.data import RemoteGeoData_ArcGISImageServer, Data
from glue_map.map.state import MapViewerState
from glue_map.map.viewer import IPyLeafletMapViewer
from glue_map.timeseries.viewer import TimeSeriesViewer
from tempods.components.subset_control_widget import SubsetControlWidget

from glue.config import colormaps
from ipyleaflet import Map, Marker, LayersControl, TileLayer, WidgetControl, GeoJSON
from datetime import date, datetime, timezone, timedelta
from ipywidgets import SelectionSlider, Layout, DatePicker, widgets, FloatSlider, DOMWidget
import pandas as pd
import numpy as np

from pathlib import Path
from typing import cast

from solara.lab import use_task


v.theme.dark = True

@solara.component
def ViewerToSolara(viewer, class_list = [], style = {}):
    class_string = " ".join(["widget-layout"] + class_list)
    style_string = ";".join([f"{k}: {v}" for k, v in style.items()])
    with rv.Card(outlined=True, class_ = class_string, style_ = style_string):
        with rv.CardText(children = [viewer.layout]):
            pass
    

@solara.component
def WidgetToSolara(widget, class_list = [], style = {}):
    class_string = " ".join(["widget-layout"] + class_list)
    style_string = ";".join([f"{k}: {v}" for k, v in style.items()])
    with rv.Card(outlined=True, class_ = class_string, style_ = style_string):
        with rv.CardText(children = [widget]):
            pass

INIT_DATE = "2024-10-15" ## just a default

@solara.component
def Page():

    print('Rendering Page')
    
    
    
    def _setup_mapviewer(glue_app: gj.JupyterApplication) -> IPyLeafletMapViewer:
        coastlines_path = Path(__file__).parent.parent.parent / "notebooks" / "coastlines.geojson"
        with open(str(coastlines_path), 'r') as f:
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
        map_state = MapViewerState(basemap=TileLayer(url=stadia_base_url))
        map_viewer = cast(IPyLeafletMapViewer, glue_app.new_data_viewer("map", state=map_state, show=False))
    
        map_viewer.figure_widget.layout = {"width": "100%", "height": "500px"}
        map_viewer.map.panes = {"labels": {"zIndex": 650}}

        _ = map_viewer.map.add(TileLayer(url=stadia_labels_url, pane='labels'))
        _ = map_viewer.map.add(geo_json)
        
        return map_viewer
    
    def _setup_power_data(glue_app: gj.JupyterApplication) -> Data:
        if "Power_Plants" not in glue_app.data_collection:
            powerplant_data = Path(__file__).parent.parent.parent / "notebooks" / "Power_Plants.csv"
            power_data = cast(Data, glue_app.load_data(str(powerplant_data)))
            ## load data automatically adds it to the data collection

            big = (power_data['Install_MW'] > 100)
            med = (power_data['Install_MW'] > 10) & (power_data['Install_MW'] <= 100)
            small = (power_data['Install_MW'] <= 10)
            power_data.add_component(big*9 + med*4 + small*1, label='Size_binned')
        
        return glue_app.data_collection["Power_Plants"]
    

    def _setup_glue() -> tuple[gj.JupyterApplication, IPyLeafletMapViewer]:
        gjapp = gj.jglue()
        app = gj.JupyterApplication(gjapp.data_collection, gjapp.session)
        powerplant_data = Path(__file__).parent.parent.parent / "notebooks" / "Power_Plants.csv"
        power_data = _setup_power_data(app)
        map_viewer = _setup_mapviewer(app)
        
        asdc_url = "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/"
        tempo_data = RemoteGeoData_ArcGISImageServer(asdc_url,
                                                        name='TEMPO')
        app.add_data(tempo_data)
        # Our remote dataset does not have real components representing latitude and longitude. We link to the only components
        # it does have so that we can display this on the same viewer without trigger and IncompatibleAttribute error
        app.add_link(power_data, 'Longitude',  app.data_collection["TEMPO"], 'Pixel Axis 0')
        app.add_link(power_data, 'Latitude', app.data_collection["TEMPO"], 'TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN')
        map_viewer.add_data(tempo_data)
        return app, map_viewer

    glue_app, map_viewer = solara.use_memo(_setup_glue, [])

    
    
    

    
    

    

    
    
    
    power_data = glue_app.data_collection["Power_Plants"]
    tempo_data = glue_app.data_collection["TEMPO"]
    
    def _setup_powerplant_widget() -> SubsetControlWidget:
        powerplant_widget = SubsetControlWidget(power_data, map_viewer)
        return powerplant_widget
    powerplant_widget = solara.use_memo(_setup_powerplant_widget, [])

    # This takes a long time because in add_data it calls layer.update which resolves throough layer artsts 
    # to at sompeoint call update_profile which calls get_temporal_data
    def setup_timeseries_viewer(glue_app: gj.JupyterApplication, data: Data) -> TimeSeriesViewer:
        timeseries_viewer = cast(TimeSeriesViewer, glue_app.new_data_viewer('timeseries', show=False))
        timeseries_viewer.state.t_date = INIT_DATE
        timeseries_viewer.add_data(data)
        
        timeseries_viewer.figure.axes[1].label_offset = "-50"
        timeseries_viewer.figure.axes[1].tick_format = ".0f"
        timeseries_viewer.figure.axes[1].label = "Amount of NO2 (10^14 molecules/cm^2)"

        timeseries_viewer.figure.axes[0].label_offset = "40"
        timeseries_viewer.figure.axes[0].label = "Time (UTC)"

        timeseries_viewer.figure.axes[0].label_color = "white"
        timeseries_viewer.figure.axes[1].label_color = "white"

        timeseries_viewer.figure.axes[0].tick_style = {"stroke": "white"}
        timeseries_viewer.figure.axes[1].tick_style = {"stroke": "white"}
        
        time_values = tempo_data.get_time_steps(INIT_DATE)
        if len(time_values) > 0:
            dt = datetime.fromtimestamp(time_values[0]/1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
            timeseries_viewer.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')
    
        return timeseries_viewer
    # timeseries_viewer = cast(TimeSeriesViewer, glue_app.new_data_viewer('timeseries', data=tempo_data, show=False)) 
    timeseries_viewer_task = use_task(lambda: setup_timeseries_viewer(glue_app, tempo_data), dependencies=[])
    timeseries_viewer = None
    if timeseries_viewer_task.value is not None:
        timeseries_viewer = timeseries_viewer_task.value
    
    

    
    
    def convert_from_milliseconds(milliseconds_since_epoch):
        """Converts milliseconds since epoch to a date-time string in 'YYYY-MM-DDTHH:MM:SSZ' format."""
        dt = datetime.fromtimestamp((milliseconds_since_epoch)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        date_time_str = dt.strftime('%H:%M')
        return date_time_str
    
    def update_image(change):
        map_viewer.layers[0].state.timestep = change.new
        dt = datetime.fromtimestamp((change.new)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        if timeseries_viewer_task.value is not None:
            timeseries_viewer_task.value.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')
    
    def update_date(change):
        time_values = tempo_data.get_time_steps(change.new.isoformat())
        time_strings = [convert_from_milliseconds(t) for t in time_values]  
        time_options = [(time_strings[i], time_values[i]) for i in range(len(time_values))]
        slider.options = time_options
        if timeseries_viewer_task.value is not None:
            timeseries_viewer_task.value.state.t_date = change.new.isoformat()
    
    
    def _setup_slider():
        time_values = tempo_data.get_time_steps(INIT_DATE)
        time_strings = [convert_from_milliseconds(t) for t in time_values]
        time_options = [(time_strings[i], time_values[i]) for i in range(len(time_values))]
        return SelectionSlider(description='Time (UTC):', options=time_options, layout=Layout(width='700px', height='25px'))
    
    slider = solara.use_memo(_setup_slider, [])
    
    def _setup_date_chooser():
        # FIX: We will want to use Solara's InputDate
        # This fires too frequently, causing excessive data loading
        date_chooser = DatePicker(description='Pick a Date')
        date_chooser.value = date.fromisoformat(INIT_DATE)
        return date_chooser
    
    date_chooser = solara.use_memo(_setup_date_chooser, [])
    
    

    def _setup_opacity_slider():
        opacity_slider = FloatSlider(description='', value=1, min=0, max=1, orientation='vertical', readout=False)
        opacity_slider.layout = {"width":"28px"}

        def update_opacity(change):
            if change.new != change.old:
                map_viewer.layers[0].state.opacity = change.new
        
        opacity_slider.observe(update_opacity, 'value')
        opacity_label = WidgetControl(widget=widgets.Label('Opacity:'), position='topright')
        opacity_control = WidgetControl(widget=opacity_slider, position='topright')
        
        
        return opacity_slider, opacity_label, opacity_control
    
    opacity_slider, opacity_label, opacity_control = solara.use_memo(_setup_opacity_slider, [])
    
    def add_controls_to_map():
        
        
        map_viewer.map.add(opacity_label)
        map_viewer.map.add(opacity_control)
        
        date_chooser.observe(update_date, 'value')
        slider.observe(update_image, 'value')
        control = WidgetControl(widget=slider, position='bottomleft')
        map_viewer.map.add(control)
        
        map_viewer.map.add(WidgetControl(widget=date_chooser, position='bottomleft'))
    
    solara.use_effect(add_controls_to_map, dependencies=[])
    
    def _connect_timeseries_to_slider():

        def update_slider_value(event):
            if 'domain' in event and 'x' in event['domain']:
                value = event['domain']['x']
                t = [i[1] for i in slider.options]
                smax = max(t)
                smin = min(t)
                t = [abs(((i - smin) / (smax - smin)) - value) for i in t]
                min_index = min(range(len(t)), key = t.__getitem__)
                slider.value = slider.options[min_index][1]
        
        if timeseries_viewer_task.value is not None:
            timeseries_viewer_task.value.add_event_callback(callback = update_slider_value, events=['click'])
    solara.use_effect(_connect_timeseries_to_slider, dependencies=[timeseries_viewer_task.value])

    
    # App layout

    with solara.AppBar():
        solara.AppBarTitle("TEMPO Data Story Prototype")
    with solara.VBox():        
        with rv.Row():
            with solara.Columns(widths=[8, 3]):
                ViewerToSolara(map_viewer, class_list = ["mx-2"], style = {"outline": "1px solid white"})
                if powerplant_widget is not None:
                    WidgetToSolara(powerplant_widget, class_list = ["mx-2"], style = {"outline": "1px solid white"})
                else:
                    solara.Text("Loading Power Plant Widget...")
                # WidgetToSolara(powerplant_widget, class_list = ["mx-2"], style = {"outline": "1px solid white"})
        with rv.Col():
            if timeseries_viewer is not None:
                ViewerToSolara(timeseries_viewer, class_list = ["mx-2"], style = {"outline": "1px solid white"})
            else:
                solara.Text("Loading Timeseries Viewer...")