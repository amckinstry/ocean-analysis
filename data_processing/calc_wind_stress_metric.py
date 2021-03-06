"""
Filename:     calc_wind_stress_metric.py
Author:       Damien Irving, irving.damien@gmail.com
Description:  Calculate zonal surface wind stress (over ocean) metrics

"""

# Import general Python modules

import sys, os, pdb
import argparse
import itertools
import numpy
from scipy.interpolate import interp1d
import iris
import iris.coord_categorisation
from iris.experimental.equalise_cubes import equalise_attributes

# Import my modules

cwd = os.getcwd()
repo_dir = '/'
for directory in cwd.split('/')[1:]:
    repo_dir = os.path.join(repo_dir, directory)
    if directory == 'ocean-analysis':
        break

modules_dir = os.path.join(repo_dir, 'modules')
sys.path.append(modules_dir)
try:
    import general_io as gio
    import convenient_universal as uconv
    import timeseries
except ImportError:
    raise ImportError('Must run this script from anywhere within the ocean-analysis git repo')

# Define functions

history = []

def save_history(cube, field, filename):
    """Save the history attribute when reading the data.
    (This is required because the history attribute differs between input files 
      and is therefore deleted upon equilising attributes)  
    """ 

    history.append(cube.attributes['history'])


def create_land_mask(sftlf_cube, target_shape):
    """Create mask from an sftlf (land surface fraction) file.
    
    There is no land when cell value == 0
    
    """

    target_ndim = len(target_shape)

    mask_array = numpy.where(sftlf_cube.data < 50, False, True)

    mask = uconv.broadcast_array(mask_array, [target_ndim - 2, target_ndim - 1], target_shape)
    assert mask.shape == target_shape 

    return mask


def wind_stress_metrics(xdata, ydata, hemisphere, direction):
    """Calculate location and magnitude metric for surface wind stress."""

    assert hemisphere in ['nh', 'sh']
    assert direction in ['westerly', 'easterly']
    
    # assert regularly spaced y values
    
    if (hemisphere == 'sh') and (direction == 'westerly'):
        selection = (xdata < 0) & (ydata > 0)
    elif (hemisphere == 'nh') and (direction == 'westerly'):
        selection = (xdata > 0) & (ydata > 0)
    elif (hemisphere == 'sh') and (direction == 'easterly'):
        selection = (xdata < 0) & (xdata > -50) & (ydata < 0)
    elif (hemisphere == 'nh') and (direction == 'easterly'):
        selection = (xdata > 0) & (xdata < 40) & (ydata < 0)
    
    x_filtered = numpy.where(selection, xdata, 0)
    y_filtered = numpy.where(selection, ydata, 0)

    location = numpy.sum(x_filtered * y_filtered) / numpy.sum(y_filtered)  # centre of gravity
    magnitude = numpy.sum(y_filtered)
    
    return location, magnitude


def create_outcubes(metric_dict, atts, units_dict, time_coord):
    """Create an iris cube for each metric."""
   
    cube_list = []
    for metadata, data in metric_dict.items():
        hemisphere, direction, metric = metadata
        standard_name = '%s_%s_%s' %(hemisphere, direction, metric)
        long_name = '%s %s %s' %(hemisphere, direction, metric)
        var_name = '%s_%s_%s' %(hemisphere, direction, metric[0:3])
        iris.std_names.STD_NAMES[standard_name] = {'canonical_units': units_dict[metric]}
        metric_cube = iris.cube.Cube(data,
                                     standard_name=standard_name,
                                     long_name=long_name,
                                     var_name=var_name,
                                     units=units_dict[metric],
                                     attributes=atts,
                                     dim_coords_and_dims=[(time_coord, 0)],
                                     )
        cube_list.append(metric_cube)        

    cube_list = iris.cube.CubeList(cube_list)
    cube_list = cube_list.concatenate()

    return cube_list


def main(inargs):
    """Run the program."""

    # Read data
    cube = iris.load(inargs.infiles, 'surface_downward_eastward_stress', callback=save_history)
    equalise_attributes(cube)
    iris.util.unify_time_units(cube)
    cube = cube.concatenate_cube()
    cube = gio.check_time_units(cube)

    # Prepare data
    cube = timeseries.convert_to_annual(cube)

    sftlf_cube = iris.load_cube(inargs.sftlf_file, 'land_area_fraction')
    mask = create_land_mask(sftlf_cube, cube.shape)
    cube.data = numpy.ma.asarray(cube.data)
    cube.data.mask = mask
    
    cube = cube.collapsed('longitude', iris.analysis.MEAN)

    # Calculate metrics
    xdata = cube.coord('latitude').points
    xnew = numpy.linspace(xdata[0], xdata[-1], num=1000, endpoint=True)

    hemispheres = ['sh', 'nh']
    directions = ['easterly', 'westerly']
    
    metric_dict = {}
    for hemisphere, direction in itertools.product(hemispheres, directions):
        metric_dict[(hemisphere, direction, 'location')] = []
        metric_dict[(hemisphere, direction, 'magnitude')] = []

    for ycube in cube.slices(['latitude']):
        func = interp1d(xdata, ycube.data, kind='cubic')
        ynew = func(xnew)
        for hemisphere, direction in itertools.product(hemispheres, directions):
            loc, mag = wind_stress_metrics(xnew, ynew, hemisphere, direction)
            metric_dict[(hemisphere, direction, 'location')].append(loc)
            metric_dict[(hemisphere, direction, 'magnitude')].append(mag)
            
    # Write the output file
    atts = cube.attributes
    infile_history = {inargs.infiles[0]: history[0]}
    atts['history'] = gio.write_metadata(file_info=infile_history)
    units_dict = {'magnitude': cube.units, 'location': cube.coord('latitude').units}
    cube_list = create_outcubes(metric_dict, cube.attributes, units_dict, cube.coord('time'))

    iris.save(cube_list, inargs.outfile)


if __name__ == '__main__':

    extra_info =""" 
author:
    Damien Irving, irving.damien@gmail.com

"""

    description='Calculate zonal surface wind stress (over ocean) metrics'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("infiles", type=str, nargs='*', help="Wind stress (tauu) data files (can merge on time)")
    parser.add_argument("sftlf_file", type=str, help="Land area fraction file for ")
    parser.add_argument("outfile", type=str, help="Output file name")
    
    args = parser.parse_args()            

    main(args)
