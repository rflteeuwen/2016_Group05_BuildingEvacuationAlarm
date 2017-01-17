# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EvacuationAlarmDockWidget
                                 A QGIS plugin
 This plugin helps policemen to decide on which buildings to evacuate in case of smoke caused by fire
                             -------------------
        begin                : 2016-12-14
        git sha              : $Format:%H$
        copyright            : (C) 2016 by TU Delft Geomatics
        email                : rflteeuwen@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import random
import time

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import pyqtSignal
from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import QLineEdit, QColor
import os, sys
import qgis
import webbrowser

from qgis.networkanalysis import *
from pyspatialite import dbapi2 as sqlite
import psycopg2 as pgsql
import numpy as np
import math
import os.path


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'evacuation_alarm_dockwidget_base.ui'))


class EvacuationAlarmDockWidget(QtGui.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(EvacuationAlarmDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # initialization
        self.loadProject()
        self.wiki_button.clicked.connect(self.openinBrowser)

        # incident
        self.load_incident.clicked.connect(self.loadIncident)

        # calculations
        self.affected_buildings_button.clicked.connect(self.affected_buildings_calc)
        self.affected_list = []

        # specific building data
        self.canvas.selectionChanged.connect(self.getSpecificInformation)

        # log and close
        self.log_close.clicked.connect(self.logOutcomes)



    def loadIncident(self):
        random_address = self.findAddresses()

        future_5 = time.time() + 300
        future_10 = time.time() + 600
        future_15 = time.time() + 900

        incident1 = "%s : Fire at address %s causing dangerous smoke. \n" \
                    "Fire intensity is low. Smoke does not contain chemicals. \n" \
                    "Wind blows to the North-East with medium intensity. \n" \
                    "Decide on evacuation procedure before %s (within 15 minutes)." % (time.ctime(), str(random_address), time.ctime(future_15))
        incident2 = "%s : Fire at address %s causing dangerous smoke. \n" \
                    "Fire intensity is medium. Smoke does not contain chemicals. \n" \
                    "Wind blows to the East with low intensity. \n" \
                    "Decide on evacuation procedure before %s (within 10 minutes)." % (time.ctime(), str(random_address), time.ctime(future_10))
        incident3 = "%s : Fire at address %s causing dangerous smoke. \n" \
                    "Fire intensity is high. Smoke does contain chemicals. \n" \
                    "Wind blows to the North with high intensity. \n" \
                    "Decide on evacuation procedure before %s (within 5 minutes)." % (time.ctime(), str(random_address), time.ctime(future_5))
        incident_list = [incident1, incident2, incident3]

        message = random.choice(incident_list)

        self.incident_info.setText(message)


    def findAddresses(self):
        address_list = []
        name = "Buildings"
        layer = self.getLayer(name)
        features = layer.getFeatures()
        for item in features:
            attrs = item.attributes()
            address = attrs[0]
            address_list.append(address)

        random_address = random.choice(address_list)

        return random_address


    def openinBrowser(self):
        webbrowser.open('https://github.com/rflteeuwen/2016_Group05_BuildingEvacuationAlarm/wiki', new=2)


    def deselectAll(self):
        for a in self.iface.attributesToolBar().actions():
            if a.objectName() == 'mActionDeselectAll':
                a.trigger()
                break


    def getSpecificInformation(self):

        layer = self.iface.activeLayer()
        check_layer = self.getLayer("subset_buildings")
        selected = layer.selectedFeatures()

        if len(selected) > 1:
            self.iface.messageBar().pushMessage(
                "Please select only one building",
                level=QgsMessageBar.INFO, duration=5)
            self.deselectAll()
        elif (layer != check_layer) and self.getLayer("subset_buildings"):
            self.iface.messageBar().pushMessage(
                "Please make the subset_buildings layer active again and select from there",
                level=QgsMessageBar.INFO, duration=5)
            self.deselectAll()
        else:

            for item in selected:
                attrs = item.attributes()

                people = attrs[5]
                function = attrs[1]

                funct_list = ["hospital", "doctors", "fire_station", "kindergarten", "nursing_home", "police", "school"]

                if function in funct_list:
                    vulnerability = "Vulnerable!"
                    policemen = people / 30
                else:
                    function = "Not of particular interest"
                    vulnerability = "Not vulnerable"
                    policemen = people / 120

                if policemen < 1:
                    policemen = 1

                self.no_people_output.setPlainText(str(people))
                self.vulnerability_output.setPlainText(vulnerability)
                self.policemen_needed_output_2.setPlainText(str(policemen))
                self.building_type_output.setPlainText(str(function))


    def getLayer(self, name):
        layer = None
        #for lyr in QgsMapLayerRegistry.instance().mapLayers().values():
        for lyr in self.iface.legendInterface().layers():
            if lyr.name() == name:
                layer = lyr
                break
        return layer


    def movePlume(self, layer_name, dx, dy):
        layer = self.getLayer(layer_name)
        features = layer.getFeatures()
        for item in features:
            id = item.id()
        fId = id

        layer.startEditing()
        layerUtil = QgsVectorLayerEditUtils(layer)
        result = layerUtil.translateFeature(fId, dx, dy)
        layer.commitChanges()
        layer.triggerRepaint()
        self.canvas.refresh()


    def getFeaturesByIntersection(self, base_layer, intersect_layer, crosses):
        features = []
        # retrieve objects to be intersected (list comprehension, more pythonic)
        intersect_geom = [QgsGeometry(feat.geometry()) for feat in intersect_layer.getFeatures()]
        # retrieve base layer objects
        base = base_layer.getFeatures()
        # should improve with spatial index for large data sets
        # index = createIndex(base_layer)
        # loop through base features and intersecting elements
        # appends if intersecting, when crosses = True
        # does the opposite if crosses = False
        for feat in base:
            append = not crosses
            base_geom = feat.geometry()
            for intersect in intersect_geom:
                if base_geom.intersects(intersect):
                    append = crosses
                    break
            if append:
                features.append(feat)
        return features


    def deleteOldLayers(self):
        unwanted = ["plume1", "plume2", "plume3", "subset_buildings"]
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if layer.name() in unwanted:
                QgsMapLayerRegistry.instance().removeMapLayer(layer.id())


    def make_extra_layer(self,feature_list):

        # create new temporary layer
        vl = QgsVectorLayer("Polygon?crs=epsg:28992", "subset_buildings", "memory")
        pr = vl.dataProvider()
        vl.setLayerTransparency(50)
            
        # Enter editing mode
        vl.startEditing()

        # Add fields
        pr.addAttributes([QgsField("gid", QVariant.Int), QgsField("fclass", QVariant.String), QgsField("heightmedi", QVariant.Double), QgsField("stories", QVariant.Int), QgsField("floorarea", QVariant.Int), QgsField("people", QVariant.Int)])

        # Commit changes
        vl.commitChanges()

        # Add features
        pr.addFeatures(feature_list)

        # update layer's extent when new features have been added
        # because change of extent in provider is not propagated to the layer
        vl.updateExtents()

        # add layer to the legend
        QgsMapLayerRegistry.instance().addMapLayer(vl)

        # color layer
        layer = self.getLayer("subset_buildings")
        symbols = layer.rendererV2().symbols()
        symbol = symbols[0]
        symbol.setColor(QtGui.QColor.fromRgb(255,51,51))

        # Refresh both canvas and layer symbology (color)
        qgis.utils.iface.mapCanvas().refresh()
        qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)

        # make regular buildings layer active again
        QgsMapLayer = self.getLayer("subset_buildings")
        qgis.utils.iface.setActiveLayer(QgsMapLayer)


    def buildingLocation(self):
        name = "Buildings"
        address = self.address_input.toPlainText()
        layer = self.getLayer(name)
        features = layer.getFeatures()

        pt = 0
        for item in features:
            attrs = item.attributes()
            if str(attrs[0]) == str(address):
                pt = item.geometry().centroid().asPoint()
                self.fire_location_output.setPlainText(str(pt))
        return pt


    def currentLocation(self, scenario):
        layer = self.getLayer(scenario)
        features = layer.getFeatures()

        for item in features:
            geom = item.geometry()
            x = geom.asPolygon()
            pt = x[0][0]
            return pt


    def affected_buildings_calc(self):
        # This dictionary links the chosen inputs to the existing scenarios
        
        scenario_dict = {'North': {3: 'plume3'}, 'North-East': {2: 'plume1'}, 'East': {1: 'plume2'}}

        # read in the values specified by the user
        wind_direction = str(self.winddirection_input.currentText())
        wind_intensity = int(self.windintensity_input.value())

        # check which scenario is applicable
        if wind_direction in scenario_dict:
            if wind_intensity in scenario_dict[wind_direction]:
                scenario = scenario_dict[wind_direction][wind_intensity]
            else:
                self.iface.messageBar().pushMessage("Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario",level=QgsMessageBar.INFO, duration=5)
                return
        else:
            self.iface.messageBar().pushMessage("Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario",level=QgsMessageBar.INFO, duration=5)
            return
        # load the correct plume_layer
        self.loadPlume(scenario)

        # define dx and dy to move
        current = self.currentLocation(scenario)
        next = self.buildingLocation()
        if next == 0:
            print "hi"
            self.iface.messageBar().pushMessage(
                "This address could not be recognized, please change it",
                level=QgsMessageBar.INFO, duration=5)
            self.deleteOldLayers()
            return
        x0 = current[0]
        x1 = next[0]
        y0 = current[1]
        y1 = next[1]
        dx = x1 - x0
        dy = y1 - y0
        # move the plume to the correct location
        self.movePlume(scenario, dx, dy)

        # select the correct layers
        base_layer = self.getLayer("Buildings")
        intersect_layer = self.getLayer(scenario)

        # retrieve a list of affected buildings and their information
        affected_buildings = self.getFeaturesByIntersection(base_layer, intersect_layer, True)
        number_of_affected_buildings = len(affected_buildings)
        self.affected_list.append(affected_buildings)
        
        # create a new layer only containing the affected buildings
        self.make_extra_layer(affected_buildings)

        affected_people = 0
        for building in affected_buildings:
            affected_people += int(building['people'])

        # output
        self.affected_buildings_output.setPlainText(str(number_of_affected_buildings))
        self.affected_people_output_2.setPlainText(str(affected_people))

        # call police force calculation function right away
        self.police_force_calc(scenario, affected_people)


    def police_force_calc(self, scenario, affected_people):

        #affected_people = self.affected_people_output_2.toPlainText()

        if scenario == "plume1":
            policemen_needed = affected_people / 240
        elif scenario == "plume2":
            policemen_needed = affected_people / 120
        else:
            policemen_needed = int(affected_people) / 60

        if policemen_needed < 2:
            policemen_needed = 2
        self.policemen_needed_output.setPlainText(str(policemen_needed))

        policemen_available = int(self.nr_policeman_input.text())
        if policemen_available < policemen_needed:
            self.policemen_alarm_output.setHtml("WARNING: Not enough policemen available")
        else:
            self.policemen_alarm_output.setHtml("Enough policemen available")


    def loadProject(self):

        # empty the canvas
        QgsMapLayerRegistry.instance().removeAllMapLayers()

        # create Qt widget
        canvas = QgsMapCanvas()
        canvas.setCanvasColor(Qt.white)

        # enable this for smooth rendering
        canvas.enableAntiAliasing(True)

        # not updated US6SP10M files from ENC_ROOT
        plugin_dir = os.path.dirname(__file__)
        source_dir = plugin_dir + '/sample_data/finalProject.qgs'
        shape = plugin_dir + '/sample_data/plumes/plume1.shp'

        # read project
        project = QgsProject.instance()
        project.read(QFileInfo(source_dir))

        # set Buildings layers to active layer
        layers = qgis.utils.iface.legendInterface().layers()
        layer = self.getLayer("Buildings")
        qgis.utils.iface.setActiveLayer(layer)

        # zoom full extent
        self.canvas.zoomToFullExtent()


    def loadPlume(self, plume):

        if self.getLayer("subset_buildings"):
            self.deleteOldLayers()

        plugin_dir = os.path.dirname(__file__)
        plume_shape = plugin_dir + '/sample_data/plumes/'+ str(plume) + '.shp'
        layer = self.iface.addVectorLayer(plume_shape, str(plume), "ogr")

        # Color plume grey
        symbols = layer.rendererV2().symbols()
        symbol = symbols[0]
        symbol.setColor(QtGui.QColor.fromRgb(105,105,105))
        layer.setLayerTransparency(50)

        # Refrest canvas and layer symbology (color)
        qgis.utils.iface.mapCanvas().refresh()
        qgis.utils.iface.legendInterface().refreshLayerSymbology(layer)


    def logOutcomes(self):
        log_t = (time.strftime("%H.%M.%S"))
        log_d = (time.strftime("%d.%m.%Y"))

        plugin_dir = os.path.dirname(__file__)
        folder_dir = plugin_dir + "/log_files/"
        name  = "log_%s_%s.csv" % (log_d, log_t)
        file_dir = folder_dir + name

        header1 = "This log file was created on date %s at time %s \n \n" % (log_d, log_t)
        message = "Incident message: \n" + self.incident_info.toPlainText() + "\n \n"
        header2 = "The plugin calculated the following evacuation information: \n"
        fire_coords = "The fire is in building with coordinates: " + self.fire_location_output.toPlainText() + "\n"
        affected_buildings = "The number of buildings affected by smoke is: " + self.affected_buildings_output.toPlainText() + "\n"
        affected_people = "The estimated number of people in these buildings is: " + self.affected_people_output_2.toPlainText() + "\n"
        policemen = "The number of policemen needed to evacuate these people is: " + self.policemen_needed_output.toPlainText() + "\n"
        alarm = self.policemen_alarm_output.toPlainText() + "\n \n"
        header3 = "The affected buildings are the buildings with addresses: \n"

        log_text = header1 + message + header2 + fire_coords + affected_buildings + affected_people + policemen + alarm + header3

        f = open(file_dir, 'wt')
        f.write(log_text)
        f.close()

        f = open(file_dir, 'a')
        affected = self.affected_list[0]
        for item in affected:
            attrs = item.attributes()
            gid = (str(attrs[0]) + "\n")
            f.write(gid)
        f.close

        self.iface.messageBar().pushMessage(
            "A log file was created in your plugin directory 'log_files' (For Windows users C:\Users\username\.qgis2\python\plugins\EvacuationAlarm, for MAC users Macintosh/HD\Users\username\.qgis2\python\plugins\EvacuationAlarm). You can now load a new project or close the plugin.",
            level=QgsMessageBar.SUCCESS)

        self.refreshPlugin()


    def refreshPlugin(self):
        # reload canvas to start situation
        self.loadProject()

        # clear input fields
        self.nr_policeman_input.clear()
        self.address_input.clear()
        self.intensityfire_input.clear()
        self.windintensity_input.clear()

        # clear output fields
        self.incident_info.clear()
        self.fire_location_output.clear()
        self.affected_buildings_output.clear()
        self.affected_people_output_2.clear()
        self.policemen_needed_output.clear()
        self.policemen_alarm_output.clear()
        self.no_people_output.clear()
        self.vulnerability_output.clear()
        self.policemen_needed_output_2.clear()
        self.building_type_output.clear()


    def closeEvent(self, event):

        # empty the canvas
        QgsMapLayerRegistry.instance().removeAllMapLayers()

        self.closingPlugin.emit()
        event.accept()

        # test

