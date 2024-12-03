from datetime import date, datetime, timedelta, timezone
import json
from os import getenv
from pathlib import Path
from typing import Tuple, cast

from cosmicds.components import ViewerLayout
from glue.core import Data
from glue_jupyter import JupyterApplication, jglue
from glue_map.map import IPyLeafletMapViewer
from glue_map.map.state import MapViewerState
from glue_map.map.layer_artist import RemoteGeoData_ArcGISImageServer
from glue_map.timeseries import TimeSeriesViewer
from ipyleaflet import TileLayer, GeoJSON
import numpy as np
import solara
from solara.alias import rv

from tempods.components import SubsetControlWidget
from ..layout import Layout


@solara.component
def Page():

    def _glue_setup() -> Tuple[JupyterApplication, IPyLeafletMapViewer, TimeSeriesViewer]:
        app = jglue()

        # TODO: We should probably change where the data lives
        notebooks_dir = Path(__file__).parent.parent.parent.parent / "notebooks"
        coastlines_path = notebooks_dir / "coastlines.geojson"
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

        powerplant_datapath = notebooks_dir / "Power_Plants.csv"
        powerplant_data: Data = app.load_data(str(powerplant_datapath))

        asdc_url = "https://gis.earthdata.nasa.gov/image/rest/services/C2930763263-LARC_CLOUD/"
        tempo_data = RemoteGeoData_ArcGISImageServer(asdc_url, name="TEMPO")
        app.add_data(tempo_data)

        # Our remote dataset does not have real components representing latitude and longitude. We link to the only components
        # it does have so that we can display this on the same viewer without trigger and IncompatibleAttribute error
        app.add_link(app.data_collection["Power_Plants"], 'Longitude',  app.data_collection["TEMPO"], 'Pixel Axis 0')
        app.add_link(app.data_collection["Power_Plants"], 'Latitude', app.data_collection["TEMPO"], 'TEMPO_NO2_L3_V03_HOURLY_TROPOSPHERIC_VERTICAL_COLUMN_BETA')

        big = (powerplant_data['Install_MW'] > 100)
        med = (powerplant_data['Install_MW'] > 10) & (powerplant_data['Install_MW'] <= 100)
        small = (powerplant_data['Install_MW'] <= 10)
        powerplant_data.add_component(big*9 + med*4 + small*1, label='Size_binned')

        map = cast(IPyLeafletMapViewer, app.new_data_viewer(IPyLeafletMapViewer, data=tempo_data, state=map_state, show=False))
        map.figure_widget.layout = {"width": "100%", "height": "500px"}
        map.map.panes = {"labels": {"zIndex": 650}}
        map.map.add(TileLayer(url=stadia_labels_url, pane='labels'))
        map.map.add(geo_json)

        timeseries = cast(TimeSeriesViewer, app.new_data_viewer(TimeSeriesViewer, data=tempo_data, show=False))
        timeseries.figure.axes[1].label_offset = "-50"
        timeseries.figure.axes[1].tick_format = ".0f"
        timeseries.figure.axes[1].label = "Amount of NO2 (10^14 molecules/cm^2)"

        timeseries.figure.axes[0].label_offset = "40"
        timeseries.figure.axes[0].label = "Time (UTC)"

        timeseries.figure.axes[0].label_color = "white"
        timeseries.figure.axes[1].label_color = "white"

        timeseries.figure.axes[0].tick_style = {"stroke": "white"}
        timeseries.figure.axes[1].tick_style = {"stroke": "white"}

        return app, map, timeseries

    gjapp, map_viewer, timeseries_viewer = solara.use_memo(_glue_setup, dependencies=[])
    powerplant_data = gjapp.data_collection["Power_Plants"]
    tempo_data = gjapp.data_collection["TEMPO"]

    def convert_from_milliseconds(milliseconds_since_epoch):
        """Converts milliseconds since epoch to a date-time string in 'YYYY-MM-DDTHH:MM:SSZ' format."""
        dt = datetime.fromtimestamp((milliseconds_since_epoch)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        date_time_str = dt.strftime('%H:%M')
        return date_time_str

    time_index, set_time_index = solara.use_state(0)
    current_date, set_current_date = solara.use_state("2024-10-15")
    time_values, set_time_values = solara.use_state(tempo_data.get_time_steps(current_date))

    def update_image(index):
        print(f"update_image: {index}")
        set_time_index(index)
        timestep = time_values[index]
        dt = datetime.fromtimestamp((timestep)/ 1000, tz=timezone(offset=timedelta(hours=0), name="UTC"))
        print(np.array([dt, dt]).astype('datetime64[ms]'))
        print(map_viewer.layers[0].state.timestep, timestep)
        map_viewer.layers[0].state.timestep = timestep 
        timeseries_viewer.timemark.x = np.array([dt, dt]).astype('datetime64[ms]')

    def update_date(date):
        print("update_date")
        set_current_date(date)
        set_time_values(tempo_data.get_time_steps(date))
        picker_text_field.value_property = date
        timeseries_viewer.state.t_date = date

    def update_opacity(opacity):
        map_viewer.layers[0].state.opacity = opacity

    # Layout

    with solara.AppBar():
        solara.AppBarTitle("TEMPO Data Story")

    picker_text_field = rv.TextField(v_on="x.on", v_model=current_date, readonly=True)
    with solara.VBox():
        with solara.Row():
            with solara.Columns(widths=[8, 3]):
                ViewerLayout(map_viewer)
                SubsetControlWidget(viewer=map_viewer,
                                    data=powerplant_data,
                                    type_att=powerplant_data.id["PrimSource"],
                                    size_att=powerplant_data.id["Size_binned"])

        with solara.Row():
            rv.Menu(
                children=[
                    rv.DatePicker(v_model=current_date,
                                  on_v_model=update_date)
                ],
                v_slots=[
                    {
                        "name": "activator",
                        "variable": "x",
                        "children": [
                            picker_text_field,
                        ]
                    }
                ]
            )

        with solara.Row():
            rv.Slider(
                v_model=time_index,
                on_v_model=update_image,
                label="Time (UTC)",
                tick_labels=[],
                hide_details=True,
                dense=False,
                min=0,
                max=len(time_values) - 1,
            )
        with solara.Row():
             solara.SliderFloat(label="Opacity",
                                value=1,
                                on_value=update_opacity,
                                min=0,
                                max=1,
                                step=0.05)

        with solara.Column():
            ViewerLayout(timeseries_viewer)
