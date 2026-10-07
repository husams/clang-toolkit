#pragma once
#include "ctk/script/value.hpp"
#include <google/protobuf/message.h>
namespace ctk::application::detail {
std::string script_text(const ctk::script::Value &value);
void script_option(google::protobuf::Message &message, const std::string &name,
                   const ctk::script::Value &value);
} // namespace ctk::application::detail
