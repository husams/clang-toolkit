# Included by the existing clang-toolkit root when CTK_BUILD_APIS=ON.
# This is a schema/code-generation library, not another top-level project.
find_package(Protobuf CONFIG QUIET NAMES protobuf)
if(NOT Protobuf_FOUND)
  find_package(Protobuf REQUIRED)
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)

file(GLOB _api_protos CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/ast/v1/*.proto")
file(GLOB_RECURSE _contract_protos CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/*.proto")
set(_api_schema_dir "${CMAKE_CURRENT_BINARY_DIR}/schema")
set(_api_staged_protos)
foreach(_proto IN LISTS _contract_protos)
  file(RELATIVE_PATH _relative "${CMAKE_CURRENT_SOURCE_DIR}" "${_proto}")
  list(APPEND _api_staged_protos "${_api_schema_dir}/${_relative}")
endforeach()
add_custom_command(
  OUTPUT ${_api_staged_protos} "${_api_schema_dir}/ast_sources.json"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/assemble_ast.py"
          "--output=${_api_schema_dir}"
  DEPENDS ${_contract_protos} "${CMAKE_CURRENT_SOURCE_DIR}/catalog.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/assemble_ast.py"
          "${CMAKE_CURRENT_SOURCE_DIR}/generate_nodes.py"
  COMMENT "Assembling dedicated typed AST schemas for recursive protobuf values"
  VERBATIM)

set(_match_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/query-generated")
set(_parse_sources)
foreach(_module IN ITEMS parse_request parse_response)
  list(APPEND _parse_sources "${_match_generated_dir}/match/v1/${_module}.pb.cc"
       "${_match_generated_dir}/match/v1/${_module}.pb.h")
endforeach()
add_custom_command(
  OUTPUT ${_parse_sources} "${_match_generated_dir}/match/v1/match_result.pb.cc"
         "${_match_generated_dir}/match/v1/match_result.pb.h"
         "${_match_generated_dir}/match/v1/match_service.pb.cc"
         "${_match_generated_dir}/match/v1/match_service.pb.h"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${_match_generated_dir}"
  COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
          "--cpp_out=${_match_generated_dir}"
          --experimental_allow_proto3_optional
          "${_api_schema_dir}/match/v1/match_result.proto"
          "${_api_schema_dir}/match/v1/parse_request.proto"
          "${_api_schema_dir}/match/v1/parse_response.proto"
          "${_api_schema_dir}/match/v1/match_service.proto"
  DEPENDS "${_api_schema_dir}/match/v1/match_result.proto"
          "${_api_schema_dir}/match/v1/parse_request.proto"
          "${_api_schema_dir}/match/v1/parse_response.proto"
          "${_api_schema_dir}/match/v1/match_service.proto"
  VERBATIM)
add_library(ctk_match_api STATIC ${_parse_sources}
  "${_match_generated_dir}/match/v1/match_result.pb.cc"
  "${_match_generated_dir}/match/v1/match_result.pb.h"
  "${_match_generated_dir}/match/v1/match_service.pb.cc")
target_include_directories(ctk_match_api PUBLIC "${_match_generated_dir}")
target_link_libraries(ctk_match_api PUBLIC ctk_ast_api protobuf::libprotobuf)

set(_analysis_protos)
set(_analysis_sources)
set(_analysis_headers)
file(GLOB _analysis_source_protos CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/analysis/v1/*.proto")
foreach(_source_proto IN LISTS _analysis_source_protos)
  get_filename_component(_module "${_source_proto}" NAME_WE)
  list(APPEND _analysis_protos "${_api_schema_dir}/analysis/v1/${_module}.proto")
  list(APPEND _analysis_sources "${_match_generated_dir}/analysis/v1/${_module}.pb.cc")
  list(APPEND _analysis_headers "${_match_generated_dir}/analysis/v1/${_module}.pb.h")
endforeach()
add_custom_command(OUTPUT ${_analysis_sources} ${_analysis_headers}
  COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
    "--cpp_out=${_match_generated_dir}" --experimental_allow_proto3_optional ${_analysis_protos}
  DEPENDS ${_analysis_protos} VERBATIM)
add_library(ctk_analysis_api STATIC ${_analysis_sources})
target_include_directories(ctk_analysis_api PUBLIC "${_match_generated_dir}")
target_link_libraries(ctk_analysis_api PUBLIC ctk_match_api)

if(CTK_BUILD_NETWORK)
  find_package(gRPC CONFIG REQUIRED)
  add_custom_command(
    OUTPUT "${_match_generated_dir}/match/v1/match_service.grpc.pb.cc"
           "${_match_generated_dir}/match/v1/match_service.grpc.pb.h"
    COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
            --experimental_allow_proto3_optional
            "--grpc_out=${_match_generated_dir}"
            "--plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>"
            "${_api_schema_dir}/match/v1/match_service.proto"
    DEPENDS "${_api_schema_dir}/match/v1/match_service.proto" VERBATIM)
  add_library(ctk_match_grpc STATIC
    "${_match_generated_dir}/match/v1/match_service.grpc.pb.cc")
  target_link_libraries(ctk_match_grpc PUBLIC ctk_match_api gRPC::grpc++)
  add_custom_command(
    OUTPUT "${_match_generated_dir}/analysis/v1/analysis_service.grpc.pb.cc"
           "${_match_generated_dir}/analysis/v1/analysis_service.grpc.pb.h"
    COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
      --experimental_allow_proto3_optional "--grpc_out=${_match_generated_dir}"
      "--plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>"
      "${_api_schema_dir}/analysis/v1/analysis_service.proto"
    DEPENDS ${_analysis_protos} VERBATIM)
  add_library(ctk_analysis_grpc STATIC "${_match_generated_dir}/analysis/v1/analysis_service.grpc.pb.cc")
  target_link_libraries(ctk_analysis_grpc PUBLIC ctk_analysis_api gRPC::grpc++)
  set(_query_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/query-generated")
  set(_query_proto "${_api_schema_dir}/query/v1/query.proto")
  set(_query_message_protos)
  set(_query_message_sources)
  set(_query_message_headers)
  foreach(_module IN ITEMS commands errors events)
    list(APPEND _query_message_protos "${_api_schema_dir}/query/v1/${_module}.proto")
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
    COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
            "--cpp_out=${_query_generated_dir}"
            --experimental_allow_proto3_optional
            ${_query_message_protos} "${_query_proto}"
    COMMAND protobuf::protoc "--proto_path=${_api_schema_dir}"
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

set(_api_generated_dir "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(_api_generated_sources)
set(_api_generated_headers)
set(_api_ast_staged_protos)
foreach(_proto IN LISTS _api_protos)
  file(RELATIVE_PATH _relative "${CMAKE_CURRENT_SOURCE_DIR}" "${_proto}")
  string(REGEX REPLACE "\\.proto$" ".pb.cc" _source "${_relative}")
  string(REGEX REPLACE "\\.proto$" ".pb.h" _header "${_relative}")
  list(APPEND _api_generated_sources "${_api_generated_dir}/${_source}")
  list(APPEND _api_generated_headers "${_api_generated_dir}/${_header}")
  list(APPEND _api_ast_staged_protos "${_api_schema_dir}/${_relative}")
endforeach()

add_custom_command(
  OUTPUT ${_api_generated_sources} ${_api_generated_headers}
         "${_api_generated_dir}/ast.pb"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${_api_generated_dir}"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_nodes.py" --check
  COMMAND protobuf::protoc
          "--proto_path=${_api_schema_dir}"
          "--cpp_out=${_api_generated_dir}"
          --experimental_allow_proto3_optional
          "--descriptor_set_out=${_api_generated_dir}/ast.pb"
          --include_imports ${_api_ast_staged_protos}
  DEPENDS ${_api_ast_staged_protos} "${CMAKE_CURRENT_SOURCE_DIR}/catalog.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/node_tags.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/generate_nodes.py"
  COMMENT "Generating the clang-toolkit C++ AST protobuf contract"
  VERBATIM)

add_library(ctk_ast_api STATIC ${_api_generated_sources} ${_api_generated_headers})
set_target_properties(ctk_ast_api PROPERTIES UNITY_BUILD ON UNITY_BUILD_BATCH_SIZE 32)
set_target_properties(ctk_ast_api PROPERTIES UNITY_BUILD_UNIQUE_ID CTK_PROTO_UNITY_ID
  UNITY_BUILD_CODE_BEFORE_INCLUDE [=[
#define CTK_PROTO_CAT_IMPL(a, b) a##b
#define CTK_PROTO_CAT(a, b) CTK_PROTO_CAT_IMPL(a, b)
#define schemas CTK_PROTO_CAT(ctk_proto_schemas_, CTK_PROTO_UNITY_ID)
#define file_message_globals CTK_PROTO_CAT(ctk_proto_globals_, CTK_PROTO_UNITY_ID)
#define file_default_instances CTK_PROTO_CAT(ctk_proto_defaults_, CTK_PROTO_UNITY_ID)
#define _static_init2_ CTK_PROTO_CAT(ctk_proto_init_, CTK_PROTO_UNITY_ID)
]=]
  UNITY_BUILD_CODE_AFTER_INCLUDE [=[
#undef _static_init2_
#undef file_default_instances
#undef file_message_globals
#undef schemas
#undef CTK_PROTO_CAT
#undef CTK_PROTO_CAT_IMPL
]=])
# The recursive implementation is substantial; compile it once independently.
# The small public-import facades share batches to avoid reparsing its header.
set_source_files_properties("${_api_generated_dir}/ast/v1/semantic.pb.cc"
                            "${_api_generated_dir}/ast/v1/common.pb.cc"
                            "${_api_generated_dir}/ast/v1/operators.pb.cc"
                            "${_api_generated_dir}/ast/v1/node.pb.cc"
                            PROPERTIES SKIP_UNITY_BUILD_INCLUSION ON)
target_include_directories(ctk_ast_api PUBLIC "${_api_generated_dir}")
target_link_libraries(ctk_ast_api PUBLIC protobuf::libprotobuf)
target_compile_features(ctk_ast_api PUBLIC cxx_std_20)
