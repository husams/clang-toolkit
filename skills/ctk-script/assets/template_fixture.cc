namespace demo {
struct Root {};
template <class T, int N = 3> struct Box : Root {
  T value;
  void work() {}
};
template <class T> struct Box<T *, 3> : Root {
  T *pointer;
};
template <> struct Box<double, 3> : Root {
  double exact;
};
struct Leaf : Box<int, 3> {};
struct PartialLeaf : Box<int *, 3> {};
struct FullLeaf : Box<double, 3> {};
Box<int, 7> other;
template <class... Ts> struct Pack {};
Pack<int, double> pack;
template <template <class...> class Container> struct Wrapper {};
struct Ordinary {};
} // namespace demo
namespace first {
struct Duplicate {};
} // namespace first
namespace second {
struct Duplicate {};
} // namespace second
