add_library(ctk_core
  src/net/server.cpp
  src/storage/store.cpp
  src/script/engine.cpp
)
target_include_directories(ctk_core PUBLIC include)

if(CTK_WITH_CLANG)
  find_package(Clang REQUIRED CONFIG)
  add_library(ctk_clang src/clang/tooling.cpp)
  target_include_directories(ctk_clang PUBLIC include ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
  target_compile_definitions(ctk_clang PUBLIC ${LLVM_DEFINITIONS})
  # RHEL/Fedora ship Clang/LLVM as shared dylibs only; Homebrew ships both.
  if(TARGET clang-cpp AND TARGET LLVM)
    target_link_libraries(ctk_clang PUBLIC clang-cpp LLVM)
  else()
    target_link_libraries(ctk_clang PUBLIC clangTooling clangASTMatchers clangAnalysis clangFrontend clangAST clangBasic)
  endif()
  target_link_libraries(ctk_core PUBLIC ctk_clang)
  target_compile_definitions(ctk_core PUBLIC CTK_WITH_CLANG=1)
endif()

add_executable(ctk-server src/main.cpp)
target_link_libraries(ctk-server PRIVATE ctk_core)
