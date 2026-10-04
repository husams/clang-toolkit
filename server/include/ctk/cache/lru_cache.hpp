#pragma once

#include <cstddef>
#include <list>
#include <optional>
#include <unordered_map>
#include <utility>

namespace ctk::cache {

// Generic value cache retained for non-path uses. SnapshotCache uses the radix
// as its sole path registry and ReusePolicy for non-owning generation tokens.
template <typename K, typename V>
class LruCache {
 public:
  explicit LruCache(std::size_t capacity) : capacity_(capacity) {}

  std::optional<V> get(const K& key) {
    auto it = index_.find(key);
    if (it == index_.end()) return std::nullopt;
    order_.splice(order_.begin(), order_, it->second);
    return it->second->second;
  }

  void put(const K& key, V value) {
    if (auto it = index_.find(key); it != index_.end()) {
      it->second->second = std::move(value);
      order_.splice(order_.begin(), order_, it->second);
      return;
    }
    if (capacity_ == 0) return;
    if (order_.size() == capacity_) {
      index_.erase(order_.back().first);
      order_.pop_back();
    }
    order_.emplace_front(key, std::move(value));
    index_[key] = order_.begin();
  }

  std::size_t size() const { return order_.size(); }

 private:
  std::size_t capacity_;
  std::list<std::pair<K, V>> order_;
  std::unordered_map<K, typename std::list<std::pair<K, V>>::iterator> index_;
};

}  // namespace ctk::cache
