#include "include/myproject/logic.hpp"
#include "vendor/trace.hpp"
#include "generated/api.hpp"
void entry() {
  project::work();
  third_party::trace();
  project::generated_call();
}
