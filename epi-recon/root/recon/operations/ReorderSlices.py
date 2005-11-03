from Numeric import empty
from pylab import mlab
from recon.operations import Operation, Parameter

##############################################################################
class ReorderSlices (Operation):
    "Reorder image slices from inferior to superior."

    params=(
      Parameter(name="flip_slices", type="bool", default=False,
        description="Flip slices during reordering."),)

    #-------------------------------------------------------------------------
    def run(self, options, data):
        nslice = data.nslice
        imgdata = data.data_matrix

        # Reorder the slices from inferior to superior.
        midpoint = nslice/2 + (nslice%2 and 1 or 0)
        tmp = empty(imgdata[0].shape, imgdata.typecode())
        #print "midpoint=",midpoint
        for volume in imgdata:
            # if I can get the slice indices right, these two lines can replace
            # the nine lines which follow them! - BH
            #tmp[:midpoint] = self.flip_slices and volume[::2] or volume[::-2]
            #tmp[midpoint:] = self.flip_slices and volume[1::2] or volume[-2::-2]
            for i, slice in enumerate(volume):
                if i < midpoint:
                    if self.flip_slices: z = 2*i
                    else: z = nslice - 2*i - 1
                else:
                    if self.flip_slices: z = 2*(i - midpoint) + 1
                    else: z = nslice - 2*(i - midpoint) - 2
                #print i, z
                tmp[z] = slice
            volume[:] = tmp