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

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal
from qgis.core import *
from qgis.gui import *
from PyQt4.QtCore import *
from PyQt4 import QtGui
import os, sys
import qgis

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

        # test
        self.chemicals_yes.clicked.connect(self.print_yes)
        self.chemicals_no.clicked.connect(self.print_no)
        self.start.clicked.connect(self.loadLayers)

    def print_yes(self):
        print 'chemicals'

    def print_no(self):
        print 'no chemicals'

    def loadLayers(self):


        # create Qt widget
        canvas = QgsMapCanvas()
        canvas.setCanvasColor(Qt.white)

        # enable this for smooth rendering
        canvas.enableAntiAliasing(True)

        # not updated US6SP10M files from ENC_ROOT
        source_dir = "C:\sample_data"

        canvas_layers = []

        # load vector layers
        for files in os.listdir(source_dir):

            # load only the shapefiles
            if files.endswith(".shp"):
                vlayer = QgsVectorLayer(source_dir + "/" + files, files, "ogr")

                # add layer to the registry
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)

                # set extent to the extent of our layer

                canvas_layers.append(QgsMapCanvasLayer(vlayer))

        # refresh canvas and show it

        canvas.setLayerSet(canvas_layers)
        canvas.refresh()
        canvas.show()




    #######
    #   Data functions
    #######
    def openScenario(self, filename=""):
        scenario_open = False
        scenario_file = os.path.join(u'/Users/jorge/github/GEO1005', 'sample_data', 'time_test.qgs')
        # check if file exists
        if os.path.isfile(scenario_file):
            self.iface.addProject(scenario_file)
            scenario_open = True
        else:
            last_dir = uf.getLastDir("SDSS")
            new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
            if new_file:
                self.iface.addProject(unicode(new_file))
                scenario_open = True
        if scenario_open:
            self.updateLayers()

    def saveScenario(self):
        self.iface.actionSaveProject()

    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
        else:
            self.selectAttributeCombo.clear()
            self.clearChart()

    def setSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface, layer_name)
        self.updateAttributes(layer)

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface, layer_name)
        return layer

    def updateAttributes(self, layer):
        self.selectAttributeCombo.clear()
        if layer:
            self.clearReport()
            self.clearChart()
            fields = uf.getFieldNames(layer)
            if fields:
                self.selectAttributeCombo.addItems(fields)
                self.setSelectedAttribute()
                # send list to the report list window
                self.updateReport(fields)

    def setSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        self.updateAttribute.emit(field_name)

    def getSelectedAttribute(self):
        field_name = self.selectAttributeCombo.currentText()
        return field_name

    def startCounter(self):
        # prepare the thread of the timed even or long loop
        self.timerThread = TimedEvent(self.iface.mainWindow(), self, 'default')
        self.timerThread.timerFinished.connect(self.concludeCounter)
        self.timerThread.timerProgress.connect(self.updateCounter)
        self.timerThread.timerError.connect(self.cancelCounter)
        self.timerThread.start()
        # from here the timer is running in the background on a separate thread. user can continue working on QGIS.
        self.counterProgressBar.setValue(0)
        self.startCounterButton.setDisabled(True)
        self.cancelCounterButton.setDisabled(False)

    def cancelCounter(self):
        # triggered if the user clicks the cancel button
        self.timerThread.stop()
        self.counterProgressBar.setValue(0)
        self.counterProgressBar.setRange(0, 100)
        try:
            self.timerThread.timerFinished.disconnect(self.concludeCounter)
            self.timerThread.timerProgress.disconnect(self.updateCounter)
            self.timerThread.timerError.disconnect(self.cancelCounter)
        except:
            pass
        self.timerThread = None
        self.startCounterButton.setDisabled(False)
        self.cancelCounterButton.setDisabled(True)

    def updateCounter(self, value):
        self.counterProgressBar.setValue(value)

    def concludeCounter(self, result):
        # clean up timer thread stuff
        self.timerThread.stop()
        self.counterProgressBar.setValue(100)
        try:
            self.timerThread.timerFinished.disconnect(self.concludeCounter)
            self.timerThread.timerProgress.disconnect(self.updateCounter)
            self.timerThread.timerError.disconnect(self.cancelCounter)
        except:
            pass
        self.timerThread = None
        self.startCounterButton.setDisabled(False)
        self.cancelCounterButton.setDisabled(True)
        # do something with the results
        self.iface.messageBar().pushMessage("Infor", "The counter results: %s" % result, level=0, duration=5)


    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

#test