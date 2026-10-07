#pragma once
#include "analysis/v1/script_compilation_profile.pb.h"
#include "match/v1/match_service.pb.h"
#include <string>

namespace ctk::application::detail {
std::string invalid_file_target(const ctk::match::v1::FileMatchTarget &file);
std::string invalid_script_profile(
    const ctk::analysis::v1::ScriptCompilationProfile &profile);
} // namespace ctk::application::detail
