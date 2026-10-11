namespace navigation_demo {

int adjust(int value) {
    return value + 5;
}

class Pipeline {
public:
    int run(int first, int last) const {
        int total = 0;
        for (int value = first; value < last; ++value) {
            const int item = 10 + adjust(value) * (value + 2);
            if (item > 20) {
                total += item;
            }
        }
        return total;
    }
};

int run_pipeline() {
    Pipeline pipeline;
    const int result = pipeline.run(1, 8);
    return result;
}

} // namespace navigation_demo
