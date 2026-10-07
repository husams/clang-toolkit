#include "cfg_element_dispatcher.hpp"
#include "elements/cfg_automatic_obj_dtor.hpp"
#include "elements/cfg_base_dtor.hpp"
#include "elements/cfg_cleanup_function.hpp"
#include "elements/cfg_constructor.hpp"
#include "elements/cfg_cxx_record_typed_call.hpp"
#include "elements/cfg_delete_dtor.hpp"
#include "elements/cfg_initializer.hpp"
#include "elements/cfg_lifetime_ends.hpp"
#include "elements/cfg_loop_exit.hpp"
#include "elements/cfg_member_dtor.hpp"
#include "elements/cfg_new_allocator.hpp"
#include "elements/cfg_scope_begin.hpp"
#include "elements/cfg_scope_end.hpp"
#include "elements/cfg_statement.hpp"
#include "elements/cfg_temporary_dtor.hpp"
namespace ctk::clang_layer::control_flow {
void CfgElementDispatcher::serialize(const clang::CFGElement &native,
                                     ctk::analysis::v1::CfgElement &output,
                                     Context &context) {
  switch (native.getKind()) {
  case clang::CFGElement::Statement:
    CFGStmtSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::Constructor:
    CFGConstructorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::CXXRecordTypedCall:
    CFGCXXRecordTypedCallSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::Initializer:
    CFGInitializerSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::ScopeBegin:
    CFGScopeBeginSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::ScopeEnd:
    CFGScopeEndSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::LifetimeEnds:
    CFGLifetimeEndsSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::NewAllocator:
    CFGNewAllocatorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::LoopExit:
    CFGLoopExitSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::AutomaticObjectDtor:
    CFGAutomaticObjDtorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::DeleteDtor:
    CFGDeleteDtorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::BaseDtor:
    CFGBaseDtorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::MemberDtor:
    CFGMemberDtorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::TemporaryDtor:
    CFGTemporaryDtorSerializer{}.serialize(native, output, context);
    break;
  case clang::CFGElement::CleanupFunction:
    CFGCleanupFunctionSerializer{}.serialize(native, output, context);
    break;
  default:
    serialization::helpers::unavailable(
        "cfg.element.kind", "unsupported native CFG element kind", context);
    break;
  }
  finish(output, context);
}
} // namespace ctk::clang_layer::control_flow
