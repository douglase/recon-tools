#!/usr/bin/env python
import gtk
from pylab import Figure, figaspect, gci, show, amax, amin, squeeze, asarray, cm, angle,\
     normalize, pi, arange, meshgrid, ravel, ones, outerproduct, floor
from matplotlib.image import AxesImage
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

def iscomplex(a): return hasattr(a, "imag")

# Transforms for viewing different aspects of complex data
def ident_xform(data): return data
def abs_xform(data): return abs(data)
def phs_xform(data): return angle(data)
def real_xform(data): return data.real
def imag_xform(data): return data.imag


##############################################################################
class DimSpinner (gtk.SpinButton):

    #-------------------------------------------------------------------------
    def __init__(self, name, value, start, end, handler):
        adj = gtk.Adjustment(0, start, end, 1, 1)
        adj.name = name
        gtk.SpinButton.__init__(self, adj, 0, 0)
        adj.connect("value-changed", handler)


##############################################################################
class DimSlider (gtk.HScale):

    #-------------------------------------------------------------------------
    def __init__(self, dim_num, dim_size, dim_name):
        adj = gtk.Adjustment(0, 0, dim_size-1, 1, 1)
        adj.dim_num = dim_num
        gtk.HScale.__init__(self, adj)
        self.set_digits(0)
        self.set_value_pos(gtk.POS_RIGHT)


##############################################################################
class ControlPanel (gtk.Frame):

    #-------------------------------------------------------------------------
    def __init__(self, shape, dim_names=[], iscomplex=False):
        self._init_dimensions(shape, dim_names)
        gtk.Frame.__init__(self)
        main_vbox = gtk.VBox()
        main_vbox.set_border_width(2)

        # spinner for row dimension
        #spinner_box = gtk.HBox()
        self.row_spinner = \
          DimSpinner("row", len(shape)-2, 0, len(shape)-2, self.spinnerHandler)
        #spinner_box.add(gtk.Label("Row:"))
        #spinner_box.add(self.row_spinner)

        # spinner for column dimension
        self.col_spinner = \
          DimSpinner("col", len(shape)-1, 1, len(shape)-1, self.spinnerHandler)
        #spinner_box.add(gtk.Label("Col:"))
        #spinner_box.add(self.col_spinner)
        #main_vbox.add(spinner_box)

        # radio buttons for different aspects of complex data
        xform_map = {
          "ident": ident_xform,
          "abs": abs_xform,
          "phs": phs_xform,
          "real": real_xform,
          "imag": imag_xform}
        self.radios = []
        radio_box = gtk.HBox()
        prev_button = None
        for name in ("abs","phs","real","imag"):
            button = prev_button = gtk.RadioButton(prev_button, name)
            button.transform = xform_map[name]
            if name=="abs": button.set_active(True)
            self.radios.append(button)
            radio_box.add(button)
        if iscomplex:
            main_vbox.pack_end(radio_box, False, False, 0)
            main_vbox.pack_end(gtk.HSeparator(), False, False, 0)

        # slider for each data dimension
        self.sliders = [DimSlider(*d) for d in self.dimensions]
        for slider, dimension in zip(self.sliders, self.dimensions):
            label = gtk.Label("%s:"%dimension[2])
            label.set_alignment(0, 0.5)
            main_vbox.pack_start(label, False, False, 0)
            main_vbox.pack_start(slider, False, False, 0)

        self.add(main_vbox)

    #-------------------------------------------------------------------------
    def _init_dimensions(self, dim_sizes, dim_names):
        self.dimensions = []
        num_dims = len(dim_sizes)
        num_names = len(dim_names)
        if num_names != num_dims:
            dim_names = ["Dim %s"%i for i in range(num_dims)]
        for dim_num, (dim_size, dim_name) in\
          enumerate(zip(dim_sizes, dim_names)):
            self.dimensions.append( (dim_num, dim_size, dim_name) )
        self.slice_dims = (self.dimensions[-2][0], self.dimensions[-1][0])

    #-------------------------------------------------------------------------
    def connect(self, spinner_handler, radio_handler, slider_handler):
        # connect spinners
        self.row_spinner.get_adjustment().connect(
          "value-changed", spinner_handler)
        self.col_spinner.get_adjustment().connect(
          "value-changed", spinner_handler)

        # connect radio buttons
        for r in self.radios: r.connect("toggled", radio_handler, r.transform)

        # connect sliders
        for s in self.sliders:
            s.get_adjustment().connect("value_changed", slider_handler)

    #-------------------------------------------------------------------------
    def getDimIndex(self, dnum):
        return int(self.sliders[dnum].get_adjustment().value)

    #-------------------------------------------------------------------------
    def getRowIndex(self): return self.getDimIndex(self.slice_dims[0])

    #-------------------------------------------------------------------------
    def getColIndex(self): return self.getDimIndex(self.slice_dims[1])

    #-------------------------------------------------------------------------
    def getSlices(self):
        return tuple([
          dnum in self.slice_dims and slice(0, dsize) or self.getDimIndex(dnum)
          for dnum, dsize, _ in self.dimensions])

    #-------------------------------------------------------------------------
    def spinnerHandler(self, adj):
        newval = int(adj.value)
        row_adj = self.row_spinner.get_adjustment()
        col_adj = self.col_spinner.get_adjustment()

        if adj.name == "row":
            if newval >= int(col_adj.value):
                col_adj.set_value(newval+1)
        if adj.name == "col":
            if newval <= int(row_adj.value):
                row_adj.set_value(newval-1)

        self.slice_dims = (int(row_adj.value), int(col_adj.value))


##############################################################################
class RowPlot (FigureCanvas):

    #-------------------------------------------------------------------------
    def __init__(self, data):
        fig = Figure(figsize=(3., 6.))
        ax  = fig.add_axes([0.05, 0.05, 0.85, 0.85])
        ax.xaxis.tick_top()
        ax.yaxis.tick_right()
        FigureCanvas.__init__(self, fig)
        self.setData(data)

    #-------------------------------------------------------------------------
    def setDataRange(self, data_min, data_max):
        self.figure.axes[0].set_ylim(data_min, data_max)

    #-------------------------------------------------------------------------
    def setData(self, data):
        ax = self.figure.axes[0]
        indices = range(len(data))
        if not hasattr(self, "data"): ax.plot(indices, data)
        else: ax.lines[0].set_data(indices, data)
        ax.set_xlim(-.5, len(data)-.5)
        self.data = data
        self.draw()


##############################################################################
class ColPlot (FigureCanvas):

    #-------------------------------------------------------------------------
    def __init__(self, data):
        fig = Figure(figsize=(6., 3.))
        fig.add_axes([0.1, 0.1, 0.85, 0.85])
        FigureCanvas.__init__(self, fig)
        self.setData(data)

    #-------------------------------------------------------------------------
    def setDataRange(self, data_min, data_max):
        self.figure.axes[0].set_xlim(data_min, data_max)

    #-------------------------------------------------------------------------
    def setData(self, data):
        ax = self.figure.axes[0]
        indices = range(len(data))
        if not hasattr(self, "data"): ax.plot(data, indices)
        else: ax.lines[0].set_data(data, indices)
        ax.set_ylim(len(data)-.5, -.5)
        self.data = data
        self.draw()


##############################################################################
class SlicePlot (FigureCanvas):

    #-------------------------------------------------------------------------
    def __init__(self, data, cmap=cm.bone, norm=None):
        self.norm = None
        fig = Figure(figsize=figaspect(data))
        ax  = fig.add_axes([0.05, 0.1, 0.85, 0.85])
        ax.yaxis.tick_right()
        ax.title.set_y(1.05) 
        FigureCanvas.__init__(self, fig)
        self.cmap = cmap
        self.setData(data, norm=norm)

    #-------------------------------------------------------------------------
    def setData(self, data, norm=None):
        ax = self.figure.axes[0]

        if len(ax.images) == 0:
            ax.imshow(data, interpolation="nearest",
              cmap=self.cmap, norm=self.norm)
        elif norm != self.norm:
            ax.images[0] = AxesImage(ax, interpolation="nearest",
              cmap=self.cmap, norm=self.norm)
        ax.images[0].set_data(data)

        self.norm = norm
        nrows, ncols = data.shape[:2]
        ax.set_xlim((0,ncols))
        ax.set_ylim((nrows,0))
        self.data = data
        self.draw()

    #def getColorbar(self):
    #    ax = self.figure.colorbar(self.figure.axes[0].images[0],orientation='horizontal')
        #ax_cpy[:] = ax
        #self.figure.delaxes(ax)
    #    return ax

class ColorRange (FigureCanvas):

    def __init__(self, dRange, cmap=cm.bone, norm=None):
#    def __init__(self, ax, cmap=cm.bone, norm=None):
        #self.norm = None
        fig = Figure(figsize = (5,1))
        fig.add_axes((0.05, 0.3, 0.85, 0.6), label="Intensity Map")
        #fig.add_axes(ax)
        FigureCanvas.__init__(self, fig)
        self.figure.axes[0].yaxis.set_visible(False)
        self.cmap = cmap
        self.draw()
        self.setData(dRange, norm=norm)

    def setData(self, dataRange, norm=None):
        self.norm = norm
        dMin, dMax = dataRange
        ax = self.figure.axes[0]
        #make decently smooth gradient, try to include end-point
        r_pts = arange(dMin, dMax+(dMax-dMin)/127, (dMax-dMin)/127)
        data = outerproduct(ones(5),r_pts)
        ax.clear()
        ax.imshow(data[0:10,:], interpolation="nearest",
              cmap=self.cmap, norm=norm, extent=(r_pts[0], r_pts[-1], 0, 1))
        ax.images[0].set_data(data[0:10,:])
        ax.xaxis.set_ticks(arange(r_pts[0], r_pts[-1], (r_pts[-1]-r_pts[0])/7))
        self.data = data[0:10,:]
        self.draw()

class StatusFrame (gtk.Frame):

    def __init__(self):
        gtk.Frame.__init__(self)
        table = gtk.Table(2,2)
        #vbox = gtk.VBox()
        # pixel value
        self.pix_stat = gtk.Statusbar()
        table.attach(self.pix_stat, 1, 2, 0, 1)
        self.pix_stat.set_size_request(160,25)

        # neighborhood avg
        self.av_stat = gtk.Statusbar()
        table.attach(self.av_stat, 1, 2, 1, 2)
        self.av_stat.set_size_request(160,25)

        # neighborhood size selection (eg '9x9')
        self.ent = gtk.Entry(3)
        table.attach(self.ent, 0, 1, 0, 2)
        self.ent.set_size_request(40,30)
        #vbox.pack_start(self.status_bar, False, False, 0)
        #vbox.pack_start(self.ent, False, False, 0)
        self.context_id = self.pix_stat.get_context_id("Statusbar")
        self.add(table)
        self.show_all()
        #self.add(vbox)
        #self.status_bar.show()
        #self.ent.show()

    
    def pop_item(self):
        self.pix_stat.pop(self.context_id)

    def push_item(self, buf):
        self.pix_stat.push(self.context_id, buf)

##############################################################################
class sliceview (gtk.Window):
    mag_norm = normalize()
    phs_norm = normalize(-pi, pi)

    #-------------------------------------------------------------------------
    def __init__(self, data, dim_names=[], title="sliceview", cmap=cm.bone):
        self.data = asarray(data)

        # if data is complex, show the magnitude by default
        self.transform = iscomplex(data) and abs_xform or ident_xform

        # widget layout table
        table = gtk.Table(3, 2)

        #button
        #self.some_button = gtk.Button()
        #self.some_button.set_size_request(400,50)
        #table.attach(self.some_button, 0, 2, 2, 3)

        # control panel
        self.control_panel = ControlPanel(data.shape, dim_names, iscomplex(data))
        self.control_panel.connect(
            self.spinnerHandler, self.radioHandler, self.sliderHandler)
        self.control_panel.set_size_request(200, 200)
        table.attach(self.control_panel, 0, 1, 0, 1)

        # row plot
        self.rowplot = RowPlot(self.getRow())
        self.rowplot.set_size_request(400, 200)
        table.attach(self.rowplot, 1, 2, 0, 1)

        # column plot
        self.colplot = ColPlot(self.getCol())
        self.colplot.set_size_request(200, 400)
        table.attach(self.colplot, 0, 1, 1, 2)

        # slice image
        self.sliceplot = SlicePlot(self.getSlice(), cmap=cmap)
        self.sliceplot.mpl_connect('button_press_event', self.sliceClickHandler)
        self.sliceplot.set_size_request(400, 400)
        table.attach(self.sliceplot, 1, 2, 1, 2)

        self.updateDataRange()

        # status
        self.statbar = StatusFrame()
        self.statbar.set_size_request(200,50)
        table.attach(self.statbar, 0, 1, 2, 3)

        # colorbar
        self.cbar = ColorRange(self.sliceDataRange(), cmap=cmap)
        #self.cbar = ColorRange(self.sliceplot.getColorbar(), cmap=cmap)
        self.cbar.set_size_request(400,50)
        table.attach(self.cbar, 1, 2, 2, 3)

        

        # main window
        gtk.Window.__init__(self)
        self.connect("destroy", lambda x: gtk.main_quit())
        self.set_default_size(400,300)
        self.set_title(title)
        self.set_border_width(3)
        self.add(table)
        self.show_all()
        show()

    #-------------------------------------------------------------------------
    def getRow(self):
        return self.getSlice()[self.control_panel.getRowIndex(),:]

    #-------------------------------------------------------------------------
    def getCol(self):
        return self.getSlice()[:,self.control_panel.getColIndex()]

    #-------------------------------------------------------------------------
    def getSlice(self):
        return self.transform(
          squeeze(self.data[self.control_panel.getSlices()]))

    #-------------------------------------------------------------------------
    def updateRow(self): self.rowplot.setData(self.getRow())

    #-------------------------------------------------------------------------
    def updateCol(self): self.colplot.setData(self.getCol())

    #-------------------------------------------------------------------------
    def updateSlice(self):
        norm = self.transform == phs_xform and self.phs_norm or self.mag_norm
        self.sliceplot.setData(self.getSlice(), norm=norm)
        self.rowplot.setData(self.getRow())
        self.colplot.setData(self.getCol())
        self.cbar.setData(self.sliceDataRange(), norm=norm)

    #-------------------------------------------------------------------------
    def sliceDataRange(self):
        flatSlice = ravel(self.getSlice())
        return amin(flatSlice), amax(flatSlice)

    #------------------------------------------------------------------------- 
    def updateDataRange(self):
        flat_data = self.transform(self.data.flat)
        data_min = amin(flat_data)
        data_max = amax(flat_data)
        self.rowplot.setDataRange(data_min, data_max)
        self.colplot.setDataRange(data_max, data_min)

    #-------------------------------------------------------------------------
    def spinnerHandler(self, adj):
        print "VolumeViewer::spinnerHandler slice_dims", \
               self.control_panel.slice_dims

    #-------------------------------------------------------------------------
    def radioHandler(self, button, transform):
        if not button.get_active(): return
        self.transform = transform
        self.updateDataRange()
        self.updateSlice()

    #-------------------------------------------------------------------------
    def sliderHandler(self, adj):
        row_dim_num, col_dim_num = self.control_panel.slice_dims
        if adj.dim_num == row_dim_num: self.updateRow()
        elif adj.dim_num == col_dim_num: self.updateCol()
        else: self.updateSlice()

    def sliceClickHandler(self, event):
        if not (event.xdata and event.ydata):
            buf = "clicked outside axes"
        else:
            buf = "pix val: %f"%self.getSlice()[int(event.xdata), int(event.ydata)]
            
        self.statbar.pop_item()
        self.statbar.push_item(buf)

##############################################################################
if __name__ == "__main__":
    from pylab import randn
    sliceview(randn(6,6))
