#pragma once

#include <string>
#include <string_view>

namespace ctk::cache {

// Validate an absolute POSIX pathname and return its file-key spelling.
// Components are preserved byte-for-byte; this does not resolve symlinks.
std::string path_key(std::string_view absolute);

// Return the validated spelling for an exact directory namespace key.
// A single trailing slash is accepted and removed (except for `/`).
std::string directory_key(std::string_view absolute);

// Return a separator-terminated prefix suitable for boundary-safe traversal.
// Root remains `/`.
std::string directory_prefix(std::string_view absolute);

} // namespace ctk::cache
