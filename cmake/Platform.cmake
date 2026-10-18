# Included before project(): picks the Clang toolchain and LLVM install per platform.
# Override with -DCMAKE_CXX_COMPILER=... / -DCTK_LLVM_ROOT=... when needed.

# Cache the first native architecture instead of relying on CMake's changing
# implicit defaults. Preserve explicit settings, including an empty string and
# universal builds, on every subsequent configure.
if(CMAKE_HOST_APPLE AND NOT DEFINED CMAKE_OSX_ARCHITECTURES)
  cmake_host_system_information(RESULT _ctk_native_arch QUERY OS_PLATFORM)
  set(CMAKE_OSX_ARCHITECTURES "${_ctk_native_arch}" CACHE STRING
      "macOS target architectures (pinned on first configuration)")
endif()

if(NOT DEFINED CTK_LLVM_ROOT)
  if(CMAKE_HOST_APPLE)
    foreach(candidate /opt/homebrew/opt/llvm /usr/local/opt/llvm)
      if(EXISTS "${candidate}/bin/clang++")
        set(CTK_LLVM_ROOT "${candidate}")
        break()
      endif()
    endforeach()
  elseif(CMAKE_HOST_UNIX AND EXISTS "/usr/lib64/cmake/clang")
    set(CTK_LLVM_ROOT "/usr")  # RHEL: dnf install clang clang-devel llvm-devel
  endif()
endif()

if(CTK_LLVM_ROOT)
  set(CTK_LLVM_ROOT "${CTK_LLVM_ROOT}" CACHE PATH "LLVM/Clang install prefix")
  list(APPEND CMAKE_PREFIX_PATH "${CTK_LLVM_ROOT}")
  if(NOT DEFINED CMAKE_CXX_COMPILER AND EXISTS "${CTK_LLVM_ROOT}/bin/clang++")
    set(CMAKE_CXX_COMPILER "${CTK_LLVM_ROOT}/bin/clang++")
  endif()
  if(NOT DEFINED CMAKE_C_COMPILER AND EXISTS "${CTK_LLVM_ROOT}/bin/clang")
    set(CMAKE_C_COMPILER "${CTK_LLVM_ROOT}/bin/clang")
  endif()
endif()
