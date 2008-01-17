"This module implements details of the Analyze7.5 file format."
import numpy as N
import struct
import sys
from odict import odict
from recon.util import struct_unpack, struct_pack, NATIVE, LITTLE_ENDIAN,\
  BIG_ENDIAN, Quaternion, range_exceeds, integer_ranges
from recon.imageio import ReconImage

# datatype is a bit flag into the datatype identification byte of the Analyze
# header. 
UBYTE = 2
SHORT = 4
INTEGER = 8
FLOAT = 16
COMPLEX = 32
DOUBLE = 64

# map Analyze datatype to numpy dtype
datatype2dtype = {
  UBYTE: N.dtype(N.uint8),
  SHORT: N.dtype(N.int16),
  INTEGER: N.dtype(N.int32),
  FLOAT: N.dtype(N.float32),
  DOUBLE: N.dtype(N.float64),
  COMPLEX: N.dtype(N.complex64)}

# map numpy dtype to Analyze datatype
dtype2datatype = \
  dict([(v,k) for k,v in datatype2dtype.items()])


datatype2bitpix = dict([(dc, dt.itemsize*8)
                        for dc,dt in datatype2dtype.items()])

orientname2orientcode = {
    "radiological": 0,
    "coronal": 1,
    "saggital": 2,
    "transverse": 3,
    "coronal_flipped": 4,
    "saggital_flipped": 5,
    }

orientcode2orientname = dict([(v,k) for k,v in orientname2orientcode.items()])

# these are supposed to xform the current image into [R,A,S]
# such that R*[X,Y,Z]^T = [R,A,S]^T
# this is opposite the ANALYZE system in handedness
xforms = {
    "radiological": N.array([[-1., 0., 0.],
                             [ 0., 1., 0.],
                             [ 0., 0., 1.],]),
    "transverse": N.array([[-1., 0., 0.],
                           [ 0.,-1., 0.],
                           [ 0., 0., 1.],]),
    "coronal": N.array([[-1., 0., 0.],
                        [ 0., 0., 1.],
                        [ 0., 1., 0.],]),
    "coronal_flipped": N.array([[-1., 0., 0.],
                                [ 0., 0., 1.],
                                [ 0.,-1., 0.]],),

    "saggital": N.array([[ 0., 0.,-1.],
                         [ 1., 0., 0.],
                         [ 0., 1., 0.],]),

    "saggital_flipped": N.array([[ 0., 0.,-1.],
                                 [ 1., 0., 0.],
                                 [ 0.,-1., 0.],]),

    }

def canonical_orient(xform):
    N.putmask(xform, abs(xform) < .0001, 0)
    for k,v in xforms.items():
        if (xform==v).all():
            return k
    return ""

# what is native and what is swapped?
byteorders = {
    sys.byteorder: sys.byteorder=='little' and LITTLE_ENDIAN or BIG_ENDIAN,
    'swapped': sys.byteorder=='little' and BIG_ENDIAN or LITTLE_ENDIAN
    }

HEADER_SIZE = 348
struct_fields = odict((
    ('sizeof_hdr','i'),
    ('data_type','10s'),
    ('db_name','18s'),
    ('extents','i'),
    ('session_error','h'),
    ('regular','c'),
    ('hkey_un0','c'),
    ('ndim','h'),
    ('idim','h'),
    ('jdim','h'),
    ('kdim','h'),
    ('tdim','h'),
    ('dim5','h'),
    ('dim6','h'),
    ('dim7','h'),
    ('vox_units','4s'),
    ('cal_units','8s'),
    ('unused1','h'),
    ('datatype','h'),
    ('bitpix','h'),
    ('dim_un0','h'),
    ('pixdim0','f'),
    ('isize','f'),
    ('jsize','f'),
    ('ksize','f'),
    ('tsize','f'),
    ('pixdim5','f'),
    ('pixdim6','f'),
    ('pixdim7','f'),
    ('vox_offset','f'),
    ('scale_factor','f'),
    ('funused2','f'),
    ('funused3','f'),
    ('cal_max','f'),
    ('cal_min','f'),
    ('compressed','i'),
    ('verified','i'),
    ('glmax','i'),
    ('glmin','i'),
    ('descrip','80s'),
    ('aux_file','24s'),
    ('orient','B'),
    ('x0','h'),
    ('y0','h'),
    ('z0','h'),
    ('sunused','4s'),
    ('generated','10s'),
    ('scannum','10s'),
    ('patient_id','10s'),
    ('exp_date','10s'),
    ('exp_time','10s'),
    ('hist_un0','3s'),
    ('views','i'),
    ('vols_added','i'),
    ('start_field','i'),
    ('field_skip','i'),
    ('omax','i'),
    ('omin','i'),
    ('smax','i'),
    ('smin','i')))

field_formats = struct_fields.values()


##############################################################################
class AnalyzeReader:
    """
    Loads image data from an ANALYZE 7.5 file.
    """

    #-------------------------------------------------------------------------
    def __init__(self, filestem, target_dtype=None, vrange=()):
        self.load_header(filestem+".hdr")
        self.load_image(filestem+".img", target_dtype, vrange)

    #-------------------------------------------------------------------------
    def load_header(self, filename):
        "Load Analyze7.5 header from the given filename"

        # Determine byte order of the header.  The first header element is the
        # header size.  It should always be 384.  If it is not then you know
        # you read it in the wrong byte order.

        byte_order = byteorders[sys.byteorder]
        self.swapped = False
        reported_length = struct_unpack(file(filename),
          byte_order, field_formats[0:1])[0]
        if reported_length != HEADER_SIZE:
            byte_order = byteorders['swapped']
            self.swapped=True

        # unpack all header values
        values = struct_unpack(file(filename), byte_order, field_formats)

        # now load values into self
        hd_vals = dict()
        map(hd_vals.__setitem__, struct_fields.keys(), values)
        self.__dict__.update(hd_vals)
    #-------------------------------------------------------------------------
    def load_image(self, filename, target_dtype, vrange):
        # bytes per pixel
        bytepix = self.bitpix/8
        numtype = datatype2dtype[self.datatype]
        byteoffset = 0
        if target_dtype is not None and \
               not range_exceeds(target_dtype, numtype):
            raise ValueError("the dynamic range of the desired datatype does "\
                             "not exceed that of the raw data")            
        # need to cook tdim if vrange is set
        if self.tdim and vrange:
            vend = (vrange[1]<0 or vrange[1]>=self.tdim) \
                   and self.tdim-1 or vrange[1]
            vstart = (vrange[0] > vend) and vend or vrange[0]
            self.tdim = vend-vstart+1
            byteoffset = vstart*bytepix*N.product((self.kdim,
                                                   self.jdim,self.idim))

        dims = self.tdim > 1 and (self.tdim, self.kdim, self.jdim, self.idim) \
               or (self.kdim, self.jdim, self.idim)
        datasize = bytepix * N.product(dims)
        fp = file(filename)
        fp.seek(byteoffset, 1)
        data = N.fromstring(fp.read(datasize),numtype).reshape(dims)
        if self.swapped: data = data.byteswap()
        if target_dtype is not None and target_dtype != numtype:
            if target_dtype not in integer_ranges.keys():
                scale = self.scale_factor or 1.0
                self.data = (data*scale).astype(target_dtype)
            else:
                self.data = data.astype(target_dtype)
        else:
            self.data = data
        fp.close()
    #-------------------------------------------------------------------------
    def toImage(self):
        orient_name = orientcode2orientname.get(self.orient, "")
        M = xforms.get(orient_name, N.identity(3))
        quat = Quaternion(M=M)
        offset_ana = N.array([self.x0*self.isize, self.y0*self.jsize,
                              self.z0*self.ksize])
        offset = -N.dot(M, offset_ana)
        dimlengths = N.array([self.ksize, self.jsize, self.isize]) * \
                     N.array(self.data.shape[-3:])
        # sanity check: if the offset values were funky, don't try to set it
        if not (N.abs(offset*2) < dimlengths).all():
            offset = None
        return ReconImage(self.data.copy(), self.isize, self.jsize,
                          self.ksize, self.tsize, offset=offset,
                          scaling=(self.scale_factor or 1.0),
                          orient_xform=quat, orient_name=orient_name)

##############################################################################
class AnalyzeWriter (object):
    """
    Write a given image into a single Analyze7.5 format hdr/img pair.
    """

    #[STATIC]
    _defaults_for_fieldname = {
      'sizeof_hdr': HEADER_SIZE,
      'extents': 16384,
      'regular': 'r',
      'hkey_un0': ' ',
      'vox_units': 'mm',
      'scale_factor':1.}
    #[STATIC]
    _defaults_for_descriptor = {'i': 0, 'h': 0, 'f': 0., 'c': '\0', 's': ''}

    #-------------------------------------------------------------------------
    def __init__(self, image, dtype=None, scale=1.0):
        self.image = image
        self.scaling = scale
        if dtype is None:
            dtype = image[:].dtype
        self.datatype = dtype2datatype.get(dtype, None)
        if not self.datatype:
            raise ValueError("This data type is not supported by the "\
                             "ANALYZE format: %s"%dtype)
        self._dataview = _construct_dataview(image[:].dtype,
                                             dtype, self.scaling)
    #-------------------------------------------------------------------------
    def _default_field_value(self, fieldname, fieldformat):
        "[STATIC] Get the default value for the given field."
        return self._defaults_for_fieldname.get(fieldname, None) or \
               self._defaults_for_descriptor[fieldformat[-1]]
    #-------------------------------------------------------------------------
    def write(self, filestem):
        "Write ANALYZE format header, image file pair."
        headername, imagename = "%s.hdr"%filestem, "%s.img"%filestem
        self.write_hdr(headername)
        self.write_img(imagename)

    #-------------------------------------------------------------------------
    def write_hdr(self, filename):
        "Write ANALYZE format header (.hdr) file."
        image = self.image

        # NOT IMPLEMENTING YET
        # ReconImage r0 is the offset in xyz-space, but ANALYZE
        # calls for an offset in vox-space
        inv_xform = N.linalg.inv(image.orientation_xform.tomatrix())
        r0 = N.array([image.x0, image.y0, image.z0])
        dimscl = N.array([image.isize, image.jsize, image.ksize])
        r0_ana = (-N.dot(inv_xform, r0)/dimscl).astype(N.int16)

        dtype = datatype2dtype[self.datatype]
        if dtype in N.sctypes['int']:
            glmax = 2**(datatype2bitpix[self.datatype]-1) - 1
        elif dtype in N.sctypes['uint']:
            glmax = 2**(datatype2bitpix[self.datatype]) - 1
        else:
            glmax = 1
        imagevalues = {
          'datatype': self.datatype,
          'bitpix': datatype2bitpix[self.datatype],
          # should be 4 for (z,y,x) and (t,z,y,x) ...
          # should be 3 for (y,x) ??
          'ndim': (image.ndim >= 3 and 4 or image.ndim),
          'idim': image.idim,
          'jdim': image.jdim,
          'kdim': image.kdim,
          'tdim': (image.tdim or 1),
          'isize': image.isize,
          'jsize': image.jsize,
          'ksize': image.ksize,
          'tsize': image.tsize,
          'x0': r0_ana[0],
          'y0': r0_ana[1],
          'z0': r0_ana[2],
          'scale_factor': self.scaling,
          # SPM says that these are (0,2^bitpix-1) for integers,
          # or (0,1) for floating points
          'glmin': 0,
          'glmax': glmax,
          'cal_min': 0.0, # don't suggest display color mapping
          'cal_max': 0.0,
          'orient': orientname2orientcode.get(image.orientation,255),
        }

        def fieldvalue(fieldname, fieldformat):
            if imagevalues.has_key(fieldname):
                return imagevalues[fieldname]
            return self._default_field_value(fieldname, fieldformat)

        fieldvalues = [fieldvalue(*field) for field in struct_fields.items()]
        header = struct_pack(NATIVE, field_formats, fieldvalues)
        file(filename,'w').write(header)

    #-------------------------------------------------------------------------
    def write_img(self, filename):
        "Write ANALYZE format image (.img) file."
        # Write the image file.
        f = file(filename, "w")
        f.write(self._dataview(self.image[:]).tostring())
        f.close()

#-----------------------------------------------------------------------------
def _construct_dataview(static_dtype, new_dtype, scaling):
    xform = lambda d: d
    if static_dtype in N.sctypes['complex'] and \
       new_dtype not in N.sctypes['complex']:
        xform = lambda d: abs(d)
    if scaling != 1.0:
        # assume that this will need to be rounded to Int, so add 0.5
        xform = lambda d,g=xform: g(d)/scaling + 0.5
    xform = lambda d, g=xform: g(d).astype(new_dtype)
    return xform

#-----------------------------------------------------------------------------
def readImage(filename, **kwargs):
    return AnalyzeReader(filename, **kwargs).toImage()
#-----------------------------------------------------------------------------
def writeImage(image, filestem, **kwargs):
    AnalyzeWriter(image,**kwargs).write(filestem)
