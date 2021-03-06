# now visualization is a module ...
import numpy as np
def iscomplex(a): return a.dtype.kind is 'c'

# Transforms for viewing different aspects of complex data
def ident_xform(data): return data
def abs_xform(data): return np.abs(data)
def phs_xform(data): return np.angle(data)
def real_xform(data): return data.real
def imag_xform(data): return data.imag

# utility functions
def ask_fname(parent, prompt, action="save", filter=None):
    import gtk
    mode = {
        "save": gtk.FILE_CHOOSER_ACTION_SAVE,
        "open": gtk.FILE_CHOOSER_ACTION_OPEN,
        "folder": gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        }.get(action)
    dialog = gtk.FileChooserDialog(
        title=prompt,
        action=mode,
        parent=parent,
        buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                 gtk.STOCK_OK,gtk.RESPONSE_OK)
        )
    if filter:
        if type(filter) is type([]):
            for f in filter:
                dialog.add_filter(f)
        else:
            dialog.add_filter(filter)
    response = dialog.run()
    if response == gtk.RESPONSE_CANCEL:
        dialog.destroy()
        return
    fname = dialog.get_filename()
    dialog.destroy()
    return fname

def byte_normalized(arr, dim):
    """From arr, returns an unsigned byte normalized array
    suitable for plotting.
    """
    pass

def abs_max_normalize(arr, dim):
    """From arr, returns an array that is normalized to the
    maximum absolute value per subarray along dim.
    """
    pass
    
