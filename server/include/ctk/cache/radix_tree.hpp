#pragma once

#include <algorithm>
#include <cassert>
#include <concepts>
#include <cstddef>
#include <iterator>
#include <memory>
#include <ranges>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace ctk::cache {

// An owning compressed byte radix tree. A complete key is represented only by
// a terminal node; edge labels concatenate to the key, and non-root labels are
// nonempty. Children are unique and sorted by the unsigned first label byte.
// The tree has no internal synchronization: callers must serialize access.
// Any structural mutation invalidates all iterators and prefix ranges. Values
// live behind unique_ptr so splitting, pruning, and compression keep T stable.
template <class T> class RadixTree {
public:
  using value_type = std::pair<const std::string, T>;
  using size_type = std::size_t;
  using difference_type = std::ptrdiff_t;
  using reference = value_type &;
  using const_reference = const value_type &;

private:
  struct Node {
    explicit Node(std::string edge = {}) : label(std::move(edge)) {}

    std::string label;
    std::vector<std::unique_ptr<Node>> children;
    std::unique_ptr<value_type> value;
    Node *parent = nullptr;
  };

  static unsigned char first_byte(const Node &node) noexcept {
    return static_cast<unsigned char>(node.label.front());
  }

  static size_type common_prefix(std::string_view lhs,
                                 std::string_view rhs) noexcept {
    const size_type limit = std::min(lhs.size(), rhs.size());
    size_type i = 0;
    while (i < limit && static_cast<unsigned char>(lhs[i]) ==
                            static_cast<unsigned char>(rhs[i])) {
      ++i;
    }
    return i;
  }

  static auto child_position(Node &node, unsigned char byte) noexcept {
    return std::lower_bound(
        node.children.begin(), node.children.end(), byte,
        [](const std::unique_ptr<Node> &child, unsigned char sought) {
          return first_byte(*child) < sought;
        });
  }

  static auto child_position(const Node &node, unsigned char byte) noexcept {
    return std::lower_bound(
        node.children.begin(), node.children.end(), byte,
        [](const std::unique_ptr<Node> &child, unsigned char sought) {
          return first_byte(*child) < sought;
        });
  }

  template <bool IsConst> class basic_iterator {
    using node_pointer = std::conditional_t<IsConst, const Node *, Node *>;
    using tree_pointer =
        std::conditional_t<IsConst, const RadixTree *, RadixTree *>;

  public:
    using iterator_category = std::forward_iterator_tag;
    using iterator_concept = std::forward_iterator_tag;
    using value_type = RadixTree::value_type;
    using difference_type = RadixTree::difference_type;
    using reference =
        std::conditional_t<IsConst, const value_type &, value_type &>;
    using pointer =
        std::conditional_t<IsConst, const value_type *, value_type *>;

    basic_iterator() = default;

    template <bool OtherConst>
      requires(IsConst && !OtherConst)
    basic_iterator(const basic_iterator<OtherConst> &other)
        : tree_(other.tree_), current_(other.current_),
          boundary_(other.boundary_) {}

    reference operator*() const {
      assert(current_ != nullptr);
      return *current_->value;
    }
    pointer operator->() const { return std::addressof(operator*()); }

    basic_iterator &operator++() {
      if (current_ == nullptr)
        return *this;
      node_pointer next = current_->children.empty()
                              ? next_sibling_subtree(current_, boundary_)
                              : current_->children.front().get();
      current_ = first_terminal(next, boundary_);
      return *this;
    }
    basic_iterator operator++(int) {
      basic_iterator copy = *this;
      ++*this;
      return copy;
    }

    template <bool OtherConst>
    friend bool operator==(const basic_iterator &lhs,
                           const basic_iterator<OtherConst> &rhs) noexcept {
      // Equal iterators must have equal successors. A prefix's subtree end
      // differs from the full-tree successor even at the same terminal node.
      return lhs.tree_ == rhs.tree_ && lhs.current_ == rhs.current_ &&
             lhs.boundary_ == rhs.boundary_;
    }

  private:
    friend class RadixTree;
    template <bool> friend class basic_iterator;

    basic_iterator(tree_pointer tree, node_pointer start, node_pointer boundary)
        : tree_(tree), current_(first_terminal(start, boundary)),
          boundary_(boundary) {}

    basic_iterator(tree_pointer tree, node_pointer exact, node_pointer boundary,
                   std::nullptr_t)
        : tree_(tree), current_(exact), boundary_(boundary) {}

    static node_pointer first_terminal(node_pointer node,
                                       node_pointer boundary) noexcept {
      while (node != nullptr) {
        if (node->value)
          return node;
        if (!node->children.empty()) {
          node = node->children.front().get();
          continue;
        }
        while (node != boundary) {
          node_pointer parent = node->parent;
          auto position = std::find_if(
              parent->children.begin(), parent->children.end(),
              [node](const auto &child) { return child.get() == node; });
          ++position;
          if (position != parent->children.end()) {
            node = position->get();
            break;
          }
          node = parent;
        }
        if (node == boundary)
          return nullptr;
      }
      return nullptr;
    }

    static node_pointer next_sibling_subtree(node_pointer node,
                                             node_pointer boundary) noexcept {
      while (node != boundary) {
        node_pointer parent = node->parent;
        auto position = std::find_if(
            parent->children.begin(), parent->children.end(),
            [node](const auto &child) { return child.get() == node; });
        ++position;
        if (position != parent->children.end())
          return position->get();
        node = parent;
      }
      return nullptr;
    }

    tree_pointer tree_ = nullptr;
    node_pointer current_ = nullptr;
    node_pointer boundary_ = nullptr;
  };

  // Prefix ranges are lightweight, non-owning views; they require the tree to
  // outlive iteration and are invalidated by any structural mutation.
  template <bool IsConst>
  class basic_prefix_range
      : public std::ranges::view_interface<basic_prefix_range<IsConst>> {
    using tree_pointer =
        std::conditional_t<IsConst, const RadixTree *, RadixTree *>;
    using node_pointer = std::conditional_t<IsConst, const Node *, Node *>;

  public:
    using iterator = basic_iterator<IsConst>;

    basic_prefix_range() = default;
    iterator begin() const { return iterator(tree_, start_, start_); }
    iterator end() const { return iterator(tree_, nullptr, start_, nullptr); }
    iterator cbegin() const { return begin(); }
    iterator cend() const { return end(); }
    [[nodiscard]] bool empty() const { return begin() == end(); }

  private:
    friend class RadixTree;
    basic_prefix_range(tree_pointer tree, node_pointer start)
        : tree_(tree), start_(start) {}
    tree_pointer tree_ = nullptr;
    node_pointer start_ = nullptr;
  };

public:
  using iterator = basic_iterator<false>;
  using const_iterator = basic_iterator<true>;
  using prefix_range = basic_prefix_range<false>;
  using const_prefix_range = basic_prefix_range<true>;

  RadixTree() = default;
  RadixTree(const RadixTree &) = delete;
  RadixTree &operator=(const RadixTree &) = delete;
  // Moving transfers node and payload ownership without moving T. Iterators
  // into either tree are invalidated because the embedded root changes owner.
  RadixTree(RadixTree &&other) noexcept { take_from(other); }
  RadixTree &operator=(RadixTree &&other) noexcept {
    if (this != &other) {
      clear();
      take_from(other);
    }
    return *this;
  }

  [[nodiscard]] bool empty() const noexcept { return size_ == 0; }
  [[nodiscard]] size_type size() const noexcept { return size_; }

  iterator begin() { return iterator(this, &root_, &root_); }
  iterator end() noexcept { return iterator(this, nullptr, &root_, nullptr); }
  const_iterator begin() const { return const_iterator(this, &root_, &root_); }
  const_iterator end() const noexcept {
    return const_iterator(this, nullptr, &root_, nullptr);
  }
  const_iterator cbegin() const { return begin(); }
  const_iterator cend() const noexcept { return end(); }

  iterator find(std::string_view key) {
    Node *node = find_node(key);
    return node != nullptr && node->value
               ? iterator(this, node, &root_, nullptr)
               : end();
  }
  const_iterator find(std::string_view key) const {
    const Node *node = find_node(key);
    return node != nullptr && node->value
               ? const_iterator(this, node, &root_, nullptr)
               : end();
  }
  [[nodiscard]] bool contains(std::string_view key) const {
    const Node *node = find_node(key);
    return node != nullptr && static_cast<bool>(node->value);
  }

  template <class... Args>
    requires std::constructible_from<T, Args...>
  std::pair<iterator, bool> try_emplace(std::string key, Args &&...args) {
    Node *parent = &root_;
    std::string_view remaining(key);
    while (true) {
      if (remaining.empty()) {
        if (parent->value)
          return {iterator(this, parent, &root_, nullptr), false};
        auto value = std::make_unique<value_type>(
            std::piecewise_construct, std::forward_as_tuple(std::move(key)),
            std::forward_as_tuple(std::forward<Args>(args)...));
        iterator result(this, parent, &root_, nullptr);
        parent->value = std::move(value);
        ++size_;
        return {std::move(result), true};
      }

      auto position = child_position(
          *parent, static_cast<unsigned char>(remaining.front()));
      if (position == parent->children.end() ||
          first_byte(**position) !=
              static_cast<unsigned char>(remaining.front())) {
        // Construct the complete branch, including T, before linking it.
        auto branch = std::make_unique<Node>(std::string(remaining));
        branch->value = std::make_unique<value_type>(
            std::piecewise_construct, std::forward_as_tuple(std::move(key)),
            std::forward_as_tuple(std::forward<Args>(args)...));
        iterator result(this, branch.get(), &root_, nullptr);
        const size_type index =
            static_cast<size_type>(position - parent->children.begin());
        branch->parent = parent;
        parent->children.reserve(parent->children.size() + 1);
        parent->children.insert(parent->children.begin() +
                                    static_cast<difference_type>(index),
                                std::move(branch));
        ++size_;
        return {std::move(result), true};
      }

      Node *child = position->get();
      const size_type shared = common_prefix(child->label, remaining);
      if (shared == child->label.size()) {
        remaining.remove_prefix(shared);
        parent = child;
        continue;
      }

      // A split is assembled off-tree. Only after every potentially throwing
      // allocation and T construction succeeds do noexcept pointer/string swaps
      // publish the new branch; the existing child and its value stay in place.
      std::string common = child->label.substr(0, shared);
      std::string shortened = child->label.substr(shared);
      std::string new_suffix(remaining.substr(shared));
      auto middle = std::make_unique<Node>(std::move(common));
      const bool key_ends_at_middle = new_suffix.empty();
      std::unique_ptr<Node> new_branch;
      Node *inserted = nullptr;
      std::unique_ptr<value_type> new_value = std::make_unique<value_type>(
          std::piecewise_construct, std::forward_as_tuple(std::move(key)),
          std::forward_as_tuple(std::forward<Args>(args)...));
      if (!key_ends_at_middle) {
        new_branch = std::make_unique<Node>(std::move(new_suffix));
        new_branch->value = std::move(new_value);
        inserted = new_branch.get();
      } else {
        middle->value = std::move(new_value);
        inserted = middle.get();
      }
      middle->children.reserve(key_ends_at_middle ? 1 : 2);

      // All throwing work is complete. The old Node itself remains at the same
      // address; only its edge label changes, so references to its T stay
      // valid.
      const size_type index =
          static_cast<size_type>(position - parent->children.begin());
      iterator result(this, inserted, &root_, nullptr);
      middle->parent = parent;
      if (new_branch)
        new_branch->parent = middle.get();
      child->label.swap(shortened);
      auto old_child = std::move(parent->children[index]);
      old_child->parent = middle.get();
      if (new_branch && first_byte(*new_branch) < first_byte(*old_child)) {
        middle->children.push_back(std::move(new_branch));
        middle->children.push_back(std::move(old_child));
      } else {
        middle->children.push_back(std::move(old_child));
        if (new_branch)
          middle->children.push_back(std::move(new_branch));
      }
      parent->children[index] = std::move(middle);
      ++size_;
      return {std::move(result), true};
    }
  }

  size_type erase(std::string_view key) {
    std::vector<Node *> path{&root_};
    Node *node = &root_;
    std::string_view remaining(key);
    while (!remaining.empty()) {
      auto position =
          child_position(*node, static_cast<unsigned char>(remaining.front()));
      if (position == node->children.end() ||
          first_byte(**position) !=
              static_cast<unsigned char>(remaining.front()))
        return 0;
      Node *child = position->get();
      if (remaining.size() < child->label.size() ||
          remaining.substr(0, child->label.size()) != child->label)
        return 0;
      remaining.remove_prefix(child->label.size());
      node = child;
      path.push_back(node);
    }
    if (!node->value)
      return 0;

    // Precompute every concatenated edge that deletion can create. Allocation
    // failure here leaves the tree and its payload untouched.
    std::vector<std::pair<Node *, std::string>> joins;
    bool path_child_will_be_removed = false;
    for (size_type i = path.size(); i > 1; --i) {
      Node *current = path[i - 1];
      const bool is_target = current == node;
      const size_type child_count =
          current->children.size() - (path_child_will_be_removed ? 1U : 0U);
      const bool has_value_after_erase = current->value && !is_target;
      if (!has_value_after_erase && child_count == 1) {
        Node *only_child = nullptr;
        if (!path_child_will_be_removed) {
          only_child = current->children.front().get();
        } else {
          Node *removed = path[i];
          for (const auto &child : current->children) {
            if (child.get() != removed) {
              only_child = child.get();
              break;
            }
          }
        }
        assert(only_child != nullptr);
        std::string joined = current->label;
        joined += only_child->label;
        joins.emplace_back(current, std::move(joined));
        break;
      }
      path_child_will_be_removed = !has_value_after_erase && child_count == 0;
      if (!path_child_will_be_removed)
        break;
    }

    node->value.reset();
    --size_;
    for (size_type i = path.size(); i > 1; --i) {
      Node *current = path[i - 1];
      Node *parent = path[i - 2];
      auto position = std::find_if(
          parent->children.begin(), parent->children.end(),
          [current](const auto &child) { return child.get() == current; });
      if (!current->value && current->children.empty()) {
        parent->children.erase(position);
        continue;
      }
      if (!current->value && current->children.size() == 1) {
        auto join = std::find_if(
            joins.begin(), joins.end(),
            [current](const auto &item) { return item.first == current; });
        assert(join != joins.end());
        auto child_owner = std::move(current->children.front());
        current->children.clear();
        Node &child = *child_owner;
        current->label.swap(join->second);
        current->value = std::move(child.value);
        current->children = std::move(child.children);
        for (const auto &grandchild : current->children)
          grandchild->parent = current;
      }
      break;
    }
    return 1;
  }

  void clear() noexcept {
    root_.children.clear();
    root_.value.reset();
    size_ = 0;
  }

  prefix_range prefix(std::string_view sought) {
    return prefix_range(this, prefix_node(sought));
  }
  const_prefix_range prefix(std::string_view sought) const {
    return const_prefix_range(this, prefix_node(sought));
  }

private:
  void take_from(RadixTree &other) noexcept {
    root_.children = std::move(other.root_.children);
    root_.value = std::move(other.root_.value);
    size_ = std::exchange(other.size_, 0);
    for (const auto &child : root_.children)
      child->parent = &root_;
  }

  Node *find_node(std::string_view key) noexcept {
    Node *node = &root_;
    while (!key.empty()) {
      auto position =
          child_position(*node, static_cast<unsigned char>(key.front()));
      if (position == node->children.end() ||
          first_byte(**position) != static_cast<unsigned char>(key.front()))
        return nullptr;
      Node *child = position->get();
      if (key.size() < child->label.size() ||
          key.substr(0, child->label.size()) != child->label)
        return nullptr;
      key.remove_prefix(child->label.size());
      node = child;
    }
    return node;
  }
  const Node *find_node(std::string_view key) const noexcept {
    const Node *node = &root_;
    while (!key.empty()) {
      auto position =
          child_position(*node, static_cast<unsigned char>(key.front()));
      if (position == node->children.end() ||
          first_byte(**position) != static_cast<unsigned char>(key.front()))
        return nullptr;
      const Node *child = position->get();
      if (key.size() < child->label.size() ||
          key.substr(0, child->label.size()) != child->label)
        return nullptr;
      key.remove_prefix(child->label.size());
      node = child;
    }
    return node;
  }
  Node *prefix_node(std::string_view sought) noexcept {
    Node *node = &root_;
    while (!sought.empty()) {
      auto position =
          child_position(*node, static_cast<unsigned char>(sought.front()));
      if (position == node->children.end() ||
          first_byte(**position) != static_cast<unsigned char>(sought.front()))
        return nullptr;
      Node *child = position->get();
      const size_type shared = common_prefix(child->label, sought);
      if (shared == sought.size())
        return child; // Prefix stops inside this edge.
      if (shared != child->label.size())
        return nullptr;
      sought.remove_prefix(shared);
      node = child;
    }
    return node;
  }
  const Node *prefix_node(std::string_view sought) const noexcept {
    const Node *node = &root_;
    while (!sought.empty()) {
      auto position =
          child_position(*node, static_cast<unsigned char>(sought.front()));
      if (position == node->children.end() ||
          first_byte(**position) != static_cast<unsigned char>(sought.front()))
        return nullptr;
      const Node *child = position->get();
      const size_type shared = common_prefix(child->label, sought);
      if (shared == sought.size())
        return child;
      if (shared != child->label.size())
        return nullptr;
      sought.remove_prefix(shared);
      node = child;
    }
    return node;
  }

  Node root_;
  size_type size_ = 0;
};

} // namespace ctk::cache
