import numpy as np
import unittest
import scipy.weave
from scipy.weave import converters

CODE = """
    #line 7 "trilinear.py"    
    int num_ind_x = Nindices(1);
    int num_ind_y = Nindices(2);
    int num_ind_z = Nindices(3);
    int arr_rows = Narr(0);
    int arr_cols = Narr(1);
    int arr_depth = Narr(2);
    double x, y, z;
    int x0, y0, z0;
    int x1, y1, z1;
    double xval, yval, zval;
    for (int i=0; i<num_ind_x; ++i){
        for (int j=0; j<num_ind_y; ++j){
            for (int k=0; k<num_ind_z; ++k){
        x = indices(0, i, j, k);
        y = indices(1, i, j, k);
        z = indices(2, i, j, k);
        x0 = int(x);
        y0 = int(y);
        z0 = int(z);
        x1 = x0 + 1;
        y1 = y0 + 1;
        z1 = z0 + 1;
        if (x1 == arr_rows) {
            x1 = x0;
            }
        if (y1 == arr_cols) {
            y1 = y0;
            }
        if (z1 == arr_depth) {
            z1 = z0;
            }
        xval = ((double) x - x0);
        yval = ((double) y - y0);
        zval = ((double) z - z0);
        output(i,j,k) = 
            arr(x0, y0, z0)*(1.0-xval)*(1.0-yval)*(1.0-zval)+
            arr(x1, y0, z0)*xval*(1.0-yval)*(1.0-zval)+
            arr(x0, y1, z0)*(1.0-xval)*yval*(1.0-zval) +
            arr(x0, y0, z1)*(1.0-xval)*(1.0-yval)*zval +
            arr(x1, y0, z1)*xval*(1.0-yval)*zval +
            arr(x0, y1, z1)*(1.0-xval)*yval*zval +
            arr(x1, y1, z0)*xval*yval*(1.0-zval) +
            arr(x1, y1, z1)*xval*yval*zval;
        }}}
       """    
       
def trilinear(arr, indices, output):
    
    scipy.weave.inline(CODE, ['arr', 'indices', 'output'], 
                       type_converters=converters.blitz)
    return output
    
def build_trilinear():
    
    mod = scipy.weave.ext_tools.ext_module('trilinear')
    arr = np.array([[[0]]], np.uint32)
    indices = np.array([[[[0.]]]], np.float64)
    output = np.array([[[0.]]], np.float64)
    
    trilinear = scipy.weave.ext_tools.ext_function('trilinear',
               CODE, ['arr', 'indices', 'output'], 
               type_converters=converters.blitz)
    
    mod.add_function(trilinear)
    mod.compile()
    
    
class InterpTest(unittest.TestCase):
    
    def testMethod(self):
        import scipy.ndimage
        a = np.arange(24000.).reshape((40,30,20))
        i,j,k = np.mgrid[0:39,0:29,0:19]
        
        #Create a 3 x i x j x k array of xyz coordinates for the interpolation.
        b = np.array([i,j,k])
        c = scipy.ndimage.map_coordinates(a, b, order = 1)
        d = np.zeros(b[0].shape, dtype=np.float32)
        trilinear(a,b,d)
        for i in np.ndindex(c.shape):
            self.assertAlmostEqual(c[i],d[i])
    
    
if __name__ == "__main__":
    #unittest.main()   
    build_trilinear()
