namespace navigation_demo {

int squared(int value) {
    return value * value;
}

class Statistics {
public:
    int sum_squares(int count) const {
        int sum = 0;
        for (int index = 0; index < count; ++index) {
            sum += squared(index + 1);
        }
        return sum;
    }

    int score(int count) const {
        const int score = 100 + sum_squares(count) / (count + 1);
        return score;
    }
};

int calculate_score() {
    Statistics statistics;
    return statistics.score(12);
}

} // namespace navigation_demo
