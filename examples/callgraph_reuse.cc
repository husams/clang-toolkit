namespace demo {
void chargeCard() {}
void saveOrder() {}
void sendReceipt() {}

void checkout() {
  chargeCard();
  saveOrder();
  sendReceipt();
}

void apiRequest() { checkout(); }
void retryPayment() { chargeCard(); }
void indirect(void (*payment)()) { payment(); }
} // namespace demo
