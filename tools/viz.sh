#!/bin/bash

STEPS=8

DUMP_FILE="${1}"
PAGE_SIZE="${2}"

TOOLS_DIR="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"
HTTP_SERV="${TOOLS_DIR}/viz_http.py"

PICS_DIR="pics"

PGM_DIR="${PICS_DIR}/${DUMP_FILE}/pgm"
TILES_DIR="${PICS_DIR}/${DUMP_FILE}/tiles"

BIG_PNG="${PICS_DIR}/${DUMP_FILE}.png"
SMOL_PNG="${PICS_DIR}/${DUMP_FILE}_smol.png"

SRC_PGM_TOOL="${TOOLS_DIR}/bin_to_ppm.c"
COMPILED_PGM_TOOL="${TOOLS_DIR}/bin2pgm"

if [ ! -f "${DUMP_FILE}" ] ; then
    echo "Please provide a dump file"
    exit 1
fi

if ! ([[ "${PAGE_SIZE}" =~ ^[0-9]+$ ]] && [[ "${PAGE_SIZE}" -gt 0 ]]) ; then
    echo "Page size needs to be an integer > 0"
    exit 
fi


if [ ! -f "${COMPILED_PGM_TOOL}" ] ; then
    echo "Compiling ${COMPILED_PGM_TOOL}"
    gcc "${SRC_PGM_TOOL}" -o "${COMPILED_PGM_TOOL}" 
    if [[ $? != 0 ]] ; then
        exit 1
    fi
fi

if [ ! -d "${PGM_DIR}" ] ; then
    mkdir -p "${PGM_DIR}"
    echo "Making the sub-pics in ${PGM_DIR} ...."

    "${COMPILED_PGM_TOOL}" "${DUMP_FILE}" "${PAGE_SIZE}" "${PGM_DIR}"  "${STEPS}"
    if [[ $? != 0 ]] ; then
        rmdir "${PGM_DIR}"
        exit 1
    fi
fi

if [ ! -f "${BIG_PNG}" ] ; then
    echo "Joining the sub-pics into ${BIG_PNG} ...."
    file_list="$(ls -1 "${PGM_DIR}"/*.pgm | paste -sd " ")"
    vips --vips-progress VipsArrayJoin "${file_list}"  "${SMOL_PNG}" --across "${STEPS}"
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

if [ ! -d "${TILES_DIR}" ] ; then
    mkdir -p "${TILES_DIR}"
    echo "Building tiles in ${TILES_DIR}"
    vips dzsave "${BIG_PNG}" "${TILES_DIR}" --layout google
    if [[ $? != 0 ]] ; then
        rmdir "${TILES_DIR}"
        exit 1
    fi
fi

echo "Starting webserver... Then open your web browser to http://localhost:8000"
echo "Ctrl-C to quit"
python3 "${HTTP_SERV}" -d "${TILES_DIR}" 
