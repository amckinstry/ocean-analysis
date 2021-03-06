# ocean_3d_config.mk

# System configuration

PYTHON=/g/data/r87/dbi599/miniconda3/envs/ocean/bin/python

MY_DATA_DIR=/g/data/r87/dbi599
UA6_DATA_DIR=/g/data/ua6
CMIP5_DIR_START=/DRSv2/CMIP5
MY_CMIP5_DIR=${MY_DATA_DIR}${CMIP5_DIR_START}
UA6_CMIP5_DIR=${UA6_DATA_DIR}${CMIP5_DIR_START}

DATA_SCRIPT_DIR=~/ocean-analysis/data_processing
VIS_SCRIPT_DIR=~/ocean-analysis/visualisation

FIG_TYPE=png

# Analysis details (broad)

ORIG_VARIABLE_DIR=${MY_CMIP5_DIR}
ORIG_CONTROL_DIR=${UA6_CMIP5_DIR}
ORIG_VOL_DIR=${UA6_CMIP5_DIR}
ORIG_BASIN_DIR=${UA6_CMIP5_DIR}
ORIG_DEPTH_DIR=${UA6_CMIP5_DIR}
ORIG_AREAA_DIR=${UA6_CMIP5_DIR}
ORIG_AREAO_DIR=${UA6_CMIP5_DIR}

VAR=thetao
LONG_NAME=sea_water_salinity

MODEL=CanESM2
EXPERIMENT=historicalMisc
RUN=r1i1p4
CONTROL_RUN=r1i1p1
FX_RUN=r0i0p0

# Analysis details (specific)

MAX_DEPTH=2000
START_DATE=1950-01-01
END_DATE=2000-12-31

METRIC=ohc-metrics-globe60equiv
REF=--ref_region globe60

ZM_TICK_MAX=3.5
ZM_TICK_STEP=0.5
VM_TICK_MAX=10
VM_TICK_STEP=2
SCALE_FACTOR=3
PALETTE=BrBG_r

TARGET=${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/${VAR}/latest/dedrifted

#${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/ohc-maps/latest/ohc-maps_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_all.nc

# ${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/${VAR}-maps/latest/${VAR}-maps-time-trend-vertical-mean_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_${START_DATE}_${END_DATE}.png
# ${MY_CMIP5_DIR}/${MODEL}/${EXPERIMENT}/yr/ocean/${RUN}/${VAR}-maps/latest/${VAR}-maps-global-tas-trend-zonal-mean_Oyr_${MODEL}_${EXPERIMENT}_${RUN}_${START_DATE}_${END_DATE}.png
