cmake_minimum_required(VERSION 3.0.0)
cmake_policy(SET CMP0074 NEW)
cmake_policy(SET CMP0079 NEW)
set(CMAKE_C_STANDARD 11)
set(CMAKE_BUILD_TYPE Debug)
project(margo_server VERSION 0.1.0)

find_package (PkgConfig REQUIRED)
find_package(mercury REQUIRED)
pkg_check_modules (MARGO REQUIRED IMPORTED_TARGET margo)
pkg_check_modules (HIREDIS REQUIRED IMPORTED_TARGET hiredis)

# Code using Margo
add_executable(margo_server server.c)
target_link_libraries(margo_server PkgConfig::MARGO PkgConfig::HIREDIS)
