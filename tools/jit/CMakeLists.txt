cmake_minimum_required(VERSION 3.24)
if(CMAKE_CURRENT_SOURCE_DIR STREQUAL CMAKE_SOURCE_DIR)
  message(FATAL_ERROR "Configure from the repository root with -DCTK_BUILD_JIT=ON")
endif()

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)
find_package(Threads REQUIRED)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)
if(APPLE AND NOT DEFINED ICU_ROOT)
  foreach(prefix /opt/homebrew/opt/icu4c /usr/local/opt/icu4c)
    if(IS_DIRECTORY "${prefix}/include/unicode")
      set(ICU_ROOT "${prefix}")
      break()
    endif()
  endforeach()
endif()
find_package(ICU REQUIRED COMPONENTS uc data)
find_package(ZLIB REQUIRED)
find_path(CTK_JIT_YAML_INCLUDE_DIR yaml.h REQUIRED)
find_library(CTK_JIT_YAML_LIBRARY yaml REQUIRED)
find_path(CTK_JIT_PCRE2_INCLUDE_DIR pcre2.h REQUIRED)
find_library(CTK_JIT_PCRE2_LIBRARY pcre2-8 REQUIRED)
if(LLVM_PACKAGE_VERSION VERSION_LESS 21 OR NOT TARGET clang-cpp OR NOT TARGET LLVM)
  message(FATAL_ERROR "ctk-jit requires LLVM 21 or newer with shared Clang and LLVM libraries")
endif()

find_program(CTK_JIT_CLANG clang++ HINTS "${LLVM_TOOLS_BINARY_DIR}" NO_DEFAULT_PATH REQUIRED)
execute_process(COMMAND "${CTK_JIT_CLANG}" -print-resource-dir
  OUTPUT_VARIABLE CTK_JIT_RESOURCE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY)

set(CTK_JIT_SYSROOT "")
if(APPLE)
  if(IS_DIRECTORY "${CMAKE_OSX_SYSROOT}")
    set(CTK_JIT_SYSROOT "${CMAKE_OSX_SYSROOT}")
  else()
    execute_process(COMMAND xcrun --sdk macosx --show-sdk-path
      OUTPUT_VARIABLE CTK_JIT_SYSROOT OUTPUT_STRIP_TRAILING_WHITESPACE
      COMMAND_ERROR_IS_FATAL ANY)
  endif()
endif()

include(FetchContent)
FetchContent_Declare(ctk_ftxui
  GIT_REPOSITORY https://github.com/ArthurSonzogni/FTXUI.git
  GIT_TAG f921fad208912747c17d129a8ef75ec7624b6eec)
FetchContent_MakeAvailable(ctk_ftxui)

# FTXUI 7.0.3 maps CR to LF before delivering events. Keep them distinct for
# the workspace's Enter and Ctrl+J bindings. Adapt the pinned source without
# modifying a downloaded or locally supplied FTXUI checkout.
set(ctk_ftxui_input "src/ftxui/component/terminal_input_parser.cpp")
file(READ "${ctk_ftxui_SOURCE_DIR}/${ctk_ftxui_input}" ctk_ftxui_input_source)
set(ctk_ftxui_return_mapping [=[{"\r", "\n"},]=])
string(FIND "${ctk_ftxui_input_source}" "${ctk_ftxui_return_mapping}" ctk_ftxui_return_index)
if(ctk_ftxui_return_index LESS 0)
  message(FATAL_ERROR "Recheck the CTK Enter and Ctrl+J adapter for this FTXUI version")
endif()
string(REPLACE "${ctk_ftxui_return_mapping}" "" ctk_ftxui_input_source "${ctk_ftxui_input_source}")
set(ctk_ftxui_input_override "${CMAKE_CURRENT_BINARY_DIR}/ftxui_terminal_input_parser.cpp")
file(CONFIGURE OUTPUT "${ctk_ftxui_input_override}" CONTENT "${ctk_ftxui_input_source}" @ONLY)
get_target_property(ctk_ftxui_component_sources component SOURCES)
list(FIND ctk_ftxui_component_sources "${ctk_ftxui_input}" ctk_ftxui_input_index)
if(ctk_ftxui_input_index LESS 0)
  message(FATAL_ERROR "Cannot locate the FTXUI terminal input source")
endif()
list(REMOVE_AT ctk_ftxui_component_sources ${ctk_ftxui_input_index})
list(APPEND ctk_ftxui_component_sources "${ctk_ftxui_input_override}")
set_property(TARGET component PROPERTY SOURCES "${ctk_ftxui_component_sources}")

set(ctk_jit_server_sources "${PROJECT_SOURCE_DIR}/server/src")
add_library(ctk_jit_services STATIC
  index/project_index.cpp
  platform/root_lock.cpp
  "${ctk_jit_server_sources}/platform/index_worker.cpp"
  "${ctk_jit_server_sources}/platform/directory_watch.cpp"
  "${ctk_jit_server_sources}/platform/index_input_watch.cpp"
  "${ctk_jit_server_sources}/platform/index_file_reader.cpp"
  "${ctk_jit_server_sources}/platform/index_filesystem.cpp")
if(NOT CTK_BUILD_NETWORK)
  foreach(source IN ITEMS
      application/analysis_session.cpp
      application/query_controller.cpp
      application/match_controller.cpp
      application/operation_executor.cpp
      application/cursor_registry.cpp
      application/resource_manager.cpp
      application/file_target_validation.cpp
      application/script_controller.cpp
      application/native_script_environment.cpp
      application/script_options.cpp
      application/batch_registry.cpp
      platform/process_memory.cpp
      platform/durable_file.cpp)
    target_sources(ctk_jit_services PRIVATE "${ctk_jit_server_sources}/${source}")
  endforeach()
endif()
target_include_directories(ctk_jit_services PRIVATE
  "${ctk_jit_server_sources}/net" "${ctk_jit_server_sources}/platform")
target_link_libraries(ctk_jit_services PUBLIC ctk_core ctk_index_api
  PRIVATE Threads::Threads OpenSSL::Crypto ctk::sqlite)
if(APPLE)
  target_link_libraries(ctk_jit_services PRIVATE "-framework CoreServices")
endif()

add_executable(ctk-jit-index-worker "${ctk_jit_server_sources}/index_worker_main.cpp")
target_link_libraries(ctk-jit-index-worker PRIVATE ctk_jit_services)

add_executable(ctk-jit-runner
  main.cpp
  grammar/syntax.cpp
  grammar/lower.cpp
  grammar/help.cpp
  ir.cpp
  scoped_match.cpp
  analysis.cpp
  local_operations.cpp
  embedded_services.cpp
  semantic.cpp
  values.cpp
  filters.cpp
  documents.cpp
  typed_snapshot.cpp
  workspace.cpp
  completion.cpp
  native_workspace.cpp
  native_history.cpp
  settings.cpp
  platform/compiler_channel.cpp
  platform/file_values.cpp
  platform/launch.cpp
  platform/repl_cancellation.cpp)
target_compile_features(ctk-jit-runner PRIVATE cxx_std_23)
set_target_properties(ctk-jit-runner ctk-jit-index-worker PROPERTIES
  CXX_EXTENSIONS OFF RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
target_include_directories(ctk-jit-runner PRIVATE include ../../server/src/clang "${CTK_JIT_YAML_INCLUDE_DIR}")
target_include_directories(ctk-jit-runner SYSTEM PRIVATE
  ${CLANG_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS} "${CTK_JIT_PCRE2_INCLUDE_DIR}")
target_compile_definitions(ctk-jit-runner PRIVATE
  CTK_JIT_LEGACY_CLI="${CMAKE_CURRENT_SOURCE_DIR}/../../.venv/bin/ctk-jit"
  CTK_JIT_INDEX_WORKER="$<TARGET_FILE:ctk-jit-index-worker>"
  CTK_JIT_COMPILER="${CTK_JIT_CLANG}"
  CTK_JIT_CLANG_LIBRARY="$<TARGET_FILE:clang-cpp>"
  CTK_JIT_LLVM_LIBRARY="$<TARGET_FILE:LLVM>"
  CTK_JIT_ICU_LIBRARY="$<TARGET_FILE:ICU::uc>"
  CTK_JIT_ICU_DATA="$<TARGET_FILE:ICU::data>"
  CTK_JIT_YAML_LIBRARY="${CTK_JIT_YAML_LIBRARY}"
  CTK_JIT_PRELUDE="${CMAKE_CURRENT_SOURCE_DIR}/prelude.hpp"
  CTK_JIT_SDK_INCLUDE="${CMAKE_CURRENT_SOURCE_DIR}/include"
  CTK_JIT_CLANG_INCLUDE="${CLANG_INCLUDE_DIRS}"
  CTK_JIT_LLVM_INCLUDE="${LLVM_INCLUDE_DIRS}"
  CTK_JIT_RESOURCE_DIR="${CTK_JIT_RESOURCE_DIR}"
  CTK_JIT_SYSROOT="${CTK_JIT_SYSROOT}")
target_link_libraries(ctk-jit-runner PRIVATE
  ctk_jit_services clang-cpp LLVM ICU::uc ZLIB::ZLIB ftxui::component
  "${CTK_JIT_YAML_LIBRARY}" "${CTK_JIT_PCRE2_LIBRARY}")

add_dependencies(ctk-jit-runner ctk-jit-index-worker)
