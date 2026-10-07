include(FetchContent)
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz)
FetchContent_MakeAvailable(googletest)

add_executable(ctk_tests
  test_lru_cache.cpp
  test_radix_tree.cpp
  test_cache_identity.cpp
  test_cache_contract.cpp
  test_snapshot_cache.cpp
  test_storage_store.cpp
)
target_link_libraries(ctk_tests PRIVATE ctk_core GTest::gtest_main SQLite3::SQLite3)
if(CTK_BUILD_NETWORK)
  target_sources(ctk_tests PRIVATE test_network_config.cpp test_query_controller.cpp test_network_transport.cpp)
  target_link_libraries(ctk_tests PRIVATE ctk_network)
endif()
if(CTK_WITH_CLANG)
  string(REGEX MATCH "^[0-9]+" CTK_TEST_CLANG_VERSION_MAJOR "${CMAKE_CXX_COMPILER_VERSION}")
  target_compile_definitions(ctk_tests PRIVATE CTK_TEST_CLANG_VERSION_MAJOR=${CTK_TEST_CLANG_VERSION_MAJOR})
  target_sources(ctk_tests PRIVATE
    test_clang_query.cpp
    test_clang_query_regressions.cpp
    test_clang_serializer_regressions.cpp
    test_statement_semantics.cpp
    test_declaration_semantics.cpp
    test_expression_semantics.cpp
    test_type_semantics.cpp
    test_temporary_directory.cpp)
endif()

include(GoogleTest)
gtest_discover_tests(ctk_tests)
