# Native x86_64 Linux build against the GCC 8.5 SDK runtime.
set(CTK_SDK_ROOT "" CACHE PATH "GCC 8.5 SDK root")
set(CTK_DEPENDENCY_PREFIX "" CACHE PATH "Prefix containing SDK-compatible dependencies")
set(CTK_SDK_TARGET "x86_64-1a-linux-gnu" CACHE STRING "SDK target directory")
if(NOT IS_ABSOLUTE "${CTK_SDK_ROOT}" OR NOT EXISTS "${CTK_SDK_ROOT}/bin/g++")
  message(FATAL_ERROR "Set CTK_SDK_ROOT to an absolute GCC 8.5 SDK path")
endif()
set(_target "${CTK_SDK_ROOT}/${CTK_SDK_TARGET}")
set(CMAKE_SYSROOT "${_target}/sysroot" CACHE PATH "SDK sysroot")
set(CTK_SDK_LOADER "${CMAKE_SYSROOT}/lib64/ld-linux-x86-64.so.2"
  CACHE FILEPATH "SDK dynamic loader")
if(NOT IS_ABSOLUTE "${CTK_DEPENDENCY_PREFIX}" OR
   NOT IS_DIRECTORY "${CMAKE_SYSROOT}" OR NOT EXISTS "${CTK_SDK_LOADER}")
  message(FATAL_ERROR "Set an absolute dependency prefix and an existing SDK sysroot and loader")
endif()

list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES
  CTK_SDK_ROOT CTK_SDK_TARGET CTK_DEPENDENCY_PREFIX CTK_SDK_LOADER)
list(REMOVE_DUPLICATES CMAKE_TRY_COMPILE_PLATFORM_VARIABLES)
set(CMAKE_C_COMPILER "${CTK_SDK_ROOT}/bin/gcc" CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER "${CTK_SDK_ROOT}/bin/g++" CACHE FILEPATH "")
set(CTK_LLVM_ROOT "${CTK_SDK_ROOT}" CACHE PATH "")
set(LLVM_DIR "${CTK_SDK_ROOT}/lib.llvm/cmake/llvm" CACHE PATH "")
set(Clang_DIR "${CTK_SDK_ROOT}/lib.llvm/cmake/clang" CACHE PATH "")
set(CTK_CLANG_TOOL "${CTK_SDK_ROOT}/bin/clang++" CACHE FILEPATH "")
set(CTK_ANALYSIS_SYSROOT "${CMAKE_SYSROOT}" CACHE PATH "Default Clang analysis sysroot")
set(CTK_ANALYSIS_GCC_TOOLCHAIN "${CTK_SDK_ROOT}" CACHE PATH "Default Clang GCC SDK")
set(CTK_EXTRA_DEPENDENCY_ROOTS "" CACHE STRING "Additional compatible SDK prefixes")
set(CMAKE_PREFIX_PATH "${CTK_DEPENDENCY_PREFIX};${CTK_EXTRA_DEPENDENCY_ROOTS}"
  CACHE STRING "Target dependency prefixes")
set(CMAKE_FIND_ROOT_PATH "${CTK_DEPENDENCY_PREFIX};${CTK_EXTRA_DEPENDENCY_ROOTS};${CTK_SDK_ROOT};${CMAKE_SYSROOT}"
  CACHE STRING "Target package search roots")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
set(_runtime "${CTK_DEPENDENCY_PREFIX}/lib;${CTK_DEPENDENCY_PREFIX}/lib64;${_target}/lib64;${CMAKE_SYSROOT}/lib64;${CTK_SDK_ROOT}/lib.llvm")
foreach(_prefix IN LISTS CTK_EXTRA_DEPENDENCY_ROOTS)
  list(APPEND _runtime "${_prefix}/lib" "${_prefix}/lib64")
endforeach()
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH ON CACHE BOOL "Preserve target dependency library paths")
set(CMAKE_BUILD_RPATH "${_runtime}" CACHE STRING "SDK runtime search paths")
set(CMAKE_INSTALL_RPATH "${_runtime}" CACHE STRING "SDK runtime search paths")
# Executables built by dependencies (protoc, for example) also need the SDK
# runtime before installation, and some upstreams override INSTALL_RPATH.
string(REPLACE ";" ":" _runtime_link "${_runtime}")
set(CMAKE_EXE_LINKER_FLAGS_INIT
  "-Wl,--dynamic-linker=${CTK_SDK_LOADER},--disable-new-dtags,-rpath,${_runtime_link}")
