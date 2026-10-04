# Included by the existing clang-toolkit root when CTK_BUILD_APIS=ON.
# This is a schema/code-generation library, not another top-level project.
find_package(Protobuf CONFIG QUIET NAMES protobuf)
if(NOT Protobuf_FOUND)
  find_package(Protobuf REQUIRED)
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)

file(GLOB _api_protos CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/ast/v1/*.proto")
set(_api_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(_api_generated_sources)
set(_api_generated_headers)
foreach(_proto IN LISTS _api_protos)
  file(RELATIVE_PATH _relative "${CMAKE_CURRENT_SOURCE_DIR}" "${_proto}")
  string(REGEX REPLACE "\\.proto$" ".pb.cc" _source "${_relative}")
  string(REGEX REPLACE "\\.proto$" ".pb.h" _header "${_relative}")
  list(APPEND _api_generated_sources "${_api_generated_dir}/${_source}")
  list(APPEND _api_generated_headers "${_api_generated_dir}/${_header}")
endforeach()

add_custom_command(
  OUTPUT ${_api_generated_sources} ${_api_generated_headers}
         "${_api_generated_dir}/ast.pb"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${_api_generated_dir}"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_nodes.py" --check
  COMMAND protobuf::protoc
          "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}"
          "--cpp_out=${_api_generated_dir}"
          "--descriptor_set_out=${_api_generated_dir}/ast.pb"
          --include_imports ${_api_protos}
  DEPENDS ${_api_protos} "${CMAKE_CURRENT_SOURCE_DIR}/catalog.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/node_tags.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/generate_nodes.py"
  COMMENT "Generating the clang-toolkit C++ AST protobuf contract"
  VERBATIM)

add_library(ctk_ast_api STATIC ${_api_generated_sources} ${_api_generated_headers})
target_include_directories(ctk_ast_api PUBLIC "${_api_generated_dir}")
target_link_libraries(ctk_ast_api PUBLIC protobuf::libprotobuf)
target_compile_features(ctk_ast_api PUBLIC cxx_std_20)
