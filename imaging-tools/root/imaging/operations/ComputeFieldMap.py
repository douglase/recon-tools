from pylab import ones, zeros, Float32, Complex32, multiply, pi, angle, conjugate
from Numeric import empty, sum
from LinearAlgebra import *
import math
from imaging.imageio import writeImage
from imaging.util import unwrap_phase, compute_fieldmap
from imaging.analyze import writeImage
from imaging.operations import Operation


#-----------------------------------------------------------------------------
def phase_offset(phase):
    nvoxels = multiply.reduce(phase.shape)
    return sum(phase.flat)/(nvoxels*2*pi)

##############################################################################
class ComputeFieldMap (Operation):
    "Perform phase unwrapping and calculate field map"

    #-------------------------------------------------------------------------
    def run(self, image):

        # Make sure it's an asems image
        if not hasattr(image._procpar, "asym_time"):
            self.log("No asym_time, can't compute field map.")
            return
        asym_time = image._procpar.asym_time[1]

        # Make sure there are at least two volumes
        if image.tdim < 2:
            self.log("Cannot calculate field map from only a single volume."\
                     "  Must have at least two volumes.")
            return

        # Unwrap phases.
        diff_vols = zeros((image.tdim-1,image.zdim,image.ydim,image.xdim), Complex32)
        for vol in range(image.tdim-1):
            diff_vols[vol] = image.data[vol]*conjugate(image.data[vol+1])
        fmap_image = image._subimage(diff_vols)    
        fmap_phase = unwrap_phase(fmap_image)
        fmap_phase.data = (fmap_phase.data/asym_time).astype(Float32)
        for index, subIm in enumerate(fmap_phase.subImages()):
            writeImage(subIm, "fieldmap-%d"%(index))
