#pragma once

#include <llvm/ADT/STLFunctionalExtras.h>
#include <llvm/Support/Error.h>

namespace ctk::jit {

void install_repl_cancellation();
void request_repl_cancellation();
void clear_repl_cancellation();
bool repl_cancelled();
bool interactive_terminal();
llvm::Error with_prompt_interrupts(llvm::function_ref<llvm::Error()> run);

} // namespace ctk::jit
