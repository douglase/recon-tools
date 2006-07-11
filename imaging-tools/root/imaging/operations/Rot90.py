"""
This module defines a rotation on all slices, putting them into standard
radiological format.
"""
from pylab import reshape, rot90, flipud
from imaging.operations import Operation, Parameter
from imaging.imageio import BaseImage

##############################################################################
class Rot90 (Operation):
    """
    This class operatates slice-by-slice to rotate the images so that they are
    in radiological or neurological format.
    """

    params = (Parameter(name="orient", type="str", default="radiological",
                        description="determines data orientation, can be "\
                        "radiological or neurological"),
              )

    # x-size/y-size swap is not yet reflected

    def run(self, image):
        data = image.data
        dshape = data.shape
        if self.orient.lower()=='radiological':
            # psi = 90
            xform = lambda x: rot90(x)
        else:
            # psi = 90 * theta = 180
            xform = lambda x: rot90(flipud(x))
        for vol in data:
            for slice in vol:
                rotated = xform(slice)
                slice = reshape(slice, rotated.shape)
                slice[:] = rotated.copy()
        data = reshape(data, (dshape[0],dshape[1],rotated.shape[0],
                              rotated.shape[1]))
        image.setData(data)
        image.noteRot()
