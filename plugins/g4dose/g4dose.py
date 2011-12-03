# g4dose.py
# G4 RT-Dose plugin for dicompyler.
# Copyright (c) 2011 Derek M. Tishler, Brian P. Tonner, and dicompyler contributors.
"""
Create RT Dose file from a GEANT4 or GAMOS DICOM phantom RT simulation utilizing
dose scoring with the GmPSPrinter3ddose or GmPSPrinterG4cout printers.
"""
# All rights reserved, released under a BSD license.
#    See the file license.txt included with this distribution, available at:
#    http://code.google.com/p/dicompyler-plugins/source/browse/plugins/g4dose/license.txt

#Requires wxPython, pyDicom, numpy, PIL.
import wx
from   wx.lib.pubsub import Publisher as pub
import dicom
from   dicom.dataset import Dataset, FileDataset
import os
import numpy as np
from   PIL import Image
import util
import fnmatch

def pluginProperties():

    props = {}
    props['name'] = 'G4 RT-Dose'
    props['description'] = "View RT-Dose from a Geant4/Gamos DICOM simulation."
    props['author'] = 'D.M. Tishler & B.P. Tonner'
    props['version'] = 0.4
    props['documentation'] = 'http://code.google.com/p/dicompyler-plugins/wiki/g4dose'
    props['license'] = 'license.txt'
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = ['images']
    props['recommended_dicom'] =  ['images','rtdose']

    return props

class plugin():

    def __init__(self, parent):
        
        #Set subscriptions
        self.parent = parent
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')

    def OnUpdatePatient(self, msg):
        
        #Update data from pubsub.
        self.data = msg.data

    def addElement(self, tup):
        
        #Publish/broadcast the RT-Dose and rxdose.
        if tup:
            self.data.update({'rtdose':tup[0]})
            self.data.update({'rxdose':tup[1]})
        pub.sendMessage('patient.updated.raw_data', self.data)

    def pluginMenu(self, evt):

        #Temp GUI for file handling.
        msg  = "Please select Dose File."
        loop = True
        while loop:
            loop   = False
            #Select Dose file & Data.dat
            dirdlg = wx.FileDialog(self.parent, msg, defaultFile='dicom or 3ddose')
            if dirdlg.ShowModal() == wx.ID_OK:
                pathDose   = dirdlg.GetPath()
                patientDir = os.path.dirname(pathDose)
                #Confirm G4 simulation input and output files are found.
                if fnmatch.fnmatch(pathDose, '*3ddose*'):
                    # Dose file from printer: GmPSPrinter3ddose
                    #Parse dose file, create RT-Dose DICOM object, broadcast RT-Dose.
                    self.addElement(loadGamos3ddose(patientDir, pathDose, self.data['images']))
                    loop = False
                    break
                elif fnmatch.fnmatch(pathDose, '*dicom*'):
                    # Data.dat required for only GmPSPrinterG4cout
                    msg  = "Please select Data.dat" 
                    loop2 = True
                    while loop2:
                        loop2  = False
                        #Select Dose file & Data.dat
                        dirdlg = wx.FileDialog(self.parent,msg)
                        if dirdlg.ShowModal() == wx.ID_OK:
                            pathData   = dirdlg.GetPath()
                            patientDir = os.path.dirname(pathData) 
                            #Confirm G4 simulation input and output files are found.
                            if fnmatch.fnmatch(pathData, '*Data.dat'):
                                loop2 = False
                                break
                            else: 
                                msg  = "Data.dat required!"
                                loop2 = True
                        dirdlg.Destroy()
                    #Parse dose file, create RT-Dose DICOM object, broadcast RT-Dose.
                    self.addElement(loadG4DoseGraph(patientDir, pathData, pathDose, self.data['images']))
                    loop = False
                    break
                else: 
                    msg  = "Dose file required."
                    loop = True
            dirdlg.Destroy()

#Handle GmPSPrinter3ddose printer output
def loadGamos3ddose(ptPath, doseFile, ds):
    
    #Open DOSXYZ dose file for phantom w/ slices in z dir.
    DoseFile = open(doseFile,'r')
    
    #First line is the number of events
    NumEvents = float(DoseFile.readline())
    #Voxels is list [NX, NY, NZ]
    temp  = DoseFile.readline()  #Get Voxel dimensions
    temp  = temp.strip('\n')     #Strip linefeed
    [NX,NY,NZ] = [int(x) for x in temp.split()]
    #Get the coordinates of the x positions
    temp  = DoseFile.readline()
    temp  = temp.strip('\n')
    XVals =[float(x) for x in temp.split()]
    #Get the coordinates of the y positions
    temp  = DoseFile.readline()
    temp  = temp.strip('\n')
    YVals = [float(x) for x in temp.split()]
    #Get the coordinates of the z positions
    temp  = DoseFile.readline()
    temp  = temp.strip('\n')
    ZVals = [float(x) for x in temp.split()]

    #Create and fill 3d dose array.
    DoseData = np.zeros((NX,NY,NZ),float)
    for iz in range(0,NZ,1):
        for iy in range (0,NY,1):
            #Read in one line of x values
            temp = DoseFile.readline()
            temp = temp.strip('\n')
            row  = temp.split()
            DoseData[:,iy,iz] = row

    #Image dimensions(Pixels). NY,NX represent voxel image dimensions.
    imageCol = ds[0].pixel_array.shape[0]
    imageRow = ds[0].pixel_array.shape[1]

    #Caluculate DGS.
    Max = np.max(DoseData)
    doseGridScale = float(Max/65535.)
    #Set rx dose.
    rxdose = float(0.90*Max*100.)

    #Copy DoseData array for uncompressing and masking.
    DDVoxDimImage = np.uint32(DoseData/Max*65535.)*np.ones(np.shape(DoseData),np.uint32)
    DDImgDimImage = np.ones((NZ,imageRow,imageCol),np.uint32)
    
    #Uncompress dose image and position in FFS or HFS. Add more support!
    for i in range(NZ):
        DDImgDimImage[i,:,:] = np.array(Image.frombuffer('I',(NY,NX),DDVoxDimImage[:,:,i].tostring(),'raw','I',0,1)
                                    .resize((imageCol, imageRow), Image.NEAREST)
                                    .rotate(-90)
                                    .transpose(Image.FLIP_LEFT_RIGHT),np.uint32)
    
    #Create RT-Dose File and copy info from CT
    rtDose = copyCTtoRTDose(ptPath, ds[0], imageRow, imageCol, NZ, doseGridScale)
        
    #Store images in pixel_array(int) & Pixel Data(raw).  
    rtDose.pixel_array = DDImgDimImage
    rtDose.PixelData = DDImgDimImage.tostring()
    
    return rtDose,rxdose

#Handle GmPSPrinterG4cout printer output
def loadG4DoseGraph(ptPath, dataFile, doseFile, ds):

    #Load number of slices and compression value from data.dat.
    file = open(dataFile)
    compression = int(file.readline())
    sliceCount  = int(file.readline())

    #Load dosegraph from dicom.out
    doseTable   = np.loadtxt(doseFile)
    
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
    #voxel dimensions
    voxelCol = imageCol/compression
    voxelRow = imageRow/compression
    #Repeated values.
    voxelDim = voxelCol*voxelRow*sliceCount
    area     = voxelCol*voxelRow
    
    #G4 compression value error. See documentation.
    if doseTable[-1][0] > voxelDim:
        msgE = 'Compression value error in data.dat!\nPlease delete binary files and re-run GEANT4.'
        dial = wx.MessageDialog(None, msgE, 'Error', wx.OK | wx.ICON_ERROR)
        dial.ShowModal()
        guage.Destroy()
        return

    #Store images for resizing.
    imageList = list()
    for i in range(sliceCount):
        imageList.append([])
        imageList[i] = np.zeros((voxelCol,voxelRow),np.uint32)

    #Create a new rescaled dose table.
    Max = max(doseTable[:, 1])
    #Normalize dose data and prepare for LUT in dicompyler.
    scaleTable = np.ones((len(doseTable),2),np.float32)
    #4294967295,65535,255;2147483647,32767,127
    scaleTable[:, 1] = np.round((doseTable[:, 1]/Max)*65535.)
    doseTableInt = np.ones((len(doseTable), 2), np.uint32)*np.uint32(scaleTable)
    del scaleTable

    #Calculate dose grid scaling for rtdose.
    doseMax       = max(doseTableInt[:, 1])
    doseGridScale = float(Max/doseMax)
    #Set rx dose.
    rxdose        = float(0.90*Max*100.)
   
    #Unravel dose table into 3d dose array
    for index, vID in enumerate(doseTable[:, 0]):
        #Unravel the index instead of search. GO NUMPY!
        newIndex = np.unravel_index(int(vID), (sliceCount, voxelCol, voxelRow))
        imageList[newIndex[0]][newIndex[1]][newIndex[2]] = doseTableInt[index][1]
        #Update progress bar & check for abort.
        if prog[0]:
            guageCount += 1
            prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation")
        else:
            guage.Destroy()
            return
 
    #Convert from list of slices to 3D array of shape (slices, row, col).
    pD3D = np.zeros((sliceCount,imageRow,imageCol),np.uint32)
    for i in range(sliceCount):
        #Use PIL to resize, Voxel to Pixel conversion.
        pD3D[i] = np.array(Image.frombuffer('I', (voxelCol, voxelRow), imageList[i], 'raw', 'I', 0, 1)
                                           .resize((imageCol, imageRow), Image.NEAREST), np.uint32)
        #Update progress bar & check for abort.
        if prog[0]:
            guageCount += 1
            prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\nRe-sizing image: {0:n}".format(i+1))
        else:
            guage.Destroy()
            return

    #Create RT-Dose File and copy info from CT
    rtDose = copyCTtoRTDose(ptPath, ds[0], imageRow, imageCol, sliceCount, doseGridScale)
        
    #Store images in pixel_array(int) & Pixel Data(raw).  
    rtDose.pixel_array = pD3D
    rtDose.PixelData   = pD3D.tostring()

    #Close progress bar.
    guageCount += 1
    prog = guage.Update(guageCount,"Building RT-Dose from GEANT4 simulation\n")
    guage.Destroy()
    
    return rtDose,rxdose

def copyCTtoRTDose(path, ds, imageRow, imageCol, sliceCount, dgs):
    
    # Create a RTDose file for broadcasting.
    #Create header for RT-Dose object.
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = ds.file_meta.MediaStorageSOPClassUID # CT Image Storage
    # Needs valid UID
    file_meta.MediaStorageSOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    file_meta.ImplementationClassUID = ds.file_meta.ImplementationClassUID

    #create DICOM RT-Dose object.
    rtdose = FileDataset(path + '/rtdose.dcm', {}, file_meta=file_meta, preamble="\0"*128)
    
    #No DICOM object standard. Use only required to avoid error.
    rtdose.SOPInstanceUID = ds.SOPInstanceUID
    rtdose.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    rtdose.file_meta.TransferSyntaxUID = ds.file_meta.TransferSyntaxUID
    rtdose.PatientsName = ds.PatientsName
    rtdose.PatientID = ds.PatientID
    rtdose.PatientsBirthDate = ds.PatientsBirthDate
    rtdose.PatientsSex = ds.PatientsSex
##    rtdose.InstanceCreationDate = ds.InstanceCreationDate
##    rtdose.InstanceCreationTime = ds.InstanceCreationTime
##    rtdose.StudyDate = ds.StudyDate
##    rtdose.StudyTime = ds.StudyTime
##    rtdose.AccessionNumber = ds.AccessionNumber
##    rtdose.Manufacturer = ds.Manufacturer
##    rtdose.ReferringPhysiciansName = ds.ReferringPhysiciansName
##    rtdose.StationName = ds.StationName
##    rtdose.SliceThickness = ds.SliceThickness
##    rtdose.SoftwareVersions = ds.SoftwareVersions
##    rtdose.StudyInstanceUID = ds.StudyInstanceUID
##    rtdose.SeriesInstanceUID = ds.SeriesInstanceUID
##    rtdose.StudyID = ds.StudyID
##    rtdose.SeriesNumber = ds.SeriesNumber
##    rtdose.InstanceNumber = ds.InstanceNumber
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
    if not ds.has_key('SpacingBetweenSlices'):
        ds.SpacingBetweenSlices = ds.SliceThickness
    if ds.PatientPosition == 'FFS':
        rtdose.GridFrameOffsetVector = list(rtdose.ImagePositionPatient[2]+np.arange(ds.SliceLocation,ds.SliceLocation-sliceCount*ds.SpacingBetweenSlices,-ds.SpacingBetweenSlices))
    elif ds.PatientPosition == 'HFS':        
        rtdose.GridFrameOffsetVector = list(rtdose.ImagePositionPatient[2]-np.arange(ds.SliceLocation,ds.SliceLocation+sliceCount*ds.SpacingBetweenSlices,ds.SpacingBetweenSlices))
    else:
        print("Sorry: Patient Position not yet supported!")
        guage.Destroy()
        return    
    rtdose.DoseGridScaling = dgs

    #Saving: Plan tag is required to load saved rtdose file into dicompyler
##    plan_meta = Dataset()
##    rtdose.ReferencedRTPlans = []
##    rtdose.ReferencedRTPlans.append([])
##    rtdose.ReferencedRTPlans[0] = plan_meta
##    rtdose.ReferencedRTPlans[0].ReferencedSOPClassUID = 'RT Plan Storage'
##    rtdose.ReferencedRTPlans[0].ReferencedSOPInstanceUID = '1.2.123.456.78.9.0123.4567.89012345678901'
    #rtdose.save_as(path + "/RTDose.dcm")
    #print("Saving '{0:s}'".format(path + "/RTDose.dcm"))
    
    return rtdose
