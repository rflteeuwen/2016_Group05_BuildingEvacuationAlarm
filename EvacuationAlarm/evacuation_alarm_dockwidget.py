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

        # start
        self.start.clicked.connect(self.loadProject)

        # location
        self.enter_location_button.clicked.connect(self.show_location)

        # fire data
        self.chemicals_yes.clicked.connect(self.print_yes)
        self.chemicals_no.clicked.connect(self.print_no)
        # self.affected_buildings.clicked.connect(self.show_location)

        self.intensityfire_input.valueChanged.connect(self.print_intensity)  # to be checked in prof code

        # calculations
        self.affected_buildings_button.clicked.connect(self.affected_buildings_calc)
        self.police_force_button.clicked.connect(self.police_force_calc)
        self.policeman_alarm_button.clicked.connect(self.police_force_alarm)

        # specific building data
        self.specific_building_button.clicked.connect(self.getSpecificInformation)

    def getSpecificInformation(self):

        layer = self.iface.activeLayer()
        selected = layer.selectedFeatures()

        # to implement: we allow only one feature at a time to be selected

        if len(selected) > 1:
            self.iface.messageBar().pushMessage("Error", "Please select only one building at a time", level=QgsMessageBar.CRITICAL, duration = 3)
        else:

            for item in selected:
                attrs = item.attributes()

                people = attrs[22]
                policemen = int(people / 10)
                function = attrs[17]

                funct_list = ["hospital", "doctors", "fire_station", "kindergarten", "nursing_home", "police", "school"]

                if function in funct_list:
                    vulnerability = "Vulnerable!"
                else:
                    function = "Not of particular interest"
                    vulnerability = "Not vulnerable"

                if policemen < 1:
                    policemen = 1

                self.no_people_output.setPlainText(str(people))
                self.vulnerability_output.setPlainText(vulnerability)
                self.policemen_needed_output_2.setPlainText(str(policemen))
                self.building_type_output.setPlainText(str(function))





    def getFeaturesByIntersection(base_layer, intersect_layer, crosses):
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

    def getFieldValues(layer, fieldname, null=True, selection=False):
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

    def show_location(self):
        location = self.location_input.text()
        self.fire_location_output.setPlainText(location)

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
                print 'Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario'
        else:
            print 'Scenario not available: selected combination of wind direction and wind intensity are not linked to a predefined scenario'

        # move the plume to the correct location



        # retrieve a list of affected buildings and their information
        base_layer = '02_smallBuildings_with_functions'
        intersect_layer = scenario
        affected_buildings = getFeaturesByIntersection(base_layer, intersect_layer, True)

        # calculate number of affected people
        list_people, list_ids = getFieldValues(base_layer, 'people')
        dictionary = dict(zip(list_ids, list_people))

        affected_people = 0
        for building in affected_buildings:
            affected_people += dictionary[building.id()]

        # output
        number_of_affected_buildings = len(affected_buildings)
        self.affected_buildings_output.setPlainText(number_of_affected_buildings)

        self.affected_people_output.setPlainText(affected_people)

    def police_force_calc(self):
        pass

    def police_force_alarm(self):
        pass

    def loadProject(self):

        # create Qt widget
        canvas = QgsMapCanvas()
        canvas.setCanvasColor(Qt.white)

        # enable this for smooth rendering
        canvas.enableAntiAliasing(True)

        # not updated US6SP10M files from ENC_ROOT
        plugin_dir = os.path.dirname(__file__)
        source_dir = plugin_dir + '/sample_data/backgroundDataProject.qgs'

        # read project
        project = QgsProject.instance()
        project.read(QFileInfo(source_dir))

        # old version: loading layers separately
        '''# canvas_layers = []
        # load vector layers
        for files in os.listdir(source_dir):

            # load only the shapefiles
            if files.endswith(".qgs"):
                vproject = QgsProject(source_dir)

                # add layer to the registry
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)


                canvas_layers.append(QgsMapCanvasLayer(vlayer))

        # refresh canvas and show it

        canvas.setLayerSet(canvas_layers)
        canvas.refresh()
        canvas.show()'''

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

        # test
