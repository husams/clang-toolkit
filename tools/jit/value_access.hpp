#pragma once

#include "values.hpp"

#include <utility>

namespace ctk::jit::value_access {

constexpr std::size_t max_items = 10000;

template <typename T> const T* as(const Value& value) { return std::get_if<T>(&value.data); }

template <typename T> T* object(const Value& value) {
  const auto* handle = as<std::shared_ptr<T>>(value);
  return handle ? handle->get() : nullptr;
}

inline Value list(std::vector<Value> items = {}, bool tuple = false) {
  return {std::make_shared<Sequence>(Sequence{std::move(items), tuple})};
}

inline Value record() { return {std::make_shared<Record>()}; }

} // namespace ctk::jit::value_access
