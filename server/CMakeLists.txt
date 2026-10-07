find_package(Threads REQUIRED)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)

add_library(ctk_cache
  src/cache/cache_state.cpp
  src/cache/compilation_context.cpp
  src/cache/path_policy.cpp
  src/cache/reuse_policy.cpp
  src/cache/reverse_index.cpp
  src/cache/snapshot.cpp
  src/cache/snapshot_acquisition.cpp
  src/cache/snapshot_cache.cpp
)
target_include_directories(ctk_cache PUBLIC include)
target_compile_features(ctk_cache PUBLIC cxx_std_23)

add_library(ctk_storage
  src/storage/blob_store.cpp
  src/storage/canonical_encoder.cpp
  src/storage/metadata_repository.cpp
  src/storage/root_ownership.cpp
  src/storage/schema_migrations.cpp
  src/storage/snapshot_validation.cpp
  src/storage/sqlite_raii.cpp
  src/storage/storage_identity.cpp
  src/storage/store.cpp
  src/storage/store_lifecycle.cpp
  src/storage/store_publication.cpp
)
target_include_directories(ctk_storage PUBLIC include)
target_compile_features(ctk_storage PUBLIC cxx_std_23)
target_link_libraries(ctk_storage PRIVATE SQLite3::SQLite3 OpenSSL::Crypto)

add_library(ctk_core
  src/script/engine.cpp
)
target_include_directories(ctk_core PUBLIC include)
target_compile_features(ctk_core PUBLIC cxx_std_23)
target_link_libraries(ctk_core PUBLIC ctk_cache ctk_storage)
target_link_libraries(ctk_core PRIVATE Threads::Threads)

if(CTK_BUILD_NETWORK)
  find_path(CTK_YAML_INCLUDE_DIR yaml.h REQUIRED)
  find_library(CTK_YAML_LIBRARY yaml REQUIRED)
  target_sources(ctk_core PRIVATE
    src/platform/loopback_address.cpp
    src/config/config.cpp
    src/application/analysis_session.cpp
    src/application/query_controller.cpp)
  target_include_directories(ctk_core PRIVATE "${CTK_YAML_INCLUDE_DIR}")
  target_link_libraries(ctk_core PRIVATE "${CTK_YAML_LIBRARY}")
  add_library(ctk_network
    src/platform/endpoint_lease.cpp
    src/net/server.cpp
    src/net/protocol_adapter.cpp
    src/net/outbound_event_queue.cpp
    src/net/query_call_state.cpp
    src/net/network_service.cpp)
  target_include_directories(ctk_network PUBLIC include)
  target_link_libraries(ctk_core PUBLIC ctk_query_api)
  target_link_libraries(ctk_network PUBLIC ctk_core ctk_query_api Threads::Threads)
endif()

if(CTK_WITH_CLANG)
  find_package(Clang REQUIRED CONFIG)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_custom_target(ctk_node_serializer_coverage
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_SOURCE_DIR}/scripts/check_node_serializer_coverage.py"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    VERBATIM)
  add_library(ctk_clang
    src/platform/temporary_directory.cpp
    src/clang/tooling.cpp
    src/clang/cached_query_engine.cpp
    src/clang/serialization/node_serializers.cpp)
  file(GLOB_RECURSE _node_serializer_sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/clang/serialization/decl/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/clang/serialization/stmt/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/clang/serialization/expr/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/clang/serialization/type/*.cpp")
  file(GLOB _semantic_helper_sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/clang/serialization/*helpers.cpp")
  target_sources(ctk_clang PRIVATE ${_node_serializer_sources} ${_semantic_helper_sources}
    src/clang/serialization/constant_values.cpp)
  target_precompile_headers(ctk_clang PRIVATE src/clang/serialization/node_serializers.hpp)
  set_source_files_properties(src/platform/temporary_directory.cpp
    PROPERTIES SKIP_PRECOMPILE_HEADERS ON)
  add_dependencies(ctk_clang ctk_node_serializer_coverage)
  target_include_directories(ctk_clang PUBLIC include ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
  target_compile_definitions(ctk_clang PUBLIC ${LLVM_DEFINITIONS})
  execute_process(COMMAND "${CMAKE_CXX_COMPILER}" -print-resource-dir
    OUTPUT_VARIABLE CTK_CLANG_RESOURCE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE CTK_CLANG_RESOURCE_RESULT)
  if(NOT CTK_CLANG_RESOURCE_RESULT EQUAL 0 OR CTK_CLANG_RESOURCE_DIR STREQUAL "")
    message(FATAL_ERROR "The selected Clang compiler did not provide its resource directory")
  endif()
  target_compile_definitions(ctk_clang PRIVATE
    CTK_CLANG_RESOURCE_DIR="${CTK_CLANG_RESOURCE_DIR}"
    CTK_CLANG_TOOL_PATH="${CMAKE_CXX_COMPILER}")
  # RHEL/Fedora ship Clang/LLVM as shared dylibs only; Homebrew ships both.
  if(TARGET clang-cpp AND TARGET LLVM)
    target_link_libraries(ctk_clang PUBLIC clang-cpp LLVM)
  else()
    target_link_libraries(ctk_clang PUBLIC clangTooling clangDynamicASTMatchers clangASTMatchers clangAnalysis clangFrontend clangAST clangBasic)
  endif()
  target_link_libraries(ctk_core PUBLIC ctk_clang)
  target_link_libraries(ctk_clang PUBLIC ctk_match_api ctk_cache ctk_storage)
  target_compile_definitions(ctk_core PUBLIC CTK_WITH_CLANG=1)
endif()

if(CTK_BUILD_NETWORK)
  add_executable(ctk-server src/main.cpp)
  target_link_libraries(ctk-server PRIVATE ctk_network)
endif()
