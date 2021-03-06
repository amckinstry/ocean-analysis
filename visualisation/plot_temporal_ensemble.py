"""
Filename:     plot_temporal_ensemble.py
Author:       Damien Irving, irving.damien@gmail.com
Description:  Plot timeseries for an ensemble of models  

"""

# Import general Python modules

import sys, os, pdb
import argparse
from itertools import groupby
from  more_itertools import unique_everseen
import numpy
import iris
from iris.experimental.equalise_cubes import equalise_attributes
import iris.plot as iplt
import matplotlib.pyplot as plt
from matplotlib import gridspec
import seaborn
seaborn.set_context('talk')

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
    import timeseries
    import grids
    import convenient_universal as uconv
except ImportError:
    raise ImportError('Must run this script from anywhere within the ocean-analysis git repo')


# Define functions

experiment_colors = {'historical': 'black', 'historicalGHG': 'red',
                     'historicalAA': 'blue', 'GHG + AA': 'purple',
                     'rcp85': 'orange', 'rcp60': 'yellow',
                     'rcp45': 'green', 'rcp26': 'magenta',
                     'piControl': '0.5'}


def get_colors(family_list):
    """Define a color for each model/physics combo"""

    nfamilies = len(family_list)
    cm = plt.get_cmap('nipy_spectral')
    colors = [cm(1. * i / (nfamilies + 1)) for i in range(nfamilies + 1)]
    color_dict = {}
    count = 1  # skips the first color, which is black
    for family in family_list:
        color_dict[family] = colors[count]
        count = count + 1

    return color_dict


def get_ylabel(cube, inargs):
    """get the y axis label"""

    if inargs.ylabel:
        ylabel = inargs.ylabel
    else:
        ylabel = str(cube.units)

    if ylabel == 'kg m-2 s-1':
        ylabel = '$kg \: m^{-2} \: s^{-1}$' 
        
    return ylabel


def get_line_width(realization, model):
    """Get the line width"""

    if model == 'FGOALS-g2':
        lw = 2.0
    else:
        lw = 2.0 if realization == 'r1' else 0.5

    return lw


def plot_individual(data_dict, color_dict):
    """Plot the individual model data"""

    for key, cube in data_dict.items():
        model, physics, realization = key
        if (realization == 'r1') or (model == 'FGOALS-g2'):
            label = model + ', ' + physics
        else:
            label = None
        lw = 0.5   #get_line_width(realization, model)
        iplt.plot(cube, label=label, color=color_dict[(model, physics)], linewidth=lw)


def equalise_time_axes(cube_list):
    """Make all the time axes the same."""

    iris.util.unify_time_units(cube_list)
    reference_cube = cube_list[0]
    new_cube_list = iris.cube.CubeList([])
    for cube in cube_list:
        assert len(cube.coord('time').points) == len(reference_cube.coord('time').points)
        cube.coord('time').points = reference_cube.coord('time').points
        cube.coord('time').bounds = reference_cube.coord('time').bounds
        cube.coord('time').units = reference_cube.coord('time').units
        cube.coord('time').attributes = reference_cube.coord('time').attributes
        new_cube_list.append(cube)
    
    return new_cube_list


def plot_ensagg(data_dict, experiment, nexperiments, ensagg='mean',
                single_run=False, linestyle='-', linewidth=2.0):
    """Plot the ensemble aggregate.

    If single_run is true, the ensemble is calculated using
      only the first run from each model/physics family.

    """

    aggregators = {'mean': iris.analysis.MEAN, 'median': iris.analysis.MEDIAN}

    cube_list = iris.cube.CubeList([])
    count = 0
    for key, cube in data_dict.items():
        model, physics, realization = key
        if not single_run or ((realization == 'r1') or (model == 'FGOALS-g2')):
            cube_list.append(cube)
            count = count + 1

    if len(cube_list) > 1:
        equalise_attributes(cube_list)
        cube_list = equalise_time_axes(cube_list)
        ensemble_cube = cube_list.merge_cube()
        ensemble_agg = ensemble_cube.collapsed('ensemble_member', aggregators[ensagg])
    else:
        ensemble_agg = cube_list[0]
   
    label, color = get_ensemble_label_color(experiment, nexperiments, ensagg, count, single_run)
    iplt.plot(ensemble_agg, label=label, color=color, linestyle=linestyle, linewidth=linewidth)

    return ensemble_agg


def get_ensemble_label_color(experiment, nexperiments, agg_method, ensemble_size, single_run):
    """Get the line label and color."""

    if ensemble_size == 1:
        label = experiment
    elif single_run:
        label = 'ensemble %s (r1)'  %(agg_method) 
    else:
        label = 'ensemble %s (all runs)'  %(agg_method)
    color = 'black' 

    if nexperiments > 1:
        if ensemble_size != 1:
            label = experiment + ', ' + label
        color = experiment_colors[experiment]

    return label, color


def group_runs(data_dict):
    """Find unique model/physics groups"""

    all_info = data_dict.keys()

    model_physics_list = []
    for key, group in groupby(all_info, lambda x: x[0:2]):
        model_physics_list.append(key)

    family_list = list(unique_everseen(model_physics_list))

    return family_list


def read_data(inargs, infiles, time_bounds, ref_cube=None, anomaly=False, branch_index=None, branch_time=None):
    """Read data."""

    data_dict = {}
    file_count = 0
    for infile in infiles:
        try:
            cube = iris.load_cube(infile, gio.check_iris_var(inargs.var))
        except iris.exceptions.ConstraintMismatchError:
            print('using inferred value for', infile)
            cube = iris.load_cube(infile, gio.check_iris_var('Inferred_' + inargs.var))
            cube.long_name = inargs.var.replace('_', ' ')
            cube.var_name = cube.var_name.replace('-inferred', '')
        
        if ref_cube:
            cube = timeseries.adjust_control_time(cube, ref_cube, branch_index=branch_index, branch_time=branch_time)

        if not (ref_cube and inargs.full_control):
            time_constraint = gio.get_time_constraint(time_bounds)
            cube = cube.extract(time_constraint)

        if anomaly:
            cube.data = cube.data - cube.data[0:20].mean()     

        cube.data = cube.data.astype(numpy.float64)
        cube.cell_methods = ()
        for aux_coord in ['latitude', 'longitude']:
            try:
                cube.remove_coord(aux_coord)
            except iris.exceptions.CoordinateNotFoundError:
                pass

        new_aux_coord = iris.coords.AuxCoord(file_count, long_name='ensemble_member', units='no_unit')
        cube.add_aux_coord(new_aux_coord)
         
        model = cube.attributes['model_id']
        realization = 'r' + str(cube.attributes['realization'])
        physics = 'p' + str(cube.attributes['physics_version'])
        experiment = cube.attributes['experiment_id']

        key = (model, physics, realization)
        data_dict[key] = cube
        file_count = file_count + 1
    
    ylabel = get_ylabel(cube, inargs)
    experiment = 'historicalAA' if experiment == "historicalMisc" else experiment
    metadata_dict = {infile: cube.attributes['history']}
    
    return data_dict, experiment, ylabel, metadata_dict


def get_title(standard_name, experiment, nexperiments):
    """Get the plot title"""

    try:
        title = gio.var_names[standard_name]
    except KeyError:
        title = standard_name.replace('_', ' ')

    if nexperiments == 1:
        title = title + ', ' + experiment

    return title


def plot_file(infiles, time_bounds, inargs, nexperiments, ref_cube=None, branch_index=None, branch_time=None):
    """Plot the data for a given input file."""

    data_dict, experiment, ylabel, metadata_dict = read_data(inargs, infiles, time_bounds, ref_cube=ref_cube,
                                                             anomaly=inargs.anomaly, branch_index=branch_index,
                                                             branch_time=branch_time)
    
    model_family_list = group_runs(data_dict)
    color_dict = get_colors(model_family_list)

    if nexperiments == 1:
        plot_individual(data_dict, color_dict)
    if inargs.ensagg:
        ensemble_agg = plot_ensagg(data_dict, experiment, nexperiments, ensagg=inargs.ensagg,
                                   single_run=inargs.single_run)

    return data_dict, experiment, ylabel, metadata_dict


def main(inargs):
    """Run the program."""

    fig, ax = plt.subplots(figsize=[14, 7])
    nexperiments = len(inargs.hist_files) + len(inargs.rcp_files) + len(inargs.control_files)
    
    # Plot historical data
    for infiles in inargs.hist_files:
        data_dict, experiment, ylabel, metadata_dict = plot_file(infiles, inargs.hist_time, inargs, nexperiments)

    # Plot control data
    if inargs.control_files:
        assert inargs.hist_files, 'Control plot requires branch time information from historical files'
        ref_cube = data_dict.popitem()[1]
        if inargs.full_control:
            time_bounds = None
        else:
            plot_start_time = inargs.hist_time[0]
            plot_end_time = inargs.rcp_time[-1] if inargs.rcp_files else inargs.hist_time[-1]
            time_bounds = [plot_start_time, plot_end_time]
        for infiles in inargs.control_files:
            data_dict, experiment, ylabel, metadata_dict = plot_file(infiles, time_bounds, inargs, nexperiments,
                                                                     ref_cube=ref_cube, branch_index=inargs.branch_index,
                                                                     branch_time=inargs.branch_time)        

    # Plot rcp data
    for infiles in inargs.rcp_files:
        data_dict, experiment, ylabel, metadata_dict = plot_file(infiles, inargs.rcp_time, inargs, nexperiments)        

    if inargs.title:
         plt.title(inargs.title)
    else:
        title = get_title(inargs.var, experiment, nexperiments)
        plt.title(title)

    if inargs.ylim:
        ymin, ymax = inargs.ylim
        plt.ylim(ymin, ymax)

    #plt.ylim(-4e+23, 8e+23)

    if inargs.scientific:
        plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0), useMathText=True, useOffset=False)
        ax.yaxis.major.formatter._useMathText = True
    ax.set_ylabel(ylabel)
    ax.yaxis.major.formatter._useOffset = False

    if inargs.zero_line:
        plt.axhline(y=0, color='0.5', linestyle='--')

    if inargs.legloc:
        ax.legend(loc=inargs.legloc)
    else:
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

    ymin, ymax = plt.ylim()
    print('ymin:', ymin)
    print('ymax:', ymax)
    plt.savefig(inargs.outfile, bbox_inches='tight')
    gio.write_metadata(inargs.outfile, file_info=metadata_dict)


if __name__ == '__main__':

    extra_info =""" 

author:
    Damien Irving, irving.damien@gmail.com

"""

    description = 'Plot ensemble timeseries'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("var", type=str, help="Variable")
    parser.add_argument("outfile", type=str, help="Output file")                                     
    
    parser.add_argument("--hist_files", type=str, action='append', nargs='*', default=[],
                        help="Input files for an historical experiment")
    parser.add_argument("--rcp_files", type=str, action='append', nargs='*', default=[],
                        help="Input files for an RCP experiment")
    parser.add_argument("--control_files", type=str, action='append', nargs='*', default=[],
                        help="Input files for a control experiment")

    parser.add_argument("--hist_time", type=str, nargs=2, metavar=('START_DATE', 'END_DATE'),
                        default=('1861-01-01', '2005-12-31'),
                        help="Time bounds for historical period [default = 1861-2005]")
    parser.add_argument("--rcp_time", type=str, nargs=2, metavar=('START_DATE', 'END_DATE'),
                        default=('2006-01-01', '2100-12-31'),
                        help="Time bounds for rcp period [default = None]")

    parser.add_argument("--branch_time", type=float, default=None,
                        help="Override the branch time listed in the file metadata")
    parser.add_argument("--branch_index", type=int, default=None,
                        help="Override the branch index determined from the branch time")

    parser.add_argument("--single_run", action="store_true", default=False,
                        help="Only use run 1 in the ensemble mean [default=False]")
    parser.add_argument("--ensagg", type=str, choices=('mean', 'median'), default=None,
                        help="Plot an ensemble aggregate curve [default=False]")

    parser.add_argument("--legloc", type=int, default=None,
                        help="Legend location [default = off plot]")

    parser.add_argument("--title", type=str, default=None,
                        help="overwrite default plot title")
    parser.add_argument("--ylabel", type=str, default=None,
                        help="y axis label") 
    parser.add_argument("--ylim", type=float, nargs=2, metavar=('MIN', 'MAX'), default=None,
                        help="limits for y axis")

    parser.add_argument("--scientific", action="store_true", default=False,
                        help="Use scientific notation for the y axis scale [default=False]")
    parser.add_argument("--zero_line", action="store_true", default=False,
                        help="Draw a dahsed line at y=0 [default=False]")
    
    parser.add_argument("--full_control", action="store_true", default=False,
                        help="Plot the full control experiment [default=False]")

    parser.add_argument("--anomaly", action="store_true", default=False,
                        help="convert data to an anomaly by subracting mean of first 20 data points [default=False]")

    args = parser.parse_args()             
    main(args)
