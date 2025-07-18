<template>
  <v-app id="tempo-app">
    <v-app-bar
      app
      color="primary"
      dark
      clipped-right
      flat
      height="60"
    >
      <v-toolbar-title class="mr-5">
        <h2>TEMPO Data Story Prototype</h2>
      </v-toolbar-title>
      <v-spacer></v-spacer>
    </v-app-bar>
    <v-main>
      <v-content>
        <v-container fluid id="main-container">
          <v-row>
            <v-col>
              <v-row>
                <v-img id="colorbar" src="colorbar.png" height="400" width="100" max-width="100" contain />                 
                <jupyter-widget id="map-viewer" :widget="viewers.map" />
                <jupyter-widget id="powerplant-widget" :widget="extra_widgets.powerplant" class="ml-5"/>
              </v-row>
              <v-row>
                <jupyter-widget id="timeseries-viewer" :widget="viewers.timeseries" width="750px"/>
              </v-row>
            </v-col>
          </v-row>
        </v-container>
      </v-content>
    </v-main>
  </v-app>
</template>

<style>
html,
body {
  margin: 0;
  padding: 0;
  background: black;
}

.jp-Notebook,
.jp-OutputArea-output,
.jupyter-widgets,
.jp-Cell,
.jp-CodeCell,
.jp-Notebook-cell,
.jp-mod-noInput,
.jp-Cell-outputWrapper {
  margin: 0 !important;
  padding: 0 !important;
}

#rendered_cells {
  margin: 0 !important;
  padding: 0 !important;
  background-color: black !important;
}

#tempo-app {
  height: 100%;
  margin: 0;
  padding: 0;
}

#main-container {
  display: flex;
  flex-direction: row;
}

#powerplant-widget {
  width: 200px;
}

#map-viewer, #timeseries-viewer {
  width: 66%;
}

#map-viewer, #powerplant-widget, #timeseries-viewer {
  margin: 0.5em;
  padding: 0.5em;
}

#timeseries-viewer {
  margin-left: 100px;
  height: 400px;
}

.row {
  align-items: center;
}
</style>
