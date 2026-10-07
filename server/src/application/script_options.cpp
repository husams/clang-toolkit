#include "script_options.hpp"
#include "ctk/script/error.hpp"
namespace ctk::application::detail {
using Code = ctk::clang_layer::MatchCode;
std::string script_text(const ctk::script::Value &value) {
  if (!value.wire || !value.wire->has_scalar() ||
      value.wire->scalar().value_case() !=
          ctk::analysis::v1::ScriptScalar::kText)
    throw ctk::script::Error(Code::InvalidArgument,
                             "script argument requires a string");
  return value.wire->scalar().text();
}
void script_option(google::protobuf::Message &message, const std::string &name,
                   const ctk::script::Value &value) {
  const auto *field = message.GetDescriptor()->FindFieldByName(name);
  if (!field || field->is_repeated() || !value.wire->has_scalar())
    throw ctk::script::Error(Code::InvalidArgument,
                             "unknown or invalid script option: " + name);
  const auto &scalar = value.wire->scalar();
  const auto *reflection = message.GetReflection();
  if (field->cpp_type() == google::protobuf::FieldDescriptor::CPPTYPE_BOOL &&
      (scalar.value_case() == ctk::analysis::v1::ScriptScalar::kBoolean))
    reflection->SetBool(&message, field, scalar.boolean());
  else if ((field->cpp_type() ==
                google::protobuf::FieldDescriptor::CPPTYPE_UINT64 ||
            field->cpp_type() ==
                google::protobuf::FieldDescriptor::CPPTYPE_UINT32) &&
           (scalar.value_case() == ctk::analysis::v1::ScriptScalar::kInteger)) {
    const std::map<std::string, std::int64_t> maxima{
        {"max_depth", 256},     {"max_nodes", 100000},
        {"max_edges", 1000000}, {"max_functions", 1000},
        {"max_blocks", 100000}, {"max_elements", 1000000}};
    const auto found = maxima.find(name);
    if (found == maxima.end() ||
        scalar.integer() < (name == "max_depth" ? 0 : 1) ||
        scalar.integer() > found->second)
      throw ctk::script::Error(
          Code::InvalidArgument,
          "script analysis limit is outside server bounds: " + name);
    if (field->cpp_type() == google::protobuf::FieldDescriptor::CPPTYPE_UINT32)
      reflection->SetUInt32(&message, field, scalar.integer());
    else
      reflection->SetUInt64(&message, field, scalar.integer());
  } else
    throw ctk::script::Error(Code::InvalidArgument,
                             "wrong type for script option: " + name);
}
} // namespace ctk::application::detail
