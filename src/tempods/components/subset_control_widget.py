from itertools import product
from cosmicds.components.percentage_selector import SubsetState

from glue.core import ComponentID, Data
from glue.core.subset import AndState, CategorySubsetState, RangeSubsetState
from glue.viewers.common.viewer import Viewer
from numpy import size, unique
import solara
from solara.alias import rv


@solara.component
def SubsetControlWidget(viewer: Viewer, data: Data,
                        type_att: ComponentID,
                        size_att: ComponentID):

    type_options = list(unique(data[type_att]))
    size_options = ["Small", "Medium", "Large"]
    type_colors = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a"]
    layer_indices = {}
    type_selections = []
    size_selections = []

    def _indices():
        return product(range(len(type_options)), range(len(size_options)))

    def _type_state(type_index: int) -> SubsetState:
        return CategorySubsetState(type_att, [type_index])

    def _size_state(size_index: int) -> SubsetState:
        value = (size_index + 1) ** 2
        return RangeSubsetState(value, value, size_att)

    def _subset_state(type_index: int, size_index: int) -> SubsetState:
        return AndState(_type_state(type_index), _size_state(size_index))

    def _layer_index(type_index: int, size_index: int) -> int:
        return layer_indices[(type_index, size_index)]

    def _update_visibilities(type_indices: list[int], size_indices: list[int]):
        for t, s in _indices():
            viewer.layers[_layer_index(t, s)].state.visible = (t in type_indices) and (s in size_indices)

    def _type_selections_changed(selections: list[int]):
        nonlocal type_selections
        type_selections = selections
        _update_visibilities(selections, size_selections)

    def _size_selections_changed(selections: list[int]):
        nonlocal size_selections
        size_selections = selections
        _update_visibilities(type_selections, selections)

    for (type_idx, size_idx) in _indices():
       subset = data.new_subset(color=type_colors[type_idx], alpha=1)
       subset.style.markersize = (size_idx + 1) ** 2
       state = _subset_state(type_idx, size_idx)
       subset.subset_state = state
       viewer.add_subset(subset)
       index = len(viewer.layers) - 1
       layer_indices[(type_idx, size_idx)] = index

    _update_visibilities(type_selections, size_selections) 


    # Layout

    with rv.Card(flat=True, outlined=True, class_="subset-state-widget"):
        rv.CardTitle(children=["Select Power Plants to Show"])

        with rv.List():
            rv.Text(children=["Plant Type"])
            with rv.ListItemGroup(v_model=type_selections, on_v_model=_type_selections_changed, multiple=True):
                for index, option in enumerate(type_options):
                    rv.ListItem(
                        value=index,
                        color=type_colors[index],
                        children=[rv.ListItemTitle(children=[option.title()])]
                    )

        with rv.List():
            rv.Text(children=["Title"])
            with rv.ListItemGroup(v_model=size_selections, on_v_model=_size_selections_changed, multiple=True):
                for index, option in enumerate(size_options):
                    rv.ListItem(
                        value=index,
                        color="gray",
                        children=[rv.ListItemTitle(children=[option.title()])]
                    )
