int firstTarget(int value) { return value + 1; }
int secondTarget(int value) { return value * 2; }

int firstCaller() { return firstTarget(1); }
int secondCaller() { return secondTarget(2); }
