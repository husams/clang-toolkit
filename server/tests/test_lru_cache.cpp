#include "ctk/cache/lru_cache.hpp"

#include <gtest/gtest.h>

#include <string>

TEST(LruCache, EvictsLeastRecentlyUsed) {
  ctk::cache::LruCache<std::string, int> cache(2);
  cache.put("a", 1);
  cache.put("b", 2);
  ASSERT_EQ(cache.get("a"), 1);
  cache.put("c", 3);
  EXPECT_FALSE(cache.get("b").has_value());
  EXPECT_EQ(cache.get("a"), 1);
  EXPECT_EQ(cache.get("c"), 3);
}
