include(FetchContent)
FetchContent_Declare(googletest
  URL "${CMAKE_CURRENT_LIST_DIR}/../../third_party/googletest/googletest-1.15.2.tar.gz"
  URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(googletest)

add_executable(ctk_tests
  test_lru_cache.cpp
  test_radix_tree.cpp
  test_cache_identity.cpp
  test_cache_contract.cpp
  test_snapshot_cache.cpp
  test_storage_store.cpp
)
target_link_libraries(ctk_tests PRIVATE ctk_core GTest::gtest_main ctk::sqlite)
if(CTK_BUILD_NETWORK)
  target_sources(ctk_tests PRIVATE test_network_config.cpp test_query_controller.cpp test_network_transport.cpp test_batch_registry.cpp)
  target_link_libraries(ctk_tests PRIVATE ctk_network)
endif()
if(CTK_WITH_CLANG)
  string(REGEX MATCH "^[0-9]+" CTK_TEST_CLANG_VERSION_MAJOR "${CMAKE_CXX_COMPILER_VERSION}")
  target_compile_definitions(ctk_tests PRIVATE CTK_TEST_CLANG_VERSION_MAJOR=${CTK_TEST_CLANG_VERSION_MAJOR})
  target_compile_definitions(ctk_tests PRIVATE CTK_TEST_CLANG_TOOL_PATH="${CMAKE_CXX_COMPILER}")
  target_sources(ctk_tests PRIVATE
    test_clang_query.cpp
    test_compilation_database.cpp
    test_file_discovery.cpp
    test_clang_query_regressions.cpp
    test_clang_serializer_regressions.cpp
    test_statement_semantics.cpp
    test_base_specifier_semantics.cpp
    test_availability_states.cpp
    test_declaration_semantics.cpp
    test_expression_semantics.cpp
    test_type_semantics.cpp
    ../src/clang/serialization/testing/test_cached_values.cpp
    test_temporary_directory.cpp test_project_facade.cpp test_snapshot_closure.cpp)
  if(CTK_BUILD_NETWORK)
    target_sources(ctk_tests PRIVATE test_match_cursors.cpp test_resource_management.cpp test_ast_traversal.cpp test_cfg.cpp test_call_graph.cpp)
  endif()
endif()

if(CTK_BUILD_SCRIPT)
  target_sources(ctk_tests PRIVATE test_script_engine.cpp)
  if(CTK_BUILD_NETWORK)
    target_sources(ctk_tests PRIVATE test_script_controller.cpp)
  endif()
endif()

include(GoogleTest)
gtest_discover_tests(ctk_tests)
