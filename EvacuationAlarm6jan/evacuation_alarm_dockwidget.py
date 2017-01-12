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
from PyQt4.QtGui import QLineEdit
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

        # start
        self.start.clicked.connect(self.loadProject)

        # fire data
        self.chemicals_yes.clicked.connect(self.print_yes)
        self.chemicals_no.clicked.connect(self.print_no)
        self.affected_buildings.clicked.connect(self.show_location)





    def print_yes(self):
        self.fire_chemicals_output.setHtml("Chemicals present")

    def print_no(self):
        self.fire_chemicals_output.setHtml("No chemicals present")

    def show_location(self):
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

#test