import sys
from os.path import dirname, basename, join
from glob import glob
from types import TypeType, BooleanType


##############################################################################
def bool_valuator(val):
    if type(val)==BooleanType: return val
    lowerstr = val.lower()
    if lowerstr == "true": return True
    elif lowerstr == "false": return False
    else: raise ValueError(
      "Invalid boolean specifier '%s'. Must be either 'true' or 'false'."%\
      lowerstr)


##############################################################################
class Parameter (object):
    """
    Specifies a named, typed parameter for an Operation.  Is used for
    documentation and during config parsing.
    """

    # map type spec to callable type constructor
    _type_map = {
      "str":str,
      "bool":bool_valuator,
      "int":int,
      "float":float,
      "complex":complex}

    #-------------------------------------------------------------------------
    def __init__(self, name, type="str", default=None, description=""):
        self.name=name
        if not self._type_map.has_key(type):
            raise ValueError("type must be one of %s"%self._type_map.keys())
        self.valuator=self._type_map[type]
        self.default=default
        self.description=description

    #-------------------------------------------------------------------------
    def valuate(self, valspec): return self.valuator(valspec)


##############################################################################
class Operation (object):
    "Base class for image operations."

    class ConfigError (Exception): pass

    params=()

    #-------------------------------------------------------------------------
    def __init__(self, **kwargs): self.configure(**kwargs)

    #-------------------------------------------------------------------------
    def configure(self, **kwargs):
        for p in self.params:
            self.__dict__[p.name] = p.valuate(kwargs.pop(p.name, p.default))

        # All valid args should have been popped off the kwargs dict at this
        # point.  If any are left, it means they are not valid parameters for
        # this operation.
        leftovers = kwargs.keys()
        if leftovers:
            raise self.ConfigError("Invalid parameter '%s' for operation %s"%
              (leftovers[0], self.__class__.__name__))

    #-------------------------------------------------------------------------
    def log(self, message):
        print "[%s]: %s"%(self.__class__.__name__, message)

    #-------------------------------------------------------------------------
    def run(self, image): pass


##############################################################################
class RunLogger (object):
    """
    """

    # what command is used to run the executable log
    _magic_string = "#!/usr/bin/env runops"

    #-------------------------------------------------------------------------
    def __init__(self, ostream=sys.stdout):
        self.ostream = ostream
        print >> self.ostream, self._magic_string

    #-------------------------------------------------------------------------
    def _format_doc(self, doc):
        for line in (doc or "").splitlines():
            line = line.strip()
            if line: print >> self.ostream, "#", line

    #-------------------------------------------------------------------------
    def logop(self, operation):
        self._format_doc(operation.__class__.__doc__)
        print >> self.ostream, "[%s]"%operation.__class__.__name__
        for parameter in operation.params:
            self._format_doc(parameter.description)
            paramval = getattr(operation, parameter.name)
            print >> self.ostream, "%s = %s"%(parameter.name, paramval)
        print >> self.ostream


##############################################################################
class OperationManager (object):
    """
    This class is responsible for knowing which operations are available
    and retrieving them by name.  It should be a global singleton in the
    system.
    """
    class InvalidOperationName (Exception): pass
    class DuplicateOperationName (Exception): pass

    #-------------------------------------------------------------------------
    def __init__(self):
        self._op_index = {}
        self._load_operation_index()

    #-------------------------------------------------------------------------
    def _load_operation_index(self):
        for opmodule in self._get_operation_modules():
            for name, obj in opmodule.__dict__.items():
                if type(obj)==TypeType and issubclass(obj, Operation) \
                  and obj is not Operation:
                    if self._op_index.has_key(name):
                        raise self.DuplicateOperationName(name)
                    self._op_index[name] = obj

    #-------------------------------------------------------------------------
    def _get_operation_modules(self):
        opfiles = glob(join(dirname(__file__), "*.py"))
        opmodules = []
        for opfile in opfiles:
            opmodname = basename(opfile).split(".")[0]
            full_opmodname = "imaging.operations.%s"%opmodname
            opmodules.append(__import__(full_opmodname,{},{},[opmodname]))
        return opmodules

    #-------------------------------------------------------------------------
    def getOperationNames(self):
        "@return list of valid operation names."
        names = self._op_index.keys()
        names.sort()
        return names

    #-------------------------------------------------------------------------
    def getOperation(self, opname):
        "@return the operation for the given name"
        operation = self._op_index.get(opname, None)
        if not operation:
            raise self.InvalidOperationName("Operation '%s' not found."%opname)
        return operation
