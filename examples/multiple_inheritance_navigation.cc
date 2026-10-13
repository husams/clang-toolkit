namespace demo {
struct Root {};
struct Left : virtual Root {};
struct Right : virtual Root {};
struct Leaf : Left, Right {};
}
