int score(int rounds) {
    int total = 0;
    for (int i = 0; i < rounds; ++i) {
        if (i % 2 == 0) {
            total += 2;
        } else {
            total += 1;
        }
        if (total > 10) {
            total = 10;
        }
    }
    return total;
}
