"""
Filename:     calc_ocean_maps.py
Author:       Damien Irving, irving.damien@gmail.com
Description:  Calculate the zonal and vertical mean ocean anomaly fields

"""

# Import general Python modules

import sys, os, pdb
import argparse, math
import numpy
import iris
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
    import spatial_weights
    import grids
except ImportError:
    raise ImportError('Must run this script from anywhere within the ocean-analysis git repo')


# Define functions

history = []

vertical_layers = {'surface': [0, 50],
                   'shallow': [50, 350],
                   'middle': [350, 700],
                   'deep': [700, 2000],
                   'argo': [0, 2000]}

basins = {'atlantic': 2, 
          'pacific': 3,
          'indian': 5,
          'globe': 100}


def add_metadata(orig_atts, new_cube, standard_name, var_name, units):
    """Add metadata to the output cube.
    
    Name can be 'vertical_mean' or 'zonal_mean'
    
    """

    iris.std_names.STD_NAMES[standard_name] = {'canonical_units': units}

    new_cube.standard_name = standard_name
    new_cube.long_name = standard_name.replace('_', ' ')
    new_cube.var_name = var_name
    new_cube.attributes = orig_atts  

    return new_cube


def calc_vertical_mean(cube, layer, coord_names, atts,
                       original_standard_name, original_var_name):
    """Calculate the vertical mean over a given depth range."""

    min_depth, max_depth = vertical_layers[layer]
    level_subset = gio.iris_vertical_constraint(min_depth, max_depth)
    cube_segment = cube.extract(level_subset)

    depth_axis = cube_segment.coord('depth')
    if depth_axis.units == 'm':
        vertical_weights = spatial_weights.calc_vertical_weights_1D(depth_axis, coord_names, cube_segment.shape)
    elif depth_axis.units == 'dbar':
        vertical_weights = spatial_weights.calc_vertical_weights_2D(depth_axis, cube_segment.coord('latitude'), coord_names, cube_segment.shape)

    vertical_mean_cube = cube_segment.collapsed(['depth'], iris.analysis.MEAN, weights=vertical_weights.astype(numpy.float32))   
    vertical_mean_cube.remove_coord('depth')
    vertical_mean_cube.data = vertical_mean_cube.data.astype(numpy.float32)
        
    units = str(cube.units)
    standard_name = 'vertical_mean_%s_%s' %(layer, original_standard_name)
    var_name = '%s_vm_%s'   %(original_var_name, layer)
    vertical_mean_cube = add_metadata(atts, vertical_mean_cube, standard_name, var_name, units)

    return vertical_mean_cube


def calc_zonal_mean(cube, basin_array, basin_name, atts,
                    original_standard_name, original_var_name):
    """Calculate the zonal mean for a given ocean basin."""

    if not basin_name == 'globe':  
        cube.data.mask = numpy.where((cube.data.mask == False) & (basin_array == basins[basin_name]), False, True)

    zonal_mean_cube = cube.collapsed('longitude', iris.analysis.MEAN)
    zonal_mean_cube.remove_coord('longitude')
    zonal_mean_cube.data = zonal_mean_cube.data.astype(numpy.float32)

    units = str(cube.units)
    standard_name = 'zonal_mean_%s_%s' %(basin_name, original_standard_name)
    var_name = '%s_zm_%s'   %(original_var_name, basin_name)
    zonal_mean_cube = add_metadata(atts, zonal_mean_cube, standard_name, var_name, units)

    return zonal_mean_cube


def calc_zonal_vertical_mean(vertical_mean_cube, depth_cube, basin_array, basin_name, layer, atts,
                             original_standard_name, original_var_name):
    """Calculate the zonal mean of the vertical mean field."""

    assert layer in ['surface', 'argo']

    if not basin_name == 'globe':  
        vertical_mean_cube.data.mask = numpy.where((vertical_mean_cube.data.mask == False) & (basin_array == basins[basin_name]), False, True)

    if depth_cube:
        ndim = vertical_mean_cube.ndim
        depth_array = uconv.broadcast_array(depth_cube.data, [ndim - 2, ndim - 1], vertical_mean_cube.shape) 
    else: 
        depth_array = create_depth_array(vertical_mean_cube)

    max_depth = vertical_layers[layer][-1]
    depth_weights = numpy.ma.where(depth_array > max_depth, max_depth, depth_array)    

    zonal_vertical_mean_cube = vertical_mean_cube.collapsed(['longitude'], iris.analysis.MEAN, weights=depth_weights.astype(numpy.float32))   
    zonal_vertical_mean_cube.remove_coord('longitude')
    zonal_vertical_mean_cube.data = zonal_vertical_mean_cube.data.astype(numpy.float32)
        
    units = str(vertical_mean_cube.units)
    standard_name = 'zonal_vertical_mean_%s_%s_%s' %(basin_name, layer, original_standard_name)
    var_name = '%s_zvm_%s_%s'   %(original_var_name, basin_name, layer)
    zonal_vertical_mean_cube = add_metadata(atts, zonal_vertical_mean_cube, standard_name, var_name, units)

    return zonal_vertical_mean_cube


def create_depth_array(cube):
    """Create depth array."""

    # Idea would be to use iris to iterate over x-y slices checking
    # for first instance of missing value

    return numpy.ones(cube.shape) 


def read_optional(optional_file):
    """Read an optional file."""

    if optional_file:
        if 'no_data' in optional_file:
            cube = None
        else:
            cube = iris.load_cube(optional_file)
    else:
        cube = None

    return cube


def read_climatology(climatology_file, variable):
    """Read the optional climatology data."""

    if climatology_file:
        with iris.FUTURE.context(cell_datetime_objects=True):
            climatology_cube = iris.load_cube(climatology_file, variable)
    else:
        climatology_cube = None

    return climatology_cube


def save_history(cube, field, filename):
    """Save the history attribute when reading the data.
    (This is required because the history attribute differs between input files 
      and is therefore deleted upon equilising attributes)  
    """ 

    history.append(cube.attributes['history'])


def set_attributes(inargs, data_cube, climatology_cube, basin_cube, depth_cube):
    """Set the attributes for the output cube."""
    
    atts = data_cube.attributes

    infile_history = {}
    infile_history[inargs.infiles[0]] = history[0]

    if climatology_cube:                  
        infile_history[inargs.climatology_file] = climatology_cube.attributes['history']
    if basin_cube:                  
        infile_history[inargs.basin_file] = basin_cube.attributes['history']
    if depth_cube:                  
        infile_history[inargs.depth_file] = depth_cube.attributes['history']

    atts['history'] = gio.write_metadata(file_info=infile_history)

    return atts


def get_chunks(cube_shape, coord_names, chunk=False):
    """Provide details for chunking by time axis."""

    ntimes = cube_shape[0]

    if chunk:
        assert coord_names[0] == 'time'

        step = 2
        remainder = ntimes % step
        while remainder == 1:
            step = step + 1
            remainder = ntimes % step

        start_indexes = range(0, ntimes, step)
    else:
        start_indexes = [0]
        step = ntimes

    return start_indexes, step


def regrid_cube(cube):
    """Regrid the cube.

    For a singleton axis, curvilinear_to_rectilinear moves 
      that axis from being a dimension coordinate to a 
      scalar coordinate. 

    This function only focuses on a singleton time axis and 
      moves it back to being a dimension coordinate if need be 

    """

    singleton_flag = False
    if cube.shape[0] == 1:
        singleton_flag = True

    cube, coord_names, regrid_status = grids.curvilinear_to_rectilinear(cube)

    if singleton_flag:
        cube = iris.util.new_axis(cube, 'time')
        coord_names = [coord.name() for coord in cube.dim_coords]

    return cube, coord_names, regrid_status

     
def main(inargs):
    """Run the program."""

    try:
        time_constraint = gio.get_time_constraint(inargs.time)
    except AttributeError:
        time_constraint = iris.Constraint()

    with iris.FUTURE.context(cell_datetime_objects=True):
        data_cubes = iris.load(inargs.infiles, inargs.var & time_constraint, callback=save_history)
        equalise_attributes(data_cubes)

    climatology_cube = read_climatology(inargs.climatology_file, inargs.var)
    basin_cube = read_optional(inargs.basin_file)
    depth_cube = read_optional(inargs.depth_file) 

    atts = set_attributes(inargs, data_cubes[0], climatology_cube, basin_cube, depth_cube)

    out_cubes = []
    for data_cube in data_cubes:
        standard_name = data_cube.standard_name
        var_name = data_cube.var_name

        if climatology_cube:
            data_cube = data_cube - climatology_cube

        if basin_cube:
            data_cube = uconv.mask_marginal_seas(data_cube, basin_cube)

        data_cube, coord_names, regrid_status = regrid_cube(data_cube)
        if regrid_status:
            depth_cube = None
            # FIXME: Could delete depth file from atts

        assert coord_names[-3:] == ['depth', 'latitude', 'longitude']
        depth_axis = data_cube.coord('depth')
        assert depth_axis.units in ['m', 'dbar'], "Unrecognised depth axis units"

        out_list = iris.cube.CubeList([])
        start_indexes, step = uconv.get_chunks(data_cube.shape, coord_names, chunk=inargs.chunk)
        for index in start_indexes:

            cube_slice = data_cube[index:index+step, 0:1000, ...]

            # Vertical
            
            for layer in vertical_layers.keys():
                vertical_mean = calc_vertical_mean(cube_slice, layer, coord_names, atts, standard_name, var_name)
                out_list.append(vertical_mean)
                if layer in ['surface', 'argo']:
                    for basin in basins.keys():

                        if basin_cube and not regrid_status:
                            basin_array = basin_cube.data
                        else: 
                            basin_array = uconv.create_basin_array(vertical_mean)

                        out_list.append(calc_zonal_vertical_mean(vertical_mean.copy(), depth_cube, basin_array, basin, layer, atts, standard_name, var_name))

            # Zonal

            if basin_cube and not regrid_status:
                ndim = cube_slice.ndim
                basin_array = uconv.broadcast_array(basin_cube.data, [ndim - 2, ndim - 1], cube_slice.shape) 
            else: 
                basin_array = uconv.create_basin_array(cube_slice)

            for basin in basins.keys():
                out_list.append(calc_zonal_mean(cube_slice.copy(), basin_array, basin, atts, standard_name, var_name))

        out_cubes.append(out_list.concatenate())
        del out_list
        del cube_slice
        del basin_array

    cube_list = []
    nvars = len(vertical_layers.keys()) + len(basins.keys()) + 2*len(basins.keys())
    for var_index in range(0, nvars):
        temp_list = []
        for infile_index in range(0, len(inargs.infiles)):
            temp_list.append(out_cubes[infile_index][var_index])
        
        temp_list = iris.cube.CubeList(temp_list)     
        cube_list.append(temp_list.concatenate_cube())
    
    cube_list = iris.cube.CubeList(cube_list)

    assert cube_list[0].data.dtype == numpy.float32
    if not 'time' in coord_names:
        iris.FUTURE.netcdf_no_unlimited = True

    iris.save(cube_list, inargs.outfile)


if __name__ == '__main__':

    extra_info =""" 

author:
    Damien Irving, irving.damien@gmail.com

notes:
    On curvilinear grids it's not a good idea to use the basin file to 
    select the basin. When you regrid the missing values propagate and you
    end up with massive areas of missing values. This is what the 
    regrid_status is for. If it is true the input data is on a curvilinear grid 
    and thus the basin file will be used to mask the marginal seas but not for 
    selecting ocean basins.

"""

    description='Calculate the zonal and vertical mean ocean anomaly fields'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("infiles", type=str, nargs='*', help="Input data files")
    parser.add_argument("var", type=str, help="Input variable name (the standard_name)")
    parser.add_argument("outfile", type=str, help="Output file name")

    parser.add_argument("--climatology_file", type=str, default=None, 
                        help="Input climatology file (required if input data not already anomaly)")
    parser.add_argument("--basin_file", type=str, default=None, 
                        help="Input basin file")
    parser.add_argument("--depth_file", type=str, default=None, 
                        help="Input depth file")

    parser.add_argument("--time", type=str, nargs=2, metavar=('START_DATE', 'END_DATE'),
                        help="Time period [default = entire]")

    parser.add_argument("--chunk", action="store_true", default=False,
                        help="Split input files on time axis to avoid memory errors [default: False]")
        
    args = parser.parse_args()             
    main(args)
