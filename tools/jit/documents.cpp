#include "documents.hpp"
#include "filters.hpp"
#include "typed_snapshot.hpp"
#include "value_access.hpp"

#include <cmath>
#include <filesystem>
#include <limits>
#include <optional>
#include <set>

#include <llvm/ADT/SmallString.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>
#include <yaml.h>

namespace ctk::jit {
namespace {

using namespace value_access;
namespace fs = std::filesystem;
namespace llvmfs = llvm::sys::fs;

constexpr std::size_t max_document_bytes = 16 * 1024 * 1024;

bool write(Values& runtime, llvm::StringRef path, llvm::StringRef text, bool append) {
  if (path.empty() || path.contains('\0')) {
    runtime.fail("output requires a nonempty path");
    return false;
  }
  const auto parent = fs::path(path.str()).parent_path();
  if (!parent.empty()) {
    if (const auto error = llvmfs::create_directories(parent.string())) {
      runtime.fail(llvm::Twine("cannot create output directory: ") + error.message());
      return false;
    }
  }
  std::error_code error;
  if (append) {
    llvm::raw_fd_ostream stream(path, error, llvmfs::OF_Append);
    if (!error) {
      stream << text;
      stream.close();
      error = stream.error();
      stream.clear_error();
    }
  } else {
    llvm::SmallString<256> temporary;
    int fd = -1;
    error = llvmfs::createUniqueFile(llvm::Twine(path) + ".%%%%%%", fd, temporary);
    if (!error) {
      llvm::raw_fd_ostream stream(fd, true);
      stream << text;
      stream.close();
      error = stream.error();
      stream.clear_error();
      if (!error)
        error = llvmfs::rename(temporary, path);
      if (error)
        llvmfs::remove(temporary);
    }
  }
  if (!error)
    return true;
  runtime.fail(llvm::Twine("cannot write ") + path + ": " + error.message());
  return false;
}

std::optional<std::string> format_for_path(const fs::path& path, bool text) {
  auto extension = llvm::StringRef(path.extension().string()).lower();
  if (extension == ".yaml" || extension == ".yml")
    return "yaml";
  if (extension == ".json")
    return "json";
  if (extension == ".csv")
    return "csv";
  if (extension == ".proto" && !text)
    return "proto";
  if (text && (extension == ".txt" || extension == ".text"))
    return "text";
  return std::nullopt;
}

std::optional<Value> scalar(llvm::StringRef text, bool plain, bool json) {
  if (!plain)
    return Value{text.str()};
  const auto lower = text.lower();
  if (text.empty() || lower == "null" || text == "~")
    return Value{};
  if (lower == "true" || (!json && (lower == "yes" || lower == "on")))
    return Value{true};
  if (lower == "false" || (!json && (lower == "no" || lower == "off")))
    return Value{false};

  std::string normalized;
  for (const auto ch : text)
    if (ch != '_')
      normalized += ch;
  llvm::StringRef number(normalized);
  bool negative = number.consume_front("-");
  if (!negative)
    number.consume_front("+");
  unsigned radix = 10;
  if (number.consume_front("0x"))
    radix = 16;
  else if (number.consume_front("0b"))
    radix = 2;
  else if (!json && number.size() > 1 && number.front() == '0')
    radix = 8;
  std::uint64_t integer;
  if (!number.getAsInteger(radix, integer)) {
    if (integer > (negative ? std::uint64_t{1} << 63 : (std::uint64_t{1} << 63) - 1)) {
      return std::nullopt;
    }
    if (negative && integer == std::uint64_t{1} << 63)
      return Value{std::numeric_limits<std::int64_t>::min()};
    return Value{negative ? -static_cast<std::int64_t>(integer)
                          : static_cast<std::int64_t>(integer)};
  }
  double floating;
  if (llvm::StringRef(normalized).contains('.') || json) {
    if (!llvm::StringRef(normalized).getAsDouble(floating)) {
      if (!std::isfinite(floating))
        return std::nullopt;
      return Value{floating};
    }
  }
  return Value{text.str()};
}

class YamlReader {
public:
  YamlReader(Values& runtime, bool json)
      : runtime(runtime)
      , json(json) {}

  const Value* read(llvm::StringRef source) {
    if (json) {
      auto validated = llvm::json::parse(source);
      if (!validated)
        return runtime.fail(llvm::toString(validated.takeError()));
    }
    yaml_parser_t parser;
    if (!yaml_parser_initialize(&parser))
      return runtime.fail("could not initialize YAML parser");
    yaml_parser_set_input_string(&parser, reinterpret_cast<const unsigned char*>(source.data()),
                                 source.size());
    yaml_document_t doc;
    if (!yaml_parser_load(&parser, &doc)) {
      const std::string message = parser.problem ? parser.problem : "invalid YAML";
      yaml_parser_delete(&parser);
      return runtime.fail(message);
    }

    const auto* root = yaml_document_get_root_node(&doc);
    auto result = root ? node(doc, *root, 0) : std::optional<Value>{Value{}};
    yaml_document_delete(&doc);
    if (result) {
      if (!yaml_parser_load(&parser, &doc)) {
        runtime.fail(parser.problem ? parser.problem : "invalid YAML");
        result.reset();
      } else {
        if (yaml_document_get_root_node(&doc)) {
          runtime.fail("expected one document");
          result.reset();
        }
        yaml_document_delete(&doc);
      }
    }
    yaml_parser_delete(&parser);
    return result ? runtime.hold(std::move(*result)) : nullptr;
  }

private:
  std::optional<Value> node(yaml_document_t& doc, const yaml_node_t& value, unsigned depth) {
    if (depth > 64 || ++items > max_items || !runtime.tick()) {
      runtime.fail("document exceeds nesting or item limit");
      return std::nullopt;
    }
    if (value.type == YAML_SCALAR_NODE) {
      const auto& scalar_data = value.data.scalar;
      llvm::StringRef text(reinterpret_cast<const char*>(scalar_data.value), scalar_data.length);
      auto decoded = scalar(text, scalar_data.style == YAML_PLAIN_SCALAR_STYLE, json);
      if (!decoded)
        runtime.fail("document number is outside the native numeric range");
      return decoded;
    }
    if (value.type == YAML_SEQUENCE_NODE) {
      std::vector<Value> result;
      const auto& seq = value.data.sequence.items;
      for (auto item = seq.start; item != seq.top; ++item) {
        auto member = node(doc, *yaml_document_get_node(&doc, *item), depth + 1);
        if (!member)
          return std::nullopt;
        result.push_back(std::move(*member));
      }
      return list(std::move(result));
    }
    if (value.type == YAML_MAPPING_NODE) {
      auto result = std::make_shared<Record>();
      const auto& pairs = value.data.mapping.pairs;
      for (auto pair = pairs.start; pair != pairs.top; ++pair) {
        auto key = node(doc, *yaml_document_get_node(&doc, pair->key), depth + 1);
        const auto* name = key ? as<std::string>(*key) : nullptr;
        if (!name) {
          runtime.fail("document object keys must be strings");
          return std::nullopt;
        }
        auto member = node(doc, *yaml_document_get_node(&doc, pair->value), depth + 1);
        if (!member)
          return std::nullopt;
        result->set(*name, std::move(*member));
      }
      return Value{std::move(result)};
    }
    runtime.fail("unsupported YAML node");
    return std::nullopt;
  }

  Values& runtime;
  bool json;
  std::size_t items = 0;
};

std::optional<std::vector<std::vector<std::string>>> parse_csv(Values& runtime,
                                                               llvm::StringRef source) {
  std::vector<std::vector<std::string>> rows;
  std::vector<std::string> row;
  std::string cell;
  bool quoted = false, closed = false;
  for (std::size_t i = 0; i < source.size(); ++i) {
    const char ch = source[i];
    if (quoted) {
      if (ch == '"') {
        if (i + 1 < source.size() && source[i + 1] == '"') {
          cell += ch;
          ++i;
        } else {
          quoted = false;
          closed = true;
        }
      } else {
        cell += ch;
      }
    } else if (ch == ',' || ch == '\n' || ch == '\r') {
      if (ch == ',') {
        row.push_back(std::move(cell));
      } else if (!row.empty() || !cell.empty() || closed) {
        row.push_back(std::move(cell));
        if (row.size() > max_items || rows.size() > max_items) {
          runtime.fail("CSV exceeds item limit");
          return std::nullopt;
        }
        rows.push_back(std::move(row));
        row.clear();
      }
      cell.clear();
      closed = false;
      if (ch == '\r' && i + 1 < source.size() && source[i + 1] == '\n')
        ++i;
    } else if (closed) {
      runtime.fail("unexpected characters after CSV quote");
      return std::nullopt;
    } else if (ch == '"' && cell.empty()) {
      quoted = true;
    } else {
      cell += ch;
    }
  }
  if (quoted) {
    runtime.fail("unterminated CSV quote");
    return std::nullopt;
  }
  if (!row.empty() || !cell.empty() || closed) {
    row.push_back(std::move(cell));
    rows.push_back(std::move(row));
  }
  return rows;
}

enum class Cell { String, Integer, Float, Boolean };

llvm::StringRef cell_name(Cell cell) {
  switch (cell) {
  case Cell::String: return "str";
  case Cell::Integer: return "int";
  case Cell::Float: return "float";
  case Cell::Boolean: return "bool";
  }
  llvm_unreachable("unknown CSV cell type");
}

std::optional<Cell> cell_type(const Value& value) {
  if (as<std::string>(value))
    return Cell::String;
  if (as<std::int64_t>(value))
    return Cell::Integer;
  if (as<double>(value))
    return Cell::Float;
  if (as<bool>(value))
    return Cell::Boolean;
  return std::nullopt;
}

std::optional<Value> csv_value(llvm::StringRef text, Cell cell) {
  if (cell == Cell::String)
    return Value{text.str()};
  if (cell == Cell::Boolean) {
    if (text == "true" || text == "false")
      return Value{text == "true"};
    return std::nullopt;
  }
  text = text.trim();
  if (cell == Cell::Integer) {
    std::int64_t result;
    text.consume_front("+");
    if (!text.getAsInteger(10, result))
      return Value{result};
  } else {
    double result;
    if (!text.getAsDouble(result))
      return Value{result};
  }
  return std::nullopt;
}

const Value* csv_document(Values& runtime, llvm::StringRef source, bool loading) {
  if (!loading)
    source.consume_front("\xef\xbb\xbf");
  const auto rows = parse_csv(runtime, source);
  if (!rows)
    return nullptr;
  if (rows->empty())
    return loading ? runtime.fail("CSV is missing a header") : runtime.hold(list());
  std::vector<std::pair<std::string, Cell>> columns;
  std::set<std::string> distinct;
  for (llvm::StringRef header : rows->front()) {
    Cell cell = Cell::String;
    if (loading) {
      const auto [name, type] = header.rsplit(':');
      for (auto candidate : {Cell::String, Cell::Integer, Cell::Float, Cell::Boolean}) {
        if (type == cell_name(candidate)) {
          header = name;
          cell = candidate;
          break;
        }
      }
    }
    if (header.empty() || !distinct.insert(header.str()).second)
      return runtime.fail("CSV has duplicate or empty columns");
    columns.emplace_back(header.str(), cell);
  }
  std::vector<Value> result;
  const bool single_value = loading && columns.size() == 1 && columns[0].first == "value";
  for (std::size_t index = 1; index < rows->size(); ++index) {
    const auto& values = (*rows)[index];
    if (values.size() != columns.size())
      return runtime.fail("CSV row has the wrong number of columns");
    auto row = std::make_shared<Record>();
    for (std::size_t col = 0; col < columns.size(); ++col) {
      const auto& [name, kind] = columns[col];
      auto value = csv_value(values[col], kind);
      if (!value)
        return runtime.fail(llvm::Twine("invalid CSV ") + cell_name(kind) + " value");
      if (single_value)
        result.push_back(std::move(*value));
      else
        row->set(name, std::move(*value));
    }
    if (!single_value)
      result.push_back({std::move(row)});
  }
  return runtime.hold(list(std::move(result)));
}

void csv_row(std::string& output, const std::vector<std::string>& columns) {
  for (std::size_t index = 0; index < columns.size(); ++index) {
    if (index)
      output += ',';
    const auto& cell = columns[index];
    const bool quote =
        cell.find_first_of(",\"\r\n") != std::string::npos || (columns.size() == 1 && cell.empty());
    if (!quote) {
      output += cell;
      continue;
    }
    output += '"';
    for (char character : cell) {
      if (character == '"')
        output += '"';
      output += character;
    }
    output += '"';
  }
  output += "\r\n";
}

llvm::Expected<std::string> csv_encode(const Value& value) {
  auto fail = [](const char* message) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
  };
  const auto* items = object<Sequence>(value);
  if (!items || items->tuple)
    return fail("CSV requires a list");
  if (items->items.empty())
    return std::string("value:str\r\n");
  const auto* first = object<Record>(items->items.front());
  const auto keys = first ? first->keys : std::vector<std::string>{"value"};
  if (keys.empty())
    return fail("CSV records must have the same nonempty fields");
  std::vector<Cell> types;
  std::vector<std::string> columns;
  for (const auto& key : keys) {
    const auto type = cell_type(first ? first->fields.find(key)->second : items->items.front());
    if (!type)
      return fail("CSV supports only flat lists of primitive values or records");
    types.push_back(*type);
    columns.push_back(key + ":" + cell_name(*type).str());
  }
  std::string result;
  csv_row(result, columns);
  for (const auto& item : items->items) {
    const auto* row = first ? object<Record>(item) : nullptr;
    if (first && (!row || row->keys.size() != keys.size()))
      return fail("CSV records must have the same nonempty fields");
    for (std::size_t index = 0; index < keys.size(); ++index) {
      const auto* selected = &item;
      if (row) {
        const auto found = row->fields.find(keys[index]);
        if (found == row->fields.end())
          return fail("CSV records must have the same nonempty fields");
        selected = &found->second;
      }
      if (cell_type(*selected) != types[index])
        return fail("CSV column types must be consistent");
      if (const auto* text = as<std::string>(*selected))
        columns[index] = *text;
      else if (const auto* integer = as<std::int64_t>(*selected))
        columns[index] = std::to_string(*integer);
      else if (const auto* number = as<double>(*selected))
        columns[index] = format_float(*number);
      else
        columns[index] = *as<bool>(*selected) ? "true" : "false";
    }
    csv_row(result, columns);
    if (result.size() > max_document_bytes)
      return fail("CSV exceeds byte limit");
  }
  return result;
}

const Value* read(Values& runtime, const Value& path, const char* explicit_format, bool loading) {
  const auto* filename = as<std::string>(path);
  if (!filename || filename->empty() || filename->find('\0') != std::string::npos)
    return runtime.fail("read requires a nonempty file path");
  fs::path file(*filename);
  if (loading && !file.has_extension()) {
    std::vector<fs::path> candidates;
    for (const auto* extension : {".yaml", ".yml", ".json", ".csv", ".proto"}) {
      auto candidate = file;
      candidate.replace_extension(extension);
      if (llvmfs::exists(candidate.string()))
        candidates.push_back(std::move(candidate));
    }
    if (candidates.size() != 1)
      return runtime.fail("extensionless load needs exactly one matching file");
    file = std::move(candidates.front());
  }
  const auto format = explicit_format
                          ? std::optional<std::string>{llvm::StringRef(explicit_format).lower()}
                          : format_for_path(file, !loading);
  if (!format)
    return runtime.fail("unsupported document format");

  auto content = llvm::MemoryBuffer::getFile(file.string());
  if (!content)
    return runtime.fail(llvm::Twine("cannot read ") + file.string() + ": " +
                        content.getError().message());
  auto source = (*content)->getBuffer();
  if (source.size() > max_document_bytes)
    return runtime.fail("document exceeds byte limit");
  if (*format == "proto" && loading) {
    auto value = decode_snapshot(source);
    return value ? runtime.hold(std::move(*value)) : runtime.fail(llvm::toString(value.takeError()));
  }
  if (*format == "json" || *format == "yaml")
    return YamlReader(runtime, *format == "json").read(source);
  if (*format == "csv")
    return csv_document(runtime, source, loading);
  if (*format != "text" || loading)
    return runtime.fail("unsupported document format");

  std::vector<Value> lines;
  while (!source.empty()) {
    const auto delimiter = source.find_first_of("\r\n");
    if (lines.size() >= max_items)
      return runtime.fail("document exceeds item limit");
    lines.push_back({source.take_front(delimiter).str()});
    if (delimiter == llvm::StringRef::npos)
      break;
    const bool crlf = source.substr(delimiter, 2) == "\r\n";
    source = source.drop_front(delimiter + (crlf ? 2 : 1));
  }
  return runtime.hold(list(std::move(lines)));
}

extern "C" const Value* ctk_jit_document_read_v1(Values* runtime, const Value* path,
                                                 const char* format, std::int32_t loading) {
  return read(*runtime, *path, format, loading != 0);
}

extern "C" const Value* ctk_jit_document_save_v1(Values* runtime, const Value* path,
                                                 const Value* value, const char* explicit_format) {
  const auto* filename = as<std::string>(*path);
  if (!filename || filename->empty() || filename->find('\0') != std::string::npos)
    return runtime->fail("save requires a nonempty file path");
  fs::path file(*filename);
  const auto inferred = format_for_path(file, false);
  const auto format = explicit_format        ? std::optional<std::string>{explicit_format}
                      : file.has_extension() ? inferred
                                             : std::optional<std::string>{"yaml"};
  if (!format || (*format != "json" && *format != "yaml" && *format != "proto" && *format != "csv"))
    return runtime->fail("unsupported document format");
  if (file.has_extension()) {
    if (inferred != format)
      return runtime->fail("file extension and requested format disagree");
  } else {
    file.replace_extension("." + *format);
  }
  if (*format == "proto" || *format == "csv") {
    auto bytes = *format == "proto" ? encode_snapshot(*value) : csv_encode(*value);
    if (!bytes) return runtime->fail(llvm::toString(bytes.takeError()));
    return write(*runtime, file.string(), *bytes, false) ? value : nullptr;
  }
  const std::array arguments{*value, Value{std::int64_t{2}}};
  const auto* serialized = call_builtin(*runtime, "json", arguments, Record{});
  if (!serialized)
    return nullptr;
  // JSON is a YAML 1.2 document and preserves ordering and scalar types.
  return write(*runtime, file.string(), *as<std::string>(*serialized), false) ? value : nullptr;
}

extern "C" const Value* ctk_jit_document_output_v1(Values* runtime, const Value* path,
                                                   std::int32_t append) {
  if (!path) {
    runtime->state.output_path.clear();
    return runtime->hold({});
  }
  const auto* filename = as<std::string>(*path);
  if (!filename)
    return runtime->fail("output requires a file path");
  if (!write(*runtime, *filename, "", append != 0))
    return nullptr;
  runtime->state.output_path = *filename;
  return runtime->hold({});
}

extern "C" const Value* ctk_jit_document_print_v1(Values* runtime, const Value* value,
                                                  const Value* path, std::int32_t append) {
  const auto* filename = as<std::string>(*path);
  if (!filename)
    return runtime->fail("output requires a file path");
  const auto* rendered = ctk_jit_value_render_v1(runtime, value);
  if (!rendered)
    return nullptr;
  return write(*runtime, *filename, *as<std::string>(*rendered) + '\n', append != 0) ? value
                                                                                     : nullptr;
}

} // namespace

bool emit_text(Values& runtime, llvm::StringRef text) {
  if (runtime.consume_depth)
    return true;
  if (runtime.state.output_path.empty()) {
    if (!text.empty()) {
      runtime.output += text;
      runtime.output += '\n';
    }
  } else if (!write(runtime, runtime.state.output_path, text.str() + '\n', true)) {
    return false;
  }
  ++runtime.emissions;
  return true;
}

llvm::Error expose_documents(llvm::orc::LLJIT& jit) {
  llvm::orc::SymbolMap symbols;
  auto expose = [&](llvm::StringRef name, auto* function) {
    symbols[jit.mangleAndIntern(name)] = {llvm::orc::ExecutorAddr::fromPtr(function),
                                          llvm::JITSymbolFlags::Exported |
                                              llvm::JITSymbolFlags::Callable};
  };
  expose("ctk_jit_document_read_v1", &ctk_jit_document_read_v1);
  expose("ctk_jit_document_save_v1", &ctk_jit_document_save_v1);
  expose("ctk_jit_document_output_v1", &ctk_jit_document_output_v1);
  expose("ctk_jit_document_print_v1", &ctk_jit_document_print_v1);
  return jit.getMainJITDylib().define(llvm::orc::absoluteSymbols(std::move(symbols)));
}

} // namespace ctk::jit
