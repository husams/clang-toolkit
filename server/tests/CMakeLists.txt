include(FetchContent)
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz)
FetchContent_MakeAvailable(googletest)

add_executable(ctk_tests test_lru_cache.cpp)
target_link_libraries(ctk_tests PRIVATE ctk_core GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(ctk_tests)
