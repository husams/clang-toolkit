namespace navigation_demo {

int scale(int value, int multiplier) {
    return value * multiplier;
}

class Calculator {
public:
    explicit Calculator(int limit) : limit_(limit) {
    }

    int evaluate(int value) const {
        int bounded = value;
        if (bounded > limit_) {
            bounded = limit_;
        }

        // The call and multiplication occupy only part of this source line.
        const int result = 7 + scale(bounded, 3) * 2;
        return result - 1;
    }

private:
    int limit_;
};

int compute_total(int count) {
    Calculator calculator(25);
    int total = 0;
    for (int index = 0; index < count; ++index) {
        total += calculator.evaluate(index + 4);
    }
    return total;
}

} // namespace navigation_demo
