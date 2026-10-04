#include "ctk/cache/compilation_context.hpp"

#include "ctk/cache/path_policy.hpp"

#include <algorithm>
#include <array>
#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>

namespace ctk::cache {
namespace {

bool valid_utf8(std::string_view value) {
  for (std::size_t i = 0; i < value.size();) {
    const auto first = static_cast<unsigned char>(value[i]);
    if (first <= 0x7f) {
      ++i;
      continue;
    }
    std::size_t length = 0;
    std::uint32_t codepoint = 0;
    if (first >= 0xc2 && first <= 0xdf) {
      length = 2;
      codepoint = first & 0x1f;
    } else if (first >= 0xe0 && first <= 0xef) {
      length = 3;
      codepoint = first & 0x0f;
    } else if (first >= 0xf0 && first <= 0xf4) {
      length = 4;
      codepoint = first & 0x07;
    } else {
      return false;
    }
    if (i + length > value.size())
      return false;
    for (std::size_t j = 1; j < length; ++j) {
      const auto next = static_cast<unsigned char>(value[i + j]);
      if ((next & 0xc0) != 0x80)
        return false;
      codepoint = (codepoint << 6) | (next & 0x3f);
    }
    if ((length == 2 && codepoint < 0x80) ||
        (length == 3 && codepoint < 0x800) ||
        (length == 4 && codepoint < 0x10000) ||
        (codepoint >= 0xd800 && codepoint <= 0xdfff) || codepoint > 0x10ffff) {
      return false;
    }
    i += length;
  }
  return true;
}

void require_utf8(std::string_view value) {
  if (!valid_utf8(value))
    throw std::invalid_argument("identity contains invalid UTF-8");
}

void append_json_string(std::string &output, std::string_view value) {
  require_utf8(value);
  constexpr std::array<char, 16> hex = {'0', '1', '2', '3', '4', '5', '6', '7',
                                        '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};
  output.push_back('"');
  for (const unsigned char ch : value) {
    switch (ch) {
    case '"':
      output += "\\\"";
      break;
    case '\\':
      output += "\\\\";
      break;
    case '\b':
      output += "\\b";
      break;
    case '\f':
      output += "\\f";
      break;
    case '\n':
      output += "\\n";
      break;
    case '\r':
      output += "\\r";
      break;
    case '\t':
      output += "\\t";
      break;
    default:
      if (ch < 0x20) {
        output += "\\u00";
        output.push_back(hex[ch >> 4]);
        output.push_back(hex[ch & 0x0f]);
      } else {
        output.push_back(static_cast<char>(ch));
      }
    }
  }
  output.push_back('"');
}

void append_string_array(std::string &output,
                         const std::vector<std::string> &values) {
  output.push_back('[');
  bool first = true;
  for (const auto &value : values) {
    if (!first)
      output.push_back(',');
    first = false;
    append_json_string(output, value);
  }
  output.push_back(']');
}

} // namespace

std::string CompilationContext::canonical_bytes() const {
  if (schema_version != 1) {
    throw std::invalid_argument(
        "unsupported compilation identity schema version");
  }
  if (input_spelling.empty())
    throw std::invalid_argument("input spelling is empty");
  if (toolchain_identity.empty())
    throw std::invalid_argument("toolchain identity is empty");
  (void)path_key(working_directory);

  auto sorted_environment = environment;
  std::sort(sorted_environment.begin(), sorted_environment.end(),
            [](const auto &left, const auto &right) {
              return left.first < right.first;
            });
  for (std::size_t i = 0; i < sorted_environment.size(); ++i) {
    require_utf8(sorted_environment[i].first);
    require_utf8(sorted_environment[i].second);
    if (i > 0 &&
        sorted_environment[i - 1].first == sorted_environment[i].first) {
      throw std::invalid_argument("duplicate environment variable name");
    }
  }

  std::string output;
  output.reserve(256);
  output += "ctk-profile-v1:{\"arguments\":";
  append_string_array(output, arguments);
  output += ",\"environment\":{";
  bool first = true;
  for (const auto &[name, value] : sorted_environment) {
    if (!first)
      output.push_back(',');
    first = false;
    append_json_string(output, name);
    output.push_back(':');
    append_json_string(output, value);
  }
  output += "},\"input_spelling\":";
  append_json_string(output, input_spelling);
  output += ",\"resource_directory\":";
  append_json_string(output, resource_directory);
  output += ",\"reusable\":";
  output += reusable ? "true" : "false";
  output += ",\"schema_version\":" + std::to_string(schema_version);
  output += ",\"sysroot\":";
  append_json_string(output, sysroot);
  output += ",\"target\":";
  append_json_string(output, target);
  output += ",\"toolchain_identity\":";
  append_json_string(output, toolchain_identity);
  output += ",\"vfs_overlays\":";
  append_string_array(output, vfs_overlays);
  output += ",\"working_directory\":";
  append_json_string(output, working_directory);
  output.push_back('}');
  return output;
}

std::string CompilationContext::digest() const {
  return compilation_digest(canonical_bytes());
}

std::string compilation_digest(std::string_view canonical_bytes) {
  // FNV-1a 64-bit is deliberately non-cryptographic; full bytes disambiguate
  // hits.
  std::uint64_t value = 14695981039346656037ULL;
  for (const unsigned char byte : canonical_bytes) {
    value ^= byte;
    value *= 1099511628211ULL;
  }
  std::ostringstream output;
  output.imbue(std::locale::classic());
  output << "fnv1a64:" << std::hex << std::setfill('0') << std::setw(16)
         << value;
  return output.str();
}

std::string canonical_json_string(std::string_view value) {
  std::string output;
  output.reserve(value.size() + 2);
  append_json_string(output, value);
  return output;
}

} // namespace ctk::cache
