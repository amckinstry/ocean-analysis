
model=FGOALS-g2

experiments=(piControl)
rips=(r1i1p1)

fx_rip=r0i0p0
fx_experiment=historical

spatial_agg='sum'
#sum mean
vars=(hfds)

python=/g/data/r87/dbi599/miniconda3/envs/ocean/bin/python
script_dir=/home/599/dbi599/ocean-analysis/data_processing

ua6_dir=/g/data/ua6/DRSv2/CMIP5/${model}
r87_dir=/g/data/r87/dbi599/DRSv2/CMIP5/${model}

sftlf_file=${ua6_dir}/${fx_experiment}/fx/atmos/${fx_rip}/sftlf/latest/sftlf_fx_${model}_${fx_experiment}_${fx_rip}.nc


for var in "${vars[@]}"; do

if [[ "${var}" == 'pr' ]] ; then
    standard_name='precipitation_flux'
    file_var='pr-ocean'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'evspsbl' ]] ; then
    standard_name='water_evaporation_flux'
    file_var='evspsbl-ocean'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'pe' ]] ; then
    standard_name='precipitation_minus_evaporation_flux'
    file_var='pe-ocean'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'tos' ]] ; then
    standard_name='sea_surface_temperature'
    file_var='tos'
    realm='ocean'
    prefix='O'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'ohc' ]] ; then
    standard_name='ocean_heat_content'
    file_var='ohc'
    realm='ocean'
    prefix='O'
    input_tscale='yr'
    temporal_agg=' '
elif [[ "${var}" == 'rsds' ]] ; then
    standard_name='surface_downwelling_shortwave_flux_in_air'
    file_var='rsds'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'rsus' ]] ; then
    standard_name='surface_upwelling_shortwave_flux_in_air'
    file_var='rsus'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'rlds' ]] ; then
    standard_name='surface_downwelling_longwave_flux_in_air'
    file_var='rlds'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'rlus' ]] ; then
    standard_name='surface_upwelling_longwave_flux_in_air'
    file_var='rlus'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'hfss' ]] ; then
    standard_name='surface_upward_sensible_heat_flux'
    file_var='hfss'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'hfls' ]] ; then
    standard_name='surface_upward_latent_heat_flux'
    file_var='hfls'
    realm='atmos'
    prefix='A'
    input_tscale='mon'
    temporal_agg='--annual'
elif [[ "${var}" == 'hfds' ]] ; then
    standard_name='surface_downward_heat_flux_in_sea_water'
    file_var='hfds'
    realm='ocean'
    prefix='O'
    input_tscale='mon'
    temporal_agg='--annual'
fi

for experiment in "${experiments[@]}"; do
for rip in "${rips[@]}"; do

mkdir -p /g/data/r87/dbi599/DRSv2/CMIP5/${model}/${experiment}/yr/${realm}/${rip}/${var}/latest/

input_file=${ua6_dir}/${experiment}/${input_tscale}/${realm}/${rip}/${var}/latest/${file_var}_${prefix}${input_tscale}_${model}_${experiment}_${rip}_*.nc

output_file=${r87_dir}/${experiment}/yr/${realm}/${rip}/${var}/latest/${file_var}-zonal-${spatial_agg}_${prefix}yr_${model}_${experiment}_${rip}_all.nc

command="${python} ${script_dir}/calc_zonal_aggregate.py ${input_file} ${standard_name} ${spatial_agg} ${output_file} ${temporal_agg} --area"
# --area --realm ocean --sftlf_file ${sftlf_file} 

echo ${command}
${command}

done
done
done
