import solara



# Will work with current cosmicds layout
# from cosmicds.layout import BaseLayout
# @solara.component
# def Layout(children=[]):
#     # Note that children being passed here for this example will be a Page() element.
#     route_current, routes_all = solara.use_route()
#     return BaseLayout(None, children=children, story_name="TEMPO")


# Solara docs example layout
# @solara.component
# def Layout(children=[]):
    # Note that children being passed here for this example will be a Page() element.
    # route_current, routes_all = solara.use_route()
    # with solara.Column():
        # put all buttons in a single row
        # with solara.Row():
        #     for route in routes_all:
        #         with solara.Link(route):
        #             solara.Button(route.path, color="red" if route_current == route else None)
        # under the navigation buttons, we add our children (the single Page())
        # solara.Column(children=children)
    
    


# the no-layout layout
# @solara.component
# def Layout(children=[]):
#     # there will only be 1 child, which is the Page()
#     return children[0]


@solara.component
def Layout(children):
    route, routes = solara.use_route()
    dark_effective = solara.lab.use_dark_effective()
    with solara.AppLayout(toolbar_dark=dark_effective, color=None):
        with solara.AppBar():
            solara.AppBarTitle("TEMPO Data Viewer")
            solara.lab.ThemeToggle()
        with solara.Column():
            # Add the main content area
            solara.Column(children=children)

