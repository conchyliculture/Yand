#!/bin/bash

# This script will take a large binary file as an input, then will
# convert each byte into a greyscale pixel, that will be stored in
# 8 PGM pictures.
# These pictures are then horizontally joined.
# This picture is scaled 200%, and then used to generate at Leaflet
# compatible tile pyramid.
# This pyramid can be explored by pointing your web browser to the
# small python HTTP server that's then exposed
#
#         ########  -> ########  -> etc....
#         ########  |  ########  |
#         ##++####  |  ########  |
#         ########  |  ########  |
#         ##   ###  |  ########  |
#         ###+++##  |  ########  |
#         ########  |  ########  |
#         ######## -   ######## -


DUMP_FILEPATH=$(realpath "${1}")
DUMP_FILENAME=$(basename "${DUMP_FILEPATH}")
DUMP_FILESIZE=$(stat --printf='%s' "${DUMP_FILEPATH}")
PAGE_SIZE="${2}"

NUMBER_OF_SPLITS="${3}"
if [ "${NUMBER_OF_SPLITS}" == "" ] ; then
    NUMBER_OF_SPLITS=8
fi

TOOLS_DIR="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"
HTTP_SERV="${TOOLS_DIR}/viz_http.py"

PICS_DIR="pics"

PGM_DIR="${PICS_DIR}/${DUMP_FILENAME}/pgm"
TILES_DIR="${PICS_DIR}/${DUMP_FILENAME}/tiles"

BIG_PNG="${PICS_DIR}/${DUMP_FILENAME}.png"
SMOL_PNG="${PICS_DIR}/${DUMP_FILENAME}_smol.png"

SRC_PGM_TOOL="${TOOLS_DIR}/bin_to_ppm.c"
COMPILED_PGM_TOOL="${TOOLS_DIR}/bin2pgm"

if [ ! -f "${DUMP_FILEPATH}" ] ; then
    echo "Please provide a dump file"
    exit 1
fi

if ! ([[ "${PAGE_SIZE}" =~ ^[0-9]+$ ]] && [[ "${PAGE_SIZE}" -gt 0 ]]) ; then
    echo "Page size needs to be an integer > 0"
    exit
fi

if [ ! -f "${COMPILED_PGM_TOOL}" ] ; then
    echo "Compiling ${COMPILED_PGM_TOOL}"
    gcc -Werror -Wpedantic "${SRC_PGM_TOOL}" -o "${COMPILED_PGM_TOOL}"
    if [[ $? != 0 ]] ; then
        exit 1
    fi
fi

if [ ! -d "${PGM_DIR}" ] ; then
    mkdir -p "${PGM_DIR}"
    echo "Making the sub-pics in ${PGM_DIR} ...."

    "${COMPILED_PGM_TOOL}" "${DUMP_FILEPATH}" "${PAGE_SIZE}" "${PGM_DIR}" "${NUMBER_OF_SPLITS}"
    if [[ $? != 0 ]] ; then
        rmdir "${PGM_DIR}"
        exit 1
    fi
fi

if [ ! -d "${TILES_DIR}" ] ; then
    if [ ! -f "${BIG_PNG}" ] ; then
        echo "Joining the sub-pics into ${BIG_PNG} ...."
        file_list="$(ls -1 "${PGM_DIR}"/*.pgm | paste -sd " ")"
        vips --vips-progress VipsArrayJoin "${file_list}"  "${SMOL_PNG}" --across "${NUMBER_OF_SPLITS}"
        if [[ $? != 0 ]] ; then
            exit 1
        fi
        echo "Scaling it up for more glorious pixels"
        vips --vips-progress VipsResize "${SMOL_PNG}" "${BIG_PNG}" 2
        if [[ $? != 0 ]] ; then
            exit 1
        fi
        rm "${SMOL_PNG}"
    fi
    mkdir -p "${TILES_DIR}"
    echo "Building tiles in ${TILES_DIR}"
    vips --vips-progress dzsave "${BIG_PNG}" "${TILES_DIR}" --layout google
    if [[ $? != 0 ]] ; then
        rmdir "${TILES_DIR}"
        exit 1
    fi
fi

echo "ALL DONE"
echo
if [ -f ${BIG_PNG} ]; then
    echo "You might want to delete ${BIG_PNG}, it's not going to be used any more"
fi
python3 "${HTTP_SERV}" -d "${TILES_DIR}" -s ${NUMBER_OF_SPLITS} -t ${DUMP_FILESIZE} -p ${PAGE_SIZE}
