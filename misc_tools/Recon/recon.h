/*****************************************************************************
* Header file for recon_main.c                                               *
*****************************************************************************/

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/time.h>
#include <string.h>
//#include <gtk/gtk.h>
#include <fftw3.h>
#include <netinet/in.h>
#include <vecLib/cblas.h>


#define   MAX_OPS                    100 
#define MULTISLICE 0
#define COMPRESSED 1
#define UNCOMPRESSED 2

#define SIGN(x) ( (x)>=0  ? +1 : -1 )
#define MAX(x,y) ( (x) > (y) ? (x) : (y) )
#define MIN(x,y) ( (x) > (y) ? (y) : (x) )
#define ABS(x) ( ((x) < 0.0) ? -(x) : (x) )

/* Define the FID file sub-header */
typedef struct{
  short int  scale;     // spare short word (at byte 0)
  short int  status;       // status word for block header (at byte 2)
  short int  index;     // index of data block (counting from 1) (at byte 4)
  short int  mode;     // spare short word (at byte 6)
  int   ctcount;     // spare long word (at byte 8)
  float      lpval1;       // 2D-f2 left phase (at byte 12)
  float      rpval1;       // 2D-f2 right phase (at byte 16)
  float      lvl;     // real part of imaginary bias (at byte 20)
  float      tlt;     // imag part of imaginary bias (at byte 24)
} sub_hdr_struct; // TOTAL bytes: 28

/* Define the FID file main header */
typedef struct{
  int nblocks;  // number of block in the file (at byte 0)
  int ntraces;  // number of traces per block (at byte 4)
  int np;  // number of points (real & imag) per trace (at byte 8)
  int ebytes;  // number of bytes per point (at byte 12)
  int tbytes;  // number of bytes per trace (at byte 16)
  int bbytes;  // number of bytes per block (including sub-header) (at byte 20)
  short int vers_id;  // (at byte 24)
  short int status;  // (at byte 26)
  int nbheaders;  // number of block headers per block (usually 1) (at byte 28)
} main_hdr_struct;  // TOTAL bytes: 32

/***** The following structure contains all image data and parameters *****/

typedef struct{
  /* From procpar file */
  int n_fe;          /* Number of frequency-encoding lines */
  int n_pe;          /* Number of phase-encoding lines */
  int precision;     /* Bit-depth of the data */
  int n_refs;        /* Number of ref scans */
  float thk;         /* Slice thickness */
  int n_segs;        /* Number of segments */
  int navs_per_seg;  
  int n_slice_total; /* Number of slices (2D data) in all volumes */
  int n_slice;   /* Number of slices (2D data) in a volume */
  int n_vol;         /* Number of data volumes not including the ref scans */
  int n_vol_total;  /* Number of image volume plus ref vols */
  float fov;         /* Field of View */
  float *pss;
  double Tl;          /* time lag from PE to PE */
  float asym_times[2];
  char pslabel[30];

  /* From data files */
  fftw_complex ****data;
  fftw_complex ***ref1;
  fftw_complex ***ref2;
  double ***mask;
  double ***fmap;
} image_struct;


/* The following structure contains an operation to be performed and its 
   optional parameters. */

typedef struct{
  void (*op) ();
  char op_name[30];
  char param_1[20];
  char param_2[20];
  char param_3[20];
  char param_4[20];
  int  op_active;
} op_struct;


/* Declaration of operation functions */
void read_image(image_struct *image, op_struct op);
void write_image(image_struct *image, op_struct op);
void ifft2d(image_struct *image, op_struct op);
void bal_phs_corr(image_struct *image, op_struct op);
void get_fieldmap(image_struct *image, op_struct op);
void geo_undistort(image_struct *image, op_struct op);
void viewer(image_struct *image, op_struct op);
void surf_plot(image_struct *image, op_struct op);
//void gtk_viewer(image_struct *image, op_struct op);

/* Declaration of Data IO functions */
void read_procpar(char *procpar_path, image_struct *image);
void read_oplist(char *oplist_path, op_struct *op_seq);
int get_data(char *data_path, image_struct *image);

/* Declaration of helper functions */
void swap_bytes(unsigned char *x, int size);
unsigned char* create_mask(image_struct *img, double thresh_fact);
int comparator(double *a, double *b);
void compute_field_map(image_struct *image, double threshold);

/* Helper functions auxiliary to Balanced Phase Correction
   (defined in bpc.c)
*/
void apply_phase_correction(fftw_complex *data, fftw_complex *corrector,
			    int rowsize, int volsize, int nvols);
void unwrap_ref_volume(double *uphase, fftw_complex ***vol, 
		       int zdim, int ydim, int xdim, int xstart, int xstop);
void maskbyfit(double *line, double *sigma, double *mask, double tol, 
	       double tol_growth, int len);

/* Helper functions auxiliary to Geometric Undistortion
   (defined in geo_undist.c
*/
void get_kernel(fftw_complex ****kernel, double ***fmap, double ***vmask,
		double Tl, int ns, int nr, int nc);
void zsolve_regularized(fftw_complex *A, fftw_complex *y, fftw_complex *x,
			int M, int N, int NRHS, double lambda);
void zregularized_inverse(fftw_complex *A, int M, int N, double lambda);