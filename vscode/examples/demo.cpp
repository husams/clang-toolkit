namespace demo {
struct Order {
  int quantity;
  bool valid() const { return quantity > 0; }
};
Order createOrder(int quantity) { return Order{quantity}; }
Order currentOrder{3};
}
