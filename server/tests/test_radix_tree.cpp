#include "ctk/cache/radix_tree.hpp"

#include <algorithm>
#include <concepts>
#include <cstdint>
#include <map>
#include <memory>
#include <random>
#include <ranges>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#include <gtest/gtest.h>

namespace ctk::cache {
namespace {

struct UnsignedLess {
  bool operator()(std::string_view lhs, std::string_view rhs) const noexcept {
    return std::lexicographical_compare(
        lhs.begin(), lhs.end(), rhs.begin(), rhs.end(), [](char a, char b) {
          return static_cast<unsigned char>(a) < static_cast<unsigned char>(b);
        });
  }
};

struct NonSortable {
  explicit NonSortable(int n) : value(n) {}
  int value;
};

struct MaybeThrow {
  explicit MaybeThrow(int n) : value(n) {
    if (throw_on_construction)
      throw 17;
  }
  int value;
  static inline bool throw_on_construction = false;
};

using Tree = RadixTree<NonSortable>;
static_assert(std::forward_iterator<Tree::iterator>);
static_assert(std::forward_iterator<Tree::const_iterator>);
static_assert(std::ranges::forward_range<Tree>);
static_assert(std::ranges::forward_range<const Tree>);
static_assert(std::ranges::common_range<Tree>);
static_assert(std::ranges::common_range<const Tree>);
static_assert(std::ranges::sized_range<Tree>);
static_assert(std::ranges::sized_range<const Tree>);
static_assert(std::ranges::forward_range<Tree::prefix_range>);
static_assert(std::ranges::common_range<Tree::prefix_range>);
static_assert(std::ranges::view<Tree::prefix_range>);
static_assert(std::ranges::forward_range<Tree::const_prefix_range>);
static_assert(!std::random_access_iterator<Tree::iterator>);
static_assert(!std::permutable<Tree::iterator>);
static_assert(!std::sortable<Tree::iterator>);
static_assert(std::same_as<decltype((std::declval<Tree::iterator>()->first)),
                           const std::string &>);

TEST(RadixTreeTest, EmptyKeysAndTerminalNodesWithChildren) {
  Tree tree;
  EXPECT_TRUE(tree.empty());
  EXPECT_EQ(tree.begin(), tree.end());

  auto [empty, inserted_empty] = tree.try_emplace("", 0);
  auto [parent, inserted_parent] = tree.try_emplace("unit", 1);
  auto [child, inserted_child] = tree.try_emplace("unittest", 2);
  EXPECT_TRUE(inserted_empty);
  EXPECT_TRUE(inserted_parent);
  EXPECT_TRUE(inserted_child);
  EXPECT_EQ(empty->second.value, 0);
  EXPECT_EQ(parent->second.value, 1);
  EXPECT_EQ(child->second.value, 2);
  EXPECT_EQ(tree.size(), 3U);

  auto [same, inserted_again] = tree.try_emplace("unit", 99);
  EXPECT_FALSE(inserted_again);
  EXPECT_EQ(same->second.value, 1);
  EXPECT_EQ(tree.find("unit")->first, "unit");
  EXPECT_TRUE(tree.contains(""));
  EXPECT_FALSE(tree.contains("units"));
  EXPECT_EQ(tree.find("unitt"), tree.end());
}

TEST(RadixTreeTest, ConstAndMutableIteratorsCompareAcrossTypes) {
  Tree tree;
  tree.try_emplace("first", 1);
  tree.try_emplace("second", 2);
  const Tree &constant = tree;

  auto mutable_it = tree.begin();
  auto const_it = constant.cbegin();
  EXPECT_EQ(mutable_it, const_it);
  EXPECT_EQ(const_it, mutable_it);
  ++mutable_it;
  ++const_it;
  EXPECT_EQ(mutable_it, const_it);
  EXPECT_EQ(tree.end(), constant.cend());
  EXPECT_EQ(constant.cend(), tree.end());
}

TEST(RadixTreeTest, IteratorEqualityIncludesTheTraversalBoundary) {
  Tree tree;
  tree.try_emplace("a", 1);
  tree.try_emplace("ab", 2);
  tree.try_emplace("b", 3);
  auto prefix = tree.prefix("a");
  auto subset = prefix.begin();
  ++subset;
  auto whole = tree.find("ab");
  EXPECT_EQ(std::addressof(*subset), std::addressof(*whole));
  EXPECT_NE(subset, whole);
  auto equal_subset = subset;
  EXPECT_EQ(++subset, ++equal_subset);
  EXPECT_EQ(subset, prefix.end());
  EXPECT_EQ((++whole)->first, "b");
}

TEST(RadixTreeTest, SplitsOnDivergenceAndWhenNewKeyEndsInsideAnEdge) {
  Tree tree;
  tree.try_emplace("alphabet", 1);
  tree.try_emplace("alpine", 2);
  tree.try_emplace("alpha", 3);
  tree.try_emplace("al", 4);
  tree.try_emplace("altar", 5);

  EXPECT_EQ(tree.find("alphabet")->second.value, 1);
  EXPECT_EQ(tree.find("alpine")->second.value, 2);
  EXPECT_EQ(tree.find("alpha")->second.value, 3);
  EXPECT_EQ(tree.find("al")->second.value, 4);
  EXPECT_EQ(tree.find("altar")->second.value, 5);
  EXPECT_EQ(tree.size(), 5U);
}

TEST(RadixTreeTest, IterationAlgorithmsAndUnsignedByteOrdering) {
  Tree tree;
  const std::string high_byte(1, static_cast<char>(0x80));
  const std::string low_byte(1, static_cast<char>(0x01));
  tree.try_emplace("", 0);
  tree.try_emplace("b", 1);
  tree.try_emplace("a", 2);
  tree.try_emplace(high_byte, 3);
  tree.try_emplace(low_byte, 4);

  std::vector<std::string> keys;
  std::ranges::for_each(
      tree, [&keys](const auto &value) { keys.push_back(value.first); });
  EXPECT_TRUE(std::ranges::is_sorted(keys, UnsignedLess{}));
  EXPECT_EQ(keys.front(), "");
  EXPECT_EQ(keys[1], low_byte);
  EXPECT_EQ(keys.back(), high_byte);

  auto distance = std::ranges::distance(tree);
  EXPECT_EQ(distance, 5);
  auto found = std::ranges::find_if(
      tree, [](const auto &pair) { return pair.second.value == 2; });
  ASSERT_NE(found, tree.end());
  EXPECT_EQ(found->first, "a");

  auto selected =
      tree | std::views::filter([](const auto &pair) {
        return pair.second.value % 2 == 0;
      }) |
      std::views::transform([](const auto &pair) { return pair.first; });
  std::vector<std::string> filtered(selected.begin(), selected.end());
  EXPECT_EQ(filtered.size(), 3U);
}

TEST(RadixTreeTest, PrefixMayEndInsideAnEdgeAndIncludesTheExactTerminal) {
  Tree tree;
  tree.try_emplace("prefix-long", 1);
  tree.try_emplace("prefix-later", 2);
  tree.try_emplace("prefix", 3);
  tree.try_emplace("preform", 4);

  std::vector<std::string> keys;
  for (const auto &[key, value] : tree.prefix("prefix-lo")) {
    (void)value;
    keys.push_back(key);
  }
  ASSERT_EQ(keys.size(), 1U);
  EXPECT_EQ(keys.front(), "prefix-long");

  keys.clear();
  for (const auto &value : tree.prefix("prefix"))
    keys.push_back(value.first);
  EXPECT_EQ(keys, (std::vector<std::string>{"prefix", "prefix-later",
                                            "prefix-long"}));
  EXPECT_EQ(tree.prefix("missing").begin(), tree.prefix("missing").end());

  const Tree &constant = tree;
  static_assert(
      std::same_as<decltype(*constant.begin()), const Tree::value_type &>);
  auto const_range = constant.prefix("prefix");
  EXPECT_EQ(std::ranges::distance(const_range), 3);
  EXPECT_EQ(const_range.cbegin(), const_range.begin());
  EXPECT_EQ(const_range.cend(), const_range.end());
  EXPECT_FALSE(const_range.empty());
  EXPECT_TRUE(constant.prefix("absent").empty());

  auto composed =
      tree.prefix("prefix") | std::views::filter([](const auto &pair) {
        return pair.second.value != 3;
      }) |
      std::views::transform([](const auto &pair) { return pair.first; });
  EXPECT_EQ(std::vector<std::string>(composed.begin(), composed.end()),
            (std::vector<std::string>{"prefix-later", "prefix-long"}));
}

TEST(RadixTreeTest, MovingPreservesValuesAndLeavesSourceUsable) {
  Tree source;
  source.try_emplace("", 0);
  source.try_emplace("move-target", 1);
  source.try_emplace("move-other", 2);
  auto *stable_value = std::addressof(source.find("move-target")->second);

  Tree moved(std::move(source));
  EXPECT_TRUE(source.empty());
  EXPECT_EQ(source.size(), 0U);
  EXPECT_EQ(std::addressof(moved.find("move-target")->second), stable_value);
  EXPECT_EQ(std::ranges::distance(moved), 3);
  source.try_emplace("reused", 4);
  EXPECT_TRUE(source.contains("reused"));

  Tree destination;
  destination.try_emplace("old", 5);
  destination = std::move(moved);
  EXPECT_TRUE(moved.empty());
  EXPECT_FALSE(destination.contains("old"));
  EXPECT_EQ(std::addressof(destination.find("move-target")->second),
            stable_value);
  EXPECT_EQ(std::ranges::distance(destination), 3);
}

TEST(RadixTreeTest, ErasePrunesAndMergesWithoutMovingSurvivingValues) {
  Tree tree;
  tree.try_emplace("shared", 1);
  tree.try_emplace("shared-left", 2);
  tree.try_emplace("shared-right", 3);
  auto *stable_value = std::addressof(tree.find("shared-right")->second);

  EXPECT_EQ(tree.erase("shared-left"), 1U);
  EXPECT_EQ(tree.erase("shared"), 1U);
  ASSERT_NE(tree.find("shared-right"), tree.end());
  EXPECT_EQ(std::addressof(tree.find("shared-right")->second), stable_value);
  EXPECT_EQ(tree.find("shared-right")->second.value, 3);
  EXPECT_EQ(tree.erase("shared-right"), 1U);
  EXPECT_TRUE(tree.empty());
  EXPECT_EQ(tree.erase("shared-right"), 0U);
}

TEST(RadixTreeTest, PrefixAndIterationFollowUnsignedOrdering) {
  Tree tree;
  std::string key_a(1, static_cast<char>(0x7f));
  std::string key_b(1, static_cast<char>(0x80));
  tree.try_emplace(key_b, 2);
  tree.try_emplace(key_a, 1);
  auto it = tree.begin();
  ASSERT_NE(it, tree.end());
  EXPECT_EQ(it->first, key_a);
  ++it;
  ASSERT_NE(it, tree.end());
  EXPECT_EQ(it->first, key_b);
}

TEST(RadixTreeTest, ThrowingValueConstructionLeavesTreeUnchanged) {
  RadixTree<MaybeThrow> tree;
  tree.try_emplace("existing-key", 1);
  const auto original_size = tree.size();

  MaybeThrow::throw_on_construction = true;
  EXPECT_THROW(tree.try_emplace("existing-new-branch", 2), int);
  EXPECT_THROW(tree.try_emplace("existing", 3), int);
  MaybeThrow::throw_on_construction = false;

  EXPECT_EQ(tree.size(), original_size);
  EXPECT_TRUE(tree.contains("existing-key"));
  EXPECT_FALSE(tree.contains("existing-new-branch"));
  EXPECT_FALSE(tree.contains("existing"));
}

TEST(RadixTreeTest, RandomizedOperationsMatchAnUnsignedOrderedMap) {
  RadixTree<int> tree;
  std::map<std::string, int, UnsignedLess> model;
  std::mt19937 random(0xC7A5U);
  std::uniform_int_distribution<int> operation(0, 2);
  std::uniform_int_distribution<int> length(0, 9);
  std::uniform_int_distribution<int> byte(0, 5);

  for (int step = 0; step < 1500; ++step) {
    std::string key;
    for (int i = 0, n = length(random); i < n; ++i) {
      key.push_back(
          static_cast<char>(byte(random) == 5 ? 0x80 : 'a' + byte(random)));
    }
    switch (operation(random)) {
    case 0: {
      const int value = step;
      const bool inserted = model.emplace(key, value).second;
      auto result = tree.try_emplace(key, value);
      EXPECT_EQ(result.second, inserted);
      break;
    }
    case 1:
      EXPECT_EQ(tree.erase(key), model.erase(key));
      break;
    default:
      EXPECT_EQ(tree.contains(key), model.contains(key));
      break;
    }

    ASSERT_EQ(tree.size(), model.size());
    auto actual = tree.begin();
    for (const auto &[expected_key, expected_value] : model) {
      ASSERT_NE(actual, tree.end());
      EXPECT_EQ(actual->first, expected_key);
      EXPECT_EQ(actual->second, expected_value);
      ++actual;
    }
    EXPECT_EQ(actual, tree.end());
  }
}

} // namespace
} // namespace ctk::cache
