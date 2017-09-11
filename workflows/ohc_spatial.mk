# ohc_spatial.mk
#
# Description: Workflow for producing ocean heat content spatial fields
#
# To execute:
#   1. copy name of target file from ohc_spatial.mk 
#   2. paste it into ohc_spatial_config.mk as the target THETAO  
#   3. $ make -n -B -f ohc_spatial.mk  (-n is a dry run) (-B is a force make)


# Define marcos

include ohc_spatial_config.mk
all : ${TARGET}

# Filenames

CONTROL_FILES=$(wildcard ${ORIG_CONTROL_DIR}/${MODEL}/piControl/mon/ocean/${CONTROL_RUN}/thetao/latest/thetao_Omon_${MODEL}_piControl_${CONTROL_RUN}_*.nc)
CONTROL_DIR=${MY_CMIP5_DIR}/${MODEL}/piControl/yr/ocean/${CONTROL_RUN}/thetao/latest
DRIFT_COEFFICIENTS=${CONTROL_DIR}/thetao-coefficients_Oyr_${MODEL}_piControl_${CONTROL_RUN}_all.nc

THETAO_FILES=$(wildcard ${ORIG_THETAO_DIR}/${MODEL}/${EXPERIMENT}/mon/ocean/${RUN}/thetao/latest/thetao_Omon_${MODEL}_${EXPERIMENT}_${RUN}_*.nc)

DEDRIFTED_THETAO_DIR=${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/thetao/latest/dedrifted
DEDRIFTED_THETAO_FILES = $(patsubst ${ORIG_THETAO_DIR}/${MODEL}/${EXPERIMENT}/mon/ocean/${RUN}/thetao/latest/thetao_Omon_%.nc, ${DEDRIFTED_THETAO_DIR}/thetao_Oyr_%.nc, ${THETAO_FILES})

OHC_DIR=${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/ohc/latest
DEDRIFTED_OHC_DIR=${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/ohc/latest/dedrifted

OHC_FILES=$(wildcard ${OHC_DIR}/ohc_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_*.nc)
DEDRIFTED_OHC_FILES=$(wildcard ${DEDRIFTED_OHC_DIR}/ohc-dedrifted_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_*.nc)

OCEAN_AREA_FILE=${ORIG_AREAO_DIR}/${MODEL}/${EXPERIMENT}/fx/ocean/${FX_RUN}/areacello/latest/areacello_fx_${MODEL}_${EXPERIMENT}_${FX_RUN}.nc
OCEAN_VOLUME_FILE=${ORIG_VOL_DIR}/${MODEL}/${EXPERIMENT}/fx/ocean/${FX_RUN}/volcello/latest/volcello_fx_${MODEL}_${EXPERIMENT}_${FX_RUN}.nc

OHC_TREND_FILE=${OHC_DIR}/ohc-trend_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_1850-2005.nc
OHC_TREND_WRT_TROPICS_FILE=${OHC_DIR}/ohc-trend-wrt-tropics_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_1850-2005.nc
DEDRIFTED_OHC_TREND_FILE=${DEDRIFTED_OHC_DIR}/ohc-dedrifted-trend_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_1850-2005.nc
DEDRIFTED_OHC_TREND_WRT_TROPICS_FILE=${DEDRIFTED_OHC_DIR}/ohc-dedrifted-trend-wrt-tropics_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_1850-2005.nc

# De-drift

${DRIFT_COEFFICIENTS} :
	mkdir -p ${CONTROL_DIR} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_drift_coefficients.py ${CONTROL_FILES} $@ --var sea_water_potential_temperature --annual

${DEDRIFTED_THETAO_DIR} : ${DRIFT_COEFFICIENTS}
	mkdir -p $@
	${PYTHON} ${DATA_SCRIPT_DIR}/remove_drift.py ${THETAO_FILES} sea_water_potential_temperature $< $@/ --annual 
        #--no_parent_check

# OHC

${OHC_DIR} :
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_ohc.py ${THETAO_FILES} sea_water_potential_temperature --volume_file ${OCEAN_VOLUME_FILE} --annual
        #--area_file ${OCEAN_AREA_FILE}

${DEDRIFTED_OHC_DIR} :
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_ohc.py ${DEDRIFTED_THETAO_FILES} sea_water_potential_temperature --volume_file ${OCEAN_VOLUME_FILE} 
        #--area_file ${OCEAN_AREA_FILE}

# Trends

${OHC_TREND_FILE} : 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_trend.py ${OHC_FILES} ocean_heat_content $@ --time_bounds 1850-01-01 2005-12-31 --regrid

${OHC_TREND_WRT_TROPICS_FILE} : 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_trend.py ${OHC_FILES} ocean_heat_content $@ --time_bounds 1850-01-01 2005-12-31 --subtract_tropics --regrid

${DEDRIFTED_OHC_TREND_FILE} : 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_trend.py ${DEDRIFTED_OHC_FILES} ocean_heat_content $@ --time_bounds 1850-01-01 2005-12-31 --regrid

${DEDRIFTED_OHC_TREND_WRT_TROPICS_FILE} : 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_trend.py ${DEDRIFTED_OHC_FILES} ocean_heat_content $@ --time_bounds 1850-01-01 2005-12-31 --subtract_tropics --regrid

# Plots

## no-dedrifting, regular trend


## dedrifted, regular trend


## no-dedrifting, trend wrt tropics

#python ../visualisation/plot_map.py 1 4 --infile /g/data/r87/dbi599/DRSv2/CMIP5/CanESM2/historicalMisc/yr/ocean/r1i1p4/ohc/latest/ohc-trend-wrt-tropics_Oyr_CanESM2_historicalMisc_r1i1p4_1850-2005.nc ocean_heat_content none none none colour0 1 PlateCarree --infile /g/data/r87/dbi599/DRSv2/CMIP5/CCSM4/historicalMisc/yr/ocean/r1i1p10/ohc/latest/ohc-trend-wrt-tropics_Oyr_CCSM4_historicalMisc_r1i1p10_1850-2005.nc ocean_heat_content none none none colour0 2 PlateCarree --infile /g/data/r87/dbi599/DRSv2/CMIP5/CSIRO-Mk3-6-0/historicalMisc/yr/ocean/r1i1p4/ohc/latest/ohc-trend-wrt-tropics_Oyr_CSIRO-Mk3-6-0_historicalMisc_r1i1p4_1850-2005.nc ocean_heat_content none none none colour0 3 PlateCarree --infile /g/data/r87/dbi599/DRSv2/CMIP5/FGOALS-g2/historicalMisc/yr/ocean/r2i1p1/ohc/latest/ohc-trend-wrt-tropics_Oyr_FGOALS-g2_historicalMisc_r2i1p1_1850-2005.nc ocean_heat_content none none none colour0 4 PlateCarree  --palette RdBu_r --colourbar_ticks -9.0 -7.5 -6.0 -4.5 -3.0 -1.5 0.0 1.5 3.0 4.5 6.0 7.5 9.0 --colourbar_ticks -0.9 -0.75 -0.6 -0.45 -0.3 -0.15 0.0 0.15 0.3 0.45 0.6 0.75 0.9 --colourbar_ticks -9.0 -7.5 -6.0 -4.5 -3.0 -1.5 0.0 1.5 3.0 4.5 6.0 7.5 9.0 --colourbar_ticks -0.9 -0.75 -0.6 -0.45 -0.3 -0.15 0.0 0.15 0.3 0.45 0.6 0.75 0.9 --extend both --scale_factor 17 colour0 --subplot_headings CanESM2 CCSM4 CSIRO-Mk3-6-0 FGOALS-g2 --title "Trend_in_OHC_wrt_tropics_(historicalAA,_1850-2005)" --ofile /g/data/r87/dbi599/figures/ohc-trend-wrt-tropics_Oyr_ensemble_historicalMisc_r1_1850-2005.png --figure_size 32 8 --colourbar_type individual

#height = 8 * nrows
#width = 8 * ncols



## dedrifting, trend wrt tropics


