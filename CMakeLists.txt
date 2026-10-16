cmake_minimum_required(VERSION 3.15)
project(iec61850_bridge C)
add_subdirectory(vendor/libiec61850 EXCLUDE_FROM_ALL)
add_executable(iec61850-bridge native/iec61850_bridge.c)
target_include_directories(iec61850-bridge PRIVATE
    vendor/libiec61850/src/iec61850/inc
    vendor/libiec61850/src/mms/inc
    vendor/libiec61850/src/common/inc
    vendor/libiec61850/hal/inc
)
target_link_libraries(iec61850-bridge PRIVATE iec61850)
