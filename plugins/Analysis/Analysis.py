#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# Analysis.py
"""dicompyler plugin that calculates congruence between selected structure and an isodose line."""

import os.path, threading
import wx
from wx.xrc import XmlResource, XRCCTRL, XRCID
from wx.lib.pubsub import Publisher as pub
#from matplotlib import _cntr as cntr
#from matplotlib import __version__ as mplversion
#import matplotlib.nxutils as nx
#import numpy.ma as ma
#import numpy as np
#from dicompyler import guiutil, util
import xlrd
from dicompyler import dvhdata, dvhcalc
#from dicompyler.dicomparser import DicomParser as dp
global tolerances


def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'SRT DVH Analysis'
    props['description'] = "Analyzes DVH parameters according to TG-101 protocol"
    props['author'] = 'Landon Clark'
    props['version'] = 0.1
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = ['rtss', 'rtdose']
    props['recommended_dicom'] = ['rtss', 'rtdose', 'rtss', 'images']

    return props

class plugin:
    """Analyzes DVH."""

    def __init__(self, parent):

        self.parent = parent
        
        # Set up pubsub
        #pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.parsed_data')     

        # Load the XRC file for our gui resources
        xrc = os.path.join(os.path.dirname(__file__), 'Analysis.xrc')
        self.res = XmlResource(xrc)

    def OnUpdatePatient(self, msg):
        """Update and load the patient data."""

        self.data = msg.data
    
    def pluginMenu(self, evt):
        """Method called after the panel has been initialized."""

        panelAnalysis = self.res.LoadDialog(self.parent, "AnalysisPanel")
        panelAnalysis.SetTitle("TG-101 Stereotactic Plan Analysis")
        panelAnalysis.Init(self.data['structures'], self.data['dvhs'])
        panelAnalysis.ShowModal()
        

        #self.tools.append({'label':"Tracker", 'bmp':trackerbmp, 'shortHelp':"Send to Tracker", 'eventhandler':self.SendToTracker})
        #self.tools.append({'label':"Report", 'bmp':reportbmp, 'shortHelp':"Print out a report", 'eventhandler':self.PrintReport})
        
        # Set up preferences
        
        # Set up pubsub
        #pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.parsed_data') 
        
        return panelAnalysis
         
          
    def OnDestroy(self, evt):
        """Unbind to all events before the plugin is destroyed."""
        
        pub.unsubscribe(self.OnUpdatePatient)

class AnalysisPanel(wx.Dialog):
    """Panel that shows DVH and constraint value comparisons."""    
    
    def __init__(self):
        pre = wx.PreDialog()
        # the Create step is done by XRC.
        self.PostCreate(pre)
        
    def Init(self, structures, dvhs):
        """Method called after panel has ben initialized."""
        
        # Initialize variables
        self.dvhs = {} # raw dvhs from initial DICOM data
        self.dvhdata = {} # dict of dvh constraint functions
        self.structures = structures
        self.dvhs = dvhs
       
        # Setup toolbar controls
        #trackerbmp = wx.Bitmap(util.GetResourcePath('tracker.png'))
        #reportbmp = wx.Bitmap(util.GetResourcePath('report.png'))
        #drawingstyles = ['Solid', 'Transparent', 'Dot', 'Dash', 'Dot Dash']
        self.tools = []
        
        # Initialize the Analysis fractionation control and labels
        self.lblFractions = XRCCTRL(self, 'lblFractions')
        self.choiceFractions = XRCCTRL(self, 'choiceFractions')    
        self.lblDVHStructures = XRCCTRL(self, 'lblDVHStructures')
        self.lblDVHStructureID = XRCCTRL(self, 'lblDVHStructureID')        
        self.lblDVHVolume = XRCCTRL(self, 'lblDVHVolume')  
        self.lblDVHLimit = XRCCTRL(self, 'lblDVHLimit')
        self.lblDVHPlan = XRCCTRL(self, 'lblDVHPlan')
        
        # Predefined organs from TG-101
        self.lblOptic = XRCCTRL(self, 'lblOptic')
        self.lblOptic = XRCCTRL(self, 'lblOptic')
        self.lblCochlea = XRCCTRL(self, 'lblCochlea')
        self.lblBrainstem = XRCCTRL(self, 'lblBrainstem')
        self.lblSpinal1 = XRCCTRL(self, 'lblSpinal1')
        self.lblSpinal2 = XRCCTRL(self, 'lblSpinal2')
        self.lblCauda = XRCCTRL(self, 'lblCauda')
        self.lblSacral = XRCCTRL(self, 'lblSacral')
        self.lblEsophagus = XRCCTRL(self, 'lblEsophagus')
        self.lblBrachial = XRCCTRL(self, 'lblBrachial')        
        self.lblHeart = XRCCTRL(self, 'lblHeart')        
        self.lblGreatVessels = XRCCTRL(self, 'lblGreatVessels')   
        self.lblTrachea = XRCCTRL(self, 'lblTrachea')
        self.lblSmallerBronchus = XRCCTRL(self, 'lblSmallerBronchus')
        self.lblRib = XRCCTRL(self, 'lblRib')
        self.lblSkin = XRCCTRL(self, 'lblSkin')
        self.lblStomach = XRCCTRL(self, 'lblStomach')
        self.lblBowel = XRCCTRL(self, 'lblBowel')
        self.lblRenalHilum = XRCCTRL(self, 'lblRenalHilum')
        self.lblLung1 = XRCCTRL(self, 'lblLung1')
        self.lblLung2 = XRCCTRL(self, 'lblLung2')
        self.lblLiver = XRCCTRL(self, 'lblLiver')
        self.lblRenalCortex =   XRCCTRL(self, 'lblRenalCortex')      
    
        # Structures from plan
        self.choiceOptic = XRCCTRL(self, 'choiceOptic')
        self.choiceCochlea = XRCCTRL(self, 'choiceCochlea')
        self.choiceBrainstem = XRCCTRL(self, 'choiceBrainstem')
        self.choiceSpinal = XRCCTRL(self, 'choiceSpinal')
        self.choiceCauda = XRCCTRL(self, 'choiceCauda')
        self.choiceSacral = XRCCTRL(self, 'choiceSacral')
        self.choiceEsophagus = XRCCTRL(self, 'choiceEsophagus')
        self.choiceBrachial = XRCCTRL(self, 'choiceBrachial')        
        self.choiceHeart = XRCCTRL(self, 'choiceHeart')        
        self.choiceGreatVessels = XRCCTRL(self, 'choiceGreatVessels')   
        self.choiceTrachea = XRCCTRL(self, 'choiceTrachea')
        self.choiceSmallBronchus = XRCCTRL(self, 'choiceSmallBronchus')
        self.choiceRib = XRCCTRL(self, 'choiceRib')
        self.choiceSkin = XRCCTRL(self, 'choiceSkin')
        self.choiceStomach = XRCCTRL(self, 'choiceStomach')
        self.choiceBowel = XRCCTRL(self, 'choiceBowel')
        self.choiceRenalHilum = XRCCTRL(self, 'choiceRenalHilum') 
        self.choiceLungs = XRCCTRL(self, 'choiceLungs')
        self.choiceLiver = XRCCTRL(self, 'choiceLiver')
        self.choiceRenalCortex = XRCCTRL(self, 'choiceRenalCortex')
        
        # Volumes defined per fraction/Organ
        self.volOptic = XRCCTRL(self, 'volOptic')
        self.volCochlea = XRCCTRL(self, 'volCochlea')
        self.volBrainstem = XRCCTRL(self, 'volBrainstem')
        self.volSpinal1 = XRCCTRL(self, 'volSpinal1')
        self.volSpinal2 = XRCCTRL(self, 'volSpinal2')
        self.volCauda = XRCCTRL(self, 'volCauda')
        self.volSacral = XRCCTRL(self, 'volSacral')
        self.volEsophagus = XRCCTRL(self, 'volEsophagus')
        self.volBrachial = XRCCTRL(self, 'volBrachial')        
        self.volHeart = XRCCTRL(self, 'volHeart')        
        self.volGreatVessels = XRCCTRL(self, 'volGreatVessels')   
        self.volTrachea = XRCCTRL(self, 'volTrachea')
        self.volSmallBronchus = XRCCTRL(self, 'volSmallBronchus')
        self.volRib = XRCCTRL(self, 'volRib')
        self.volSkin = XRCCTRL(self, 'volSkin')
        self.volStomach = XRCCTRL(self, 'volStomach')
        self.volBowel = XRCCTRL(self, 'volBowel')
        self.volRenalHilum = XRCCTRL(self, 'volRenalHilum')   
        
        # Doses defined per fraction/Organ (Critical Volume/Threshold organs)
        self.thresholdLungs1 = XRCCTRL(self, 'thresholdLungs1')
        self.thresholdLungs2 = XRCCTRL(self, 'thresholdLungs2')
        self.thresholdLiver = XRCCTRL(self, 'thresholdLiver')
        self.thresholdRenalCortex = XRCCTRL(self, 'thresholdRenalCortex')        
        
        # Dose limits (in cGy) for each organ/fractionation
        self.limitOptic = XRCCTRL(self, 'limitOptic')
        self.limitCochlea = XRCCTRL(self, 'limitCochlea')
        self.limitBrainstem = XRCCTRL(self, 'limitBrainstem')
        self.limitSpinal1 = XRCCTRL(self, 'limitSpinal1')
        self.limitSpinal2 = XRCCTRL(self, 'limitSpinal2')
        self.limitCauda = XRCCTRL(self, 'limitCauda')
        self.limitSacral = XRCCTRL(self, 'limitSacral')
        self.limitEsophagus = XRCCTRL(self, 'limitEsophagus')
        self.limitBrachial = XRCCTRL(self, 'limitBrachial')        
        self.limitHeart = XRCCTRL(self, 'limitHeart')        
        self.limitGreatVessels = XRCCTRL(self, 'limitGreatVessels')   
        self.limitTrachea = XRCCTRL(self, 'limitTrachea')
        self.limitSmallBronchus = XRCCTRL(self, 'limitSmallBronchus')
        self.limitRib = XRCCTRL(self, 'limitRib')
        self.limitSkin = XRCCTRL(self, 'limitSkin')
        self.limitStomach = XRCCTRL(self, 'limitStomach')
        self.limitBowel = XRCCTRL(self, 'limitBowel')
        self.limitRenalHilum = XRCCTRL(self, 'limitRenalHilum')       
        self.limitLungs1 = XRCCTRL(self, 'limitLungs1')
        self.limitLungs2 = XRCCTRL(self, 'limitLungs2')
        self.limitLiver = XRCCTRL(self, 'limitLiver')
        self.limitRenalCortex = XRCCTRL(self, 'limitRenalCortex')
        
        # Dose values obtained from plan in Dicompyler
        self.planOptic = XRCCTRL(self, 'planOptic')
        self.planCochlea = XRCCTRL(self, 'planCochlea')
        self.planBrainstem = XRCCTRL(self, 'planBrainstem')
        self.planSpinal1 = XRCCTRL(self, 'planSpinal1')
        self.planSpinal2 = XRCCTRL(self, 'planSpinal2')
        self.planCauda = XRCCTRL(self, 'planCauda')
        self.planSacral = XRCCTRL(self, 'planSacral')
        self.planEsophagus = XRCCTRL(self, 'planEsophagus')
        self.planBrachial = XRCCTRL(self, 'planBrachial')        
        self.planHeart = XRCCTRL(self, 'planHeart')        
        self.planGreatVessels = XRCCTRL(self, 'planGreatVessels')   
        self.planTrachea = XRCCTRL(self, 'planTrachea')
        self.planSmallBronchus = XRCCTRL(self, 'planSmallBronchus')
        self.planRib = XRCCTRL(self, 'planRib')
        self.planSkin = XRCCTRL(self, 'planSkin')
        self.planStomach = XRCCTRL(self, 'planStomach')
        self.planBowel = XRCCTRL(self, 'planBowel')
        self.planRenalHilum = XRCCTRL(self, 'planRenalHilum')
        self.planLungs1 = XRCCTRL(self, 'planLungs1')
        self.planLungs2 = XRCCTRL(self, 'planLungs2')
        self.planLiver = XRCCTRL(self, 'planLiver')
        self.planRenalCortex = XRCCTRL(self, 'planRenalCortex')    
        
        # Bind ui events to the proper methods
        wx.EVT_COMBOBOX(self, XRCID('choiceFractions'), self.ReadTolerances)
        wx.EVT_COMBOBOX(self, XRCID('choiceOptic'), self.FindPlanOptic)
        wx.EVT_COMBOBOX(self, XRCID('choiceCochlea'), self.FindPlanCochlea)
        wx.EVT_COMBOBOX(self, XRCID('choiceBrainstem'), self.FindPlanBrainstem)
        wx.EVT_COMBOBOX(self, XRCID('choiceSpinal'), self.FindPlanSpinal)
        wx.EVT_COMBOBOX(self, XRCID('choiceCauda'), self.FindPlanCauda)
        wx.EVT_COMBOBOX(self, XRCID('choiceSacral'), self.FindPlanSacral)
        wx.EVT_COMBOBOX(self, XRCID('choiceEsophagus'), self.FindPlanEsophagus)
        wx.EVT_COMBOBOX(self, XRCID('choiceBrachial'), self.FindPlanBrachial)
        wx.EVT_COMBOBOX(self, XRCID('choiceHeart'), self.FindPlanHeart)
        wx.EVT_COMBOBOX(self, XRCID('choiceGreatVessels'), self.FindPlanGreatVessels)
        wx.EVT_COMBOBOX(self, XRCID('choiceTrachea'), self.FindPlanTrachea)
        wx.EVT_COMBOBOX(self, XRCID('choiceSmallBronchus'), self.FindPlanSmallBronchus)
        wx.EVT_COMBOBOX(self, XRCID('choiceRib'), self.FindPlanRib)
        wx.EVT_COMBOBOX(self, XRCID('choiceSkin'), self.FindPlanSkin)
        wx.EVT_COMBOBOX(self, XRCID('choiceStomach'), self.FindPlanStomach)
        wx.EVT_COMBOBOX(self, XRCID('choiceBowel'), self.FindPlanBowel)
        wx.EVT_COMBOBOX(self, XRCID('choiceRenalHilum'), self.FindPlanRenalHilum)
        wx.EVT_COMBOBOX(self, XRCID('choiceLungs'), self.FindPlanLungs)
        wx.EVT_COMBOBOX(self, XRCID('choiceLiver'), self.FindPlanLiver)
        wx.EVT_COMBOBOX(self, XRCID('choiceRenalCortex'), self.FindPlanRenalCortex)
        #self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.ResetStructureChoices() 

    def ReadTolerances(self, evt=None):
        """Read in a text file that contains TG-101 constraints e.g. [volume,Fx1dose,...etc]."""
        if (evt == None):
            self.choiceFractions.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        FractionID = self.choiceFractions.GetSelection()
        
        # Lookup is column in tolerance excel file (A1=0,0) 
        # Column 2 is volume value
        if FractionID == 0:
            self.volOptic.Clear()
            self.volCochlea.Clear()
            self.volBrainstem.Clear()
            self.volSpinal1.Clear()
            self.volSpinal2.Clear()
            self.volCauda.Clear()
            self.volSacral.Clear()
            self.volEsophagus.Clear()
            self.volBrachial.Clear()
            self.volHeart.Clear()
            self.volGreatVessels.Clear()
            self.volTrachea.Clear()
            self.volSmallBronchus.Clear()
            self.volRib.Clear()
            self.volSkin.Clear()
            self.volStomach.Clear()
            self.volBowel.Clear()
            self.volRenalHilum.Clear()
            self.volLungs1.Clear()
            self.volLungs2.Clear()
            self.volLiver.Clear()
            self.volRenalCortex.Clear()
            self.limitOptic.Clear()
            self.limitCochlea.Clear()
            self.limitBrainstem.Clear()
            self.limitSpinal1.Clear()
            self.limitSpinal2.Clear()
            self.limitCauda.Clear()
            self.limitSacral.Clear()
            self.limitEsophagus.Clear()
            self.limitBrachial.Clear()
            self.limitHeart.Clear()
            self.limitGreatVessels.Clear()
            self.limitTrachea.Clear()
            self.limitSmallBronchus.Clear()
            self.limitRib.Clear()
            self.limitSkin.Clear()
            self.limitStomach.Clear()
            self.limitBowel.Clear()
            self.limitRenalHilum.Clear()
            self.limitLungs1.Clear()
            self.limitLungs2.Clear()
            self.limitLiver.Clear()
            self.limitRenalCortex.Clear()   
            self.planOptic.Clear()
            self.planCochlea.Clear()
            self.planBrainstem.Clear()
            self.planSpinal1.Clear()
            self.planSpinal2.Clear()
            self.planCauda.Clear()
            self.planSacral.Clear()
            self.planEsophagus.Clear()
            self.planBrachial.Clear()        
            self.planHeart.Clear()       
            self.planGreatVessels.Clear()  
            self.planTrachea.Clear()
            self.planSmallBronchus.Clear()
            self.planRib.Clear()
            self.planSkin.Clear()
            self.planStomach.Clear()
            self.planBowel.Clear()
            self.planRenalHilum.Clear()
            self.planLungs1.Clear()
            self.planLungs2.Clear()
            self.planLiver.Clear()
            self.planRenalCortex.Clear()   
            lookup = 7  # This will set the limit values to '-' from .xls              
        if FractionID == 1:
            lookup = 2
        elif FractionID == 2:
            lookup = 3
        elif FractionID == 3:
            lookup = 4
        elif FractionID == 4:
            lookup = 5
        elif FractionID == 5:
            lookup = 6
        tolerances = os.path.join(os.path.dirname(__file__), 'tolerances.xls')    
        wb = xlrd.open_workbook(tolerances)
        sh = wb.sheet_by_name(u'tolerances')
            
        #Convert Renal Hilum to percentage for visualization only
        #(will be set back to a ratio in the FindPlanRenalHilum)
        self.ratioRenalHilum = str(sh.cell(18,1).value)
        self.percentageRenalHilum = str(sh.cell(18,1).value * 100) + '%'           
            
        # Look up tolerance volumes
        self.volOptic.SetValue(str(sh.cell(1,1).value))
        self.volCochlea.SetValue(str(sh.cell(2,1).value))
        self.volBrainstem.SetValue(str(sh.cell(3,1).value))
        self.volSpinal1.SetValue(str(sh.cell(4,1).value))
        self.volSpinal2.SetValue(str(sh.cell(5,1).value))
        self.volCauda.SetValue(str(sh.cell(6,1).value))
        self.volSacral.SetValue(str(sh.cell(7,1).value))
        self.volEsophagus.SetValue(str(sh.cell(8,1).value))
        self.volBrachial.SetValue(str(sh.cell(9,1).value))
        self.volHeart.SetValue(str(sh.cell(10,1).value))
        self.volGreatVessels.SetValue(str(sh.cell(11,1).value))
        self.volTrachea.SetValue(str(sh.cell(12,1).value))
        self.volSmallBronchus.SetValue(str(sh.cell(13,1).value))
        self.volRib.SetValue(str(sh.cell(14,1).value))
        self.volSkin.SetValue(str(sh.cell(15,1).value))
        self.volStomach.SetValue(str(sh.cell(16,1).value))
        self.volBowel.SetValue(str(sh.cell(17,1).value))
        self.volRenalHilum.SetValue(self.percentageRenalHilum)  ##
        self.limitLungs1.SetValue(str(sh.cell(19,1).value))
        self.limitLungs2.SetValue(str(sh.cell(20,1).value))
        self.limitLiver.SetValue(str(sh.cell(21,1).value))
        self.limitRenalCortex.SetValue(str(sh.cell(22,1).value))
        
        # Look up tolerance doses
        self.limitOptic.SetValue(str(sh.cell(1,lookup).value))
        self.limitCochlea.SetValue(str(sh.cell(2,lookup).value))
        self.limitBrainstem.SetValue(str(sh.cell(3,lookup).value))
        self.limitSpinal1.SetValue(str(sh.cell(4,lookup).value))
        self.limitSpinal2.SetValue(str(sh.cell(5,lookup).value))
        self.limitCauda.SetValue(str(sh.cell(6,lookup).value))
        self.limitSacral.SetValue(str(sh.cell(7,lookup).value))
        self.limitEsophagus.SetValue(str(sh.cell(8,lookup).value))
        self.limitBrachial.SetValue(str(sh.cell(9,lookup).value))
        self.limitHeart.SetValue(str(sh.cell(10,lookup).value))
        self.limitGreatVessels.SetValue(str(sh.cell(11,lookup).value))
        self.limitTrachea.SetValue(str(sh.cell(12,lookup).value))
        self.limitSmallBronchus.SetValue(str(sh.cell(13,lookup).value))
        self.limitRib.SetValue(str(sh.cell(14,lookup).value))
        self.limitSkin.SetValue(str(sh.cell(15,lookup).value))
        self.limitStomach.SetValue(str(sh.cell(16,lookup).value))
        self.limitBowel.SetValue(str(sh.cell(17,lookup).value))
        self.limitRenalHilum.SetValue(str(sh.cell(18,lookup).value))
        self.thresholdLungs1.SetValue(str(sh.cell(19,lookup).value))
        self.thresholdLungs2.SetValue(str(sh.cell(20,lookup).value))
        self.thresholdLiver.SetValue(str(sh.cell(21,lookup).value))
        self.thresholdRenalCortex.SetValue(str(sh.cell(22,lookup).value))      

    def ResetStructureChoices(self):
        """Populate the structure list."""

        # Reinitialize the lists; will have double the entries if not
        self.choiceOptic.Clear()
        self.choiceCochlea.Clear()
        self.choiceBrainstem.Clear()
        self.choiceSpinal.Clear()
        self.choiceCauda.Clear()
        self.choiceSacral.Clear()
        self.choiceEsophagus.Clear()
        self.choiceBrachial.Clear()       
        self.choiceHeart.Clear()        
        self.choiceGreatVessels.Clear()  
        self.choiceTrachea.Clear()
        self.choiceSmallBronchus.Clear()
        self.choiceRib.Clear()
        self.choiceSkin.Clear()
        self.choiceStomach.Clear()
        self.choiceBowel.Clear()
        self.choiceRenalHilum.Clear()
        self.choiceLungs.Clear()
        self.choiceLiver.Clear()
        self.choiceRenalCortex.Clear()
        
        # Pad the first item after initializing
        self.choiceOptic.Append('-')
        self.choiceCochlea.Append('-')
        self.choiceBrainstem.Append('-')
        self.choiceSpinal.Append('-')
        self.choiceCauda.Append('-')
        self.choiceSacral.Append('-')
        self.choiceEsophagus.Append('-')
        self.choiceBrachial.Append('-')      
        self.choiceHeart.Append('-')        
        self.choiceGreatVessels.Append('-') 
        self.choiceTrachea.Append('-')
        self.choiceSmallBronchus.Append('-')
        self.choiceRib.Append('-')
        self.choiceSkin.Append('-')
        self.choiceStomach.Append('-')
        self.choiceBowel.Append('-')
        self.choiceRenalHilum.Append('-')
        self.choiceLungs.Append('-')
        self.choiceLiver.Append('-')
        self.choiceRenalCortex.Append('-')        

        for id, structure in self.structures.iteritems():
            i = self.choiceOptic.Append(structure['name'])
            self.choiceOptic.SetClientData(i, id)
            
            i = self.choiceCochlea.Append(structure['name'])
            self.choiceCochlea.SetClientData(i, id)
            
            i = self.choiceBrainstem.Append(structure['name'])
            self.choiceBrainstem.SetClientData(i, id)
            
            i = self.choiceSpinal.Append(structure['name'])
            self.choiceSpinal.SetClientData(i, id)
            
            
            i = self.choiceCauda.Append(structure['name'])
            self.choiceCauda.SetClientData(i, id)
            
            i = self.choiceSacral.Append(structure['name'])
            self.choiceSacral.SetClientData(i, id)
            
            i = self.choiceEsophagus.Append(structure['name'])
            self.choiceEsophagus.SetClientData(i, id)
            
            i = self.choiceBrachial.Append(structure['name'])   
            self.choiceBrachial.SetClientData(i, id)
            
            i = self.choiceHeart.Append(structure['name'])   
            self.choiceHeart.SetClientData(i, id)
            
            i = self.choiceGreatVessels.Append(structure['name'])  
            self.choiceGreatVessels.SetClientData(i, id)
            
            i = self.choiceTrachea.Append(structure['name'])
            self.choiceTrachea.SetClientData(i, id)
            
            i = self.choiceSmallBronchus.Append(structure['name'])
            self.choiceSmallBronchus.SetClientData(i, id)
            
            i = self.choiceRib.Append(structure['name'])
            self.choiceRib.SetClientData(i, id)
            
            i = self.choiceSkin.Append(structure['name'])
            self.choiceSkin.SetClientData(i, id)
            
            i = self.choiceStomach.Append(structure['name'])
            self.choiceStomach.SetClientData(i, id)
            
            i = self.choiceBowel.Append(structure['name'])
            self.choiceBowel.SetClientData(i, id)
            
            i = self.choiceRenalHilum.Append(structure['name']) 
            self.choiceRenalHilum.SetClientData(i, id)
            
            i = self.choiceLungs.Append(structure['name'])
            self.choiceLungs.SetClientData(i, id)
            
            i = self.choiceLiver.Append(structure['name'])
            self.choiceLiver.SetClientData(i, id)
            
            i = self.choiceRenalCortex.Append(structure['name']) 
            self.choiceRenalCortex.SetClientData(i, id)
          
    def FindPlanOptic(self, evt=None):
        if (evt == None):
            self.choiceOptic.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceOptic.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volOptic.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planOptic.SetValue(dose)
        
    def FindPlanCochlea(self, evt=None):
        if (evt == None):
            self.choiceCochlea.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceCochlea.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volCochlea.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planCochlea.SetValue(dose)    
        
    def FindPlanBrainstem(self, evt=None):
        if (evt == None):
            self.choiceBrainstem.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceBrainstem.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volBrainstem.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planBrainstem.SetValue(dose)   
        
    def FindPlanSpinal(self, evt=None):
        if (evt == None):
            self.choiceSpinal.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceSpinal.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol1 = float(self.volSpinal1.GetValue())*100/total_vol
            Vol2 = float(self.volSpinal2.GetValue())*100/total_vol
            dose1 = self.dvhdata[id].GetDoseConstraint(Vol1)
            dose2 = self.dvhdata[id].GetDoseConstraint(Vol2)
            dose1 = str(dose1/100)   # Dose from DVH is in cGy
            dose2 = str(dose2/100)
            self.planSpinal1.SetValue(dose1)  
            self.planSpinal2.SetValue(dose2) 
        
    def FindPlanCauda(self, evt=None):
        if (evt == None):
            self.choiceCauda.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceCauda.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volCauda.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planCauda.SetValue(dose)  
        
    def FindPlanSacral(self, evt=None):
        if (evt == None):
            self.choiceSacral.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceSacral.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volSacral.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planSacral.SetValue(dose) 
        
    def FindPlanEsophagus(self, evt=None):
        if (evt == None):
            self.choiceEsophagus.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceEsophagus.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volEsophagus.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planEsophagus.SetValue(dose)  
        
    def FindPlanBrachial(self, evt=None):
        if (evt == None):
            self.choiceBrachial.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceBrachial.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volBrachial.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planBrachial.SetValue(dose) 
        
    def FindPlanHeart(self, evt=None):
        if (evt == None):
            self.choiceHeart.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceHeart.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volHeart.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planHeart.SetValue(dose)  
        
    def FindPlanGreatVessels(self, evt=None):
        if (evt == None):
            self.choiceGreatVessels.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceGreatVessels.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volGreatVessels.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planGreatVessels.SetValue(dose)  
        
    def FindPlanTrachea(self, evt=None):
        if (evt == None):
            self.choiceTrachea.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceTrachea.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volTrachea.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planTrachea.SetValue(dose) 
        
    def FindPlanSmallBronchus(self, evt=None):
        if (evt == None):
            self.choiceSmallBronchus.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceSmallBronchus.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volSmallBronchus.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planSmallBronchus.SetValue(dose)
        
    def FindPlanRib(self, evt=None):
        if (evt == None):
            self.choiceRib.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceRib.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volRib.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planRib.SetValue(dose)  
        
    def FindPlanSkin(self, evt=None):
        if (evt == None):
            self.choiceSkin.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceSkin.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volSkin.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planSkin.SetValue(dose)  
        
    def FindPlanStomach(self, evt=None):
        if (evt == None):
            self.choiceStomach.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceStomach.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volStomach.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planStomach.SetValue(dose)  
        
    def FindPlanBowel(self, evt=None):
        if (evt == None):
            self.choiceBowel.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceBowel.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.volBowel.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planBowel.SetValue(dose) 
        
    def FindPlanRenalHilum(self, evt=None):
        # Read explanation in ReadTolerances; was changed from ratio (.666)
        # to 66.6% for visualization.  Set that back here.

        if (evt == None):
            self.choiceRenalHilum.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceRenalHilum.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            #total_vol = dvhdata.CalculateVolume(self.structures[id])
            Vol = float(self.ratioRenalHilum)*100
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            self.planRenalHilum.SetValue(dose)  
        
    def FindPlanLungs(self, evt=None):
        if (evt == None):
            self.choiceLungs.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceLungs.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            absDose1 = float(self.thresholdLungs1.GetValue())
            absDose2 = float(self.thresholdLungs2.GetValue())
            constraint1 = float(self.dvhdata[id].GetVolumeConstraint(absDose1))
            constraint2 = float(self.dvhdata[id].GetVolumeConstraint(absDose2))
            total_vol = float(dvhdata.CalculateVolume(self.structures[id]))
            crit_vol1 = total_vol - constraint1
            crit_vol2 = total_vol - constraint2
            crit_vol1 = str(round(crit_vol1,1))
            crit_vol2 = str(round(crit_vol2,1))
            self.planLungs1.SetValue(crit_vol1)  
            self.planLungs2.SetValue(crit_vol2)  
        
    def FindPlanLiver(self, evt=None):
        if (evt == None):
            self.choiceLiver.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceLiver.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            absDose = float(self.thresholdLiver.GetValue())
            constraint = float(self.dvhdata[id].GetVolumeConstraint(absDose))
            total_vol = float(dvhdata.CalculateVolume(self.structures[id]))
            crit_vol = total_vol - constraint
            crit_vol = str(round(crit_vol,1))
            self.planLiver.SetValue(crit_vol)
        
    def FindPlanRenalCortex(self, evt=None):
        if (evt == None):
            self.choiceRenalCortex.SetSelection(0)
            choiceItem = 0
        else:
            choiceItem = evt.GetInt()
        id = self.choiceRenalCortex.GetClientData(choiceItem)
        if id > 0:   #exclude '-'
            self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
            absDose = float(self.thresholdRenalCortex.GetValue())
            constraint = float(self.dvhdata[id].GetVolumeConstraint(absDose))
            total_vol = float(dvhdata.CalculateVolume(self.structures[id]))
            crit_vol = total_vol - constraint
            crit_vol = str(round(crit_vol,1))
            self.planRenalCortex.SetValue(crit_vol)       
        
    