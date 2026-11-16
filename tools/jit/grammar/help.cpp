#include "help.hpp"

#include <algorithm>
#include <stdexcept>
#include <vector>

#include <llvm/ADT/STLExtras.h>
#include <llvm/ADT/SmallVector.h>
#include <llvm/ADT/StringMap.h>
#include <llvm/Support/Base64.h>
#include <llvm/Support/JSON.h>
#include <zlib.h>

namespace ctk::jit {
namespace {

#include "help.inc"

llvm::json::Object read_help() {
  std::vector<char> compressed;
  if (auto error = llvm::decodeBase64(help_data, compressed))
    throw std::runtime_error(llvm::toString(std::move(error)));
  std::string text(help_size, '\0');
  auto size = static_cast<unsigned long>(text.size());
  const auto result =
      uncompress(reinterpret_cast<unsigned char *>(text.data()), &size,
                 reinterpret_cast<const unsigned char *>(compressed.data()),
                 compressed.size());
  if (result != Z_OK || size != text.size())
    throw std::runtime_error("could not read bundled CTK help");
  auto parsed = llvm::json::parse(text);
  if (!parsed)
    throw std::runtime_error(llvm::toString(parsed.takeError()));
  auto *documents = parsed->getAsObject();
  if (!documents)
    throw std::runtime_error("bundled CTK help has an invalid format");
  return std::move(*documents);
}

const llvm::json::Object &help_documents() {
  static const auto documents = read_help();
  return documents;
}

} // namespace

NativeHelp native_help(llvm::StringRef topic) {
  const auto &documents = help_documents();
  auto key = topic;
  if (key.starts_with("matchers ") && !documents.getArray(key))
    key = key.drop_front(9);
  if (const auto *content = documents.getArray(key)) {
    return {(*content)[0].getAsString().value_or("").str(),
            (*content)[1].getAsString().value_or("").str()};
  }
  auto message =
      "unknown help topic: " + topic.str() + "; use help to list commands";
  return {message, message};
}

std::vector<std::string> native_help_topics(llvm::StringRef prefix) {
  std::vector<std::string> results;
  for (const auto &[name, unused] : help_documents())
    if (llvm::StringRef(name).starts_with_insensitive(prefix) &&
        !name.str().empty())
      results.push_back(name.str());
  std::ranges::sort(results);
  return results;
}

std::vector<std::string> native_subcommands(llvm::StringRef command) {
  std::vector<std::string> results;
  const auto *content = help_documents().getArray(command);
  if (!content || command.empty() || command.contains(' '))
    return results;
  const auto text = (*content)[0].getAsString().value_or("");
  llvm::SmallVector<llvm::StringRef> lines;
  text.split(lines, '\n');
  bool usage = false;
  for (const auto line : lines) {
    if (line == "Usage:") {
      usage = true;
      continue;
    }
    if (!usage)
      continue;
    if (!line.starts_with("  "))
      break;
    auto words = line.trim();
    if (!words.consume_front(command) || !words.consume_front(" "))
      continue;
    const auto word = words.take_until([](char ch) { return ch == ' '; });
    // Placeholders, literals and option groups are arguments, not commands.
    if (word.empty() || !llvm::all_of(word, [](char ch) {
          return (ch >= 'a' && ch <= 'z') || ch == '_';
        }))
      continue;
    if (std::ranges::find(results, word.str()) == results.end())
      results.push_back(word.str());
  }
  return results;
}

bool editor_keyword(llvm::StringRef word) {
  static const auto keywords = [] {
    llvm::StringMap<bool> result;
    llvm::SmallVector<llvm::StringRef> words;
    llvm::StringRef(editor_keywords).split(words, ' ', -1, false);
    for (const auto item : words)
      result.try_emplace(item, true);
    return result;
  }();
  return keywords.contains(word);
}

llvm::StringRef editor_matcher_kind(llvm::StringRef word) {
  static const auto kinds = [] {
    llvm::StringMap<llvm::StringRef> result;
    for (const auto &[kind, list] :
         {std::pair<llvm::StringRef, llvm::StringRef>{"node",
                                                      editor_node_matchers},
          {"narrowing", editor_narrowing_matchers},
          {"traversal", editor_traversal_matchers}}) {
      llvm::SmallVector<llvm::StringRef> words;
      list.split(words, ' ', -1, false);
      for (const auto item : words)
        result.try_emplace(item, kind);
    }
    return result;
  }();
  return kinds.lookup(word);
}

} // namespace ctk::jit
