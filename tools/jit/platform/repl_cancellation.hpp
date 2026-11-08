#pragma once

namespace ctk::jit {

void install_repl_cancellation();
void clear_repl_cancellation();
bool repl_cancelled();

} // namespace ctk::jit
