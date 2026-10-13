namespace demo {
struct Root;
struct Root {
    int value;
    virtual int run(int x = 1) const = 0;
protected:
    mutable int state;
    virtual void hook() {}
private:
    unsigned bits : 3;
    void privateMethod() {}
};
struct Left : virtual public Root { int left; };
using LeftAlias = Left;
class Right : protected Root {
public:
    static int count;
    int run(int x) const override { return x; }
private:
    int secret;
};
class Leaf : public LeftAlias, private Right {
public:
    Leaf() = default;
    virtual ~Leaf() = default;
    int run(int x) const override { auto inner = [](int nested = 2) { return nested; }; return x + inner(); }
    int run(double x) { return int(x); }
    static void utility() {}
    explicit operator bool() const { return true; }
    template<class T> T identity(T value) { return value; }
protected:
    int shield;
private:
    mutable int hidden;
    struct Nested { int nested; void inside() {} };
};
struct Solo { int item; void bump() { ++item; } };
template<class Base> struct Dependent : Base { int own; };
Solo makeSolo() { Solo value; return value; }
void sink(int) {}
int work(int argument = 2) { sink(argument); return argument; }
}
namespace other { struct Solo {}; }
