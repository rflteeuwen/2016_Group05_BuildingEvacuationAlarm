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
from PyQt4.QtGui import QLineEdit
import os, sys
import qgis

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

        # incident
        self.load_incident.clicked.connect(self.loadIncident)

        # location
        self.enter_location_button.clicked.connect(self.show_location)

        # fire data
        self.chemicals_yes.clicked.connect(self.print_yes)
        self.chemicals_no.clicked.connect(self.print_no)
        # self.affected_buildings.clicked.connect(self.show_location)

        self.intensityfire_input.valueChanged.connect(self.print_intensity)  # to be checked in prof code

        # calculations
        self.affected_buildings_button.clicked.connect(self.affected_buildings_calc)

        # specific building data
        self.specific_building_button.clicked.connect(self.getSpecificInformation)

    def loadIncident(self):
        random_address = self.findAddresses()

        t = (time.strftime("%H:%M:%S"))
        d = (time.strftime("%d/%m/%Y"))


        incident1 = "%s, %s: Fire at address %s causing dangerous smoke. \n" \
                    "Smoke does not contain chemicals. Fire intensity is low. \n" \
                    "Wind intensity is high and to North East direction. \n" \
                    "Decide on evacuation procedure within 15 minutes." % (str(d), str(t), str(random_address))
        incident2 = "%s, %s: Fire at address %s causing dangerous smoke. \n" \
                    "Smoke does not contain chemicals. Fire intensity is high. \n" \
                    "Wind intensity is low and to East direction. \n" \
                    "Decide on evacuation procedure within 15 minutes." % (str(d), str(t), str(random_address))
        incident3 = "%s, %s: Fire at address %s causing dangerous smoke. \n" \
                    "Smoke does contain chemicals. Fire intensity is high. \n" \
                    "Wind intensity is high and to North direction. \n" \
                    "Decide on evacuation procedure within 15 minutes." % (str(d), str(t), str(random_address))
        incident_list = [incident1, incident2, incident3]

        message = random.choice(incident_list)

        self.incident_info.setText(message)

    def findAddresses(self):
        address_list = []

        layer = self.iface.activeLayer()
        features = layer.getFeatures()
        for item in features:
            attrs = item.attributes()
            address = attrs[0]
            address_list.append(address)

        random_address = random.choice(address_list)

        return random_address


    def getSpecificInformation(self):

        layer = self.iface.activeLayer()
        selected = layer.selectedFeatures()
        name = layer.name()

        # we allow only one feature at a time to be selected and it must be in the buildings layer
        if len(selected) > 1:
            self.iface.messageBar().pushMessage("Error", "Please select only one building at a time", level=QgsMessageBar.CRITICAL, duration = 5)
        elif name != "Buildings":
            self.iface.messageBar().pushMessage("Error", "The Buildings layer was not active, please make the layer active and reselect the building", level=QgsMessageBar.CRITICAL, duration=5)
        else:

            for item in selected:
                attrs = item.attributes()

                people = attrs[22]
                function = attrs[17]

                funct_list = ["hospital", "doctors", "fire_station", "kindergarten", "nursing_home", "police", "school"]

                if function in funct_list:
                    vulnerability = "Vulnerable!"
                    policemen = int(people / 25)
                else:
                    function = "Not of particular interest"
                    vulnerability = "Not vulnerable"
                    policemen = int(people / 50)

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

    def movePlume(self,layer_name, dx, dy, fId=1):
        layer = self.getLayer(layer_name)
        layer.startEditing()
        layerUtil = QgsVectorLayerEditUtils(layer)
        result = layerUtil.translateFeature(fId, dx, dy)
        # result is 1, means translation was not succesful
        layer.commitChanges()
        layer.triggerRepaint()
        self.canvas.refresh()


        print result
        return result

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
    '''
    def getFieldValues(self, layer, fieldname, null=True, selection=False):
        attributes = []
        ids = []
        if fieldExists(layer, fieldname):
            if selection:
                features = layer.selectedFeatures()
            else:
                request = QgsFeatureRequest().setSubsetOfAttributes([getFieldIndex(layer, fieldname)])
                features = layer.getFeatures(request)
            if null:
                for feature in features:
                    attributes.append(feature.attribute(fieldname))
                    ids.append(feature.id())
            else:
                for feature in features:
                    val = feature.attribute(fieldname)
                    if val != NULL:
                        attributes.append(val)
                        ids.append(feature.id())
        return attributes, ids
    '''

    def show_location(self):
        # by selecting a building in which the fire is
        layer = self.iface.activeLayer()
        selected = layer.selectedFeatures()
        name = layer.name()

        # we allow only one feature at a time to be selected and it must be in the buildings layer
        if len(selected) > 1:
            self.iface.messageBar().pushMessage("Error", "Please select only one building at a time", level=QgsMessageBar.CRITICAL, duration = 5)
        elif name != "Buildings":
            self.iface.messageBar().pushMessage("Error", "The Buildings layer was not active, please make the layer active and reselect the building", level=QgsMessageBar.CRITICAL, duration=5)
        else:
            for building in selected:
                pt = building.geometry().centroid().asPoint()
                self.fire_location_output.setPlainText(str(pt))

    def print_yes(self):
        self.fire_chemicals_output.setHtml("Chemicals present")

    def print_no(self):
        self.fire_chemicals_output.setHtml("No chemicals present")

    def print_intensity(self):
        intensity = str(self.intensityfire_input.value())
        self.fire_intensity_output.setPlainText(intensity)

    def affected_buildings_calc(self):
        # This dictionary links the chosen inputs to the existing scenarios
        scenario_dict = {'North': {3: 'plume3'}, 'North-East': {2: 'plume1'}, 'East': {1: 'plume2'}}

        # read in the values specified by the user
        wind_direction = str(self.winddirection_input.currentText())
        wind_intensity = int(self.windintensity_input.value())
        # fire_location =


        # check which scenario is applicable
        if wind_direction in scenario_dict:
            if wind_intensity in scenario_dict[wind_direction]:
                scenario = scenario_dict[wind_direction][wind_intensity]
            else:
                self.iface.messageBar().pushMessage("Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario",level=QgsMessageBar.CRITICAL, duration=6)

        else:
            self.iface.messageBar().pushMessage("Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario",level=QgsMessageBar.CRITICAL, duration=6)

        # load the correct plume_layer
        self.loadPlume(scenario)

        # move the plume to the correct location

        self.movePlume(scenario, 10000, 10000)


        # select the correct layers
        base_layer = self.getLayer("Buildings")
        intersect_layer = self.getLayer(scenario)

        # retrieve a list of affected buildings and their information
        affected_buildings = self.getFeaturesByIntersection(base_layer, intersect_layer, True)
        number_of_affected_buildings = len(affected_buildings)

        affected_people = 0
        for building in affected_buildings:
            affected_people += int(building['people'])

        # output
        self.affected_buildings_output.setPlainText(str(number_of_affected_buildings))
        self.affected_people_output_2.setPlainText(str(affected_people))

        # call police force calculation function right away
        self.police_force_calc()

    def police_force_calc(self):

        affected_people = self.affected_people_output_2.toPlainText()
        policemen_needed = int(affected_people) / 10

        self.policemen_needed_output.setPlainText(str(policemen_needed))

        policemen_available = int(self.nr_policeman_input.text())
        if policemen_available < policemen_needed:
            self.policemen_alarm_output.setHtml("Warning: Not enough policemen available")

        else:
            self.policemen_alarm_output.setHtml("There are enough policemen available")

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
        source_dir = plugin_dir + '/sample_data/backgroundDataProject.qgs'
        shape = plugin_dir + '/sample_data/plumes/plume1.shp'

        # read project
        project = QgsProject.instance()
        project.read(QFileInfo(source_dir))

        # set Buildings layers to active layer
        layers = qgis.utils.iface.legendInterface().layers()
        QgsMapLayer = layers[0]
        qgis.utils.iface.setActiveLayer(QgsMapLayer)

        # zoom full extent
        self.canvas.zoomToFullExtent()


    def loadPlume(self, plume):
        plugin_dir = os.path.dirname(__file__)
        plume_shape = plugin_dir + '/sample_data/plumes/'+ str(plume) + '.shp'
        layer = self.iface.addVectorLayer(plume_shape, str(plume), "ogr")
        layer.setLayerTransparency(50)
        #layer.setLayerColor


    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

        # test

