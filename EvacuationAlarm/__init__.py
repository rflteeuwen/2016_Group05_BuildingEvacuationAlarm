# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EvacuationAlarm
                                 A QGIS plugin
 This plugin helps policemen in deciding on which buildings to evacuate in case of smoke caused by fire
                             -------------------
        begin                : 2016-12-14
        copyright            : (C) 2016 by TUDelft
        email                : rflteeuwen@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load EvacuationAlarm class from file EvacuationAlarm.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .evacuation_alarm import EvacuationAlarm
    return EvacuationAlarm(iface)
