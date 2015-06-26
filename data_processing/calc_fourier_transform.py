"""
Filename:     calc_fourier_transform.py
Author:       Damien Irving, d.irving@student.unimelb.edu.au
Description:  Calculate Fourier transform

"""

# Import general Python modules

import sys, os, pdb
import argparse
import numpy, math
from scipy import fftpack
from scipy import signal
from copy import deepcopy

# Import my modules

cwd = os.getcwd()
repo_dir = '/'
for directory in cwd.split('/')[1:]:
    repo_dir = os.path.join(repo_dir, directory)
    if directory == 'climate-analysis':
        break

modules_dir = os.path.join(repo_dir, 'modules')
sys.path.append(modules_dir)

try:
    import netcdf_io as nio
    import convenient_universal as uconv
except ImportError:
    raise ImportError('Must run this script from anywhere within the climate-analysis git repo')


# Define functions
    
def filter_signal(signal, indep_var, min_freq, max_freq, exclusion):
    """Filter a signal by performing a Fourier Tranform and then
    an inverse Fourier Transform for a selected range of frequencies"""
    
    sig_fft, sample_freq = fourier_transform(signal, indep_var)
    filtered_signal = inverse_fourier_transform(sig_fft, sample_freq, min_freq=min_freq, max_freq=max_freq, exclude=exclusion)
    
    return filtered_signal


def fourier_transform(signal, indep_var):
    """Calculate the Fourier Transform.
    
    Args:
      signal (numpy.ndarray): Data to be transformed 
      indep_var (list/tuple): Independent variable (i.e. 1 dimensional time axis or longitude axis)
    
    Returns:
      sig_fft (numpy.ndarray): Coefficients obtained from the Fourier Transform
      freqs (numpy.ndarray): Wave frequency associated with each coefficient
    
    """
    
    spacing = indep_var[1] - indep_var[0]
    sig_fft = fftpack.fft(signal)
    sample_freq = fftpack.fftfreq(len(indep_var), d=spacing) * len(indep_var) * spacing  #units = cycles per length of domain
    sample_freq = numpy.resize(sample_freq, sig_fft.shape)
    
    return sig_fft, sample_freq


def inverse_fourier_transform(coefficients, sample_freq, 
                              min_freq=None, max_freq=None, exclude='negative'):
    """Inverse Fourier Transform.
    
    Args:
      coefficients (numpy.ndarray): Coefficients obtained from the Fourier Transform
      sample_freq (numpy.ndarray): Wave frequency associated with each coefficient
      max_freq, min_freq (float, optional): Exclude values outside [min_freq, max_freq]
        frequency range. (Note that this filtering keeps both the positive and 
        negative half of the spectrum)
      exclude (str, optional): Exclude either the 'positive' or 'negative' 
        half of the Fourier spectrum. (A Hilbert transform, for example, excludes 
        the negative part of the spectrum)
                                 
    """
    
    assert exclude in ['positive', 'negative', None]
    
    coefs = deepcopy(coefficients)  # Deep copy to prevent side effects
                                    # (shallow copy not sufficient for complex
                                    # things like numpy arrays)
    
    if exclude == 'positive':
        coefs[sample_freq > 0] = 0
    elif exclude == 'negative':
        coefs[sample_freq < 0] = 0
    
    if (max_freq == min_freq) and max_freq:
        coefs[numpy.abs(sample_freq) != max_freq] = 0
    
    if max_freq:
        coefs[numpy.abs(sample_freq) > max_freq] = 0
    
    if min_freq:
        coefs[numpy.abs(sample_freq) < min_freq] = 0
    
    result = fftpack.ifft(coefs)
    
    return result


def first_localmax_index(data):
    """Return index of first local maxima. 

    If there is no local maxima (e.g. if all the values are zero), 
    it will simply return zero.

    """
    localmax_indexes = signal.argrelextrema(data, numpy.greater, mode='wrap')

    if localmax_indexes[0].size > 0:
        return localmax_indexes[0][0]
    else:
        return 0


def get_coefficients(data, lon_axis, min_freq, max_freq):
    """Calculate magnitude and phase coefficients for each frequency. 

    Returns:
      A list [mag_min_freq, phase_min_freq, ... mag_max_freq, phase_max_freq]
      where the phase is represented by the location of the first local maxima 
      along the longitude axis
    
    """

    outdata_list = [] 
    exclusion = None
    for freq in range(min_freq, max_freq + 1):
        filtered_signal = numpy.apply_along_axis(filter_signal, -1, 
                                                 data, lon_axis, 
                                                 freq, freq, 
                                                 exclusion)

        localmax_vals = numpy.max(filtered_signal, axis=-1)
        localmax_indexes = numpy.apply_along_axis(first_localmax_index, -1, filtered_signal)
        localmax_lons = map(lambda x: lon_axis[x], localmax_indexes)
        
        outdata_list.append(localmax_vals)
        outdata_list.append(localmax_lons)

    return outdata_list


def get_coefficient_atts(orig_darray, min_freq, max_freq):
    """Get the attributes for the coefficient output file.

    Returns:
      A list [mag-atts_min-freq, phase-atts_min-freq, ... mag-atts_max-freq, mag-phase_max-freq] 

    """
    
    method = 'filtered'
    outvar_atts_list = []
    outvar_axes_list = []
    for freq in range(min_freq, max_freq + 1):
        filter_text = get_filter_text(method, freq, freq)
        mag_atts = {'id': 'wave'+str(freq)+'_amp',
                    'standard_name': 'amplitude_of_'+method+'_'+orig_darray.attrs['long_name'],
                    'long_name': 'amplitude_of_'+method+'_'+orig_darray.attrs['long_name'],
                    'units': orig_darray.attrs['units'],
                    'notes': filter_text}
        outvar_atts_list.append(mag_atts)
        outvar_axes_list.append(orig_darray.getAxisList()[:-1])
        
        phase_atts = {'id': 'wave'+str(freq)+'_phase',
                      'standard_name': 'first_local_maxima_of_'+method+'_'+orig_darray.long_name,
                      'long_name': 'first_local_maxima_of_'+method+'_'+orig_darray.long_name,
                      'units': orig_darray.getLongitude().units,
                      'notes': filter_text}
        outvar_atts_list.append(phase_atts)    
        outvar_axes_list.append(orig_darray.getAxisList()[:-1])

    return outvar_atts_list, outvar_axes_list


def hilbert_transform(data, lon_axis, min_freq, max_freq, out_type=None):
    """Perform the Hilbert transform.

    There is the option of placing the output array in a list of length 1
    (this is useful in some cases)

    """
    
    exclusion = 'negative'
    outdata = numpy.apply_along_axis(filter_signal, -1, 
                                     data, lon_axis, 
                                     min_freq, max_freq, 
                                     exclusion)
    outdata = 2 * numpy.abs(outdata)

    if out_type == list:
        return [outdata,]
    else:
        return outdata


def get_hilbert_atts(orig_data, min_freq, max_freq):
    """Get the attributes for the output Hilbert transform file."""
   
    method = 'hilbert_transformed'
    filter_text = get_filter_text(method, min_freq, max_freq)
    var_atts = {'id': 'env'+orig_data.id,
                'standard_name': method+'_'+orig_data.long_name,
                'long_name': method+'_'+orig_data.long_name,
                'units': orig_data.units,
                'notes': filter_text}

    outvar_atts_list = [var_atts,]
    outvar_axes_list = [orig_data.getAxisList(),]

    return outvar_atts_list, outvar_axes_list


def get_filter_text(method, min_freq, max_freq):
    """Get the notes attribute text according to the analysis
    method and frequency range."""

    if min_freq and max_freq:
        filter_text = '%s with frequency range: %s to %s' %(method, min_freq, max_freq)
    else:
        filter_text = '%s with all frequencies retained' %(method)

    return filter_text


def spectrum(signal_fft, freqs, scaling='amplitude', variance=None):
    """Calculate the spectral density for a given Fourier Transform.
    
    Args:
      signal_fft, freqs (numpy.ndarray): Typically the output of fourier_transform()
      scaling (str, optional): Choices for the amplitude scaling for each frequency
        are as follows (see Wilks 2011, p440):
         'amplitude': no scaling at all (C)
         'power': sqaure the amplitude (C^2)
         'R2': variance explained = [(n/2)*C^2] / (n-1)*variance^2, 
         where n and variance are the length and variance of the 
         orignal data series (R2 = the proportion of the variance 
         explained by each harmonic)    

    """

    assert scaling in ['amplitude', 'power', 'R2']
    if scaling == 'R2':
        assert variance, \
        "To calculate variance explained must provide variance value" 
        
    if len(signal_fft.shape) > 1:
        print "WARNING: Ensure that frequency is the final axis"
    
    # Calculate the entire amplitude spectrum
    n = signal_fft.shape[-1]
    amp = numpy.abs(signal_fft) / n
    
    # The positive and negative half are identical, so just keep positive
    # and double its amplitude
    freq_limit_index = int(math.floor(n / 2)) 
    pos_amp = 2 * numpy.take(amp, range(1, freq_limit_index), axis=-1)
    pos_freqs = numpy.take(freqs, range(1, freq_limit_index), axis=-1)
    
    if scaling == 'amplitude':
        result = pos_amp
    elif scaling == 'power':
        result = (pos_amp)**2
    elif scaling == 'R2':
        result = ((n / 2) * (pos_amp**2)) / ((n - 1) * (variance))
    
    return result, pos_freqs


def main(inargs):
    """Run the program."""
    
    # Read the data
    dset_in = xray.open_dataset(inargs.infile)
    gio.check_xrayDataset(dset_in, inargs.variable)

    subset_dict = gio.get_subset_kwargs(inargs)
    darray = dset_in[inargs.var].sel(**subset_dict)

    assert darray.dims[-1] == 'longitude', \
    'This script is setup to perform the fourier transform along the longitude axis'
    
    # Apply longitude filter (i.e. set unwanted longitudes to zero)
    data_masked = apply_lon_mask(darray.values, darray['longitude'].values) if inargs.valid_lon else darray.values  # FIXME: apply_lon_mask needs to be written
    
    # Perform task
    min_freq, max_freq = inargs.filter
    if inargs.outtype == 'coefficients':
        outdata_list = get_coefficients(data_masked, darray['longitude'].values, min_freq, max_freq)
        outvar_atts_list, outvar_axes_list = get_coefficient_atts(darray, min_freq, max_freq)
    elif inargs.outtype == 'hilbert':
        outdata_list = hilbert_transform(data_masked, darray['longitude'].values, min_freq, max_freq, out_type=list)
        outvar_atts_list, outvar_axes_list = get_hilbert_atts(indata.data, min_freq, max_freq)

    # Write the output file
    d = {}
    d['latitude'] = darray['latitude']
    d['longitude'] = darray['longitude']

    for season in season_months.keys(): 
        d[inargs.var+'_'+season] = (['latitude', 'longitude'], cmeans[season])
        if not inargs.no_sig:
            d['p_'+season] = (['latitude', 'longitude'], pvals[season])

    dset_out = xray.Dataset(d)

    for season in season_months.keys(): 
        dset_out[inargs.var+'_'+season].attrs = cmean_atts[season]
        if not inargs.no_sig:
            dset_out['p_'+season].attrs = pval_atts[season]
    
    output_metadata = {inargs.infile: dset_in.attrs['history'],}
    if inargs.date_file:
        output_metadata[inargs.date_file] = dt_list_metadata

    gio.set_global_atts(dset_out, dset_in.attrs, output_metadata)
    dset_out.to_netcdf(inargs.outfile, format='NETCDF3_CLASSIC')


if __name__ == '__main__':

    extra_info =""" 
example (vortex.earthsci.unimelb.edu.au):
    /usr/local/uvcdat/1.5.1/bin/cdat calc_fourier_transform.py 
    va_Merra_250hPa_30day-runmean-Jun2002_r360x181.nc va test.nc 
    --filter 2 9 --outtype hilbert
author:
    Damien Irving, d.irving@student.unimelb.edu.au
notes:
    Note that the Hilbert transform excludes the negative half 
    of the frequency spectrum and doubles the final amplitude. This does not
    give the same result as if you simply retain the negative half.
references:
    http://docs.scipy.org/doc/numpy/reference/routines.fft.html
    http://gribblelab.org/scicomp/09_Signals_sampling_filtering.html
    
"""

    description='Perform Fourier Transform along lines of constant latitude'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("infile", type=str, help="Input file name")
    parser.add_argument("variable", type=str, help="Input file variable")
    parser.add_argument("outfile", type=str, help="Output file name")
            
    # Input data options
    parser.add_argument("--latitude", type=float, nargs=2, metavar=('START', 'END'),
                        help="Latitude range over which to perform Fourier Transform [default = entire]")
    parser.add_argument("--valid_lon", type=float, nargs=2, metavar=('START', 'END'), default=None,
                        help="Longitude range over which to perform Fourier Transform (all other values are set to zero) [default = entire]")
    parser.add_argument("--time", type=str, nargs=3, metavar=('START_DATE', 'END_DATE', 'MONTHS'),
                        help="Time period [default = entire]")

    # Output options
    parser.add_argument("--filter", type=int, nargs=2, metavar=('LOWER', 'UPPER'), default=None,
                        help="Range of frequecies to retain in filtering [e.g. 3,3 would retain the wave that repeats 3 times over the domain")
    parser.add_argument("--outtype", type=str, default='hilbert', choices=('hilbert', 'coefficients'),
                        help="The output can be a hilbert transform or the magnitude and phase coefficients for each frequency")

  
    args = parser.parse_args()            

    print 'Input files: ', args.infile
    print 'Output file: ', args.outfile  

    main(args)
