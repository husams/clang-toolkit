#pragma once

struct MyTest {
  int value;
};

template <class T> struct TemplateType {
  T saved{};
  void add(T value) { saved = value; }
};
