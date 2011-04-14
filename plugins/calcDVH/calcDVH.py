import dicomgui

import wx
from wx.lib.pubsub import Publisher as pub
import os
import numpy as np
import scipy.ndimage
import matplotlib.nxutils as nx


def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'Calc DVH'
    props['description'] = "Recalculates DVHs if RTDose changes."
    props['author'] = 'Stephen Terry'
    props['version'] = 0.1
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = ['rtdose','rtss']
    props['recommended_dicom'] = ['rtdose','rtss']

    return props

class plugin:
    
    def __init__(self, parent):
        
        self.parent = parent
        
        # Set up pubsub
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.parsed_data')
        
    def OnUpdatePatient(self, msg):
        """Update and load the patient data."""
        if msg.data.has_key('rtdose'):
            self.rtdose = msg.data['rtdose']
        if msg.data.has_key('structures'):
            self.structures = msg.data['structures']
        if msg.data.has_key('dvhs'):
            self.dvhs = msg.data['dvhs']
        if msg.data.has_key('images'):
            self.images = msg.data['images']

    def pluginMenu(self, evt):
        self.CalculateDVH(self.structures[11])

    def CalculateDVH(self, structure):
    
        sPlanes = structure['planes']
        
        #Define coarseness of grid for sampling dose (in mm)
        scaling = 1
        
        n = 0
        z_offset = np.array([float(x) for x in self.rtdose.GridFrameOffsetVector])
        voxel_doses = np.array([])
        #volume = 0.
        voxel_volume = (scaling*scaling*(z_offset[1] - z_offset[0]))/1000.
        dose_scaling = [self.rtdose.PixelSpacing[0],
                        self.rtdose.PixelSpacing[1],
                        z_offset[1] - z_offset[0]]
        
        # Iterate over each plane in the structure
        for sPlane in sPlanes.itervalues():
            contours = []
            for c, contour in enumerate(sPlane):
                # Create arrays for the x,y coordinate pair for the triangulation
                x = []
                y = []
                for point in contour['contourData']:
                    x.append(point[0])
                    y.append(point[1])
    
                contours.append({'data':contour['contourData']})
                
            
            z = sPlane[0]['contourData'][0][2]

            #Create grid of indices that encompasses the contour
            xrange = 1 + (np.ceil(np.max(x)) - np.floor(np.min(x)))/scaling
            yrange = 1 + (np.ceil(np.max(y)) - np.floor(np.min(y)))/scaling
            
            #Define functions for converting between xyz space and index (ijk) space
            scale_x = lambda a: a*scaling + np.floor(np.min(x))
            scale_y = lambda a: a*scaling + np.floor(np.min(y))
            
            grid = np.indices((np.ceil(xrange),np.ceil(yrange)))
            idx = np.array(zip(grid[0].ravel(), grid[1].ravel()))
            xy = np.array(zip(scale_x(grid[0].ravel()), scale_y(grid[1].ravel())))
            
            #If the dose point is within an odd number of contours,
            #then it is assumed to be within the structure
            num_of_contours = np.zeros(len(idx))
            for contour in contours:
                xy_poly = np.array([(a[0],a[1]) for a in contour['data']])
                tmp = nx.points_inside_poly(xy, xy_poly)
                num_of_contours += nx.points_inside_poly(xy, xy_poly)
            
                in_structure = (num_of_contours % 2).astype('int')
                #in_structure = nx.points_inside_poly(xy, xy_poly)
            
            

            for x_it,y_it in xy[in_structure]:
                
                voxel_doses = np.append(voxel_doses, self._interpolate_image(
                                np.swapaxes(self.rtdose.pixel_array,0,2),
                                dose_scaling,self.rtdose.ImagePositionPatient,
                                np.array([[x_it],[y_it],[z]]))*
                                self.rtdose.DoseGridScaling*100.)
                
 
        bins = np.ceil(voxel_doses.max())
        diff_dvh, bin_edges = np.histogram(voxel_doses, bins=bins,
                                range=(0.0,bins))
        cum_dvh = GenerateCDVH(bin_edges, diff_dvh*voxel_volume)
    
        pass

    def _interpolate_image(self, input_array, scale, offset, xyz_coords):
        
        indices = np.empty(xyz_coords.shape)
        indices[0] = (xyz_coords[0] - offset[0])/scale[0]
        indices[1] = (xyz_coords[1] - offset[1])/scale[1]
        indices[2] = (xyz_coords[2] - offset[2])/scale[2]            
        #return trilinear_interp(input_array, indices)
        return scipy.ndimage.map_coordinates(input_array, indices, order=1)
    
def GenerateCDVH(dose, volume):
        """Generate a cumulative DVH (cDVH) from a differential DVH (dDVH)"""



        # Get the min and max dose and volume values
        mindose = int(dose[0])
        maxdose = int(dose[-1])
        maxvol = sum(volume)

        # Determine the dose values that are missing from the original data
        missingdose = np.ones(mindose) * maxvol

        # Generate the cumulative dose and cumulative volume data
        k = 0
        cumvol = []
        cumdose = []
        while k < len(dose):
            cumvol += [sum(volume[k:])]
            cumdose += [dose[k]]
            k += 1
        cumvol = np.array(cumvol)
        cumdose = np.array(cumdose)*100

        return cumvol                
