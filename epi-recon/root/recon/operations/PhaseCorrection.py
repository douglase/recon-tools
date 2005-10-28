from pylab import mlab, angle, cos, sin, Float, Complex32
from recon.util import shifted_fft, shifted_inverse_fft
from recon.operations import Operation


##############################################################################
class PhaseCorrection (Operation):

    #-------------------------------------------------------------------------
    def run(self, params, options, data):
        ref_data = data.ref_data
        ksp_data = data.data_matrix
        nslice = params.nslice
        n_pe_true = params.n_pe_true
        n_fe = params.n_fe
        n_fe_true = params.n_fe_true

        # Compute point-by-point phase correction
        ref_phs = mlab.zeros_like(ref_data).astype(Float)
        for slice in range(len(ref_data)):
            for pe in range(len(ref_data[slice])):
                ref_phs[slice,pe,:] = \
                  angle(shifted_inverse_fft(ref_data[slice,pe]))

        # Apply the phase correction to the image data.
        for volume in ksp_data:
            for slice, phscor_slice in zip(volume, ref_phs):
                for pe, theta in zip(slice, phscor_slice):
                    correction = cos(-theta) + 1.0j*sin(-theta)

                    # Shift echo time by adding phase shift.
                    echo = shifted_inverse_fft(pe)*correction
                    pe[:] = shifted_fft(echo).astype(Complex32)
