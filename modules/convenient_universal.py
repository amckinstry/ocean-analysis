"""Collection of convenient functions that will work with my anaconda or uvcdat install.

Functions:
  adjust_lon_range   -- Express longitude values in desired 360 degree interval
  apply_lon_filter   -- Set values outside of specified longitude range to zero
  get_threshold      -- Turn the user input threshold into a numeric threshold
  single2list        -- Check if item is a list, then convert if not

"""

import numpy
from scipy import stats
import pdb, re


def match_dates(dates, time_axis, invert_matching=False, return_indexes=False):
    """Take simple list of dates and match with the corresponding times in a detailed time axis.
    
    (For the genutil picker to work correctly in nio.temporal_extract, the
    date list must match perfectly)
 
    Args:   
      dates (list/tuple): List of dates in a simple format (e.g. 1979-01-01)
      time_axis (list/tuple): Time axis with detailed date format (e.g. 1979-01-01 12:00:0.0)
      invert_matching (bool, optional): Return a list of time_axis values that aren't 
        (True) or are (False; default) in dates
      return_indexes (bool, optional): Returned time_axis values are index numbers (True)
        or actual dates (False; default)
        
    """
    
    dates_split = map(split_dt, dates)
    time_axis_split = map(split_dt, time_axis)
    
    matches_indexes = []
    matches_dates = []
    misses_indexes = range(0, len(time_axis))
    misses_dates = time_axis[:]  # creates a shallow copy
    
    for date in dates_split:
        try:
            index = time_axis_split.index(date)
            if invert_matching:
                misses_dates.remove(time_axis[index])
                misses_indexes.remove(index)
            else:
                matches_dates.append(time_axis[index])
                matches_indexes.append(index)
        except ValueError:
            pass        

    if invert_matching and return_indexes:
        return misses_indexes
    elif invert_matching and not return_indexes:
        return misses_dates
    elif not invert_matching and return_indexes:
        return matches_indexes
    else:
        return matches_dates


def find_nearest(array, value):
    """Find the closest array item to value."""
    
    idx = (numpy.abs(numpy.array(array) - value)).argmin()
    return array[idx]



def list_kwargs(func):
    """List keyword arguments of a function."""
    
    details = inspect.getargspec(func)
    nopt = len(details.defaults)
    
    return details.args[-nopt:]


def hi_lo(data_series, current_max, current_min):
    """Determine the new highest and lowest value."""
    
    try:
        highest = MV2.max(data_series)
    except:
        highest = max(data_series)
    
    if highest > current_max:
        new_max = highest
    else:
        new_max = current_max
    
    try:    
        lowest = MV2.min(data_series)
    except:
        lowest = min(data_series)
    
    if lowest < current_min:
        new_min = lowest
    else:
        new_min = current_min
    
    return new_max, new_min


def dict_filter(indict, key_list):
    """Filter dictionary according to specified keys."""
    
    return dict((key, value) for key, value in indict.iteritems() if key in key_list)


def coordinate_pairs(lat_axis, lon_axis):
    """Take the latitude and longitude values from given grid axes
    and produce a flattened lat and lon array, with element-wise pairs 
    corresponding to every grid point."""
    
    lon_mesh, lat_mesh = numpy.meshgrid(lon_axis, lat_axis)  # This is the correct order
    
    return lat_mesh.flatten(), lon_mesh.flatten()


def find_duplicates(inlist):
    """Return list of duplicates in a list."""
    
    D = defaultdict(list)
    for i,item in enumerate(mylist):
        D[item].append(i)
    D = {k:v for k,v in D.items() if len(v)>1}
    
    return D


def adjust_lon_range(lons, radians=True, start=0.0):
    """Express longitude values in a 360 degree (or 2*pi radians) interval.

    Args:
      lons (list/tuple): Longitude axis values (monotonically increasing)
      radians (bool): Specify whether input data are in radians (True) or
        degrees (False). Output will be the same units.
      start (float, optional): Start value for the output interval (add 360 degrees or 2*pi
        radians to get the end point)
    
    """
    
    lons = single2list(lons, numpy_array=True)    
    
    interval360 = 2.0*numpy.pi if radians else 360.0
    end = start + interval360    
    
    less_than_start = numpy.ones([len(lons),])
    while numpy.sum(less_than_start) != 0:
        lons = numpy.where(lons < start, lons + interval360, lons)
        less_than_start = lons < start
    
    more_than_end = numpy.ones([len(lons),])
    while numpy.sum(more_than_end) != 0:
        lons = numpy.where(lons >= end, lons - interval360, lons)
        more_than_end = lons >= end

    return lons


def apply_lon_filter(data, lon_bounds):
    """Set values outside of specified longitude range to zero.

    Args:
      data (numpy.ndarray): Array of longitude values.
      lon_bounds (list/tuple): Specified longitude range (min, max)

    """
    
    # Convert to common bounds (0, 360)
    lon_min = adjust_lon_range(lon_bounds[0], radians=False, start=0.0)
    lon_max = adjust_lon_range(lon_bounds[1], radians=False, start=0.0)
    lon_axis = adjust_lon_range(data.getLongitude()[:], radians=False, start=0.0)

    # Make required values zero
    ntimes, nlats, nlons = data.shape
    lon_axis_tiled = numpy.tile(lon_axis, (ntimes, nlats, 1))
    
    new_data = numpy.where(lon_axis_tiled < lon_min, 0.0, data)
    
    return numpy.where(lon_axis_tiled > lon_max, 0.0, new_data)


def get_significance(data_subset, data_all, 
                     p_var, p_standard_name,
                     size_subset, size_all):
    """Perform significance test.

    size_subset and size_all can either be a variable name (and the variable 
    attributes will be returned; useful in cases where the size is an array) or a
    single number (useful in cases where the size is constant and you want it in the
    p_var attributes).
    
    The approach for the significance test is to compare the mean of the subsetted
    data with that of the entire data sample via an independent, two-sample,
    parametric t-test (for details, see Wilks textbook). 
    
    http://stackoverflow.com/questions/21494141/how-do-i-do-a-f-test-in-python

    FIXME: If equal_var=False then it will perform a Welch t-test, which is for samples
    with unequal variance (early versions of scipy do not have this option). To test whether
    the variances are equal or not you use an F-test (i.e. do the test at each grid point and
    then assign equal_var accordingly). If your data is close to normally distributed you can 
    use the Barlett test (scipy.stats.bartlett), otherwise the Levene test (scipy.stats.levene).
    
    FIXME: I need to account for autocorrelation in the data by calculating an effective
    sample size (see Wilkes, p 147). I can get the autocorrelation using either
    genutil.autocorrelation or the acf function in the statsmodels time series analysis
    python library, however I cannot see how to alter the sample size in stats.ttest_ind.

    FIXME: I also need to consider whether a parametric t-test is appropriate. One of my samples
    might be very non-normally distributed, which means a non-parametric test might be better. 
    
    """

#    alpha = 0.05 
#    w, p_value = scipy.stats.levene(data_included, data_excluded)
#    if p_value > alpha:
#        equal_var = False# Reject the null hypothesis that Var(X) == Var(Y)
#    else:
#        equal_var = True

    assert type(size_subset) == type(size_all)
    assert type(size_subset) in [str, float, int]

    t, pvals = stats.mstats.ttest_ind(data_subset, data_all, axis=0) # stats.ttest_ind has an equal_var option that mstats does not
    print 'WARNING: Significance test assumed equal variances'

    pval_atts = {'id': p_var,
                 'standard_name': p_standard_name,
                 'long_name': p_standard_name,
                 'units': ' ',
                 'notes': """Two-tailed p-value from standard independent two sample t-test comparing the subsetted data (size=%s) to a sample containing all the data (size=%s)""" %(str(size_subset), str(size_all)),
                 'reference': 'scipy.stats.ttest_ind(a, b, axis=t, equal_var=False)'}

    if type(size_subset) == str:

        size_subset_atts = {'id': size_subset,
                            'standard_name': size_subset,
                            'long_name': size_subset,
                            'units': ' ',
                            'notes': """Size of sample that exceeds the threshold"""}

        size_all_atts = {'id': size_all,
                         'standard_name': size_all,
                         'long_name': size_all,
                         'units': ' ',
                         'notes': """Size of the entire data"""}

        return pvals, pval_atts, size_subset_atts, size_all_atts

    else:

        return pvals, pval_atts


def get_threshold(data, threshold_str, axis=None):
    """Turn the user input threshold into a numeric threshold."""
    
    if 'pct' in threshold_str:
        value = float(re.sub('pct', '', threshold_str))
        threshold_float = numpy.percentile(data, value, axis=axis)
    else:
        threshold_float = float(threshold_str)
    
    return threshold_float


def single2list(item, numpy_array=False):
    """Check if item is a list, then convert if not."""
    
    try:
        test = len(item)
    except TypeError:
        output = [item,]
    else:
        output = item 
        
    if numpy_array and not isinstance(output, numpy.ndarray):
        return numpy.array(output)
    else:
        return output
