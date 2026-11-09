#include "filters.hpp"
#include "file_values.hpp"
#include "semantic.hpp"
#include "value_access.hpp"
#include "ctk/support/algorithm.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <optional>
#include <set>
#include <string_view>

#include <llvm/ADT/StringSwitch.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MathExtras.h>
#include <unicode/locid.h>
#include <unicode/uchar.h>
#include <unicode/unistr.h>

namespace ctk::jit {
namespace {

using namespace value_access;

constexpr std::size_t max_bytes = 1048576;

enum class Filter {
  Unknown,
  Range,
  Length,
  Map,
  Keep,
  Take,
  Drop,
  First,
  Last,
  Reverse,
  Keys,
  Values,
  Entries,
  Pick,
  Flatten,
  ToList,
  ToTuple,
  Zip,
  ZipLongest,
  Enumerate,
  Unique,
  UniqueBy,
  Sort,
  SortBy,
  Join,
  Split,
  Upper,
  Lower,
  Casefold,
  Camel,
  Pascal,
  Snake,
  Kebab,
  Trim,
  TrimStart,
  TrimEnd,
  Replace,
  StripPrefix,
  StripSuffix,
  StartsWith,
  EndsWith,
  Contains,
  Json,
  Pretty,
  Table
};

struct Signature {
  Filter kind = Filter::Unknown;
  std::size_t required = 0;
  llvm::StringRef parameters;
  llvm::StringRef keyword_only;
  bool variadic = false;
};

Signature signature(llvm::StringRef name) {
  return llvm::StringSwitch<Signature>(name)
      .Case("range", {Filter::Range, 1, "", "", true})
      .Cases("len", "length", {Filter::Length, 1, "value"})
      .Case("map", {Filter::Map, 2, "value callback"})
      .Case("filter", {Filter::Keep, 2, "value callback"})
      .Case("take", {Filter::Take, 2, "value n"})
      .Case("drop", {Filter::Drop, 2, "value n"})
      .Case("first", {Filter::First, 1, "value n"})
      .Case("last", {Filter::Last, 1, "value n"})
      .Case("reverse", {Filter::Reverse, 1, "value"})
      .Case("keys", {Filter::Keys, 1, "value"})
      .Case("values", {Filter::Values, 1, "value"})
      .Case("entries", {Filter::Entries, 1, "value"})
      .Case("pick", {Filter::Pick, 1, "value", "", true})
      .Case("flatten", {Filter::Flatten, 1, "value"})
      .Case("to_list", {Filter::ToList, 1, "value"})
      .Case("to_tuple", {Filter::ToTuple, 1, "value"})
      .Case("zip", {Filter::Zip, 2, "value other", "strict", true})
      .Case("zip_longest", {Filter::ZipLongest, 2, "value other", "fill", true})
      .Case("enumerate", {Filter::Enumerate, 1, "value start"})
      .Case("unique", {Filter::Unique, 1, "value"})
      .Case("unique_by", {Filter::UniqueBy, 2, "value callback"})
      .Case("sort", {Filter::Sort, 1, "value reverse"})
      .Case("sort_by", {Filter::SortBy, 2, "value callback reverse"})
      .Case("join", {Filter::Join, 1, "value separator"})
      .Case("split_by", {Filter::Split, 2, "value separator"})
      .Case("upper", {Filter::Upper, 1, "value"})
      .Case("lower", {Filter::Lower, 1, "value"})
      .Case("casefold", {Filter::Casefold, 1, "value"})
      .Case("camel_case", {Filter::Camel, 1, "value"})
      .Case("pascal_case", {Filter::Pascal, 1, "value"})
      .Case("snake_case", {Filter::Snake, 1, "value"})
      .Case("kebab_case", {Filter::Kebab, 1, "value"})
      .Case("trim", {Filter::Trim, 1, "value"})
      .Case("trim_start", {Filter::TrimStart, 1, "value"})
      .Case("trim_end", {Filter::TrimEnd, 1, "value"})
      .Case("replace", {Filter::Replace, 3, "value old new count"})
      .Case("strip_prefix", {Filter::StripPrefix, 2, "value prefix"})
      .Case("strip_suffix", {Filter::StripSuffix, 2, "value suffix"})
      .Case("starts_with", {Filter::StartsWith, 2, "value part"})
      .Case("ends_with", {Filter::EndsWith, 2, "value part"})
      .Case("contains", {Filter::Contains, 2, "value part"})
      .Case("json", {Filter::Json, 1, "value indent"})
      .Case("pretty", {Filter::Pretty, 1, "value indent depth max_items"})
      .Case("table", {Filter::Table, 2, "value columns max_items"})
      .Default({});
}

struct Arguments {
  std::vector<const Value*> values;
  const Value* option = nullptr;

  template <typename T> const T* get(std::size_t index) const {
    return values[index] ? as<T>(*values[index]) : nullptr;
  }

  template <typename T> std::optional<T> get(std::size_t index, T fallback) const {
    if (!values[index])
      return fallback;
    if (const auto* value = as<T>(*values[index]))
      return *value;
    return std::nullopt;
  }

  const Value& operator[](std::size_t index) const { return *values[index]; }
};

std::optional<Arguments> bind(Values& runtime, const Signature& spec,
                              llvm::ArrayRef<Value> positional, const Record& keywords) {
  llvm::SmallVector<llvm::StringRef> labels;
  spec.parameters.split(labels, ' ', -1, false);
  if ((!spec.variadic && positional.size() > labels.size()) ||
      (spec.kind == Filter::Range && positional.size() > 3)) {
    runtime.fail("too many positional arguments");
    return std::nullopt;
  }

  Arguments args;
  args.values.resize(std::max(labels.size(), positional.size()));
  for (std::size_t index = 0; index < positional.size(); ++index) {
    args.values[index] = &positional[index];
  }
  for (const auto& name : keywords.keys) {
    const auto* value = &keywords.fields.find(name)->second;
    if (name == spec.keyword_only && !spec.keyword_only.empty()) {
      args.option = value;
      continue;
    }
    const auto found = llvm::find(labels, name);
    if (found == labels.end()) {
      runtime.fail(llvm::Twine("unknown parameter '") + name + "'");
      return std::nullopt;
    }
    const auto index = static_cast<std::size_t>(found - labels.begin());
    if (args.values[index]) {
      runtime.fail(llvm::Twine("multiple values for parameter '") + name + "'");
      return std::nullopt;
    }
    args.values[index] = value;
  }
  if (args.values.size() < spec.required ||
      llvm::any_of(llvm::ArrayRef(args.values).take_front(spec.required),
                   [](const Value* value) { return !value; })) {
    runtime.fail("missing required argument");
    return std::nullopt;
  }
  return args;
}

const Value* range(Values& runtime, const Arguments& args) {
  if (llvm::any_of(args.values, [](const Value* value) { return !as<std::int64_t>(*value); })) {
    return runtime.fail("range accepts one to three integer arguments");
  }
  const auto count = args.values.size();
  auto start = count == 1 ? 0 : *args.get<std::int64_t>(0);
  const auto stop = *args.get<std::int64_t>(count == 1 ? 0 : 1);
  const auto step = count == 3 ? *args.get<std::int64_t>(2) : 1;
  if (step == 0)
    return runtime.fail("range step must not be zero");
  std::vector<Value> items;
  while (step > 0 ? start < stop : start > stop) {
    if (items.size() == max_items)
      return runtime.fail("range exceeds item limit");
    items.push_back({start});
    if (llvm::AddOverflow(start, step, start))
      break;
  }
  return runtime.hold(list(std::move(items)));
}

const Value* mapping(Values& runtime, Filter filter, const Arguments& args) {
  const auto* data = object<Record>(args[0]);
  if (!data)
    return runtime.fail("mapping filter requires a record");
  if (filter == Filter::Pick) {
    auto result = std::make_shared<Record>();
    for (std::size_t index = 1; index < args.values.size(); ++index) {
      const auto* key = args.get<std::string>(index);
      if (!key)
        return runtime.fail("pick names must be strings");
      const auto field = data->fields.find(*key);
      if (field == data->fields.end())
        return runtime.fail(llvm::Twine("missing field ") + *key);
      result->set(*key, field->second);
    }
    return runtime.hold({std::move(result)});
  }

  std::vector<Value> result;
  for (const auto& key : data->keys) {
    const auto& value = data->fields.find(key)->second;
    if (filter == Filter::Keys) {
      result.push_back({key});
    } else if (filter == Filter::Values) {
      result.push_back(value);
    } else {
      auto entry = std::make_shared<Record>();
      entry->set("key", {key});
      entry->set("value", value);
      result.push_back({std::move(entry)});
    }
  }
  return runtime.hold(list(std::move(result)));
}

const Value* zip(Values& runtime, const Arguments& args, bool longest) {
  bool strict = true;
  if (!longest && args.option) {
    const auto* option = as<bool>(*args.option);
    if (!option)
      return runtime.fail("strict must be bool");
    strict = *option;
  }
  const Value fill = longest && args.option ? *args.option : Value{};
  std::vector<const Sequence*> sources;
  for (const auto* value : args.values) {
    const auto* source = object<Sequence>(*value);
    if (!source)
      return runtime.fail("zip requires lists or tuples");
    sources.push_back(source);
  }
  std::size_t length = sources.front()->items.size();
  for (const auto* source : sources) {
    const auto size = source->items.size();
    if (longest)
      length = std::max(length, size);
    else if (strict && size != length)
      return runtime.fail("zip inputs must have equal lengths");
    else
      length = std::min(length, size);
  }

  std::vector<Value> rows;
  for (std::size_t index = 0; index < length; ++index) {
    std::vector<Value> row;
    for (const auto* source : sources) {
      if (!runtime.tick())
        return nullptr;
      row.push_back(index < source->items.size() ? source->items[index] : fill);
    }
    rows.push_back(list(std::move(row), true));
  }
  return runtime.hold(list(std::move(rows)));
}

class Callback {
public:
  explicit Callback(const Value& value)
      : value(value) {
    if (const auto* runnable = object<Runnable>(value)) {
      minimum = runnable->minimum;
      maximum = runnable->maximum;
    } else if (const auto* builtin = as<BuiltinFunction>(value)) {
      const auto spec = signature(builtin->name);
      minimum = spec.required;
      maximum = spec.variadic ? max_items : spec.parameters.count(' ') + 1;
    }
  }

  bool valid() const { return minimum <= maximum && maximum != 0; }

  const Value* operator()(Values& runtime, const Value& item) const {
    Value arguments;
    if (minimum > 1) {
      const auto* sequence = object<Sequence>(item);
      if (!sequence || !sequence->tuple)
        return runtime.fail("callback requires a tuple item");
      arguments = list(sequence->items);
    } else {
      arguments = list({item});
    }
    const Value keywords = record();
    return ctk_jit_value_invoke_v1(&runtime, &value, &arguments, &keywords);
  }

private:
  const Value& value;
  std::size_t minimum = 1;
  std::size_t maximum = 0;
};

int int_float_order(std::int64_t integer, double floating) {
  if (floating >= 0x1p63)
    return -1;
  if (floating < -0x1p63)
    return 1;
  const auto integral = static_cast<std::int64_t>(floating);
  if (integer != integral)
    return integer < integral ? -1 : 1;
  const auto converted = static_cast<double>(integer);
  return (converted > floating) - (converted < floating);
}

int order(const Value& left, const Value& right) {
  if (const auto* l = as<std::string>(left))
    return l->compare(*as<std::string>(right));
  if (const auto* l = as<std::int64_t>(left)) {
    if (const auto* r = as<std::int64_t>(right))
      return (*l > *r) - (*l < *r);
    return int_float_order(*l, *as<double>(right));
  }
  if (const auto* r = as<std::int64_t>(right))
    return -int_float_order(*r, *as<double>(left));
  const auto l = *as<double>(left), r = *as<double>(right);
  return (l > r) - (l < r);
}

} // namespace

std::string format_float(double number) {
#if defined(_GLIBCXX_RELEASE) && _GLIBCXX_RELEASE < 11
  std::ostringstream output;
  output.imbue(std::locale::classic());
  // Find the shortest scientific representation that round-trips to number.
  std::string rendered;
  for (int precision = 0; precision < std::numeric_limits<double>::max_digits10;
       ++precision) {
    output.str("");
    output << std::scientific << std::setprecision(precision) << number;
    rendered = output.str();
    if (!std::isfinite(number))
      return rendered;
    std::istringstream input(rendered);
    input.imbue(std::locale::classic());
    double roundtrip;
    if (input >> roundtrip && roundtrip == number)
      break;
  }
  llvm::StringRef scientific(rendered);
#else
  char buffer[48];
  const auto sci =
      std::to_chars(buffer, buffer + sizeof(buffer), number, std::chars_format::scientific);
  llvm::StringRef scientific(buffer, sci.ptr - buffer);
#endif
  int exponent = 0;
  auto power = scientific.split('e').second;
  power.consume_front("+");
  if (power.getAsInteger(10, exponent))
    return scientific.str();
  if (exponent < -4 || exponent >= 16)
    return scientific.str();
#if defined(_GLIBCXX_RELEASE) && _GLIBCXX_RELEASE < 11
  auto mantissa = scientific.split('e').first;
  const bool negative = mantissa.consume_front("-");
  auto digits = mantissa.str();
  digits.erase(std::remove(digits.begin(), digits.end(), '.'), digits.end());
  std::string result = negative ? "-" : "";
  if (exponent < 0) {
    result += "0." + std::string(-1 - exponent, '0') + digits;
  } else {
    const auto point = static_cast<std::size_t>(exponent + 1);
    if (point < digits.size()) {
      digits.insert(point, 1, '.');
    } else {
      digits.resize(point, '0');
    }
    result += digits;
  }
#else
  const auto fixed =
      std::to_chars(buffer, buffer + sizeof(buffer), number, std::chars_format::fixed);
  std::string result(buffer, fixed.ptr);
#endif
  if (result.find('.') == std::string::npos)
    result += ".0";
  return result;
}

namespace {

bool typed_key(Values& runtime, const Value& value, std::string& key, unsigned depth) {
  if (!runtime.tick())
    return false;
  if (depth >= 32) {
    runtime.fail("unique key tuple nesting exceeds depth limit");
    return false;
  }
  if (const auto* number = as<std::int64_t>(value)) {
    key += "i" + std::to_string(*number) + ";";
  } else if (const auto* number = as<double>(value)) {
    if (*number >= -0x1p63 && *number < 0x1p63 && std::trunc(*number) == *number) {
      key += "i" + std::to_string(static_cast<std::int64_t>(*number)) + ";";
    } else {
      key += "f" + format_float(*number) + ";";
    }
  } else if (const auto* text = as<std::string>(value)) {
    key += "s" + std::to_string(text->size()) + ":" + *text;
  } else if (const auto* flag = as<bool>(value)) {
    key += *flag ? "T" : "F";
  } else if (std::holds_alternative<std::monostate>(value.data)) {
    key += "n";
  } else if (const auto* items = object<Sequence>(value); items && items->tuple) {
    key += '(';
    for (const auto& item : items->items)
      if (!typed_key(runtime, item, key, depth + 1))
        return false;
    key += ')';
  } else {
    runtime.fail("unsupported unique key type");
    return false;
  }
  return true;
}

const Value* transform(Values& runtime, Filter filter, const Arguments& args,
                       const Sequence& sequence) {
  const bool sorting = filter == Filter::Sort || filter == Filter::SortBy;
  const bool keyed = filter == Filter::Map || filter == Filter::Keep ||
                     filter == Filter::UniqueBy || filter == Filter::SortBy;
  std::optional<Callback> callback;
  if (keyed) {
    callback.emplace(args[1]);
    if (!callback->valid())
      return runtime.fail("callback has incompatible arity");
  }
  bool descending = false;
  if (sorting) {
    const auto reverse = args.get<bool>(keyed ? 2 : 1, false);
    if (!reverse)
      return runtime.fail("reverse must be bool");
    descending = *reverse;
  }

  std::vector<Value> result;
  std::vector<std::pair<Value, Value>> decorated;
  std::set<std::string> seen;
  std::optional<bool> string_keys;
  // Callbacks may change the source collection. Recheck its length and copy
  // each current item before invoking user code.
  for (std::size_t index = 0; index < sequence.items.size(); ++index) {
    if (!runtime.tick())
      return nullptr;
    if (index >= max_items)
      return runtime.fail("collection filter exceeds item limit");
    const auto item = sequence.items[index];
    const auto* key = callback ? (*callback)(runtime, item) : &item;
    if (!key)
      return nullptr;
    if (filter == Filter::Map) {
      result.push_back(*key);
    } else if (filter == Filter::Keep) {
      const auto* keep = as<bool>(*key);
      if (!keep)
        return runtime.fail("filter callback must return bool");
      if (*keep)
        result.push_back(item);
    } else if (sorting) {
      const bool text = as<std::string>(*key) != nullptr;
      if ((!text && !as<std::int64_t>(*key) && !as<double>(*key)) ||
          (string_keys && *string_keys != text)) {
        return runtime.fail("sort keys must be homogeneous finite numbers or strings");
      }
      string_keys = text;
      decorated.emplace_back(*key, item);
    } else {
      std::string encoded;
      if (!typed_key(runtime, *key, encoded, 0))
        return nullptr;
      if (seen.insert(std::move(encoded)).second)
        result.push_back(item);
    }
  }
  if (sorting) {
    std::stable_sort(decorated.begin(), decorated.end(), [&](const auto& left, const auto& right) {
      const auto result = order(left.first, right.first);
      return descending ? result > 0 : result < 0;
    });
    for (auto& [key, item] : decorated)
      result.push_back(std::move(item));
  }
  return runtime.hold(list(std::move(result)));
}

const Value* collection(Values& runtime, Filter filter, const Arguments& args) {
  const auto* sequence = object<Sequence>(args[0]);
  if (!sequence)
    return runtime.fail("collection filter requires a list or tuple");
  const auto& items = sequence->items;
  if (filter == Filter::Map || filter == Filter::Keep || filter == Filter::Sort ||
      filter == Filter::SortBy || filter == Filter::Unique || filter == Filter::UniqueBy) {
    return transform(runtime, filter, args, *sequence);
  }
  if (filter == Filter::Take || filter == Filter::Drop || filter == Filter::First ||
      filter == Filter::Last) {
    if (!args.values[1]) {
      return runtime.hold(items.empty()             ? Value{}
                          : filter == Filter::First ? items.front()
                                                    : items.back());
    }
    const auto* count = args.get<std::int64_t>(1);
    if (!count || *count < 0)
      return runtime.fail("collection count must be nonnegative");
    const auto size = std::min<std::uint64_t>(*count, items.size());
    auto first = items.begin();
    auto last = items.end();
    if (filter == Filter::Drop)
      first += size;
    else if (filter == Filter::Last)
      first = last - size;
    else
      last = first + size;
    return runtime.hold(list(std::vector<Value>(first, last)));
  }
  if (filter == Filter::Join) {
    const auto separator = args.get<std::string>(1, {});
    if (!separator)
      return runtime.fail("join separator must be a string");
    std::string result;
    for (std::size_t index = 0; index < items.size(); ++index) {
      const auto* part = as<std::string>(items[index]);
      if (!part)
        return runtime.fail("join requires string items");
      if (index)
        result += *separator;
      result += *part;
      if (result.size() > max_bytes)
        return runtime.fail("join output exceeds byte limit");
    }
    return runtime.hold({std::move(result)});
  }
  if (filter == Filter::Flatten) {
    std::vector<Value> result;
    for (const auto& item : items) {
      const auto* nested = object<Sequence>(item);
      if (!nested)
        return runtime.fail("flatten requires nested collections");
      if (nested->items.size() > max_items - result.size())
        return runtime.fail("flatten exceeds item limit");
      result.insert(result.end(), nested->items.begin(), nested->items.end());
    }
    return runtime.hold(list(std::move(result)));
  }
  if (filter == Filter::Enumerate) {
    auto index = args.get<std::int64_t>(1, 0);
    if (!index)
      return runtime.fail("start must be an integer");
    std::vector<Value> result;
    for (const auto& item : items) {
      result.push_back(list({Value{*index}, item}, true));
      if (llvm::AddOverflow(*index, std::int64_t{1}, *index) && result.size() < items.size())
        return runtime.fail("enumerate index exceeds signed 64-bit integer range");
    }
    return runtime.hold(list(std::move(result)));
  }
  if (filter == Filter::Reverse)
    return runtime.hold(list(std::vector<Value>(items.rbegin(), items.rend())));
  return runtime.hold(list(items, filter == Filter::ToTuple));
}

icu::UnicodeString case_words(const icu::UnicodeString& text, Filter filter) {
  std::vector<UChar32> points;
  for (int index = 0; index < text.length();) {
    const auto point = text.char32At(index);
    points.push_back(point);
    index += U16_LENGTH(point);
  }

  const auto& locale = icu::Locale::getRoot();
  icu::UnicodeString result;
  icu::UnicodeString word;
  auto append = [&] {
    if (word.isEmpty())
      return;
    if (filter == Filter::Snake || filter == Filter::Kebab) {
      if (!result.isEmpty())
        result.append(filter == Filter::Snake ? '_' : '-');
      result.append(word.toLower(locale));
    } else if (filter == Filter::Camel && result.isEmpty()) {
      result.append(word.toLower(locale));
    } else {
      const auto first_end = U16_LENGTH(word.char32At(0));
      icu::UnicodeString first(word, 0, first_end);
      icu::UnicodeString rest(word, first_end);
      result.append(first.toUpper(locale)).append(rest.toLower(locale));
    }
    word.remove();
  };
  for (std::size_t index = 0; index < points.size(); ++index) {
    const auto current = points[index];
    if (!u_isalnum(current) && u_getNumericValue(current) == U_NO_NUMERIC_VALUE) {
      append();
      continue;
    }
    if (index && u_isupper(current) && !word.isEmpty()) {
      const auto previous = points[index - 1];
      const auto next = index + 1 < points.size() ? points[index + 1] : 0;
      if (u_islower(previous) || u_isdigit(previous) || (u_isupper(previous) && u_islower(next))) {
        append();
      }
    }
    word.append(current);
  }
  append();
  return result;
}

const Value* string_filter(Values& runtime, Filter filter, const Arguments& args) {
  const auto* value = args.get<std::string>(0);
  if (!value)
    return runtime.fail("value must be a string");
  if (value->size() > max_bytes)
    return runtime.fail("filter text exceeds byte limit");

  if (filter >= Filter::Upper && filter <= Filter::TrimEnd) {
    auto text = icu::UnicodeString::fromUTF8(*value);
    const auto& locale = icu::Locale::getRoot();
    if (filter == Filter::Upper)
      text.toUpper(locale);
    else if (filter == Filter::Lower)
      text.toLower(locale);
    else if (filter == Filter::Casefold)
      text.foldCase();
    else if (filter <= Filter::Kebab)
      text = case_words(text, filter);
    else {
      auto space = [](UChar32 point) {
        return u_isUWhiteSpace(point) || (point >= 0x1c && point <= 0x1f);
      };
      int first = 0, last = text.length();
      if (filter != Filter::TrimEnd) {
        while (first < last && space(text.char32At(first)))
          first = text.moveIndex32(first, 1);
      }
      if (filter != Filter::TrimStart) {
        while (last > first && space(text.char32At(text.moveIndex32(last, -1))))
          last = text.moveIndex32(last, -1);
      }
      text.retainBetween(first, last);
    }
    std::string result;
    text.toUTF8String(result);
    if (result.size() > max_bytes)
      return runtime.fail("filter text exceeds byte limit");
    return runtime.hold({std::move(result)});
  }

  const auto* argument = args.get<std::string>(1);
  if (!argument || argument->size() > max_bytes)
    return runtime.fail("string filter argument must be a string within the byte limit");
  const llvm::StringRef text(*value);
  if (filter == Filter::StartsWith)
    return runtime.hold({ctk::compat::starts_with(text, *argument)});
  if (filter == Filter::EndsWith)
    return runtime.hold({ctk::compat::ends_with(text, *argument)});
  if (filter == Filter::Contains)
    return runtime.hold({ctk::compat::contains(text, *argument)});
  if (filter == Filter::StripPrefix) {
    return runtime.hold(
        {ctk::compat::starts_with(text, *argument) ? text.drop_front(argument->size()).str() : *value});
  }
  if (filter == Filter::StripSuffix) {
    return runtime.hold(
        {ctk::compat::ends_with(text, *argument) ? text.drop_back(argument->size()).str() : *value});
  }
  if (argument->empty())
    return runtime.fail("separator or replacement key must be nonempty");
  if (filter == Filter::Replace) {
    const auto* replacement = args.get<std::string>(2);
    const auto count = args.get<std::int64_t>(3, -1);
    if (!replacement || replacement->size() > max_bytes || !count || *count < -1)
      return runtime.fail("replace requires a string and a count of -1 or greater");
    std::string result;
    auto rest = text;
    for (std::int64_t index = 0; *count < 0 || index < *count; ++index) {
      const auto at = rest.find(*argument);
      if (at == llvm::StringRef::npos)
        break;
      result += rest.take_front(at);
      result += *replacement;
      if (result.size() > max_bytes)
        return runtime.fail("replace output exceeds byte limit");
      rest = rest.drop_front(at + argument->size());
    }
    result += rest;
    if (result.size() > max_bytes)
      return runtime.fail("replace output exceeds byte limit");
    return runtime.hold({std::move(result)});
  }
  llvm::SmallVector<llvm::StringRef> parts;
  text.split(parts, *argument, max_items);
  if (parts.size() > max_items)
    return runtime.fail("split exceeds item limit");
  std::vector<Value> result;
  for (auto part : parts)
    result.push_back({part.str()});
  return runtime.hold(list(std::move(result)));
}

// The serializer keeps CTK record insertion order. LLVM's JSON object does
// not preserve that order when it renders.
class DataWriter {
public:
  DataWriter(Values& runtime, unsigned indent, unsigned max_depth, std::size_t remaining,
             bool pretty)
      : runtime(runtime)
      , indent(indent)
      , max_depth(max_depth)
      , remaining(remaining)
      , pretty(pretty) {}

  bool write(const Value& value, unsigned level = 0) {
    if (const auto* entry = object<FileEntry>(value))
      return write(file_record(*entry), level);
    if (const auto* text = as<std::string>(value))
      return quote(*text);
    if (const auto* flag = as<bool>(value))
      return append(*flag ? "true" : "false");
    if (const auto* number = as<std::int64_t>(value))
      return append(std::to_string(*number));
    if (const auto* number = as<double>(value))
      return append(format_float(*number));
    if (std::holds_alternative<std::monostate>(value.data))
      return append("null");

    const auto* sequence = object<Sequence>(value);
    const auto* mapping = object<Record>(value);
    if (!sequence && !mapping) {
      if (!pretty)
        return fail("json accepts ordinary serializable data");
      const auto* rendered = ctk_jit_value_render_v1(&runtime, &value);
      return rendered && append(*as<std::string>(*rendered));
    }
    if (level >= max_depth) {
      return pretty ? append("… <depth omitted>") : fail("json exceeds depth limit");
    }
    const auto size = sequence ? sequence->items.size() : mapping->keys.size();
    if (!pretty && size > remaining)
      return fail("json exceeds item limit");
    const auto selected = std::min(size, remaining);
    remaining -= selected;
    const bool tuple = pretty && sequence && sequence->tuple;
    if (!append(tuple ? "(" : sequence ? "[" : "{"))
      return false;
    for (std::size_t index = 0; index < selected; ++index) {
      if (!runtime.tick() || !delimiter(index, level + 1))
        return false;
      if (sequence) {
        if (!write(sequence->items[index], level + 1))
          return false;
      } else {
        const auto& key = mapping->keys[index];
        if (!quote(key) || !append(pretty || indent ? ": " : ":") ||
            !write(mapping->fields.find(key)->second, level + 1))
          return false;
      }
    }
    if (selected < size) {
      if (!delimiter(selected, level + 1) ||
          !append("… " + std::to_string(size - selected) + " items omitted"))
        return false;
    } else if (tuple && size == 1 && !append(",")) {
      return false;
    }
    if (size && indent && !line(level))
      return false;
    return append(tuple ? ")" : sequence ? "]" : "}");
  }

  std::string result;

private:
  bool fail(llvm::StringRef message) {
    runtime.fail(message);
    return false;
  }

  bool append(llvm::StringRef text) {
    if (text.size() > max_bytes - result.size())
      return fail("formatted output exceeds byte limit");
    result += text;
    return true;
  }

  bool quote(llvm::StringRef text) {
    if (text.size() > max_bytes - result.size())
      return fail("formatted output exceeds byte limit");
    std::string encoded;
    llvm::raw_string_ostream output(encoded);
    output << llvm::json::Value(text);
    return append(encoded);
  }

  bool line(unsigned level) { return append("\n") && append(std::string(level * indent, ' ')); }

  bool delimiter(std::size_t index, unsigned level) {
    if (index && !append(indent || !pretty ? "," : ", "))
      return false;
    return !indent || line(level);
  }

  Values& runtime;
  unsigned indent;
  unsigned max_depth;
  std::size_t remaining;
  bool pretty;
};

const Value* table(Values& runtime, const Arguments& args) {
  const auto* sequence = object<Sequence>(args[0]);
  const auto* columns = object<Sequence>(args[1]);
  const auto maximum = args.get<std::int64_t>(2, 100);
  if (!sequence || !columns || columns->items.empty() || columns->items.size() > 50 || !maximum ||
      *maximum < 0) {
    return runtime.fail("table requires rows, up to 50 columns and a nonnegative item limit");
  }

  std::vector<std::string> names;
  std::set<std::string> seen;
  for (const auto& column : columns->items) {
    const auto* name = as<std::string>(column);
    if (!name || !seen.insert(*name).second)
      return runtime.fail("invalid or duplicate column");
    names.push_back(*name);
  }

  auto escaped = [](llvm::StringRef text) {
    std::string result;
    for (const char ch : text) {
      if (ch == '\n')
        result += "\\n";
      else if (ch == '\r')
        result += "\\r";
      else if (ch == '\t')
        result += "\\t";
      else
        result += ch;
    }
    return result;
  };
  auto width = [](llvm::StringRef text) {
    return static_cast<std::size_t>(
        llvm::count_if(text, [](unsigned char byte) { return (byte & 0xc0) != 0x80; }));
  };
  std::vector<std::string> headers;
  std::vector<std::size_t> widths;
  for (const auto& name : names) {
    headers.push_back(escaped(name));
    widths.push_back(width(headers.back()));
  }

  const auto limit =
      std::min<std::size_t>(std::min<std::int64_t>(*maximum, 100), sequence->items.size());
  std::vector<std::vector<std::string>> rows;
  for (std::size_t index = 0; index < limit; ++index) {
    const auto* row = object<Record>(sequence->items[index]);
    if (!row)
      return runtime.fail("table rows must be ordinary dictionaries");
    auto& cells = rows.emplace_back();
    for (std::size_t column = 0; column < names.size(); ++column) {
      if (!runtime.tick())
        return nullptr;
      const auto field = row->fields.find(names[column]);
      if (field == row->fields.end())
        return runtime.fail(llvm::Twine("missing field ") + names[column]);
      if (const auto* text = as<std::string>(field->second)) {
        cells.push_back(escaped(*text));
      } else {
        DataWriter writer(runtime, 0, 8, 100, false);
        if (!writer.write(field->second))
          return nullptr;
        cells.push_back(std::move(writer.result));
      }
      widths[column] = std::max(widths[column], width(cells.back()));
    }
  }

  std::string output;
  auto line = [&](const std::vector<std::string>& cells) {
    for (std::size_t index = 0; index < cells.size(); ++index) {
      if (index)
        output += "  ";
      output += cells[index];
      output.append(widths[index] - width(cells[index]), ' ');
    }
  };
  line(headers);
  for (const auto& row : rows) {
    output += '\n';
    line(row);
  }
  if (limit < sequence->items.size())
    output += "\n… more rows omitted";
  if (rows.empty())
    output += '\n';
  return runtime.hold({std::move(output)});
}

const Value* formatting(Values& runtime, Filter filter, const Arguments& args) {
  if (filter == Filter::Table)
    return table(runtime, args);
  const bool pretty = filter == Filter::Pretty;
  const auto indent = args.get<std::int64_t>(1, pretty ? 2 : 0);
  const auto depth = pretty ? args.get<std::int64_t>(2, 8) : std::optional<std::int64_t>{32};
  const auto bound =
      pretty ? args.get<std::int64_t>(3, 100) : std::optional<std::int64_t>{max_items};
  if (!indent || *indent < 0 || *indent > 8 || !depth || *depth < 0 || (pretty && *depth > 8) ||
      !bound || *bound < 0) {
    return runtime.fail("invalid formatting limits");
  }
  DataWriter writer(runtime, *indent, *depth, std::min<std::int64_t>(*bound, max_items), pretty);
  return writer.write(args[0]) ? runtime.hold({std::move(writer.result)}) : nullptr;
}

} // namespace

bool is_builtin(llvm::StringRef name) { return signature(name).kind != Filter::Unknown; }

const Value* call_builtin(Values& runtime, llvm::StringRef name, llvm::ArrayRef<Value> positional,
                          const Record& keywords) {
  const auto spec = signature(name);
  if (spec.kind == Filter::Unknown)
    return runtime.fail(llvm::Twine("undefined callable '") + name + "'");
  auto args = bind(runtime, spec, positional, keywords);
  if (!args)
    return nullptr;

  switch (spec.kind) {
  case Filter::Range:
    return range(runtime, *args);
  case Filter::Length: {
    const auto& value = (*args)[0];
    std::size_t size;
    if (const auto* text = as<std::string>(value)) {
      size = llvm::count_if(*text, [](unsigned char byte) { return (byte & 0xc0) != 0x80; });
    } else if (const auto* sequence = object<Sequence>(value)) {
      size = sequence->items.size();
    } else if (const auto* mapping = object<Record>(value)) {
      size = mapping->keys.size();
    } else if (const auto native_size = semantic_length(value)) {
      size = *native_size;
    } else {
      return runtime.fail("len requires a sized value");
    }
    if (size > max_items)
      return runtime.fail("len result exceeds item limit");
    return runtime.hold({static_cast<std::int64_t>(size)});
  }
  case Filter::Keys:
  case Filter::Values:
  case Filter::Entries:
  case Filter::Pick:
    return mapping(runtime, spec.kind, *args);
  case Filter::Zip:
  case Filter::ZipLongest:
    return zip(runtime, *args, spec.kind == Filter::ZipLongest);
  case Filter::Json:
  case Filter::Pretty:
  case Filter::Table:
    return formatting(runtime, spec.kind, *args);
  default:
    if (spec.kind == Filter::Split ||
        (spec.kind >= Filter::Upper && spec.kind <= Filter::Contains)) {
      return string_filter(runtime, spec.kind, *args);
    }
    return collection(runtime, spec.kind, *args);
  }
}

} // namespace ctk::jit
