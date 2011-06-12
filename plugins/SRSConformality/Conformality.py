#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# Conformality.py
"""dicompyler plugin that calculates congruence between selected structure and an isodose line."""

import wx
from wx.xrc import XmlResource, XRCCTRL, XRCID
from wx.lib.pubsub import Publisher as pub
from matplotlib import _cntr as cntr
from matplotlib import __version__ as mplversion
import matplotlib.nxutils as nx
import numpy.ma as ma
import numpy as np
import guiutil, util

def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'Conformality'
    props['description'] = "Calculate congruence between a selected structure and an isodose line."
    props['author'] = 'Landon Clark'
    props['version'] = 0.1
    props['plugin_type'] = 'main'
    props['plugin_version'] = 1
    props['min_dicom'] = ['images']
    props['recommended_dicom'] = ['images', 'rtss', 'rtdose']

    return props

def pluginLoader(parent):
    """Function to load the plugin."""

    # Load the XRC file for our gui resources
    res = XmlResource(util.GetBasePluginsPath('Conformality.xrc'))

    panelConformality = res.LoadPanel(parent, 'pluginConformality')
    panelConformality.Init(res)

    return panelConformality

class plugin(wx.Panel):
    """Plugin to calculate congruence between selected structure and an isodose line."""

    def __init__(self):
        pre = wx.PrePanel()
        # the Create step is done by XRC.
        self.PostCreate(pre)
        

    
    def Init(self, res):
        """Method called after the panel has been initialized."""
        
        # Initialize the Conformality selector controls
        self.lblType = XRCCTRL(self, 'lblType')
        self.choiceConformalityStructure = XRCCTRL(self, 'choiceConformalityStructure')    
        self.choiceConformalityDose = XRCCTRL(self, 'choiceConformalityDose')
        self.lblConformalityIndex = XRCCTRL(self, 'lblConformalityIndex')
        self.lblUnderdoseRatio = XRCCTRL(self, 'lblUnderdoseRatio')
        self.lblOverdoseRatio = XRCCTRL(self, 'lblOverdoseRatio')
        self.lblTargetVolume = XRCCTRL(self, 'lblTargetVolume')
        self.lblCoverageVolume = XRCCTRL(self, 'lblCoverageVolume')
        self.lblIsodoseVolume = XRCCTRL(self, 'lblIsodoseVolume')
        
        # Bind ui events to the proper methods
        wx.EVT_CHOICE(self, XRCID('choiceConformalityStructure'), self.OnStructureSelect)
        wx.EVT_CHOICE(self, XRCID('choiceConformalityDose'), self.OnIsodoseCheck)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        # Initialize variables
        self.conformalitydata = {} 
        self.structureid = {}
       
        # Setup toolbar controls

        # Set up preferences
        
        # Set up pubsub
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.parsed_data')
        pub.subscribe(self.OnStructureCheck, 'colorcheckbox.checked.structure')
        pub.subscribe(self.OnStructureUncheck, 'colorcheckbox.unchecked.structure')
        
    def OnUpdatePatient(self, msg):
        """Update and load the patient data."""
        
        #print msg.data        
        if msg.data.has_key('images'):
            self.images = msg.data['images']
        if msg.data.has_key('rxdose'):
            self.rxdose = msg.data['rxdose']
        if msg.data.has_key('rtdose'):
            self.rtdose = msg.data['rtdose']
        if msg.data.has_key('structures'):
            self.structures = msg.data['structures']
        if msg.data.has_key('dose'):    
            self.dose = msg.data['dose']
        self.EnableConformality(False)
    
    def OnDestroy(self, evt):
        """Unbind to all events before the plugin is destroyed."""
        
        pub.unsubscribe(self.OnUpdatePatient)
        pub.unsubscribe(self.OnStructureCheck)
        pub.unsubscribe(self.OnIsodoseCheck)

    def OnStructureCheck(self, msg):
        """Load a list of the currently checked structures."""

        structure = msg.data

        # Get the structure number
        id = structure['data']['id']
        structure['data']['color'] = structure['color'].Get()
        self.EnableConformality(True)
        i = self.choiceConformalityStructure.Append(structure['data']['name'])
        self.choiceConformalityStructure.SetClientData(i, id)
        # Select the first structure
        self.OnStructureSelect()
        if not len(structure):
            self.EnableConformality(False)
        
    def OnStructureUncheck(self, msg):
        """Remove the unchecked structures from the list."""

        structure = msg.data

        # Get the structure number
        id = structure['data']['id']
        # Remove the structure from the structure choice box
        for n in range(self.choiceConformalityStructure.GetCount()):
            if (id == self.choiceConformalityStructure.GetClientData(n)):
                # Save if the currently selected item's position
                currSelection = self.choiceConformalityStructure.GetSelection()
                self.choiceConformalityStructure.Delete(n)
                break

        # If the currently selected item will be deleted,
        # select the last item instead
        if (n == currSelection):
            if (self.choiceConformalityStructure.GetCount() >= 1):
                self.OnStructureSelect()
        # Disable the control if it is the last item
        if (self.choiceConformalityStructure.GetCount() == 0):
            self.EnableConformality(False)
            self.OnStructureUnselect()

    def OnStructureSelect(self, evt=None):
        """Load the properties of the currently selected structure."""

        if (evt == None):
            self.choiceConformalityStructure.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        # Load the structure id chosen from the choice control
        self.structureid = self.choiceConformalityStructure.GetClientData(choiceItem)

    def OnStructureUnselect(self):
        """Clear the properties of the selected structure."""

        self.lblConformalityIndex.SetLabel('-')
        self.lblUnderdoseRatio.SetLabel('-')
        self.lblOverdoseRatio.SetLabel('-')
        self.lblCoverageVolume.SetLabel('-')

    def EnableConformality(self, value):
        """Enable or disable the constraint selector."""

        self.choiceConformalityStructure.Enable(value)
        self.choiceConformalityDose.Enable(value)

    def OnIsodoseCheck(self, evt=None):
        """When the isodose list changes, update the panel."""

        if (evt == None):
            self.choiceConformalityDose.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        isodoseID = self.choiceConformalityDose.GetSelection()
        # Here "isodoseID == 0" is the '-' in the list, from conformality.xrc file
        if isodoseID == 1:
            isodose = 100
        if isodoseID == 2:
            isodose = 90
        if isodoseID == 3:
            isodose = 80
        if isodoseID == 4:
            isodose = 70            
        if isodoseID == 5:
            isodose = 60        
        if isodoseID == 6:
            isodose = 50     
        dosedata = self.dose.GetDoseData()
        
        #set thresholds for conformality
        lowerlimit = isodose * self.rxdose / 100   
        
        structure = self.structures[self.structureid]
        PITV, CV = CalculateCI(self, self.structures[self.structureid], lowerlimit)
        TV = self.structures[self.structureid]['volume']
        
        self.lblTargetVolume.SetLabel(str(TV)[0:6])
        self.lblCoverageVolume.SetLabel(str(CV)[0:6])
        self.lblIsodoseVolume.SetLabel(str(PITV))
        self.lblConformalityIndex.SetLabel(str(CV*CV/(TV*PITV)*100)[0:5])
        self.lblUnderdoseRatio.SetLabel(str(CV/(TV)*100)[0:5])
        self.lblOverdoseRatio.SetLabel(str(CV/(PITV)*100)[0:5])
        
def CalculateCI(self, structure, lowerlimit):
    """From a selected structure and isodose line, return conformality index."""
    # Read "A simple scoring ratio to index the conformity of radiosurgical
    #treatment plans" by Ian Paddick.
    #J Neurosurg (Suppl 3) 93:219-222, 2000

    sPlanes = structure['planes']
    
    # Get the dose to pixel LUT
    doselut = self.dose.GetPatientToPixelLUT()

    # Generate a 2d mesh grid to create a polygon mask in dose coordinates
    # Code taken from Stack Overflow Answer from Joe Kington:
    # http://stackoverflow.com/questions/3654289/scipy-create-2d-polygon-mask/3655582
    # Create vertex coordinates for each grid cell
    x, y = np.meshgrid(np.array(doselut[0]), np.array(doselut[1]))
    x, y = x.flatten(), y.flatten()
    dosegridpoints = np.vstack((x,y)).T

    # Get the dose and image data information
    dd = self.dose.GetDoseData()
    id = self.dose.GetImageData()

    # Create an empty array of bins to store the histogram in cGy
    # only if the structure has contour data
    if len(sPlanes):
        maxdose = int(dd['dosemax'] * dd['dosegridscaling'] * 100)
    PITV = 0   #Rx isodose volume in cc
    CV = 0    #coverage volume

    # Iterate over each plane in the structure
    for z, sPlane in sPlanes.iteritems():

        # Get the contours with calculated areas and the largest contour index
        contours, largestIndex = calculate_contour_areas(sPlane)

        # Get the dose plane for the current structure plane
        doseplane = self.dose.GetDoseGrid(z)* dd['dosegridscaling'] * 100

        # If there is no dose for the current plane, go to the next plane
        if not len(doseplane):
            break

        # Calculate the histogram for each contour
        for i, contour in enumerate(contours):
            m = get_contour_mask(doselut, dosegridpoints, contour['data'])
            PITV_vol, CV_vol = calculate_volume(m, doseplane, lowerlimit,
                                           dd, id, structure)
            PITV = PITV + PITV_vol
            CV = CV + CV_vol

    # Volume units are given in cm^3
    PITV = PITV/1000
    CV = CV/1000
    return PITV, CV

def calculate_contour_areas(plane):
    """Calculate the area of each contour for the given plane.
       Additionally calculate and return the largest contour index."""

    # Calculate the area for each contour in the current plane
    contours = []
    largest = 0
    largestIndex = 0
    for c, contour in enumerate(plane):
        # Create arrays for the x,y coordinate pair for the triangulation
        x = []
        y = []
        for point in contour['contourData']:
            x.append(point[0])
            y.append(point[1])

        cArea = 0
        # Calculate the area based on the Surveyor's formula
        for i in range(0, len(x)-1):
            cArea = cArea + x[i]*y[i+1] - x[i+1]*y[i]
        cArea = abs(cArea / 2)
        # Remove the z coordinate from the xyz point tuple
        data = map(lambda x: x[0:2], contour['contourData'])
        # Add the contour area and points to the list of contours
        contours.append({'area':cArea, 'data':data})

        # Determine which contour is the largest
        if (cArea > largest):
            largest = cArea
            largestIndex = c

    return contours, largestIndex

def get_contour_mask(doselut, dosegridpoints, contour):
    """Get the mask for the contour with respect to the dose plane."""

    grid = nx.points_inside_poly(dosegridpoints, contour)
    grid = grid.reshape((len(doselut[1]), len(doselut[0])))

    return grid

def calculate_volume(mask, doseplane, lowerlimit, dd, id, structure):
    """Calculate the differential DVH for the given contour and dose plane."""

    # Multiply the structure mask by the dose plane to get the dose mask
    mask = ma.array(doseplane, mask=~mask)

    # Calculate the volume for the contour for the given dose plane
    PITV_vol = np.sum(doseplane>lowerlimit) * ((id['pixelspacing'][0]) *
                      (id['pixelspacing'][1]) *
                      (structure['thickness']))
    CV_vol = np.sum(mask>lowerlimit) * ((id['pixelspacing'][0]) *
                      (id['pixelspacing'][1]) *
                      (structure['thickness']))
    return PITV_vol, CV_vol
