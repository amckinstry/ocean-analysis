# Script for running the plot_atmos_heat_budget.py script
# May need to run apply_mask.sh first to apply ocean mask to atmos data

model=IPSL-CM5A-LR
mip=r1i1p3
experiment=historicalMisc

python=/g/data/r87/dbi599/miniconda3/envs/ocean/bin/python
script_dir=/home/599/dbi599/ocean-analysis/visualisation

ua6_dir=/g/data/ua6/DRSv2/CMIP5/${model}/${experiment}/mon
r87_dir=/g/data/r87/dbi599/DRSv2/CMIP5/${model}/${experiment}/mon

outfile=/g/data/r87/dbi599/figures/heat-cycle/atmos-heat-budget_Oyr_${model}_${experiment}_${mip}_all.png   #_hf-atmos
rsds_files="--rsds_files ${r87_dir}/ocean/${mip}/rsds/latest/rsds-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
rsus_files="--rsus_files ${r87_dir}/ocean/${mip}/rsus/latest/rsus-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
rlds_files="--rlds_files ${r87_dir}/ocean/${mip}/rlds/latest/rlds-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
rlus_files="--rlus_files ${r87_dir}/ocean/${mip}/rlus/latest/rlus-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
hfss_files="--hfss_files ${r87_dir}/ocean/${mip}/hfss/latest/hfss-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
hfls_files="--hfls_files ${r87_dir}/ocean/${mip}/hfls/latest/hfls-atmos_Omon_${model}_${experiment}_${mip}_*.nc"
hfds_files="--hfds_files ${r87_dir}/ocean/${mip}/hfds/latest/hfds_Omon_${model}_${experiment}_${mip}_*.nc"
hfsithermds_files="--hfsithermds_files ${ua6_dir}/ocean/${mip}/hfsithermds/latest/hfsithermds_Omon_${model}_${experiment}_${mip}_*.nc"

command="${python} ${script_dir}/plot_atmos_heat_budget.py ${outfile} ${rsds_files} ${rsus_files} ${rlds_files} ${rlus_files} ${hfss_files} ${hfls_files} --area --time 1850-01-01 2005-12-31"
# ${rsds_files} ${rsus_files} ${rlds_files} ${rlus_files} ${hfss_files} ${hfls_files} ${hfds_files} ${hfsithermds_files} ${hfds_files} --area  --hfrealm ocean --time 1850-01-01 2005-12-31

echo ${command}
${command}
echo ${outfile}