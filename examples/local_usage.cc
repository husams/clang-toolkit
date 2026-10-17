void use(int);

void example(bool ready) {
    int x;
    if (ready) x = 10;
    use(x);
    x = 20;
    x = 30;
    use(x);
}
