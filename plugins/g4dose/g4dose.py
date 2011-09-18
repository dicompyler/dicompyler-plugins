# g4dose.py
"""G4 RT-Dose plugin for dicompyler."""
# Copyright (c) 2011 Derek M. Tishler, Brian P. Tonner, and dicompyler contributors.
# All rights reserved, released under a BSD license.
#    See the file license.txt included with this distribution, available at:
#    http://code.google.com/p/dicompyler-plugins/source/browse/plugins/g4dose/license.txt

import wx
from wx.lib.pubsub import Publisher as pub
import dicom
import os
import numpy as np
from PIL import Image
import util

def pluginProperties():

    props = {}
    props['name'] = 'G4 RT-Dose'
    props['description'] = "Create RT-Dose from a Geant4 DICOM simulation."
    props['author'] = 'D.M. Tishler & B.P. Tonner'
    props['version'] = 0.2
    props['documentation'] = 'http://code.google.com/p/dicompyler-plugins/wiki/g4dose'
    props['license'] = 'license.txt'
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = ['images']
    props['recommended_dicom'] =  ['images','rtdose']

    return props

class plugin():

    def __init__(self, parent):

        self.parent = parent
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')

    def OnUpdatePatient(self, msg):

        self.data = msg.data

    def addElement(self, tup):
        #Publish the RT-Dose and rxdose to pubsub.
        if tup:
            self.data.update({'rtdose':tup[0]})
            self.data.update({'rxdose':tup[1]})
        pub.sendMessage('patient.updated.raw_data', self.data)

    def pluginMenu(self, evt):

        msg = "Please select the GEANT4 DICOM project folder."
        loop=True
        
        while loop:
            loop=False
            dirdlg = wx.DirDialog(self.parent,msg)
            if dirdlg.ShowModal() == wx.ID_OK:
                path = dirdlg.GetPath()
                #Confirm G4 simulation input and output files are found.
                if os.path.isfile(path+"/Data.dat") and os.path.isfile(path+"/dicom.out"):
                    self.addElement(loadG4DoseGraph(path,self.data['images']))
                else:
                    print os.path.isfile(path+"/Data.dat")
                    print path+"/Data.dat"
                    print os.path.isfile(path+"/dicom.out")
                    msg = "Please select the GEANT4 DICOM project folder.\nData.dat + Dicom.out are required!"
                    loop=True
            dirdlg.Destroy()

def loadG4DoseGraph(path,ds):

    #Load number of slices and compression value from data.dat.
    file = open(path+"/Data.dat")
    compression = int(file.readline())
    sliceCount = int(file.readline())

    #Load dosegraph from dicom.out
    doseTable = np.loadtxt(path+"/dicom.out")
    
    #Exit if simulator had null output.
    if len(doseTable) == 0:
        msgE = 'dicom.out is empty!\nCheck simulation for errors.\nExiting'
        dial = wx.MessageDialog(None, msgE, 'Error', wx.OK | wx.ICON_ERROR)
        dial.ShowModal()
        return

    #Temp, progress bar.
    guageCount = 0
    prog = [True,False]
    guage = wx.ProgressDialog("G4 RT-Dose","Building RT-Dose from GEANT4 simulation\n",
                              len(doseTable)+sliceCount+1,style=wx.PD_REMAINING_TIME |
                              wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT)

    #image dimensions from images(DICOM dosegraph object)
    imageCol = ds[0].pixel_array.shape[0]
    imageRow = ds[0].pixel_array.shape[1]

    #G4 compression value error. See documentation.
    if doseTable[-1][0] > sliceCount*imageCol/compression*imageRow/compression:
        msgE = 'Compression value error in data.dat!\nPlease delete binary files and re-run GEANT4.'
        dial = wx.MessageDialog(None, msgE, 'Error', wx.OK | wx.ICON_ERROR)
        dial.ShowModal()
        return

    #voxel dimensions
    voxelCol = imageCol/compression
    voxelRow = imageRow/compression

    #Repeated values.
    voxelDim = voxelCol*voxelRow*sliceCount
    area = voxelCol*voxelRow

    #Store images for resizing.
    imageList = list()
    for i in range(sliceCount):
        imageList.append([])
        imageList[i] = np.zeros((voxelCol,voxelRow),np.uint32)

    #Highest dose value, float.
    Max = max(doseTable[:, 1])
    #Normalize dose data and prepare for LUT in dicompyler.
    scaleTable = np.ones((len(doseTable),2),np.uint32)
    #4294967295,65535,255;2147483647,32767,127
    scaleTable[:, 1] = np.round((doseTable[:, 1]/Max)*65535.)
    doseTableInt = np.ones((len(doseTable),2),np.uint32)*scaleTable
    del scaleTable
        
    doseMax =  max(doseTableInt[:, 1])
    doseGridScale = float(Max/doseMax)
    #Set rx dose.
    rxdose = float(0.90*Max*100.)
   
    curRow = 0
    curSlice = 0

    for index, vID in enumerate(doseTable[:, 0]):
        #Search for corresponding slice.
        for i in range(curSlice,sliceCount):
            if vID >= i*area and vID < (i+1)*area:
                curSlice = i
                curRow = 0
                break
        #Search for corresponding row.
        for j in range(curRow,voxelRow):
            #Find the row that vID falls into.
            if (vID - curSlice*area) >= j*voxelRow and (vID - curSlice*area) < (j+1)*voxelRow:
                curRow = j
                break
        #2xN -> SlicesxRowxCol
        yShift = curRow
        xShift = vID - curRow*voxelCol - curSlice*area
        imageList[curSlice][yShift][xShift] = doseTableInt[index][1]
        #Update progress bar & check for abort.
        if prog[0]:
            guageCount+=1
            prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\nProcessing slice: {0:n}".format(curSlice+1))
        else:
            guage.Destroy()
            return
 
    imageData = []
    #Convert from list of slices to 3D array of shape (slices, row, col).
    pD3D = np.zeros((sliceCount,imageRow,imageCol),np.uint32)
    for i in range(sliceCount):
        imageData.append([])
        #Use PIL to resize, Voxel to Pixel conversion.
        imageData[i] = np.array(Image.frombuffer('I',(voxelRow,voxelCol),imageList[i],'raw','I',0,1).resize((imageCol, imageRow), Image.NEAREST),np.uint32)
        pD3D[i] = imageData[i]
        if prog[0]:
            guageCount+=1
            prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\nRe-sizing image: {0:n}".format(i+1))
        else:
            guage.Destroy()
            return

    #Create new RT-Dose file from sample.
    try:
        rtDose = copyCTtoRTDose(dicom.read_file(util.GetBasePluginsPath('rtdosesample.dcm')), ds[0], imageRow, imageCol, sliceCount, doseGridScale)
    except:
        #RT-Dose sample not found.
        try:
            rtDose = copyCTtoRTDose(dicom.read_file(util.GetBasePluginsPath('g4dose/rtdosesample.dcm')), ds[0], imageRow, imageCol, sliceCount, doseGridScale)
        except:
            dial = wx.MessageDialog(None, 'Could not load sample RT-Dose.dcm!\nPlease see documentation', 'Error', wx.OK | wx.ICON_ERROR)
            dial.ShowModal()
            guageCount+=1
            guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\n")
            return
        
    #Store images in pixel_array(int) & Pixel Data(raw).  
    rtDose.pixel_array = pD3D
    rtDose.PixelData = pD3D.tostring()

    #Close progress bar.
    guageCount+=1
    prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\n")
    guage.Destroy()
    
    return rtDose,rxdose

def copyCTtoRTDose(rtdose,ds,imageRow,imageCol, sliceCount,dgs):

    #No DICOM object standard...
    
##    rtdose.InstanceCreationDate = ds.InstanceCreationDate
##    rtdose.InstanceCreationTime = ds.InstanceCreationTime
    rtdose.SOPInstanceUID = ds.SOPInstanceUID
##    rtdose.StudyDate = ds.StudyDate
##    rtdose.StudyTime = ds.StudyTime
##    rtdose.AccessionNumber = ds.AccessionNumber
##    rtdose.Manufacturer = ds.Manufacturer
##    rtdose.ReferringPhysiciansName = ds.ReferringPhysiciansName
##    rtdose.StationName = ds.StationName
    rtdose.PatientsName = ds.PatientsName
    rtdose.PatientID = ds.PatientID
    rtdose.PatientsBirthDate = ds.PatientsBirthDate
    rtdose.PatientsSex = ds.PatientsSex
##    rtdose.SliceThickness = ds.SliceThickness
##    rtdose.SoftwareVersions = ds.SoftwareVersions
    rtdose.StudyInstanceUID = ds.StudyInstanceUID
    rtdose.SeriesInstanceUID = ds.SeriesInstanceUID
    rtdose.StudyID = ds.StudyID
    rtdose.SeriesNumber = ds.SeriesNumber
    rtdose.InstanceNumber = ds.InstanceNumber
    #Image info.
    rtdose.ImagePositionPatient = ds.ImagePositionPatient
    rtdose.ImageOrientationPatient = ds.ImageOrientationPatient
    rtdose.FrameofReferenceUID = ds.FrameofReferenceUID
    rtdose.PositionReferenceIndicator = ds.PositionReferenceIndicator
    rtdose.PixelSpacing = ds.PixelSpacing
    rtdose.SamplesperPixel = 1
    rtdose.PhotometricInterpretation = 'MONOCHROME2'
    rtdose.NumberofFrames = sliceCount
    rtdose.Rows =  imageRow
    rtdose.Columns = imageCol
    rtdose.BitsAllocated = 32
    rtdose.BitsStored = 32
    rtdose.HighBit =31
    rtdose.PixelRepresentation = 0
    rtdose.DoseUnits = 'GY'
    rtdose.DoseType = 'PHYSICAL'
    rtdose.DoseSummationType = 'FRACTION'
    rtdose.GridFrameOffsetVector = list(rtdose.ImagePositionPatient[2]+np.arange(ds.SliceLocation,ds.SliceLocation-sliceCount*ds.SpacingBetweenSlices,-ds.SpacingBetweenSlices))
    rtdose.DoseGridScaling = dgs
##    del rtdose.ReferencedRTPlans
    
    return rtdose
