# Included by the existing clang-toolkit root when CTK_BUILD_APIS=ON.
# This is a schema/code-generation library, not another top-level project.
find_package(Protobuf CONFIG QUIET NAMES protobuf)
if(NOT Protobuf_FOUND)
  find_package(Protobuf REQUIRED)
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)

file(GLOB _api_protos CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/ast/v1/*.proto")

if(CTK_WITH_CLANG OR CTK_BUILD_NETWORK)
  set(_match_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/query-generated")
  add_custom_command(
    OUTPUT "${_match_generated_dir}/match/v1/match_result.pb.cc"
           "${_match_generated_dir}/match/v1/match_result.pb.h"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${_match_generated_dir}"
    COMMAND protobuf::protoc "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}"
            "--cpp_out=${_match_generated_dir}"
            --experimental_allow_proto3_optional
            "${CMAKE_CURRENT_SOURCE_DIR}/match/v1/match_result.proto"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/match/v1/match_result.proto"
            ${_api_protos}
    VERBATIM)
  add_library(ctk_match_api STATIC
    "${_match_generated_dir}/match/v1/match_result.pb.cc"
    "${_match_generated_dir}/match/v1/match_result.pb.h")
  target_include_directories(ctk_match_api PUBLIC "${_match_generated_dir}")
  target_link_libraries(ctk_match_api PUBLIC ctk_ast_api protobuf::libprotobuf)
endif()

if(CTK_BUILD_NETWORK)
  find_package(gRPC CONFIG REQUIRED)
  set(_query_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/query-generated")
  set(_query_proto "${CMAKE_CURRENT_SOURCE_DIR}/query/v1/query.proto")
  set(_query_message_protos)
  set(_query_message_sources)
  set(_query_message_headers)
  foreach(_module IN ITEMS commands errors events)
    list(APPEND _query_message_protos "${CMAKE_CURRENT_SOURCE_DIR}/query/v1/${_module}.proto")
    list(APPEND _query_message_sources "${_query_generated_dir}/query/v1/${_module}.pb.cc")
    list(APPEND _query_message_headers "${_query_generated_dir}/query/v1/${_module}.pb.h")
  endforeach()
  add_custom_command(
    OUTPUT ${_query_message_sources} ${_query_message_headers}
           "${_query_generated_dir}/query/v1/query.pb.cc"
           "${_query_generated_dir}/query/v1/query.pb.h"
           "${_query_generated_dir}/query/v1/query.grpc.pb.cc"
           "${_query_generated_dir}/query/v1/query.grpc.pb.h"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${_query_generated_dir}"
    COMMAND protobuf::protoc "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}"
            "--cpp_out=${_query_generated_dir}"
            --experimental_allow_proto3_optional
            ${_query_message_protos} "${_query_proto}"
    COMMAND protobuf::protoc "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}"
            --experimental_allow_proto3_optional
            "--grpc_out=${_query_generated_dir}"
            "--plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>"
            "${_query_proto}"
    DEPENDS ${_query_message_protos} "${_query_proto}" VERBATIM)
  add_library(ctk_query_api STATIC
    ${_query_message_sources}
    "${_query_generated_dir}/query/v1/query.pb.cc"
    "${_query_generated_dir}/query/v1/query.grpc.pb.cc")
  target_include_directories(ctk_query_api PUBLIC "${_query_generated_dir}")
  target_link_libraries(ctk_query_api PUBLIC ctk_match_api protobuf::libprotobuf gRPC::grpc++)
endif()
if(NOT CTK_BUILD_APIS AND NOT CTK_WITH_CLANG AND NOT CTK_BUILD_NETWORK)
  return()
endif()

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
          --experimental_allow_proto3_optional
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
