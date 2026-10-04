#include "ctk/cache/path_policy.hpp"

#include <stdexcept>

namespace ctk::cache {
namespace {

std::string validate(std::string_view absolute) {
  if (absolute.empty() || absolute.front() != '/') {
    throw std::invalid_argument("path must be absolute");
  }

  for (const char ch : absolute) {
    if (ch == '\0')
      throw std::invalid_argument("path contains NUL");
  }

  if (absolute.size() > 1 && absolute.back() == '/' &&
      absolute[absolute.size() - 2] == '/') {
    throw std::invalid_argument("path contains repeated separators");
  }

  std::size_t component_begin = 1;
  for (std::size_t i = 1; i <= absolute.size(); ++i) {
    if (i != absolute.size() && absolute[i] != '/')
      continue;
    const auto component =
        absolute.substr(component_begin, i - component_begin);
    const bool optional_trailing_empty =
        i == absolute.size() && component.empty() && absolute.back() == '/' &&
        absolute.size() > 1;
    if (component.empty() && !optional_trailing_empty && absolute != "/") {
      throw std::invalid_argument("path contains repeated separators");
    }
    if (component == "." || component == "..") {
      throw std::invalid_argument("path contains dot component");
    }
    component_begin = i + 1;
  }
  return std::string(absolute);
}

} // namespace

std::string path_key(std::string_view absolute) {
  auto result = validate(absolute);
  if (result.size() > 1 && result.back() == '/')
    result.pop_back();
  return result;
}

std::string directory_key(std::string_view absolute) {
  return path_key(absolute);
}

std::string directory_prefix(std::string_view absolute) {
  auto result = directory_key(absolute);
  if (result != "/")
    result.push_back('/');
  return result;
}

} // namespace ctk::cache
