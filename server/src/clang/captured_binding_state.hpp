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
  void append(Row row) {
    retained_bytes_ += sizeof(Row);
    for (const auto &[name, node] : row)
      retained_bytes_ += sizeof(node) + name.size() + 64;
    rows.push_back(std::move(row));
  }
  std::vector<Row> rows;

private:
  ctk::cache::SnapshotPtr snapshot_;
  std::size_t retained_bytes_{};
};
} // namespace ctk::clang_layer
