"""Collection of functions for dealing with grids.

Functions:
  curvilinear_to_rectilinear  -- Regrid curvilinear data to a rectilinear 
                                 grid if necessary
  get_grid_spacing            -- Return an array of grid spacings
  regrid_1D                   -- Regrid data with only one spatial dimension

"""

import pdb
import numpy
import iris
from iris.experimental.regrid import regrid_weighted_curvilinear_to_rectilinear


def _check_coord_names(cube, coord_names):
    """Remove specified coordinate name.

    The iris standard names for lat/lon coordinates are:
      latitude, grid_latitude, longitude, grid_longitude

    If a cube uses one for the dimension coordinate and the 
      other for the auxillary coordinate, the 
      regrid_weighted_curvilinear_to_rectilinear method won't work

    Args:
      cube (iris.cube.Cube)
      coord_names(list)

    """

    if 'grid_latitude' in coord_names:
        cube.coord('grid_latitude').standard_name = None
        coord_names = [coord.name() for coord in cube.dim_coords]
    if 'grid_longitude' in coord_names:
        cube.coord('grid_longitude').standard_name = None
        coord_names = [coord.name() for coord in cube.dim_coords]

    return cube, coord_names


def _make_grid(lat_values, lon_values):
    """Make a dummy cube with desired grid."""
       
    latitude = iris.coords.DimCoord(lat_values,
                                    standard_name='latitude',
                                    units='degrees_north',
                                    coord_system=iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS))
    longitude = iris.coords.DimCoord(lon_values,                    
                                     standard_name='longitude',
                                     units='degrees_east',
                                     coord_system=iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS))

    dummy_data = numpy.zeros((len(lat_values), len(lon_values)))
    new_cube = iris.cube.Cube(dummy_data, dim_coords_and_dims=[(latitude, 0), (longitude, 1)])

    new_cube.coord('longitude').guess_bounds()
    new_cube.coord('latitude').guess_bounds()

    return new_cube


def get_grid_spacing(cube):
    """Return an array of grid spacings."""

    if not cube.coord('latitude').has_bounds():
        cube.coord('latitude').guess_bounds()

    spacing = [numpy.diff(bounds)[0] for bounds in cube.coord('latitude').bounds]
    
    return numpy.array(spacing)


def get_grid_res(horiz_shape):
    """Define horizontal resolution of new grid. 

    Calculation makes sure new grid is similar resolution to old grid
    (erring on side of slightly more coarse)

    """

    assert len(horiz_shape) == 2
    orig_npoints = horiz_shape[0] * horiz_shape[1]

    res_options = numpy.array([1.0, 1.5, 2.0, 2.5])
    npoints_ref = numpy.array([181 * 360, 121 * 240, 91 * 180, 73 * 144])

    idx = (numpy.abs(npoints_ref - orig_npoints)).argmin()
    
    new_res = res_options[idx]
    if orig_npoints < npoints_ref[idx]:
        new_res = new_res + 0.5

    new_res = new_res + 0.5  # safety buffer

    print("new horizontal grid resolution =", new_res)

    return new_res


def curvilinear_to_rectilinear(cube, target_grid_cube=None):
    """Regrid curvilinear data to a rectilinear grid if necessary."""

    coord_names = [coord.name() for coord in cube.dim_coords]
    aux_coord_names = [coord.name() for coord in cube.aux_coords]

    if 'time' in aux_coord_names:
        aux_coord_names.remove('time')
    if 'depth' in aux_coord_names:
        aux_coord_names.remove('depth')

    if aux_coord_names == ['latitude', 'longitude']:

        if not target_grid_cube:
            grid_res = get_grid_res(cube.coord('latitude').shape)
            lats = numpy.arange(-90, 90.01, grid_res)
            lons = numpy.arange(0, 360, grid_res)
            target_grid_cube = _make_grid(lats, lons)

        # Interate over slices (experimental regridder only works on 2D slices)
        cube, coord_names = _check_coord_names(cube, coord_names)
        slice_dims = coord_names

        if 'time' in slice_dims:
            slice_dims.remove('time')
        if 'depth' in slice_dims:
            slice_dims.remove('depth')
    
        cube_list = []
        for i, cube_slice in enumerate(cube.slices(slice_dims)):
            weights = numpy.ones(cube_slice.shape)
            cube_slice.coord(axis='x').coord_system = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
            cube_slice.coord(axis='y').coord_system = iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS)
            regridded_cube = regrid_weighted_curvilinear_to_rectilinear(cube_slice, weights, target_grid_cube)
            cube_list.append(regridded_cube)

        new_cube = iris.cube.CubeList(cube_list)
        new_cube = new_cube.merge_cube()
        coord_names = [coord.name() for coord in new_cube.dim_coords]

        regrid_status = True

    else:

        new_cube = cube
        regrid_status = False
    
    return new_cube, coord_names, regrid_status


def regrid_1D(cube, target_cube, y_axis_name, clear_units=False):
    """Regrid data with only one spatial dimension"""

    ref_lats = [(y_axis_name, target_cube.coord(y_axis_name).points)]  
    regridded_cube = cube.interpolate(ref_lats, iris.analysis.Linear())
    regridded_cube.coord(y_axis_name).bounds = target_cube.coord(y_axis_name).bounds
    regridded_cube.coord(y_axis_name).coord_system = target_cube.coord(y_axis_name).coord_system
    regridded_cube.coord(y_axis_name).attributes = target_cube.coord(y_axis_name).attributes

    regridded_cube.coord(y_axis_name).var_name = target_cube.coord(y_axis_name).var_name
    regridded_cube.coord(y_axis_name).standard_name = target_cube.coord(y_axis_name).standard_name
    regridded_cube.coord(y_axis_name).long_name = target_cube.coord(y_axis_name).long_name

    if clear_units:
        regridded_cube.units= ''

    return regridded_cube 
