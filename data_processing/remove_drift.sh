
model=GISS-E2-R

experiments=(historicalMisc)
rip=r1i1p107

control_rip=r1i1p1

indtype=ohc-sum-hemispheric-metrics
# ohc-zonal-sum ohc-sum-hemispheric-metrics

var=ocean_heat_content_nh_sum_div_globe_sum
# ocean_heat_content ocean_heat_content_globe_sum ocean_heat_content_nh_sum_div_globe_sum

outdtype=ohc-nh-sum-div-globe-sum
# ohc-zonal-sum ohc-nh-sum-div-globe-sum

python=/g/data/r87/dbi599/miniconda3/envs/ocean/bin/python
script_dir=/home/599/dbi599/ocean-analysis/data_processing

ua6_dir=/g/data/ua6/DRSv2/CMIP5/${model}
r87_dir=/g/data/r87/dbi599/DRSv2/CMIP5/${model}

for experiment in "${experiments[@]}"; do

control_file=${r87_dir}/piControl/yr/ocean/${control_rip}/ohc/latest/${indtype}_Oyr_${model}_piControl_${control_rip}_all.nc
coefficient_file=${r87_dir}/piControl/yr/ocean/${control_rip}/ohc/latest/${outdtype}-coefficients_Oyr_${model}_piControl_${control_rip}_all.nc
experiment_dir=${r87_dir}/${experiment}/yr/ocean/${rip}/ohc/latest
experiment_file=${experiment_dir}/${indtype}_Oyr_${model}_${experiment}_${rip}_all.nc
dedrifted_dir=${experiment_dir}/dedrifted
dedrifted_file=${dedrifted_dir}/${outdtype}_Oyr_${model}_${experiment}_${rip}_all.nc

coefficient_command="${python} ${script_dir}/calc_drift_coefficients.py ${control_file} ${var} ${coefficient_file}"
mkdir_command="mkdir ${dedrifted_dir}"
drift_command="${python} ${script_dir}/remove_drift.py ${experiment_file} ${var} annual ${coefficient_file} ${dedrifted_file} --branch_time 0"
# --branch_time 342005 (CCSM4) 175382.5 (FGOALS-g2) 0 (GISS-E2-R) --no_parent_check

echo ${coefficient_command}
${coefficient_command}

echo ${mkdir_command}
${mkdir_command}

echo ${drift_command}
${drift_command}

done

