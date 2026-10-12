struct Box {
  struct Inner { int hidden() { return 9; } };
  int run() { return 7; }
  int other() { return 8; }
};
