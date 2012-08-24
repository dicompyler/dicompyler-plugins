#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# Analysis.py
"""dicompyler plugin that calculates congruence between selected structure and an isodose line."""

import os.path
import wx
from wx.xrc import XmlResource, XRCCTRL, XRCID
from wx.lib.pubsub import Publisher as pub
#from matplotlib import _cntr as cntr
#from matplotlib import __version__ as mplversion
#import matplotlib.nxutils as nx
#import numpy.ma as ma
#import numpy as np
#from dicompyler import guiutil, util
from dicompyler import dvhdata
#from dicompyler.dicomparser import DicomParser as dp

def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'SRT DVH Analysis'
    props['description'] = "Analyzes DVH parameters according to TG-101 protocol"
    props['author'] = 'Landon Clark'
    props['version'] = 0.2
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
        
        # Set up pubsub
        #pub.subscribe(self.OnUpdatePatient, 'patient.updated.parsed_data') 
        
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
        #drawingstyles = ['Solid', 'Transparent', 'Dot', 'Dash', 'Dot Dash']
        #self.tools = []
        
        self.widgetDict = {'choiceOptic': ['Optic', 'OpticMax'],
                           'choiceCochlea': ['CochleaMax'],
                           'choiceBrainstem': ['Brainstem', 'BrainstemMax'],
                           'choiceSpinal': ['Spinal1', 'Spinal2', 'SpinalMax'],
                           'choiceCauda': ['Cauda', 'CaudaMax'],
                           'choiceSacral': ['Sacral', 'SacralMax'],
                           'choiceEsophagus': ['Esophagus', 'EsophagusMax'],
                           'choiceBrachial': ['Brachial', 'BrachialMax'],
                           'choiceHeart': ['Heart', 'HeartMax'],
                           'choiceGreatVessels': ['GreatVessels', 'GreatVesselsMax'],
                           'choiceTrachea': ['Trachea', 'TracheaMax'],
                           'choiceSmallBronchus': ['SmallBronchus', 'SmallBronchusMax'],
                           'choiceRib': ['Rib', 'RibMax'],
                           'choiceSkin': ['Skin', 'SkinMax'],
                           'choiceStomach': ['Stomach', 'StomachMax'],
                           'choiceBowel': ['Bowel', 'BowelMax'],
                           'choiceRenalHilum': ['RenalHilum'],
                           'choiceLungs': ['Lungs1', 'Lungs2'],
                           'choiceLiver': ['Liver'],
                           'choiceRenalCortex': ['RenalCortex'] 
                           }
                           
        self.volDict = {1: 'Optic',
                        2: 'Brainstem',
                        3: 'Spinal1',
                        4: 'Spinal2',
                        5: 'Cauda',
                        6: 'Sacral',
                        7: 'Esophagus',
                        8: 'Brachial',
                        9: 'Heart',
                        10: 'GreatVessels',
                        11: 'Trachea',
                        12: 'SmallBronchus',
                        13: 'Rib',
                        14: 'Skin',
                        15: 'Stomach',
                        16: 'Bowel',
                        17: 'RenalHilum',
                        18: 'Lungs1',
                        19: 'Lungs2',
                        20: 'Liver',
                        21: 'RenalCortex'
                        }
               
        self.initialGuessDict =  {'choiceOptic':        ['optic pathway',
                                                         'optic structures'],
                                  'choiceCochlea':      ['cochlea'],
                                  'choiceBrainstem':    ['brainstem'],
                                  'choiceSpinal':       ['spinal cord', 'cord'],
                                  'choiceCauda':        ['cauda', 'caude equina'],
                                  'choiceEsophagus':    ['esophagus'],  
                                  'choiceBrachial':     ['brachial plexus'],
                                  'choiceHeart':        ['heart'],
                                  'choiceGreatVessels': ['great vessels', 
                                                         'greater vessels', 'gv'],
                                  'choiceTrachea':      ['trachea', 'trachea/bronchus',
                                                         'bronchus', 'large bronchus'],
                                  'choiceSmallBronchus':['small bronchus', 
                                                         'smaller bronchus'],
                                  'choiceRib':          ['rib', 'ribs'],
                                  'choiceSkin':         ['skin', 'skin 5mm', 'skin (5mm)',
                                                         'skin(5mm)', 'skin(0.5cm)', 
                                                         'skin (0.5cm)'],
                                  'choiceStomach':      ['stomach'],
                                  'choiceBowel':        ['bowel'],
                                  'choiceRenalHilum':   ['renal hilum'],
                                  'choiceLungs':        ['lungs', 'total lung',
                                                         'total lungs', 'lung'],
                                  'choiceLiver':        ['liver'],
                                  'choiceRenalCortex':  ['renal cortex']
                                  }
                                  
        "Tolerances from TG-101 table."
        "Format (serial) [volume, limit(1fx), limit(2fx), limit(3fx), limit(4fx), limit(5fx)]"
        "Format (parall) [thresh, limit(1fx), limit(2fx), limit(3fx), limit(4fx), limit(5fx)]"
        self.toleranceOptic =              [0.2, 8.0, 11.7, 15.3, 19.2, 23.0]
        self.toleranceOpticMax =           [0, 10, 13.7, 17.4, 21.2, 25]
        self.toleranceCochleaMax =         [0, 9, 13.1, 17.1, 21.1, 25]
        self.toleranceBrainstem =          [0.5, 10, 14, 18, 20.5, 23]
        self.toleranceBrainstemMax =       [0, 15, 19.1, 23.1, 27.1, 31]
        self.toleranceSpinal1 =            [0.35, 10, 14, 18, 20.5, 23]
        self.toleranceSpinal2 =            [1.2, 7, 9.7, 12.3, 13.4, 14.5]
        self.toleranceSpinalMax =          [0, 14, 18, 21.9, 26, 30]
        self.toleranceCauda =              [5, 14, 18, 21.9, 26, 30]
        self.toleranceCaudaMax =           [0, 16, 20, 24, 28 ,32]
        self.toleranceSacral =             [5, 14.4, 18.5, 22.5, 26.3, 30]
        self.toleranceSacralMax =          [0, 16, 20, 24, 28, 32]
        self.toleranceEsophagus =          [5, 11.9, 14.8, 17.7, 18.6, 19.5]
        self.toleranceEsophagusMax =       [0, 15.4, 20.3, 25.2, 30.1, 35]
        self.toleranceBrachial =           [3, 14, 17.2, 20.4, 23.7, 27]
        self.toleranceBrachialMax =        [0, 17.5, 20.8, 24, 27.3, 30.5]
        self.toleranceHeart =              [15, 16, 20, 24, 28, 32]
        self.toleranceHeartMax =           [0, 22, 26, 30, 34, 38]
        self.toleranceGreatVessels =       [10, 31, 35, 39, 43, 47]
        self.toleranceGreatVesselsMax =    [0, 37, 41, 45, 49, 53]
        self.toleranceTrachea =            [4, 10.5, 12.8, 15, 15.8, 16.5]
        self.toleranceTracheaMax =         [0, 20.2, 25.1, 30, 35, 40]
        self.toleranceSmallBronchus =      [0.5, 12.4, 15.7, 18.9, 20, 21]
        self.toleranceSmallBronchusMax =   [0, 13.3, 18.2, 23.1, 28.1, 33]
        self.toleranceRib =                [1, 22, 25.4, 28.8, 31.9, 35]
        self.toleranceRibMax =             [0, 30, 33.5, 36.9, 40, 43]
        self.toleranceSkin =               [10, 23, 26.5, 30, 33.3, 36.5]
        self.toleranceSkinMax =            [0, 26, 29.5, 33, 36.3, 39.5]
        self.toleranceStomach =            [10, 11.2, 13.9, 16.5, 17.3, 18]
        self.toleranceStomachMax =         [0, 12.4, 17.3, 22.2, 27.1, 32]
        self.toleranceBowel =              [5, 11.9, 14.8, 17.7, 18.6, 19.5]
        self.toleranceBowelMax =           [0, 15.4, 20.3, 25.2, 30.1, 35]
        self.toleranceRenalHilum =         ['66.6%', 10.6, 14.6, 18.6, 20.8, 23]
        self.toleranceLungs1 =             ['> 1500', 7, 9.3, 11.6, 12.1, 12.5]
        self.toleranceLungs2 =             ['> 1000', 7.4, 9.9, 12.4, 13, 13.5]
        self.toleranceLiver =              ['> 700', 9.1, 14.2, 19.2, 20.1, 21]
        self.toleranceRenalCortex =        ['> 200', 8.4, 12.2, 16, 16.8, 17.5]        
        
        # Initialize the Analysis fractionation control
        self.choiceFractions = XRCCTRL(self, 'choiceFractions')    
        
        # Volumes defined per fraction/Organ
        # Doses defined per fraction/Organ (Critical Volume/Threshold organs)
        # NOTE: Lungs, Liver, and RenalCortex are actually THRESHOLDS (in Gy),
        #       NOT volumes.  This was only done for a simpler for_loop.
        #       See columns on GUI.        
        for i, organName in self.volDict.iteritems():                   # Look up GUI Column 2 values                          
            volName = 'vol' + organName
            setattr(self, volName, XRCCTRL(self, volName))        
        
        # Define structure lists (choices) and dose limits (in cGy) for each organ/fractionation
        for choiceName, organList in self.widgetDict.iteritems():   # i.e. ['Optic', 'OpticMax']
            setattr(self, choiceName, XRCCTRL(self, choiceName))      # structure lists (choices) i.e. self.choiceOptic
            for organName in organList:   
                limitName = 'limit' + organName                        # TG limit values  i.e. 'limitOptic'         
                planName = 'plan' + organName                          # Dose values obtained from plan in Dicompyler i.e. 'planOptic' 
                imgName = 'img' + organName                 #Image box indicator that initializes with a transparent.png image i.e. 'imgOptic'
                setattr(self, limitName, XRCCTRL(self, limitName))      # i.e. self.limitOptic
                setattr(self, planName, XRCCTRL(self, planName))      # i.e. self.planOptic
                setattr(self, imgName, XRCCTRL(self, imgName))        # i.e. self.imgOptic
        
        # Bind ui events to the proper methods
        wx.EVT_COMBOBOX(self, XRCID('choiceFractions'), self.ReadTolerances)
        wx.EVT_COMBOBOX(self, XRCID('choiceOptic'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceCochlea'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceBrainstem'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceSpinal'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceCauda'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceSacral'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceEsophagus'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceBrachial'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceHeart'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceGreatVessels'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceTrachea'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceSmallBronchus'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceRib'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceSkin'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceStomach'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceBowel'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceRenalHilum'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceLungs'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceLiver'), self.OnComboOrgan)
        wx.EVT_COMBOBOX(self, XRCID('choiceRenalCortex'), self.OnComboOrgan)
        #self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
  
        self.SetStructureChoices() 
        self.InitialGuessCombobox()
        self.DisableChoices()

    def PrintEventInfo(self, event):
        print event.GetEventObject().GetName(), 'name'
        print event.GetEventObject().GetLabel(), 'label'

    def ReadTolerances(self, event=None):
        """Read in a text file that contains TG-101 constraints 
        e.g. [volume,Fx1dose,...etc]."""
        FractionID = self.choiceFractions.GetSelection()
        
        # Initialize the cells after the fractionation is changed
        self.ResetVolumeValues()
        self.ResetLimitValues()
        self.ResetPlanValues()
        if FractionID == 0:    
            self.DisableChoices()
            self.ResetImgs()
        else:
            self.EnableChoices()
            self.ResetImgs()
            for i, organName in self.volDict.iteritems():                   # Look up GUI Column 2 values                          
                if hasattr(self, 'vol' + organName) == True:                # exclude max points in column 2       
                    VolObject = getattr(self, 'vol' + organName)  
                    tolerance = getattr(self, 'tolerance' + organName)
                    if type(tolerance[0]) != str:                     # All except hilum and parallel organs
                        VolObject.SetValue(str(tolerance[0]))         
                    if type(tolerance[0]) == str:                     # hilum and lungs
                        if '%' in tolerance[0]:                       # hilum
                            s = tolerance[0]                                          # i.e. '66.6%' -> 0.666
                            setattr(self, 'ratio' + organName, float(s.rstrip('%')) / 100)               # i.e. self.ratioRenalHilum
                            setattr(self, 'percentage' + organName, s)   # i.e. self.percentageRenalHilum
                            VolObject.SetValue(s)                      # i.e. self.volRenalHilum
                        if '>' in tolerance[0]:              # lungs
                            VolObject.SetValue(str(tolerance[FractionID]))        
            for choiceName, organList in self.widgetDict.iteritems():       # Look up GUI Column 3 values                                        
                for organName in organList:                                 # i.e. 'Optic, OpticMax' 
                    tolerance = getattr(self, 'tolerance' + organName)      # i.e. 'self.toleranceOptic'                                            
                    LimitObject = getattr(self, 'limit' + organName)        # i.e. self.limitOptic
                    if type(tolerance[0]) != str:
                        LimitObject.SetValue(str(tolerance[FractionID]))
                    if type(tolerance[0]) == str:
                        if '%' in tolerance[0]:
                            LimitObject.SetValue(str(tolerance[FractionID]))  
                        if '>' in tolerance[0]:
                            LimitObject.SetValue(tolerance[0])    
        
            # Autopopulate the preset structures, if found by name
            for choiceName, organList in self.widgetDict.iteritems():           # i.e. ['Optic', 'OpticMax']    
                ChoiceObject = getattr(self, choiceName)                        # i.e. self.choiceOptic
                CurrentChoiceObject = ChoiceObject.GetCurrentSelection()
                if CurrentChoiceObject > 0:                                         # ignore choice(0) = ''
                    for organName in organList:                                     # i.e. 'Optic'     
                        self.FindOrganPlan(ChoiceObject.GetClientData(CurrentChoiceObject), organName)

    def SetStructureChoices(self):
        """Populate the structure list."""
        # Reinitialize the lists; will have double the entries if not
        choiceList = self.widgetDict.keys()             # i.e. ['choiceOptic', 'choiceCochlea', ...]
        for choiceName in choiceList:                   # i.e. 'choiceOptic'
            choiceObject = getattr(self, choiceName)    # i.e. self.choiceOptic
            choiceObject.Clear()                        # i.e. self.choiceOptic.Enable()
            choiceObject.Append('')                     # Pad the first item       
            for id, structure in self.structures.iteritems(): 
                i = choiceObject.Append(structure['name'])
                choiceObject.SetClientData(i, id)            
            
    def InitialGuessCombobox(self):
        for choiceName, guessList in self.initialGuessDict.iteritems():                     # i.e. ['skin', 'skin (0.5cm)']    
            ChoiceObject = getattr(self, choiceName)                                        # i.e. self.choiceSkin
            for i in range(ChoiceObject.GetCount()):                                        # combobox list ['', 'Optic', 'Skin', ...]                  
                if self.KeywordsInCombobox(ChoiceObject.GetString(i), guessList) == True:              
                    ChoiceObject.SetSelection(i)
    
    def KeywordsInCombobox(self, comboboxString, guessList):
        for guess in guessList:
            if comboboxString.lower() == guess:
                return True               
    
    def ResetVolumeValues(self):
        # NOTE: Lungs, Liver, and RenalCortex are actually THRESHOLDS (in Gy),
        #       NOT volumes.  This was only done for a simpler for_loop.
        #       See columns on GUI.
        for choiceName, organList in self.widgetDict.iteritems():   # i.e. ['Optic', 'OpticMax']
            for organName in organList:                             # i.e. 'Optic'      
                if hasattr(self, 'vol' + organName) == True:        # exclude statictext = max point                   
                    VolObject = getattr(self, 'vol' + organName)    # i.e. self.volOptic
                    VolObject.Clear()
    
    def ResetLimitValues(self):                                     # not event based; do for all in dict
        for choiceName, organList in self.widgetDict.iteritems():   # i.e. ['Optic', 'OpticMax']
            for organName in organList:                             # i.e. 'Optic'                                            
                LimitObject = getattr(self, 'limit' + organName)    # i.e. self.limitOptic
                LimitObject.Clear()
     
    def ResetPlanValues(self):                                      # not event based; do for all in dict
        for choiceName, organList in self.widgetDict.iteritems():   # i.e. ['Optic', 'OpticMax']
            for organName in organList:                             # i.e. 'Optic'                                         
                PlanObject = getattr(self, 'plan' + organName)      # i.e. self.planOptic
                PlanObject.Clear()

    def ResetImgs(self):
        for choiceName, organList in self.widgetDict.iteritems():   # i.e. ['Optic', 'OpticMax']
            for organName in organList:                             # i.e. 'Optic'                     
                ImgObject = getattr(self, 'img' + organName)        # i.e. self.imgOptic
                ImgObject.SetBitmap(self.GetBitmap('transparent.png'))
        
    def EnableChoices(self):
        choiceList = self.widgetDict.keys()     # i.e. ['choiceOptic', 'choiceCochlea', ...]
        for choiceName in choiceList:                   # i.e. 'choiceOptic'
            choiceObject = getattr(self, choiceName)    # i.e. self.choiceOptic
            choiceObject.Enable()                       # i.e. self.choiceOptic.Enable()
        
    def DisableChoices(self):
        choiceList = self.widgetDict.keys()      # i.e. ['choiceOptic', 'choiceCochlea', ...]
        for choiceName in choiceList:                    # i.e. 'choiceOptic'
            choiceObject = getattr(self, choiceName)     # i.e. self.choiceOptic
            choiceObject.Enable(False)                   # i.e. self.choiceOptic.Enable(False)

    def GetBitmap(self, string):
        img = os.path.join(os.path.dirname(__file__), string) 
        img = wx.Image(img, wx.BITMAP_TYPE_ANY)
        img = wx.BitmapFromImage(img) 
        return img    
    
    def OnComboOrgan(self, event=None):                                     # event based; do for only on combobox organ
        choiceItem = event.GetInt()                                         # i.e. userinput ---->  index of selected organ
        choiceName = event.GetEventObject().GetName()                       # i.e. choiceObject (name of organ label)
        choiceObject = getattr(self, choiceName)                            # i.e. choiceObject = self.choiceOptic
        id = choiceObject.GetClientData(choiceItem)                         # i.e. id = self.choiceOptic.GetClientData(choiceItem)
        for organName in self.widgetDict[choiceName]:                       # i.e. ['Optic', 'OpticMax']  
            if id > 0:                                                  # exclude choice(0) = ''
                #FindPlanObject = getattr(self, 'FindPlan' + organName)          # i.e. self.FindPlanOptic
                #FindPlanObject(id)
                self.FindOrganPlan(id, organName)
            else:
                PlanObject = getattr(self, 'plan' + organName)      # i.e. self.planOptic
                ImgObject = getattr(self, 'img' + organName)      # i.e. self.planOptic
                PlanObject.Clear()            
                ImgObject.SetBitmap(self.GetBitmap('transparent.png'))
        
    def FindOrganPlan(self, id, organName):   
        LimitObject = getattr(self, 'limit' + organName)      # i.e. self.planOptic
        PlanObject = getattr(self, 'plan' + organName)      # i.e. self.planOptic
        ImgObject = getattr(self, 'img' + organName)      # i.e. self.planOptic
        self.dvhdata[id] = dvhdata.DVH(self.dvhs[id])
        if hasattr(self, 'vol' + organName) == True:        # exclude statictext = max point                   
            VolObject = getattr(self, 'vol' + organName)    # i.e. self.volOptic     
            if '%' in VolObject.GetValue():   #hilum
                s = VolObject.GetValue()
                s = s.rstrip('%')
                formatted_vol = s 
        if '> ' in LimitObject.GetValue():  #hilum and lung
            s = LimitObject.GetValue()
            s = s.lstrip('> ')
            formatted_limit = s
        if 'Max' not in organName:
            total_vol = dvhdata.CalculateVolume(self.structures[id])
            if 'formatted_vol' in locals():
                Vol = float(formatted_vol)*100/total_vol
            else:
                Vol = float(VolObject.GetValue())*100/total_vol
            dose = self.dvhdata[id].GetDoseConstraint(Vol)
            dose = str(dose/100)   # Dose from DVH is in cGy
            if 'formatted_limit' in locals():
                crit_vol = total_vol - float(formatted_limit)
                crit_vol = str(round(crit_vol,1))
                PlanObject.SetValue(crit_vol) 
                if float(PlanObject.GetValue()) > float(formatted_limit):
                    ImgObject.SetBitmap(self.GetBitmap('check.png'))
                else:
                    ImgObject.SetBitmap(self.GetBitmap('flag.png'))
            else:
                PlanObject.SetValue(dose)
                if float(PlanObject.GetValue()) < float(LimitObject.GetValue()):
                    ImgObject.SetBitmap(self.GetBitmap('check.png'))
                else:
                    ImgObject.SetBitmap(self.GetBitmap('flag.png'))

        else:                   # dose max
            dose = self.dvhdata[id].GetDoseConstraint(0) #dose at DVH tail
            dose = str(dose/100)
            PlanObject.SetValue(dose)
            if float(PlanObject.GetValue()) < float(LimitObject.GetValue()):
                ImgObject.SetBitmap(self.GetBitmap('check.png'))
            else:
                ImgObject.SetBitmap(self.GetBitmap('flag.png'))                 