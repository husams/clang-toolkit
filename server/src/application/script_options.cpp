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
} // namespace ctk::application::detail
