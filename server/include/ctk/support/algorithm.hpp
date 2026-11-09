#pragma once

#include <algorithm>
#include <functional>
#include <iterator>
#include <string_view>
#include <vector>

namespace ctk::compat {

inline bool starts_with(std::string_view text, std::string_view prefix) {
  return text.substr(0, prefix.size()) == prefix;
}

inline bool starts_with(std::string_view text, char prefix) {
  return !text.empty() && text.front() == prefix;
}

inline bool ends_with(std::string_view text, std::string_view suffix) {
  return text.size() >= suffix.size() && text.substr(text.size() - suffix.size()) == suffix;
}

inline bool ends_with(std::string_view text, char suffix) {
  return !text.empty() && text.back() == suffix;
}

namespace detail {

template <class Container, class Key>
auto contains(const Container& container, const Key& key, int)
    -> decltype(container.contains(key)) {
  return container.contains(key);
}

template <class Container, class Key>
auto contains(const Container& container, const Key& key, long)
    -> decltype(container.find(key) != container.end()) {
  return container.find(key) != container.end();
}

template <class Needle>
bool contains(std::string_view text, const Needle& needle, ...) {
  return text.find(needle) != std::string_view::npos;
}

} // namespace detail

template <class Container, class Key>
bool contains(const Container& container, const Key& key) {
  return detail::contains(container, key, 0);
}

template <class T, class Allocator, class Predicate>
void erase_if(std::vector<T, Allocator>& items, Predicate predicate) {
  items.erase(std::remove_if(items.begin(), items.end(), predicate), items.end());
}

template <class T, class Allocator, class Value>
void erase(std::vector<T, Allocator>& items, const Value& value) {
  items.erase(std::remove(items.begin(), items.end(), value), items.end());
}

template <class Container, class Predicate>
void erase_if(Container& items, Predicate predicate) {
  for (auto it = items.begin(); it != items.end();) {
    if (predicate(*it)) {
      it = items.erase(it);
    } else {
      ++it;
    }
  }
}

template <class Range, class Value>
auto find(Range& items, const Value& value) {
  return std::find(std::begin(items), std::end(items), value);
}

template <class Range, class Value, class Projection>
auto find(Range& items, const Value& value, Projection project) {
  return std::find_if(std::begin(items), std::end(items),
                      [&](const auto& item) { return std::invoke(project, item) == value; });
}

template <class Range, class Predicate>
auto find_if(Range& items, Predicate predicate) {
  return std::find_if(std::begin(items), std::end(items), predicate);
}

template <class Range, class Compare = std::less<>>
void sort(Range& items, Compare compare = {}) {
  std::sort(std::begin(items), std::end(items), compare);
}

template <class Range, class Projection>
void sort(Range& items, std::less<> compare, Projection project) {
  std::sort(std::begin(items), std::end(items), [&](const auto& lhs, const auto& rhs) {
    return compare(std::invoke(project, lhs), std::invoke(project, rhs));
  });
}

template <class Range, class Argument>
auto any_of(Range&& items, Argument argument) {
  return std::any_of(std::begin(items), std::end(items), argument);
}

template <class Range, class Argument>
auto none_of(Range&& items, Argument argument) {
  return std::none_of(std::begin(items), std::end(items), argument);
}

template <class Range, class Argument>
auto count(Range&& items, Argument argument) {
  return std::count(std::begin(items), std::end(items), argument);
}

template <class Range, class Argument>
auto count_if(Range&& items, Argument argument) {
  return std::count_if(std::begin(items), std::end(items), argument);
}

template <class Range, class Argument>
auto for_each(Range&& items, Argument argument) {
  return std::for_each(std::begin(items), std::end(items), argument);
}

template <class Range, class Argument>
auto is_sorted(Range&& items, Argument argument) {
  return std::is_sorted(std::begin(items), std::end(items), argument);
}

template <class Range>
auto distance(Range&& items) {
  return std::distance(std::begin(items), std::end(items));
}

template <class Range>
void reverse(Range& items) {
  std::reverse(std::begin(items), std::end(items));
}

template <class Left, class Right, class Output>
auto set_difference(const Left& left, const Right& right, Output out) {
  return std::set_difference(std::begin(left), std::end(left), std::begin(right), std::end(right),
                             out);
}

} // namespace ctk::compat
