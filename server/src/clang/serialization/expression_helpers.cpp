#include "expression_helpers.hpp"
#include "semantic_helpers.hpp"
#include <google/protobuf/descriptor.h>
// Native getter contracts: Clang AST/Expr.h, AST/ExprCXX.h,
// AST/OperationKinds.def.
namespace ctk::clang_layer::serialization::helpers {
void write_expr_info(const clang::Expr &native, ctk::ast::v1::ExprInfo &payload,
                     SerializationContext &context) {
  write_type(native.getType(), *payload.mutable_type(), context);
  switch (native.getValueKind()) {
  case clang::VK_PRValue:
    payload.set_value_category(ctk::ast::v1::VALUE_CATEGORY_PRVALUE);
    break;
  case clang::VK_LValue:
    payload.set_value_category(ctk::ast::v1::VALUE_CATEGORY_LVALUE);
    break;
  case clang::VK_XValue:
    payload.set_value_category(ctk::ast::v1::VALUE_CATEGORY_XVALUE);
    break;
  }
  switch (native.getObjectKind()) {
  case clang::OK_Ordinary:
    payload.set_object_kind(ctk::ast::v1::OBJECT_KIND_ORDINARY);
    break;
  case clang::OK_BitField:
    payload.set_object_kind(ctk::ast::v1::OBJECT_KIND_BIT_FIELD);
    break;
  case clang::OK_VectorComponent:
    payload.set_object_kind(ctk::ast::v1::OBJECT_KIND_VECTOR_COMPONENT);
    break;
  case clang::OK_MatrixComponent:
    payload.set_object_kind(ctk::ast::v1::OBJECT_KIND_MATRIX_COMPONENT);
    break;
  case clang::OK_ObjCProperty:
  case clang::OK_ObjCSubscript:
    unavailable("info.object_kind",
                "Objective-C object kind has no protocol enum alternative",
                context);
    break;
  }
  payload.set_is_type_dependent(native.isTypeDependent());
  payload.set_is_value_dependent(native.isValueDependent());
  payload.set_is_instantiation_dependent(native.isInstantiationDependent());
  payload.set_contains_unexpanded_parameter_pack(
      native.containsUnexpandedParameterPack());
  payload.set_contains_errors(native.containsErrors());
}
namespace {
// Common inheritance paths are short and known; owned child messages are never
// traversed here, so adding ExprInfo cannot manufacture absent child values.
ctk::ast::v1::ExprInfo *expr_info(google::protobuf::Message &payload) {
  if (auto *info = dynamic_cast<ctk::ast::v1::ExprInfo *>(&payload))
    return info;
  for (const char *name :
       {"info", "cast", "call", "construction", "expression"}) {
    const auto *field = payload.GetDescriptor()->FindFieldByName(name);
    if (!field || field->is_repeated() ||
        field->cpp_type() != google::protobuf::FieldDescriptor::CPPTYPE_MESSAGE)
      continue;
    const auto &type = field->message_type()->name();
    if (type != "ExprInfo" && type != "CastExprInfo" &&
        type != "CallExprInfo" && type != "CXXConstructExprInfo")
      continue;
    if (auto *result = expr_info(
            *payload.GetReflection()->MutableMessage(&payload, field)))
      return result;
  }
  return nullptr;
}
ctk::ast::v1::CastKind cast_kind(clang::CastKind kind) {
  switch (kind) {
  case clang::CK_Dependent:
    return ctk::ast::v1::CAST_KIND_DEPENDENT;
  case clang::CK_BitCast:
    return ctk::ast::v1::CAST_KIND_BIT_CAST;
  case clang::CK_LValueBitCast:
    return ctk::ast::v1::CAST_KIND_L_VALUE_BIT_CAST;
  case clang::CK_LValueToRValueBitCast:
    return ctk::ast::v1::CAST_KIND_L_VALUE_TO_R_VALUE_BIT_CAST;
  case clang::CK_LValueToRValue:
    return ctk::ast::v1::CAST_KIND_L_VALUE_TO_R_VALUE;
  case clang::CK_NoOp:
    return ctk::ast::v1::CAST_KIND_NO_OP;
  case clang::CK_BaseToDerived:
    return ctk::ast::v1::CAST_KIND_BASE_TO_DERIVED;
  case clang::CK_DerivedToBase:
    return ctk::ast::v1::CAST_KIND_DERIVED_TO_BASE;
  case clang::CK_UncheckedDerivedToBase:
    return ctk::ast::v1::CAST_KIND_UNCHECKED_DERIVED_TO_BASE;
  case clang::CK_Dynamic:
    return ctk::ast::v1::CAST_KIND_DYNAMIC;
  case clang::CK_ToUnion:
    return ctk::ast::v1::CAST_KIND_TO_UNION;
  case clang::CK_ArrayToPointerDecay:
    return ctk::ast::v1::CAST_KIND_ARRAY_TO_POINTER_DECAY;
  case clang::CK_FunctionToPointerDecay:
    return ctk::ast::v1::CAST_KIND_FUNCTION_TO_POINTER_DECAY;
  case clang::CK_NullToPointer:
    return ctk::ast::v1::CAST_KIND_NULL_TO_POINTER;
  case clang::CK_NullToMemberPointer:
    return ctk::ast::v1::CAST_KIND_NULL_TO_MEMBER_POINTER;
  case clang::CK_BaseToDerivedMemberPointer:
    return ctk::ast::v1::CAST_KIND_BASE_TO_DERIVED_MEMBER_POINTER;
  case clang::CK_DerivedToBaseMemberPointer:
    return ctk::ast::v1::CAST_KIND_DERIVED_TO_BASE_MEMBER_POINTER;
  case clang::CK_MemberPointerToBoolean:
    return ctk::ast::v1::CAST_KIND_MEMBER_POINTER_TO_BOOLEAN;
  case clang::CK_ReinterpretMemberPointer:
    return ctk::ast::v1::CAST_KIND_REINTERPRET_MEMBER_POINTER;
  case clang::CK_UserDefinedConversion:
    return ctk::ast::v1::CAST_KIND_USER_DEFINED_CONVERSION;
  case clang::CK_ConstructorConversion:
    return ctk::ast::v1::CAST_KIND_CONSTRUCTOR_CONVERSION;
  case clang::CK_IntegralToPointer:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_TO_POINTER;
  case clang::CK_PointerToIntegral:
    return ctk::ast::v1::CAST_KIND_POINTER_TO_INTEGRAL;
  case clang::CK_PointerToBoolean:
    return ctk::ast::v1::CAST_KIND_POINTER_TO_BOOLEAN;
  case clang::CK_ToVoid:
    return ctk::ast::v1::CAST_KIND_TO_VOID;
  case clang::CK_MatrixCast:
    return ctk::ast::v1::CAST_KIND_MATRIX_CAST;
  case clang::CK_VectorSplat:
    return ctk::ast::v1::CAST_KIND_VECTOR_SPLAT;
  case clang::CK_IntegralCast:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_CAST;
  case clang::CK_IntegralToBoolean:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_TO_BOOLEAN;
  case clang::CK_IntegralToFloating:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_TO_FLOATING;
  case clang::CK_FloatingToFixedPoint:
    return ctk::ast::v1::CAST_KIND_FLOATING_TO_FIXED_POINT;
  case clang::CK_FixedPointToFloating:
    return ctk::ast::v1::CAST_KIND_FIXED_POINT_TO_FLOATING;
  case clang::CK_FixedPointCast:
    return ctk::ast::v1::CAST_KIND_FIXED_POINT_CAST;
  case clang::CK_FixedPointToIntegral:
    return ctk::ast::v1::CAST_KIND_FIXED_POINT_TO_INTEGRAL;
  case clang::CK_IntegralToFixedPoint:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_TO_FIXED_POINT;
  case clang::CK_FixedPointToBoolean:
    return ctk::ast::v1::CAST_KIND_FIXED_POINT_TO_BOOLEAN;
  case clang::CK_FloatingToIntegral:
    return ctk::ast::v1::CAST_KIND_FLOATING_TO_INTEGRAL;
  case clang::CK_FloatingToBoolean:
    return ctk::ast::v1::CAST_KIND_FLOATING_TO_BOOLEAN;
  case clang::CK_BooleanToSignedIntegral:
    return ctk::ast::v1::CAST_KIND_BOOLEAN_TO_SIGNED_INTEGRAL;
  case clang::CK_FloatingCast:
    return ctk::ast::v1::CAST_KIND_FLOATING_CAST;
  case clang::CK_AnyPointerToBlockPointerCast:
    return ctk::ast::v1::CAST_KIND_ANY_POINTER_TO_BLOCK_POINTER_CAST;
  case clang::CK_FloatingRealToComplex:
    return ctk::ast::v1::CAST_KIND_FLOATING_REAL_TO_COMPLEX;
  case clang::CK_FloatingComplexToReal:
    return ctk::ast::v1::CAST_KIND_FLOATING_COMPLEX_TO_REAL;
  case clang::CK_FloatingComplexToBoolean:
    return ctk::ast::v1::CAST_KIND_FLOATING_COMPLEX_TO_BOOLEAN;
  case clang::CK_FloatingComplexCast:
    return ctk::ast::v1::CAST_KIND_FLOATING_COMPLEX_CAST;
  case clang::CK_FloatingComplexToIntegralComplex:
    return ctk::ast::v1::CAST_KIND_FLOATING_COMPLEX_TO_INTEGRAL_COMPLEX;
  case clang::CK_IntegralRealToComplex:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_REAL_TO_COMPLEX;
  case clang::CK_IntegralComplexToReal:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_COMPLEX_TO_REAL;
  case clang::CK_IntegralComplexToBoolean:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_COMPLEX_TO_BOOLEAN;
  case clang::CK_IntegralComplexCast:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_COMPLEX_CAST;
  case clang::CK_IntegralComplexToFloatingComplex:
    return ctk::ast::v1::CAST_KIND_INTEGRAL_COMPLEX_TO_FLOATING_COMPLEX;
  case clang::CK_AtomicToNonAtomic:
    return ctk::ast::v1::CAST_KIND_ATOMIC_TO_NON_ATOMIC;
  case clang::CK_NonAtomicToAtomic:
    return ctk::ast::v1::CAST_KIND_NON_ATOMIC_TO_ATOMIC;
  case clang::CK_BuiltinFnToFnPtr:
    return ctk::ast::v1::CAST_KIND_BUILTIN_FN_TO_FN_PTR;
  case clang::CK_AddressSpaceConversion:
    return ctk::ast::v1::CAST_KIND_ADDRESS_SPACE_CONVERSION;
  default:
    return ctk::ast::v1::CAST_KIND_UNSPECIFIED;
  }
}
} // namespace
void write_common(const clang::Stmt &native, google::protobuf::Message &payload,
                  SerializationContext &context) {
  if (const auto *expression = llvm::dyn_cast<clang::Expr>(&native)) {
    if (auto *info = expr_info(payload))
      write_expr_info(*expression, *info, context);
  }
}
void write_call(const clang::CallExpr &native,
                ctk::ast::v1::CallExprInfo &payload,
                SerializationContext &context) {
  write_expr_info(native, *payload.mutable_expression(), context);
  if (auto *callee = native.getCallee())
    write_expr(callee, *payload.mutable_callee_expression(), context);
  if (auto *callee = native.getDirectCallee())
    write_symbol(*callee, *payload.mutable_direct_callee(), context);
  for (const auto *argument : native.arguments()) {
    if (!helpers::can_expand(payload, "arguments", context))
      break;
    write_expr(argument, *payload.add_arguments(), context);
  }
}
void write_cast(const clang::CastExpr &native,
                ctk::ast::v1::CastExprInfo &payload,
                SerializationContext &context) {
  write_expr_info(native, *payload.mutable_expression(), context);
  if (auto *operand = native.getSubExpr())
    write_expr(operand, *payload.mutable_operand(), context);
  auto kind = cast_kind(native.getCastKind());
  if (kind != ctk::ast::v1::CAST_KIND_UNSPECIFIED)
    payload.set_kind(kind);
  else
    unavailable("cast.kind",
                "Native cast kind has no protocol enum alternative", context);
  for (const auto *base : native.path()) {
    if (!helpers::can_expand(payload, "base_path", context))
      break;
    write_base(*base, *payload.add_base_path(), context);
  }
}
void write_construction(const clang::CXXConstructExpr &native,
                        ctk::ast::v1::CXXConstructExprInfo &payload,
                        SerializationContext &context) {
  write_expr_info(native, *payload.mutable_expression(), context);
  if (auto *constructor = native.getConstructor())
    write_symbol(*constructor, *payload.mutable_constructor(), context);
  for (const auto *argument : native.arguments()) {
    if (!helpers::can_expand(payload, "arguments", context))
      break;
    write_expr(argument, *payload.add_arguments(), context);
  }
  switch (native.getConstructionKind()) {
  case clang::CXXConstructionKind::Complete:
    payload.set_construction_kind(
        ctk::ast::v1::CONSTRUCTION_KIND_COMPLETE_OBJECT);
    break;
  case clang::CXXConstructionKind::NonVirtualBase:
    payload.set_construction_kind(
        ctk::ast::v1::CONSTRUCTION_KIND_NONVIRTUAL_BASE);
    break;
  case clang::CXXConstructionKind::VirtualBase:
    payload.set_construction_kind(ctk::ast::v1::CONSTRUCTION_KIND_VIRTUAL_BASE);
    break;
  case clang::CXXConstructionKind::Delegating:
    payload.set_construction_kind(ctk::ast::v1::CONSTRUCTION_KIND_DELEGATING);
    break;
  }
  payload.set_is_elidable(native.isElidable());
  payload.set_is_list_initialization(native.isListInitialization());
  payload.set_is_std_initializer_list_initialization(
      native.isStdInitListInitialization());
  payload.set_requires_zero_initialization(native.requiresZeroInitialization());
  payload.set_had_multiple_candidates(native.hadMultipleCandidates());
}
ctk::ast::v1::UnaryOpcode unary_opcode(clang::UnaryOperatorKind kind) {
  switch (kind) {
  case clang::UO_PostInc:
    return ctk::ast::v1::UNARY_OPCODE_POST_INC;
  case clang::UO_PostDec:
    return ctk::ast::v1::UNARY_OPCODE_POST_DEC;
  case clang::UO_PreInc:
    return ctk::ast::v1::UNARY_OPCODE_PRE_INC;
  case clang::UO_PreDec:
    return ctk::ast::v1::UNARY_OPCODE_PRE_DEC;
  case clang::UO_AddrOf:
    return ctk::ast::v1::UNARY_OPCODE_ADDR_OF;
  case clang::UO_Deref:
    return ctk::ast::v1::UNARY_OPCODE_DEREF;
  case clang::UO_Plus:
    return ctk::ast::v1::UNARY_OPCODE_PLUS;
  case clang::UO_Minus:
    return ctk::ast::v1::UNARY_OPCODE_MINUS;
  case clang::UO_Not:
    return ctk::ast::v1::UNARY_OPCODE_NOT;
  case clang::UO_LNot:
    return ctk::ast::v1::UNARY_OPCODE_L_NOT;
  case clang::UO_Real:
    return ctk::ast::v1::UNARY_OPCODE_REAL;
  case clang::UO_Imag:
    return ctk::ast::v1::UNARY_OPCODE_IMAG;
  case clang::UO_Extension:
    return ctk::ast::v1::UNARY_OPCODE_EXTENSION;
  case clang::UO_Coawait:
    return ctk::ast::v1::UNARY_OPCODE_COAWAIT;
  }
  return ctk::ast::v1::UNARY_OPCODE_UNSPECIFIED;
}
ctk::ast::v1::BinaryOpcode binary_opcode(clang::BinaryOperatorKind kind) {
  switch (kind) {
  case clang::BO_PtrMemD:
    return ctk::ast::v1::BINARY_OPCODE_PTR_MEM_D;
  case clang::BO_PtrMemI:
    return ctk::ast::v1::BINARY_OPCODE_PTR_MEM_I;
  case clang::BO_Mul:
    return ctk::ast::v1::BINARY_OPCODE_MUL;
  case clang::BO_Div:
    return ctk::ast::v1::BINARY_OPCODE_DIV;
  case clang::BO_Rem:
    return ctk::ast::v1::BINARY_OPCODE_REM;
  case clang::BO_Add:
    return ctk::ast::v1::BINARY_OPCODE_ADD;
  case clang::BO_Sub:
    return ctk::ast::v1::BINARY_OPCODE_SUB;
  case clang::BO_Shl:
    return ctk::ast::v1::BINARY_OPCODE_SHL;
  case clang::BO_Shr:
    return ctk::ast::v1::BINARY_OPCODE_SHR;
  case clang::BO_LT:
    return ctk::ast::v1::BINARY_OPCODE_LT;
  case clang::BO_GT:
    return ctk::ast::v1::BINARY_OPCODE_GT;
  case clang::BO_LE:
    return ctk::ast::v1::BINARY_OPCODE_LE;
  case clang::BO_GE:
    return ctk::ast::v1::BINARY_OPCODE_GE;
  case clang::BO_EQ:
    return ctk::ast::v1::BINARY_OPCODE_EQ;
  case clang::BO_NE:
    return ctk::ast::v1::BINARY_OPCODE_NE;
  case clang::BO_Cmp:
    return ctk::ast::v1::BINARY_OPCODE_CMP;
  case clang::BO_And:
    return ctk::ast::v1::BINARY_OPCODE_AND;
  case clang::BO_Xor:
    return ctk::ast::v1::BINARY_OPCODE_XOR;
  case clang::BO_Or:
    return ctk::ast::v1::BINARY_OPCODE_OR;
  case clang::BO_LAnd:
    return ctk::ast::v1::BINARY_OPCODE_L_AND;
  case clang::BO_LOr:
    return ctk::ast::v1::BINARY_OPCODE_L_OR;
  case clang::BO_Assign:
    return ctk::ast::v1::BINARY_OPCODE_ASSIGN;
  case clang::BO_MulAssign:
    return ctk::ast::v1::BINARY_OPCODE_MUL_ASSIGN;
  case clang::BO_DivAssign:
    return ctk::ast::v1::BINARY_OPCODE_DIV_ASSIGN;
  case clang::BO_RemAssign:
    return ctk::ast::v1::BINARY_OPCODE_REM_ASSIGN;
  case clang::BO_AddAssign:
    return ctk::ast::v1::BINARY_OPCODE_ADD_ASSIGN;
  case clang::BO_SubAssign:
    return ctk::ast::v1::BINARY_OPCODE_SUB_ASSIGN;
  case clang::BO_ShlAssign:
    return ctk::ast::v1::BINARY_OPCODE_SHL_ASSIGN;
  case clang::BO_ShrAssign:
    return ctk::ast::v1::BINARY_OPCODE_SHR_ASSIGN;
  case clang::BO_AndAssign:
    return ctk::ast::v1::BINARY_OPCODE_AND_ASSIGN;
  case clang::BO_XorAssign:
    return ctk::ast::v1::BINARY_OPCODE_XOR_ASSIGN;
  case clang::BO_OrAssign:
    return ctk::ast::v1::BINARY_OPCODE_OR_ASSIGN;
  case clang::BO_Comma:
    return ctk::ast::v1::BINARY_OPCODE_COMMA;
  }
  return ctk::ast::v1::BINARY_OPCODE_UNSPECIFIED;
}
ctk::ast::v1::OverloadedOperatorKind
overloaded_operator(clang::OverloadedOperatorKind kind) {
  switch (kind) {
  case clang::OO_New:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_NEW;
  case clang::OO_Delete:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_DELETE;
  case clang::OO_Array_New:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_ARRAY_NEW;
  case clang::OO_Array_Delete:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_ARRAY_DELETE;
  case clang::OO_Plus:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PLUS;
  case clang::OO_Minus:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_MINUS;
  case clang::OO_Star:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_STAR;
  case clang::OO_Slash:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_SLASH;
  case clang::OO_Percent:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PERCENT;
  case clang::OO_Caret:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_CARET;
  case clang::OO_Amp:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_AMP;
  case clang::OO_Pipe:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PIPE;
  case clang::OO_Tilde:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_TILDE;
  case clang::OO_Exclaim:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_EXCLAIM;
  case clang::OO_Equal:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_EQUAL;
  case clang::OO_Less:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_LESS;
  case clang::OO_Greater:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_GREATER;
  case clang::OO_PlusEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PLUS_EQUAL;
  case clang::OO_MinusEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_MINUS_EQUAL;
  case clang::OO_StarEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_STAR_EQUAL;
  case clang::OO_SlashEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_SLASH_EQUAL;
  case clang::OO_PercentEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PERCENT_EQUAL;
  case clang::OO_CaretEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_CARET_EQUAL;
  case clang::OO_AmpEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_AMP_EQUAL;
  case clang::OO_PipeEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PIPE_EQUAL;
  case clang::OO_LessLess:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_LESS_LESS;
  case clang::OO_GreaterGreater:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_GREATER_GREATER;
  case clang::OO_LessLessEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_LESS_LESS_EQUAL;
  case clang::OO_GreaterGreaterEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_GREATER_GREATER_EQUAL;
  case clang::OO_EqualEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_EQUAL_EQUAL;
  case clang::OO_ExclaimEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_EXCLAIM_EQUAL;
  case clang::OO_LessEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_LESS_EQUAL;
  case clang::OO_GreaterEqual:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_GREATER_EQUAL;
  case clang::OO_Spaceship:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_SPACESHIP;
  case clang::OO_AmpAmp:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_AMP_AMP;
  case clang::OO_PipePipe:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PIPE_PIPE;
  case clang::OO_PlusPlus:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_PLUS_PLUS;
  case clang::OO_MinusMinus:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_MINUS_MINUS;
  case clang::OO_Comma:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_COMMA;
  case clang::OO_ArrowStar:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_ARROW_STAR;
  case clang::OO_Arrow:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_ARROW;
  case clang::OO_Call:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_CALL;
  case clang::OO_Subscript:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_SUBSCRIPT;
  case clang::OO_Conditional:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_CONDITIONAL;
  case clang::OO_Coawait:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_COAWAIT;
  case clang::OO_None:
    return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_UNSPECIFIED;
  case clang::NUM_OVERLOADED_OPERATORS:
    break;
  }
  return ctk::ast::v1::OVERLOADED_OPERATOR_KIND_UNSPECIFIED;
}
ctk::ast::v1::AtomicOpcode atomic_opcode(clang::AtomicExpr::AtomicOp op) {
  switch (op) {
  case clang::AtomicExpr::AO__atomic_add_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_and_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_clear:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__atomic_compare_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__atomic_compare_exchange_n:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__atomic_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__atomic_exchange_n:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__atomic_fetch_add:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_and:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_max:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_min:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_nand:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_or:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_fetch_sub:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__atomic_fetch_udec:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__atomic_fetch_uinc:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#endif
  case clang::AtomicExpr::AO__atomic_fetch_xor:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_load:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__atomic_load_n:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__atomic_max_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_min_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_nand_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_or_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_store:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__atomic_store_n:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__atomic_sub_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__atomic_test_and_set:
    return ctk::ast::v1::ATOMIC_OPCODE_OTHER;
  case clang::AtomicExpr::AO__atomic_xor_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_compare_exchange_strong:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__c11_atomic_compare_exchange_weak:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__c11_atomic_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__c11_atomic_fetch_add:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_and:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_max:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_min:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_nand:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_or:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_sub:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_fetch_xor:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__c11_atomic_init:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__c11_atomic_load:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__c11_atomic_store:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__hip_atomic_compare_exchange_strong:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__hip_atomic_compare_exchange_weak:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__hip_atomic_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__hip_atomic_fetch_add:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_and:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_max:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_min:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_or:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_sub:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_fetch_xor:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__hip_atomic_load:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__hip_atomic_store:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__opencl_atomic_compare_exchange_strong:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__opencl_atomic_compare_exchange_weak:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__opencl_atomic_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_add:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_and:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_max:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_min:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_or:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_sub:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_fetch_xor:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__opencl_atomic_init:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__opencl_atomic_load:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__opencl_atomic_store:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__scoped_atomic_add_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_and_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_compare_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__scoped_atomic_compare_exchange_n:
    return ctk::ast::v1::ATOMIC_OPCODE_COMPARE_EXCHANGE;
  case clang::AtomicExpr::AO__scoped_atomic_exchange:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__scoped_atomic_exchange_n:
    return ctk::ast::v1::ATOMIC_OPCODE_EXCHANGE;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_add:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_and:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_max:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_min:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_nand:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_or:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_sub:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_fetch_xor:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_load:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__scoped_atomic_load_n:
    return ctk::ast::v1::ATOMIC_OPCODE_LOAD;
  case clang::AtomicExpr::AO__scoped_atomic_max_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_min_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_nand_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_or_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  case clang::AtomicExpr::AO__scoped_atomic_store:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__scoped_atomic_store_n:
    return ctk::ast::v1::ATOMIC_OPCODE_STORE;
  case clang::AtomicExpr::AO__scoped_atomic_sub_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__scoped_atomic_fetch_udec:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__scoped_atomic_fetch_uinc:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
#endif
  case clang::AtomicExpr::AO__scoped_atomic_xor_fetch:
    return ctk::ast::v1::ATOMIC_OPCODE_FETCH;
  default:
    return ctk::ast::v1::ATOMIC_OPCODE_OTHER;
  }
}
const char *atomic_name(clang::AtomicExpr::AtomicOp op) {
  switch (op) {
  case clang::AtomicExpr::AO__atomic_add_fetch:
    return "__atomic_add_fetch";
  case clang::AtomicExpr::AO__atomic_and_fetch:
    return "__atomic_and_fetch";
  case clang::AtomicExpr::AO__atomic_clear:
    return "__atomic_clear";
  case clang::AtomicExpr::AO__atomic_compare_exchange:
    return "__atomic_compare_exchange";
  case clang::AtomicExpr::AO__atomic_compare_exchange_n:
    return "__atomic_compare_exchange_n";
  case clang::AtomicExpr::AO__atomic_exchange:
    return "__atomic_exchange";
  case clang::AtomicExpr::AO__atomic_exchange_n:
    return "__atomic_exchange_n";
  case clang::AtomicExpr::AO__atomic_fetch_add:
    return "__atomic_fetch_add";
  case clang::AtomicExpr::AO__atomic_fetch_and:
    return "__atomic_fetch_and";
  case clang::AtomicExpr::AO__atomic_fetch_max:
    return "__atomic_fetch_max";
  case clang::AtomicExpr::AO__atomic_fetch_min:
    return "__atomic_fetch_min";
  case clang::AtomicExpr::AO__atomic_fetch_nand:
    return "__atomic_fetch_nand";
  case clang::AtomicExpr::AO__atomic_fetch_or:
    return "__atomic_fetch_or";
  case clang::AtomicExpr::AO__atomic_fetch_sub:
    return "__atomic_fetch_sub";
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__atomic_fetch_udec:
    return "__atomic_fetch_udec";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__atomic_fetch_uinc:
    return "__atomic_fetch_uinc";
#endif
  case clang::AtomicExpr::AO__atomic_fetch_xor:
    return "__atomic_fetch_xor";
  case clang::AtomicExpr::AO__atomic_load:
    return "__atomic_load";
  case clang::AtomicExpr::AO__atomic_load_n:
    return "__atomic_load_n";
  case clang::AtomicExpr::AO__atomic_max_fetch:
    return "__atomic_max_fetch";
  case clang::AtomicExpr::AO__atomic_min_fetch:
    return "__atomic_min_fetch";
  case clang::AtomicExpr::AO__atomic_nand_fetch:
    return "__atomic_nand_fetch";
  case clang::AtomicExpr::AO__atomic_or_fetch:
    return "__atomic_or_fetch";
  case clang::AtomicExpr::AO__atomic_store:
    return "__atomic_store";
  case clang::AtomicExpr::AO__atomic_store_n:
    return "__atomic_store_n";
  case clang::AtomicExpr::AO__atomic_sub_fetch:
    return "__atomic_sub_fetch";
  case clang::AtomicExpr::AO__atomic_test_and_set:
    return "__atomic_test_and_set";
  case clang::AtomicExpr::AO__atomic_xor_fetch:
    return "__atomic_xor_fetch";
  case clang::AtomicExpr::AO__c11_atomic_compare_exchange_strong:
    return "__c11_atomic_compare_exchange_strong";
  case clang::AtomicExpr::AO__c11_atomic_compare_exchange_weak:
    return "__c11_atomic_compare_exchange_weak";
  case clang::AtomicExpr::AO__c11_atomic_exchange:
    return "__c11_atomic_exchange";
  case clang::AtomicExpr::AO__c11_atomic_fetch_add:
    return "__c11_atomic_fetch_add";
  case clang::AtomicExpr::AO__c11_atomic_fetch_and:
    return "__c11_atomic_fetch_and";
  case clang::AtomicExpr::AO__c11_atomic_fetch_max:
    return "__c11_atomic_fetch_max";
  case clang::AtomicExpr::AO__c11_atomic_fetch_min:
    return "__c11_atomic_fetch_min";
  case clang::AtomicExpr::AO__c11_atomic_fetch_nand:
    return "__c11_atomic_fetch_nand";
  case clang::AtomicExpr::AO__c11_atomic_fetch_or:
    return "__c11_atomic_fetch_or";
  case clang::AtomicExpr::AO__c11_atomic_fetch_sub:
    return "__c11_atomic_fetch_sub";
  case clang::AtomicExpr::AO__c11_atomic_fetch_xor:
    return "__c11_atomic_fetch_xor";
  case clang::AtomicExpr::AO__c11_atomic_init:
    return "__c11_atomic_init";
  case clang::AtomicExpr::AO__c11_atomic_load:
    return "__c11_atomic_load";
  case clang::AtomicExpr::AO__c11_atomic_store:
    return "__c11_atomic_store";
  case clang::AtomicExpr::AO__hip_atomic_compare_exchange_strong:
    return "__hip_atomic_compare_exchange_strong";
  case clang::AtomicExpr::AO__hip_atomic_compare_exchange_weak:
    return "__hip_atomic_compare_exchange_weak";
  case clang::AtomicExpr::AO__hip_atomic_exchange:
    return "__hip_atomic_exchange";
  case clang::AtomicExpr::AO__hip_atomic_fetch_add:
    return "__hip_atomic_fetch_add";
  case clang::AtomicExpr::AO__hip_atomic_fetch_and:
    return "__hip_atomic_fetch_and";
  case clang::AtomicExpr::AO__hip_atomic_fetch_max:
    return "__hip_atomic_fetch_max";
  case clang::AtomicExpr::AO__hip_atomic_fetch_min:
    return "__hip_atomic_fetch_min";
  case clang::AtomicExpr::AO__hip_atomic_fetch_or:
    return "__hip_atomic_fetch_or";
  case clang::AtomicExpr::AO__hip_atomic_fetch_sub:
    return "__hip_atomic_fetch_sub";
  case clang::AtomicExpr::AO__hip_atomic_fetch_xor:
    return "__hip_atomic_fetch_xor";
  case clang::AtomicExpr::AO__hip_atomic_load:
    return "__hip_atomic_load";
  case clang::AtomicExpr::AO__hip_atomic_store:
    return "__hip_atomic_store";
  case clang::AtomicExpr::AO__opencl_atomic_compare_exchange_strong:
    return "__opencl_atomic_compare_exchange_strong";
  case clang::AtomicExpr::AO__opencl_atomic_compare_exchange_weak:
    return "__opencl_atomic_compare_exchange_weak";
  case clang::AtomicExpr::AO__opencl_atomic_exchange:
    return "__opencl_atomic_exchange";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_add:
    return "__opencl_atomic_fetch_add";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_and:
    return "__opencl_atomic_fetch_and";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_max:
    return "__opencl_atomic_fetch_max";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_min:
    return "__opencl_atomic_fetch_min";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_or:
    return "__opencl_atomic_fetch_or";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_sub:
    return "__opencl_atomic_fetch_sub";
  case clang::AtomicExpr::AO__opencl_atomic_fetch_xor:
    return "__opencl_atomic_fetch_xor";
  case clang::AtomicExpr::AO__opencl_atomic_init:
    return "__opencl_atomic_init";
  case clang::AtomicExpr::AO__opencl_atomic_load:
    return "__opencl_atomic_load";
  case clang::AtomicExpr::AO__opencl_atomic_store:
    return "__opencl_atomic_store";
  case clang::AtomicExpr::AO__scoped_atomic_add_fetch:
    return "__scoped_atomic_add_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_and_fetch:
    return "__scoped_atomic_and_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_compare_exchange:
    return "__scoped_atomic_compare_exchange";
  case clang::AtomicExpr::AO__scoped_atomic_compare_exchange_n:
    return "__scoped_atomic_compare_exchange_n";
  case clang::AtomicExpr::AO__scoped_atomic_exchange:
    return "__scoped_atomic_exchange";
  case clang::AtomicExpr::AO__scoped_atomic_exchange_n:
    return "__scoped_atomic_exchange_n";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_add:
    return "__scoped_atomic_fetch_add";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_and:
    return "__scoped_atomic_fetch_and";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_max:
    return "__scoped_atomic_fetch_max";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_min:
    return "__scoped_atomic_fetch_min";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_nand:
    return "__scoped_atomic_fetch_nand";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_or:
    return "__scoped_atomic_fetch_or";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_sub:
    return "__scoped_atomic_fetch_sub";
  case clang::AtomicExpr::AO__scoped_atomic_fetch_xor:
    return "__scoped_atomic_fetch_xor";
  case clang::AtomicExpr::AO__scoped_atomic_load:
    return "__scoped_atomic_load";
  case clang::AtomicExpr::AO__scoped_atomic_load_n:
    return "__scoped_atomic_load_n";
  case clang::AtomicExpr::AO__scoped_atomic_max_fetch:
    return "__scoped_atomic_max_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_min_fetch:
    return "__scoped_atomic_min_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_nand_fetch:
    return "__scoped_atomic_nand_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_or_fetch:
    return "__scoped_atomic_or_fetch";
  case clang::AtomicExpr::AO__scoped_atomic_store:
    return "__scoped_atomic_store";
  case clang::AtomicExpr::AO__scoped_atomic_store_n:
    return "__scoped_atomic_store_n";
  case clang::AtomicExpr::AO__scoped_atomic_sub_fetch:
    return "__scoped_atomic_sub_fetch";
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__scoped_atomic_fetch_udec:
    return "__scoped_atomic_fetch_udec";
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::AtomicExpr::AO__scoped_atomic_fetch_uinc:
    return "__scoped_atomic_fetch_uinc";
#endif
  case clang::AtomicExpr::AO__scoped_atomic_xor_fetch:
    return "__scoped_atomic_xor_fetch";
  default:
    return nullptr;
  }
}
} // namespace ctk::clang_layer::serialization::helpers
