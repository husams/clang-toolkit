struct Root {
  int id;
  virtual int score(int factor) const = 0;
};

struct Middle : virtual public Root {
protected:
  double weight;
};

struct Hidden {
  int internal;
};

using MidAlias = Middle;

class Widget : public MidAlias, protected Hidden {
  int secret;
  void reset();

public:
  int count;
  static bool ready;
  bool check(int limit, const char *label) const;

protected:
  double ratio;
  void update(double value);

private:
  mutable unsigned flags;
};

enum class State : unsigned { Idle = 1, Running = 4 };
using WidgetPointer = const Widget *;

int calculate(int count, const Widget &widget, double) {
  auto scale = [](int nested) { return nested; };
  return scale(count) + widget.count;
}
