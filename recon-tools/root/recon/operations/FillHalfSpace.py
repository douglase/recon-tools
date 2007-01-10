import sys
from MLab import angle
import Numeric as N

from recon.operations import Operation, Parameter
from recon.util import embedIm, fft2d, ifft2d

class FillHalfSpace (Operation):

    params=(
        Parameter(name="fill_size", type="int", default=0,
                  description="the new number of rows to fill to in k-space"),
        Parameter(name="win_size", type="int", default=8,
                  description="length of transition window between measured "\
                  "k-space and filled k-space; a window reduces Gibbs ringing"),
        Parameter(name="iterations", type="int", default=0,
                  description="number of times to iterate the merge process"),
        Parameter(name="converge_crit", type="float", default=0,
                  description="stop iteration when the summed absolute " \
                  "difference between sucessive reconstructed volumes equals "\
                  "this amount"),
        Parameter(name="method", type="str", default="iterative",
                  description="possible values: iterative, zero filled")
        )

    def phaseMap2D(self, slice):
        (_, nx) = slice.shape
        ny = self.fill_size
        y0 = self.fill_size/2
        fill_slice = N.zeros((ny,nx), N.Complex)
        fill_slice[y0-self.over_fill:y0+self.over_fill,:] = \
                   slice[0:self.over_fill*2,:]
        
        phase_map = ifft2d(fill_slice)
        return phase_map
    
    def imageFromFill2D(self, slice):
        (_, nx) = slice.shape
        ny = self.fill_size
        fill_slice = N.zeros((ny,nx), N.Complex)
        embedIm(slice, fill_slice, self.fill_rows, 0)
        fill_slice[:] = ifft2d(fill_slice)
        return fill_slice

##     def HermitianFill(self, Im, n_fill_rows):
##         np, nf = Im.shape
##         x1 = np/2+1  # this is where x=1
##         # catch x=0 with sub-matrix symmetric with A
##         Acomp = Im[np-n_fill_rows+1:,x1-1:]
##         Bcomp = Im[np-n_fill_rows+1:,1:x1-1]
##         Im[1:n_fill_rows,1:x1] = conjugate(rot90(Acomp, k=2))
##         Im[1:n_fill_rows,x1:] = conjugate(rot90(Bcomp, k=2))
##         Im[0] = 0
##         Im[0:n_fill_rows,0] = 0

    def mergeFill2D(self, filled, measured, winsize=8):
        wsize_f = float(winsize)
        mergept = self.fill_rows
        fill_win = 0.5*(1 + N.cos(N.pi*(N.arange(wsize_f)/wsize_f)))
        measured_win = 0.5*(1 + N.cos(N.pi + N.pi*(N.arange(wsize_f)/wsize_f)))
        #filled[:mergept,:] = filled[:mergept,:]
        filled[mergept+winsize:,:] = measured[winsize:,:]
        # merge measured data with filled data in winsize merge region
        filled[mergept:mergept+winsize,:] = \
               fill_win[:,N.NewAxis]*filled[mergept:mergept+winsize,:] + \
               measured_win[:,N.NewAxis]*measured[:winsize,:]

    def cookImage2D(self, volData):
        out = sys.stdout
        (ns, _, nx) = volData.shape
        ny = self.fill_size
        cooked3D = N.zeros((ns,ny,nx), N.Complex)
        for s, slice in enumerate(volData):
            out.write("filling slice %d: "%(s,))
            theta = self.phaseMap2D(slice)
            mag = abs(self.imageFromFill2D(slice))
            cooked = N.zeros((ny, nx), N.Complex)
            prev_power = 0.
            c = self.criterion[1]=="converge" and 100000. or self.iterations
            while c > self.criterion[0]:
                prev_image = cooked.copy()
                cooked = mag*N.exp(1.j*angle(theta))
                cooked[:] = fft2d(cooked)
                cooked[self.fill_rows:,:] = slice[:]                
                cooked[:] = ifft2d(cooked)
                diff = N.sum(N.ravel(abs(cooked-prev_image)))
                mag = abs(cooked)

                c = self.criterion[1]=="converge" and diff or c-1
            cooked = mag*N.exp(1.j*angle(theta))
            cooked[:] = fft2d(cooked)
            self.mergeFill2D(cooked, slice, winsize=self.win_size)
            cooked3D[s][:] = cooked[:]
            #diff = sum(abs(cooked[:self.fill_rows].flat)) - prev_power
            out.write("absolute difference=%f\n"%(diff))
        return cooked3D.astype(volData.typecode())
    
    def run(self, image):
        ny = image.ydim
        self.over_fill = ny - self.fill_size/2
        self.fill_rows = self.fill_size - ny
        
        if self.over_fill < 1:
            self.log("not enough measured data: this method needs a few " \
                     "over-scan lines (sampled past the middle of k-space)")
            return
        if self.fill_size <= ny:
            self.log("fill size is not longer than size of measured data "\
                     "(no filling to be done)")
            return

        if self.method != "zero filled":
            if self.converge_crit > 0 and self.iterations > 0:
                self.log("you cannot specify the convergence criterion OR the"\
                         " number of iterations, NOT both: doing nothing")
                return
            elif self.converge_crit > 0:
                self.criterion = (self.converge_crit,"converge")
            elif self.iterations > 0:
                self.criterion = (0,"iterateN")
            else:
                self.log("no iterative criterion given, default to 5 loops")
                self.criterion = (0,"iterateN")
                self.iterations = 5
                
        old_image = image._subimage(image[:].copy())
        new_shape = list(image.shape)
        new_shape[-2] = self.fill_size
        image.resize(new_shape)
        # often the ysize is set wrong--as if the Y-dimension spanns the FOV
        if image.ysize > image.xsize:
            image.ysize = image.xsize

        for new_vol, old_vol in zip(image, old_image):
            if self.method == "iterative":
                cooked = self.cookImage2D(old_vol[:])                
            else:
                cooked = self.kSpaceFill(old_vol[:])
                
            new_vol[:] = cooked[:]
            
    def kSpaceFill(self, vol):
        (ns, _, nx) = vol.shape
        ny = self.fill_size
        fill_vol = N.zeros((ns,ny,nx), N.Complex32)
        for s in range(ns):
            embedIm(vol[s], fill_vol[s], self.fill_rows, 0)
        return fill_vol.astype(vol.typecode())
