from FFT import inverse_fft
from pylab import mlab, pi, fft, floor, angle, where, amax, cos, sin, Float, Complex32
from recon.operations import Operation


##############################################################################
class SegmentationCorrection (Operation):
    """
    Correct for the Nyquist ghosting in segmented scans due to mismatches
    between segments.
    """
    
    #-------------------------------------------------------------------------
    def run(self, options, data):
        ref_data = data.ref_data
        ref_nav_data = data.ref_nav_data
        ksp_data = data.data_matrix
        ksp_nav_data = data.nav_data
        pe_per_seg = data.n_pe_true/data.nseg

        # Compute the phase angle and magnitude of reference volume.
        ref_phs = mlab.zeros_like(ref_data).astype(Float)
        ref_mag = mlab.zeros_like(ref_data).astype(Float)
        for slice in range(len(ref_data)):
            for pe in range(len(ref_data[slice])):
                ft_line = inverse_fft(ref_data[slice,pe])
                ref_phs[slice,pe,:] = angle(ft_line)
                ref_mag[slice,pe,:] = abs(ft_line)

        # Compute phase angle of the reference navigator echoes.
        ref_nav_phs = mlab.zeros_like(ref_nav_data).astype(Float)
        for slice in range(len(ref_nav_data)):
            for seg in range(len(ref_nav_data[slice])):
                ref_nav_phs[slice,seg,:] = \
                  angle(inverse_fft(ref_nav_data[slice,seg]))

        # Compute phase difference from reference for each segment using nav echo.
        phs_diff = mlab.zeros_like(ksp_nav_data).astype(Float)
        nav_mag = mlab.zeros_like(ksp_nav_data).astype(Float)
        for vol in range(len(ksp_nav_data)):
            for slice in range(len(ksp_nav_data[vol])):
                for seg in range(len(ksp_nav_data[vol,slice])):
                    nav_echo = inverse_fft(ksp_nav_data[vol,slice,seg,:])
                    nav_mag[vol,slice,seg] = abs(nav_echo)
                    nav_phs = angle(nav_echo)
        
                    # Create mask for threshold of MAG_THRESH for magnitudes.
                    diff = (ref_nav_phs[slice,seg,:] - nav_phs)
                    msk1 = where(diff < -pi, 2.0*pi, 0)
                    msk2 = where(diff > pi, -2.0*pi, 0)
                    nav_mask = where(nav_mag > 0.75*amax(nav_mag), 1.0, 0.0)
                    phs_diff[vol,slice,seg,:] = diff + msk1 + msk2  

        for volnum, volume in enumerate(ksp_data):
            for slicenum, slice in enumerate(volume):
                for pe_num, pe in enumerate(slice):
                    # Compute the phase correction.
                    segnum = pe_num/pe_per_seg
                    phs_diff_line = phs_diff[volnum,slicenum,segnum]
                    nav_mag_line = nav_mag[volnum,slicenum,segnum]
                    time = data.pe_times[data.nav_per_seg + pe_num%pe_per_seg]
                    theta = -(ref_phs[slicenum,pe_num,:] - phs_diff_line*time/data.echo_time)
                    msk1 = where(theta < 0.0, 2.0*pi, 0)
                    theta = theta + msk1
                    scl = cos(theta) + 1.0j*sin(theta)
                    msk = where(nav_mag_line == 0.0, 1, 0)
                    mag_ratio = (1 - msk)*ref_mag[slicenum,pe_num,:]/(nav_mag_line + msk)
                    msk1 = (where((mag_ratio > 1.05), 0.0, 1.0))
                    msk2 = (where((mag_ratio < 0.95), 0.0, 1.0))
                    msk = msk1*msk2
                    msk = (1 - msk) + msk*mag_ratio
                    cor = scl*msk

                    # Apply the phase correction.
                    echo = inverse_fft(pe)
                    echo = echo*cor
                    pe[:] = fft(echo).astype(Complex32)
                            

