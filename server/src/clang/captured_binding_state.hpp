#pragma once

#include "ctk/clang/matching.hpp"
#include <clang/AST/ASTTypeTraits.h>
#include <unordered_map>

namespace ctk::clang_layer {
class CapturedBindingState final : public NativeBindingState {
public:
  using Row = std::unordered_map<std::string, clang::DynTypedNode>;
  explicit CapturedBindingState(ctk::cache::SnapshotPtr snapshot)
      : snapshot_(std::move(snapshot)) {}
  ctk::cache::SnapshotPtr snapshot() const override { return snapshot_; }
  std::size_t retained_bytes() const override { return retained_bytes_; }
  static std::size_t row_bytes(const Row &row) {
    std::size_t bytes = sizeof(Row);
    for (const auto &[name, node] : row)
      bytes += sizeof(node) + name.size() + 64;
    return bytes;
  }
  void append(Row row) {
    retained_bytes_ += row_bytes(row);
    rows.push_back(std::move(row));
  }
  void append(Row row, Row parents) {
    append(std::move(row));
    retained_bytes_ += row_bytes(parents);
    navigation_parents.push_back(std::move(parents));
  }
  std::vector<Row> rows;
  std::vector<Row> navigation_parents;

private:
  ctk::cache::SnapshotPtr snapshot_;
  std::size_t retained_bytes_{};
};
} // namespace ctk::clang_layer
