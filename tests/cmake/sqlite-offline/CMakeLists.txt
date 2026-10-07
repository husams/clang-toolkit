cmake_minimum_required(VERSION 3.24)
project(ctk_sqlite_offline_check LANGUAGES C)

include("${CMAKE_CURRENT_LIST_DIR}/../../../cmake/SQLite.cmake")
get_target_property(sqlite_type ctk_sqlite TYPE)
if(NOT sqlite_type STREQUAL "STATIC_LIBRARY")
  message(FATAL_ERROR "Offline SQLite must build as a static library")
endif()

add_executable(sqlite_offline smoke.c)
target_link_libraries(sqlite_offline PRIVATE ctk::sqlite)
enable_testing()
add_test(NAME sqlite_offline COMMAND sqlite_offline)
