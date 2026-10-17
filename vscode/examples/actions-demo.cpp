namespace demo {
struct Order {
  int quantity;
  bool valid() const { return quantity > 0; }
};

int adjust(int quantity) { return quantity + 1; }
int processOrder(int quantity) { return adjust(quantity); }
Order createOrder(int quantity) { return Order{quantity}; }
}
