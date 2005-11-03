from ConfigParser import SafeConfigParser
from optparse import OptionParser, Option
from recon import FIDL_FORMAT, VOXBO_FORMAT, SPM_FORMAT,MAGNITUDE_TYPE, COMPLEX_TYPE
from recon.operations import OperationManager
from recon.FidImage import FidImage

output_format_choices = (FIDL_FORMAT, VOXBO_FORMAT, SPM_FORMAT)
output_datatype_choices= (MAGNITUDE_TYPE, COMPLEX_TYPE)


##############################################################################
class OrderedConfigParser (SafeConfigParser):
    "Config parser which keeps track of the order in which sections appear."

    #-------------------------------------------------------------------------
    def __init__(self, defaults=None):
        SafeConfigParser.__init__(self, defaults=defaults)
        import odict
        self._sections = odict.odict()


##############################################################################
class ReconOptionParser (OptionParser):
    "Parse command-line arguments to the epi_recon tool."

    #-------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        OptionParser.__init__(self, *args, **kwargs)
        self._opmanager = OperationManager()
        opnames = self._opmanager.getOperationNames()
        self.set_usage("usage: %prog [options] data output")
        self.add_options((
          Option( "-c", "--config", dest="config", type="string",
            default="recon.cfg", action="store",
            help="Name of the config file describing operations and operation"\
            " parameters."),
          Option( "-r", "--vol-range", dest="vol_range", type="string", default=":",
            action="store",
            help="Which volumes to reconstruct.  Format is start:end, where "\
            "either start or end may be omitted, indicating to start with the "\
            "first or end with the last respectively.  The index of the first "\
            "volume is 0.  The default value is a single colon with no start "\
            "or end specified, meaning process all volumes."),
          Option( "-n", "--nvol", dest="nvol_to_read", type="int", default=0,
            action="store",
            help="Number of volumes within run to reconstruct." ),
          Option( "-s", "--frames-to-skip", dest="skip", type="int", default=0,
            action="store",
            help="Number of frames to skip at beginning of run." ),
          Option( "-f", "--file-format", dest="file_format", action="store",
            type="choice", default=FIDL_FORMAT, choices=output_format_choices,
            help="""{%s}
            fidl: save floating point file with interfile and 4D analyze headers.
            spm: Save individual image for each frame in analyze format.
            voxbo: Save in tes format."""%("|".join(output_format_choices)) ),
          Option( "-p", "--phs-corr", dest="phs_corr", default="", action="store",
            help="Dan, please describe the action of this option..."),
          Option( "-a", "--save-first", dest="save_first", action="store_true",
            help="Save first frame in file named 'EPIs.cub'." ),
          Option( "-t", "--tr", dest="TR", type="float", action="store",
            help="Use the TR given here rather than the one in the procpar." ),
          Option( "-l", "--flip-left-right", dest="flip_left_right",
            action="store_true", help="Flip image about the vertical axis." ),
          Option( "-y", "--output-data-type", dest="output_data_type",
            type="choice", default=MAGNITUDE_TYPE, action="store",
            choices=output_datatype_choices,
            help="""{%s}
            Specifies whether output images should contain only magnitude or
            both the real and imaginary components (only valid for analyze
            format)."""%("|".join(output_datatype_choices)) )
        ))

    #-------------------------------------------------------------------------
    def configureOperations(self, configfile):
        """
        @return a list of operation pairs (operation, args).
        @param configfile: filename of operations config file.
        """
        config = OrderedConfigParser()
        config.read(configfile)
        return [
          (self._opmanager.getOperation(opname), dict(config.items(opname)))
          for opname in config.sections()]

    #-------------------------------------------------------------------------
    def parseVolRange(self, vol_range):
        parts = vol_range.split(":")
        if len(parts) < 2: self.error(
          "The specification of vol-range must contain a colon separating "\
          "the start index from the end index.")
        try: vol_start = int(parts[0] or 0)
        except ValueError: self.error(
          "Bad vol-range start index '%s'.  Must be an integer."%parts[0])
        try: vol_end = int(parts[1] or -1)
        except ValueError: self.error(
          "Bad vol-range end index '%s'. Must be an integer."%parts[1])
        return vol_start, vol_end

    #-------------------------------------------------------------------------
    def getOptions(self):
        """
        Bundle command-line arguments and options into a single options
        object, including a resolved list of callable data operations.
        """
        options, args = self.parse_args()
        if len(args) != 2: self.error(
          "Expecting 2 arguments: datadir ouput" )

        # treat the raw args as named options
        options.datadir, options.img_file = args

        # parse vol-range
        options.vol_start, options.vol_end = \
          self.parseVolRange(options.vol_range)

        # configure operations
        options.operations = self.configureOperations(options.config)

        return options


##############################################################################
class ReconTool (object):

    #-------------------------------------------------------------------------
    def run(self):
        "Run the epi_recon tool."
        from recon.util import save_image_data

        # Get the filename names and options from the command line.
        options = ReconOptionParser().getOptions()

        # Load data from the fid file.
        data = FidImage(options.datadir, options)

        # Log some parameter info to the console.
        self.log_params(data, options)

        # Now apply the various data manipulation and artifact correction operations
        # to the time-domain (k-space) data which is stored in the arrays
        # data_matrix and nav_data as well as the ancillary data arrays ref_data and
        # ref_nav_data. The operations are applied by looping over the list of
        # operations that the user chooses on the command line. Each operation acts
        # in a independent manner upon the data arrays.
        for operation, args in options.operations:
            operation(**args).run(options, data)

        # Save data to disk.
        save_image_data(options, data)

    #-------------------------------------------------------------------------
    def log_params(self, data, options):
        """
        Print some of the values of the options and parameters dictionaries to the
        screen. 
        """
        print "Phase encode table: ", data.petable_name
        print "Pulse sequence: %s" % data.pulse_sequence
        print "Number of volumes: %d" % data.nvol
        print "Number of slices: %d" % data.nslice
        print "Number of segments: %d" % data.nseg
        print "Number of navigator echoes per segment: %d" % data.nav_per_seg
        print "Number of phase encodes per slice (including navigators if present): %d" % data.n_pe
        print "Number of frequency encodes: %d" % data.n_fe_true
        print "Raw precision (bytes): ", data.datasize
        print "Number of volumes to skip: %d" % options.skip
        print "Orientation: %s" % data.orient
        print "Pixel size (phase-encode direction): %7.2f" % data.xsize 
        print "Pixel size (frequency-encode direction): %7.2f" % data.ysize
        print "Slice thickness: %7.2f" % data.zsize

    #-------------------------------------------------------------------------
    def load_data(self, options): return recon.VarianData(options)
