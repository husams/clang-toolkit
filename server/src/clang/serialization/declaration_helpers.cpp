#include "declaration_helpers.hpp"
#include "type_helpers.hpp"

#include <clang/AST/ASTConcept.h>
#include <clang/AST/Attr.h>
#include <clang/AST/PrettyPrinter.h>
#include <clang/Basic/OperatorKinds.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::clang_layer::serialization::helpers {
namespace {
namespace pb = ctk::ast::v1;

clang::QualType declared_type(const clang::TypeDecl &native,
                              SerializationContext &context) {
#if CLANG_VERSION_MAJOR >= 22
  // Tag and typedef declaration types are created lazily in Clang 22.
  return context.ast_context.getTypeDeclType(
      clang::ElaboratedTypeKeyword::None,
      clang::NestedNameSpecifier{std::nullopt}, &native);
#else
  return context.ast_context.getTypeDeclType(&native);
#endif
}

pb::StorageClass storage_class(clang::StorageClass value) {
  switch (value) {
  case clang::SC_None:
    return pb::STORAGE_CLASS_NONE;
  case clang::SC_Extern:
    return pb::STORAGE_CLASS_EXTERN;
  case clang::SC_Static:
    return pb::STORAGE_CLASS_STATIC;
  case clang::SC_PrivateExtern:
    return pb::STORAGE_CLASS_PRIVATE_EXTERN;
  case clang::SC_Auto:
    return pb::STORAGE_CLASS_AUTO;
  case clang::SC_Register:
    return pb::STORAGE_CLASS_REGISTER;
  }
  return pb::STORAGE_CLASS_UNSPECIFIED;
}
pb::RefQualifier ref_qualifier(clang::RefQualifierKind value) {
  switch (value) {
  case clang::RQ_None:
    return pb::REF_QUALIFIER_NONE;
  case clang::RQ_LValue:
    return pb::REF_QUALIFIER_LVALUE;
  case clang::RQ_RValue:
    return pb::REF_QUALIFIER_RVALUE;
  }
  return pb::REF_QUALIFIER_UNSPECIFIED;
}
pb::OverloadedOperatorKind operator_kind(clang::OverloadedOperatorKind value) {
  switch (value) {
  case clang::OO_None:
    return pb::OVERLOADED_OPERATOR_KIND_UNSPECIFIED;
  case clang::OO_New:
    return pb::OVERLOADED_OPERATOR_KIND_NEW;
  case clang::OO_Delete:
    return pb::OVERLOADED_OPERATOR_KIND_DELETE;
  case clang::OO_Array_New:
    return pb::OVERLOADED_OPERATOR_KIND_ARRAY_NEW;
  case clang::OO_Array_Delete:
    return pb::OVERLOADED_OPERATOR_KIND_ARRAY_DELETE;
  case clang::OO_Plus:
    return pb::OVERLOADED_OPERATOR_KIND_PLUS;
  case clang::OO_Minus:
    return pb::OVERLOADED_OPERATOR_KIND_MINUS;
  case clang::OO_Star:
    return pb::OVERLOADED_OPERATOR_KIND_STAR;
  case clang::OO_Slash:
    return pb::OVERLOADED_OPERATOR_KIND_SLASH;
  case clang::OO_Percent:
    return pb::OVERLOADED_OPERATOR_KIND_PERCENT;
  case clang::OO_Caret:
    return pb::OVERLOADED_OPERATOR_KIND_CARET;
  case clang::OO_Amp:
    return pb::OVERLOADED_OPERATOR_KIND_AMP;
  case clang::OO_Pipe:
    return pb::OVERLOADED_OPERATOR_KIND_PIPE;
  case clang::OO_Tilde:
    return pb::OVERLOADED_OPERATOR_KIND_TILDE;
  case clang::OO_Exclaim:
    return pb::OVERLOADED_OPERATOR_KIND_EXCLAIM;
  case clang::OO_Equal:
    return pb::OVERLOADED_OPERATOR_KIND_EQUAL;
  case clang::OO_Less:
    return pb::OVERLOADED_OPERATOR_KIND_LESS;
  case clang::OO_Greater:
    return pb::OVERLOADED_OPERATOR_KIND_GREATER;
  case clang::OO_PlusEqual:
    return pb::OVERLOADED_OPERATOR_KIND_PLUS_EQUAL;
  case clang::OO_MinusEqual:
    return pb::OVERLOADED_OPERATOR_KIND_MINUS_EQUAL;
  case clang::OO_StarEqual:
    return pb::OVERLOADED_OPERATOR_KIND_STAR_EQUAL;
  case clang::OO_SlashEqual:
    return pb::OVERLOADED_OPERATOR_KIND_SLASH_EQUAL;
  case clang::OO_PercentEqual:
    return pb::OVERLOADED_OPERATOR_KIND_PERCENT_EQUAL;
  case clang::OO_CaretEqual:
    return pb::OVERLOADED_OPERATOR_KIND_CARET_EQUAL;
  case clang::OO_AmpEqual:
    return pb::OVERLOADED_OPERATOR_KIND_AMP_EQUAL;
  case clang::OO_PipeEqual:
    return pb::OVERLOADED_OPERATOR_KIND_PIPE_EQUAL;
  case clang::OO_LessLess:
    return pb::OVERLOADED_OPERATOR_KIND_LESS_LESS;
  case clang::OO_GreaterGreater:
    return pb::OVERLOADED_OPERATOR_KIND_GREATER_GREATER;
  case clang::OO_LessLessEqual:
    return pb::OVERLOADED_OPERATOR_KIND_LESS_LESS_EQUAL;
  case clang::OO_GreaterGreaterEqual:
    return pb::OVERLOADED_OPERATOR_KIND_GREATER_GREATER_EQUAL;
  case clang::OO_EqualEqual:
    return pb::OVERLOADED_OPERATOR_KIND_EQUAL_EQUAL;
  case clang::OO_ExclaimEqual:
    return pb::OVERLOADED_OPERATOR_KIND_EXCLAIM_EQUAL;
  case clang::OO_LessEqual:
    return pb::OVERLOADED_OPERATOR_KIND_LESS_EQUAL;
  case clang::OO_GreaterEqual:
    return pb::OVERLOADED_OPERATOR_KIND_GREATER_EQUAL;
  case clang::OO_Spaceship:
    return pb::OVERLOADED_OPERATOR_KIND_SPACESHIP;
  case clang::OO_AmpAmp:
    return pb::OVERLOADED_OPERATOR_KIND_AMP_AMP;
  case clang::OO_PipePipe:
    return pb::OVERLOADED_OPERATOR_KIND_PIPE_PIPE;
  case clang::OO_PlusPlus:
    return pb::OVERLOADED_OPERATOR_KIND_PLUS_PLUS;
  case clang::OO_MinusMinus:
    return pb::OVERLOADED_OPERATOR_KIND_MINUS_MINUS;
  case clang::OO_Comma:
    return pb::OVERLOADED_OPERATOR_KIND_COMMA;
  case clang::OO_ArrowStar:
    return pb::OVERLOADED_OPERATOR_KIND_ARROW_STAR;
  case clang::OO_Arrow:
    return pb::OVERLOADED_OPERATOR_KIND_ARROW;
  case clang::OO_Call:
    return pb::OVERLOADED_OPERATOR_KIND_CALL;
  case clang::OO_Subscript:
    return pb::OVERLOADED_OPERATOR_KIND_SUBSCRIPT;
  case clang::OO_Conditional:
    return pb::OVERLOADED_OPERATOR_KIND_CONDITIONAL;
  case clang::OO_Coawait:
    return pb::OVERLOADED_OPERATOR_KIND_COAWAIT;
  case clang::NUM_OVERLOADED_OPERATORS:
    break;
  }
  return pb::OVERLOADED_OPERATOR_KIND_UNSPECIFIED;
}
pb::SymbolKind symbol_kind(const clang::NamedDecl &native) {
  if (llvm::isa<clang::CXXConstructorDecl>(native))
    return pb::SYMBOL_KIND_CONSTRUCTOR;
  if (llvm::isa<clang::CXXDestructorDecl>(native))
    return pb::SYMBOL_KIND_DESTRUCTOR;
  if (llvm::isa<clang::CXXMethodDecl>(native))
    return pb::SYMBOL_KIND_METHOD;
  if (llvm::isa<clang::FunctionDecl>(native))
    return pb::SYMBOL_KIND_FUNCTION;
  if (llvm::isa<clang::ConceptDecl>(native))
    return pb::SYMBOL_KIND_CONCEPT;
  if (llvm::isa<clang::TemplateDecl>(native))
    return pb::SYMBOL_KIND_TEMPLATE;
  if (llvm::isa<clang::RecordDecl>(native))
    return pb::SYMBOL_KIND_RECORD;
  if (llvm::isa<clang::EnumDecl>(native))
    return pb::SYMBOL_KIND_ENUM;
  if (llvm::isa<clang::TypedefNameDecl>(native))
    return pb::SYMBOL_KIND_TYPE_ALIAS;
  if (llvm::isa<clang::NamespaceDecl, clang::NamespaceAliasDecl>(native))
    return pb::SYMBOL_KIND_NAMESPACE;
  if (llvm::isa<clang::FieldDecl, clang::IndirectFieldDecl>(native))
    return pb::SYMBOL_KIND_FIELD;
  if (llvm::isa<clang::ParmVarDecl, clang::ImplicitParamDecl>(native))
    return pb::SYMBOL_KIND_PARAMETER;
  if (llvm::isa<clang::VarDecl, clang::BindingDecl, clang::EnumConstantDecl>(
          native))
    return pb::SYMBOL_KIND_VARIABLE;
  if (llvm::isa<clang::LabelDecl>(native))
    return pb::SYMBOL_KIND_LABEL;
  if (llvm::isa<clang::UnresolvedUsingTypenameDecl,
                clang::UnresolvedUsingValueDecl,
                clang::UnresolvedUsingIfExistsDecl>(native))
    return pb::SYMBOL_KIND_UNRESOLVED;
  return pb::SYMBOL_KIND_OTHER;
}
std::string expression_spelling(const clang::Expr &native,
                                SerializationContext &context) {
  std::string result;
  llvm::raw_string_ostream stream(result);
  native.printPretty(stream, nullptr, context.ast_context.getPrintingPolicy());
  return result;
}
void constraint_description(const clang::Expr &native,
                            pb::ConstraintDescription &payload,
                            SerializationContext &context) {
  ExpansionFrame frame("constraint_description", context);
  if (!frame.allowed)
    return;

  payload.set_semantic_expression(expression_spelling(native, context));
  payload.set_is_dependent(native.isValueDependent());
  if (!native.isValueDependent() &&
      can_expand(payload, "is_satisfied", context)) {
    clang::Expr::EvalResult evaluation;
    if (native.EvaluateAsInt(evaluation, context.ast_context))
      payload.set_is_satisfied(evaluation.Val.getInt().getBoolValue());
  }
}
void parameter_description(const clang::NamedDecl &native,
                           pb::TemplateParameterDescription &payload,
                           SerializationContext &context) {
  ExpansionFrame frame("parameter_description", context);
  if (!frame.allowed)
    return;

  payload.set_name(native.getNameAsString());
  if (const auto *type = llvm::dyn_cast<clang::TemplateTypeParmDecl>(&native)) {
    payload.set_kind(pb::TEMPLATE_PARAMETER_DESCRIPTION_KIND_TYPE);
    payload.set_is_parameter_pack(type->isParameterPack());
  } else if (const auto *value =
                 llvm::dyn_cast<clang::NonTypeTemplateParmDecl>(&native)) {
    payload.set_kind(pb::TEMPLATE_PARAMETER_DESCRIPTION_KIND_NON_TYPE);
    payload.set_is_parameter_pack(value->isParameterPack());
    write_type_description(value->getType(), *payload.mutable_type(), context);
  } else if (const auto *templ =
                 llvm::dyn_cast<clang::TemplateTemplateParmDecl>(&native)) {
    payload.set_kind(pb::TEMPLATE_PARAMETER_DESCRIPTION_KIND_TEMPLATE);
    payload.set_is_parameter_pack(templ->isParameterPack());
    for (const auto *parameter : *templ->getTemplateParameters()) {
      if (!can_expand(payload, "template_parameters", context))
        break;
      parameter_description(*parameter, *payload.add_template_parameters(),
                            context);
    }
  }
}
void argument_description(const clang::TemplateArgument &native,
                          pb::TemplateArgumentDescription &payload,
                          SerializationContext &context) {
  ExpansionFrame frame("argument_description", context);
  if (!frame.allowed)
    return;

  // ArgKind and the description enum deliberately share this ordering.
  payload.set_kind(static_cast<pb::TemplateArgumentDescriptionKind>(
      static_cast<int>(native.getKind()) + 1));
  std::string spelling;
  llvm::raw_string_ostream stream(spelling);
  native.print(context.ast_context.getPrintingPolicy(), stream, true);
  payload.set_semantic_spelling(spelling);
  switch (native.getKind()) {
  case clang::TemplateArgument::Type:
    write_type_description(native.getAsType(), *payload.mutable_type(),
                           context);
    break;
  case clang::TemplateArgument::Integral:
    write_type_description(native.getIntegralType(), *payload.mutable_type(),
                           context);
    write_apsint(native.getAsIntegral(), *payload.mutable_integer());
    break;
  case clang::TemplateArgument::NullPtr:
    write_type_description(native.getNullPtrType(), *payload.mutable_type(),
                           context);
    break;
  case clang::TemplateArgument::Declaration:
    write_type_description(native.getParamTypeForDecl(),
                           *payload.mutable_type(), context);
    break;
  case clang::TemplateArgument::StructuralValue:
    write_type_description(native.getStructuralValueType(),
                           *payload.mutable_type(), context);
    if (native.getAsStructuralValue().isFloat())
      write_apfloat(native.getAsStructuralValue().getFloat(),
                    *payload.mutable_floating());
    break;
  case clang::TemplateArgument::Expression:
    write_type_description(native.getAsExpr()->getType(),
                           *payload.mutable_type(), context);
    break;
  case clang::TemplateArgument::Pack:
    for (const auto &element : native.pack_elements()) {
      if (!can_expand(payload, "pack_elements", context))
        break;
      argument_description(element, *payload.add_pack_elements(), context);
    }
    break;
  case clang::TemplateArgument::Null:
  case clang::TemplateArgument::Template:
  case clang::TemplateArgument::TemplateExpansion:
    break;
  }
}
} // namespace

void write_declaration_name(clang::DeclarationName native,
                            pb::DeclarationName &payload,
                            SerializationContext &context) {
  ExpansionFrame frame("write_declaration_name", context);
  if (!frame.allowed)
    return;

  if (native.isEmpty()) {
    payload.mutable_empty_name();
    return;
  }
  switch (native.getNameKind()) {
  case clang::DeclarationName::Identifier:
    payload.set_identifier(native.getAsIdentifierInfo()->getName().str());
    break;
  case clang::DeclarationName::CXXConstructorName:
    write_type(native.getCXXNameType(), *payload.mutable_constructor_type(),
               context);
    break;
  case clang::DeclarationName::CXXDestructorName:
    write_type(native.getCXXNameType(), *payload.mutable_destructor_type(),
               context);
    break;
  case clang::DeclarationName::CXXConversionFunctionName:
    write_type(native.getCXXNameType(), *payload.mutable_conversion_type(),
               context);
    break;
  case clang::DeclarationName::CXXOperatorName:
    payload.set_overloaded_operator(
        operator_kind(native.getCXXOverloadedOperator()));
    break;
  case clang::DeclarationName::CXXLiteralOperatorName:
    payload.set_literal_operator_suffix(
        native.getCXXLiteralIdentifier()->getName().str());
    break;
  case clang::DeclarationName::CXXDeductionGuideName:
    write_symbol(*native.getCXXDeductionGuideTemplate(),
                 *payload.mutable_deduction_guide_template(), context);
    break;
  case clang::DeclarationName::CXXUsingDirective:
    payload.mutable_using_directive();
    break;
  case clang::DeclarationName::ObjCZeroArgSelector:
  case clang::DeclarationName::ObjCOneArgSelector:
  case clang::DeclarationName::ObjCMultiArgSelector:
    unavailable(payload, "value",
                "Objective-C selector names have no alternative in this C++ "
                "semantic contract",
                context);
    break;
  }
}
void write_decl_info(const clang::Decl &native, pb::DeclInfo &payload,
                     SerializationContext &context) {
  payload.set_is_implicit(native.isImplicit());
  payload.set_is_invalid(native.isInvalidDecl());
  // Walk outward to a named scope. Anonymous block/requires contexts have no
  // symbol themselves; their enclosing declaration is the containing scope.
  if (context.projection == ProjectionPolicy::Shallow) {
    (void)can_expand(payload, "containing_scope", context);
  } else {
    for (auto *scope = native.getDeclContext(); scope;
         scope = scope->getParent()) {
      if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(
              clang::Decl::castFromDeclContext(scope))) {
        write_symbol(*named, *payload.mutable_containing_scope(), context);
        break;
      }
    }
  }
  for (const auto *attribute : native.attrs()) {
    if (!can_expand(payload, "attributes", context))
      break;

    ExpansionFrame attribute_frame("DeclInfo.attributes", context);
    if (!attribute_frame.allowed)
      break;
    type_helpers::write_attribute(*attribute, *payload.add_attributes(),
                                  context);
  }
}
void write_named_info(const clang::NamedDecl &native,
                      pb::NamedDeclInfo &payload,
                      SerializationContext &context) {
  write_decl_info(native, *payload.mutable_declaration(), context);
  write_declaration_name(native.getDeclName(), *payload.mutable_name(),
                         context);
  payload.set_qualified_name(native.getQualifiedNameAsString());
}
void write_value_info(const clang::ValueDecl &native,
                      pb::ValueDeclInfo &payload,
                      SerializationContext &context) {
  write_named_info(native, *payload.mutable_named(), context);
  if (!native.getType().isNull())
    write_type(native.getType(), *payload.mutable_type(), context);
}
void write_declarator_info(const clang::DeclaratorDecl &native,
                           pb::DeclaratorDeclInfo &payload,
                           SerializationContext &context) {
  write_value_info(native, *payload.mutable_value(), context);
  auto type = native.getType();
  if (native.getTypeSourceInfo())
    type = native.getTypeSourceInfo()->getType();
  if (const auto *parameter = llvm::dyn_cast<clang::ParmVarDecl>(&native))
    type = parameter->getOriginalType();
  if (!type.isNull())
    write_type(type, *payload.mutable_declared_type(), context);
}
void write_function_info(const clang::FunctionDecl &native,
                         pb::FunctionDeclInfo &payload,
                         SerializationContext &context) {
  write_declarator_info(native, *payload.mutable_declarator(), context);
  write_type(native.getReturnType(), *payload.mutable_return_type(), context);
  for (const auto *parameter : native.parameters()) {
    if (!can_expand(payload, "parameters", context))
      break;
    write_decl(parameter, *payload.add_parameters(), context);
  }
  // getBody() may find a different redeclaration's body. This field describes
  // the matched declaration and owns only that declaration's body.
  if (native.doesThisDeclarationHaveABody())
    write_stmt(native.getBody(), *payload.mutable_body(), context);
  if (native.hasSkippedBody())
    unavailable(payload, "body", "Clang skipped this definition's body",
                context);
  payload.set_is_this_declaration_a_definition(
      native.isThisDeclarationADefinition());
  payload.set_is_variadic(native.isVariadic());
  payload.set_is_constexpr(native.isConstexpr());
  payload.set_storage_class(storage_class(native.getStorageClass()));
}
void write_method_info(const clang::CXXMethodDecl &native,
                       pb::CXXMethodDeclInfo &payload,
                       SerializationContext &context) {
  write_function_info(native, *payload.mutable_function(), context);
  if (context.projection == ProjectionPolicy::Shallow)
    (void)can_expand(payload, "parent_record", context);
  else
    write_symbol(*native.getParent(), *payload.mutable_parent_record(), context);
  payload.set_is_static(native.isStatic());
  payload.set_is_virtual(native.isVirtual());
  payload.set_is_const(native.isConst());
  payload.set_is_volatile(native.isVolatile());
  payload.set_ref_qualifier(ref_qualifier(native.getRefQualifier()));
  for (const auto *method : native.overridden_methods()) {
    if (!can_expand(payload, "overridden_methods", context))
      break;
    write_symbol(*method, *payload.add_overridden_methods(), context);
  }
}
void write_var_info(const clang::VarDecl &native, pb::VarDeclInfo &payload,
                    SerializationContext &context) {
  write_declarator_info(native, *payload.mutable_declarator(), context);
  if (native.getInit())
    write_expr(native.getInit(), *payload.mutable_initializer(), context);
  payload.set_storage_class(storage_class(native.getStorageClass()));
  payload.set_is_constexpr(native.isConstexpr());
}
void write_type_decl_info(const clang::TypeDecl &native,
                          pb::TypeDeclInfo &payload,
                          SerializationContext &context) {
  write_named_info(native, *payload.mutable_named(), context);
  write_type_value(declared_type(native, context),
                   *payload.mutable_declared_type(), context);
}
void write_tag_info(const clang::TagDecl &native, pb::TagDeclInfo &payload,
                    SerializationContext &context) {
  write_type_decl_info(native, *payload.mutable_type_declaration(), context);
  if (native.isStruct())
    payload.set_tag_kind(pb::TAG_KIND_STRUCT);
  else if (native.isUnion())
    payload.set_tag_kind(pb::TAG_KIND_UNION);
  else if (native.isClass())
    payload.set_tag_kind(pb::TAG_KIND_CLASS);
  else if (native.isEnum())
    payload.set_tag_kind(pb::TAG_KIND_ENUM);
  else
    payload.set_tag_kind(pb::TAG_KIND_INTERFACE);
  payload.set_is_complete_definition(native.isCompleteDefinition());
}
void write_record_info(const clang::RecordDecl &native,
                       pb::RecordDeclInfo &payload,
                       SerializationContext &context) {
  write_tag_info(native, *payload.mutable_tag(), context);
  for (const auto *member : native.decls()) {
    if (!can_expand(payload, "members", context))
      break;
    write_decl(member, *payload.add_members(), context);
  }
}
void write_common(const clang::Decl &native, google::protobuf::Message &payload,
                  SerializationContext &context) {
  // The first field is a defined metadata chain; never search recursively
  // through child values or reference symbols to find a base message.
  auto *field = payload.GetDescriptor()->FindFieldByNumber(1);
  if (!field ||
      field->cpp_type() != google::protobuf::FieldDescriptor::CPPTYPE_MESSAGE)
    return;
  auto *info = payload.GetReflection()->MutableMessage(&payload, field);
  const auto &name = info->GetDescriptor()->name();
  if (name == "DeclInfo")
    write_decl_info(native, static_cast<pb::DeclInfo &>(*info), context);
  else if (name == "NamedDeclInfo")
    write_named_info(llvm::cast<clang::NamedDecl>(native),
                     static_cast<pb::NamedDeclInfo &>(*info), context);
  else if (name == "ValueDeclInfo")
    write_value_info(llvm::cast<clang::ValueDecl>(native),
                     static_cast<pb::ValueDeclInfo &>(*info), context);
  else if (name == "DeclaratorDeclInfo")
    write_declarator_info(llvm::cast<clang::DeclaratorDecl>(native),
                          static_cast<pb::DeclaratorDeclInfo &>(*info),
                          context);
  else if (name == "FunctionDeclInfo")
    write_function_info(llvm::cast<clang::FunctionDecl>(native),
                        static_cast<pb::FunctionDeclInfo &>(*info), context);
  else if (name == "CXXMethodDeclInfo")
    write_method_info(llvm::cast<clang::CXXMethodDecl>(native),
                      static_cast<pb::CXXMethodDeclInfo &>(*info), context);
  else if (name == "VarDeclInfo")
    write_var_info(llvm::cast<clang::VarDecl>(native),
                   static_cast<pb::VarDeclInfo &>(*info), context);
  else if (name == "TypeDeclInfo")
    write_type_decl_info(llvm::cast<clang::TypeDecl>(native),
                         static_cast<pb::TypeDeclInfo &>(*info), context);
  else if (name == "TagDeclInfo")
    write_tag_info(llvm::cast<clang::TagDecl>(native),
                   static_cast<pb::TagDeclInfo &>(*info), context);
  else if (name == "RecordDeclInfo")
    write_record_info(llvm::cast<clang::RecordDecl>(native),
                      static_cast<pb::RecordDeclInfo &>(*info), context);
}
void write_symbol(const clang::NamedDecl &native,
                  pb::DeclarationSymbol &payload,
                  SerializationContext &context) {
  ExpansionFrame frame("write_symbol", context);
  if (!frame.allowed)
    return;

  payload.set_name(native.getNameAsString());
  payload.set_qualified_name(native.getQualifiedNameAsString());
  payload.set_clang_class(std::string(native.getDeclKindName()) + "Decl");
  payload.set_kind(symbol_kind(native));
  payload.set_is_parameter_pack(native.isParameterPack());
  if (const auto *value = llvm::dyn_cast<clang::ValueDecl>(&native)) {
    if (!value->getType().isNull())
      write_type_description(value->getType(), *payload.mutable_type(),
                             context);
  } else if (const auto *type = llvm::dyn_cast<clang::TypeDecl>(&native)) {
    write_type_description(declared_type(*type, context),
                           *payload.mutable_type(), context);
  }
  if (const auto *function = llvm::dyn_cast<clang::FunctionDecl>(&native)) {
    if (context.projection == ProjectionPolicy::Shallow)
      (void)can_expand(payload, "function", context);
    else
      write_signature(*function, *payload.mutable_function(), context);
    if (function->isOverloadedOperator())
      payload.set_overloaded_operator(
          operator_kind(function->getOverloadedOperator()));
    if (const auto *arguments = function->getTemplateSpecializationArgs())
      for (const auto &argument : arguments->asArray()) {
        if (!can_expand(payload, "template_arguments", context))
          break;
        argument_description(argument, *payload.add_template_arguments(),
                             context);
      }
  } else if (const auto *record =
                 llvm::dyn_cast<clang::ClassTemplateSpecializationDecl>(
                     &native)) {
    for (const auto &argument : record->getTemplateArgs().asArray()) {
      if (!can_expand(payload, "template_arguments", context))
        break;
      argument_description(argument, *payload.add_template_arguments(),
                           context);
    }
  } else if (const auto *variable =
                 llvm::dyn_cast<clang::VarTemplateSpecializationDecl>(
                     &native)) {
    for (const auto &argument : variable->getTemplateArgs().asArray()) {
      if (!can_expand(payload, "template_arguments", context))
        break;
      argument_description(argument, *payload.add_template_arguments(),
                           context);
    }
  }
}
void write_base(const clang::CXXBaseSpecifier &native,
                pb::CXXBaseSpecifier &payload, SerializationContext &context) {
  ExpansionFrame frame("write_base", context);
  if (!frame.allowed)
    return;

  write_type(native.getType(), *payload.mutable_type(), context);
  switch (native.getAccessSpecifier()) {
  case clang::AS_public:
    payload.set_access(pb::ACCESS_SPECIFIER_PUBLIC);
    break;
  case clang::AS_protected:
    payload.set_access(pb::ACCESS_SPECIFIER_PROTECTED);
    break;
  case clang::AS_private:
    payload.set_access(pb::ACCESS_SPECIFIER_PRIVATE);
    break;
  case clang::AS_none:
    payload.set_access(pb::ACCESS_SPECIFIER_NONE);
    break;
  }
  payload.set_is_virtual(native.isVirtual());
  payload.set_is_pack_expansion(native.isPackExpansion());
}
void write_concept_reference(const clang::ConceptReference &native,
                             pb::ConceptReference &payload,
                             SerializationContext &context) {
  ExpansionFrame frame("write_concept_reference", context);
  if (!frame.allowed)
    return;

  if (native.getNamedConcept())
    write_symbol(*native.getNamedConcept(),
                 *payload.mutable_concept_declaration(), context);
  if (native.getFoundDecl())
    write_symbol(*native.getFoundDecl(), *payload.mutable_found_declaration(),
                 context);
  write_nested_name(native.getNestedNameSpecifierLoc().getNestedNameSpecifier(),
                    *payload.mutable_qualifier(), context);
  write_declaration_name(native.getConceptNameInfo().getName(),
                         *payload.mutable_name(), context);
  if (const auto *arguments = native.getTemplateArgsAsWritten())
    for (const auto &argument : arguments->arguments()) {
      if (!can_expand(payload, "arguments", context))
        break;
      write_template_argument(argument.getArgument(), *payload.add_arguments(),
                              context);
    }
}
void write_type_constraint(const clang::TypeConstraint &native,
                           pb::TypeConstraint &payload,
                           SerializationContext &context) {
  ExpansionFrame frame("write_type_constraint", context);
  if (!frame.allowed)
    return;

#if CLANG_VERSION_MAJOR >= 22
  write_concept_reference(*native.getConceptReference(),
                          *payload.mutable_concept_reference(), context);
  if (native.getArgPackSubstIndex())
    payload.set_argument_pack_substitution_index(
        *native.getArgPackSubstIndex());
#else
  auto *reference = payload.mutable_concept_reference();
  write_symbol(*native.getNamedConcept(),
               *reference->mutable_concept_declaration(), context);
  if (native.getFoundDecl())
    write_symbol(*native.getFoundDecl(),
                 *reference->mutable_found_declaration(), context);
  write_nested_name(native.getNestedNameSpecifierLoc().getNestedNameSpecifier(),
                    *reference->mutable_qualifier(), context);
  write_declaration_name(native.getConceptNameInfo().getName(),
                         *reference->mutable_name(), context);
  if (const auto *arguments = native.getTemplateArgsAsWritten())
    for (const auto &argument : arguments->arguments()) {
      if (!can_expand(*reference, "arguments", context))
        break;
      write_template_argument(argument.getArgument(),
                              *reference->add_arguments(), context);
    }
#endif
  if (native.getImmediatelyDeclaredConstraint())
    write_expr(native.getImmediatelyDeclaredConstraint(),
               *payload.mutable_immediately_declared_constraint(), context);
}
void write_template_parameters(const clang::TemplateParameterList &native,
                               pb::TemplateParameterList &payload,
                               SerializationContext &context) {
  ExpansionFrame frame("write_template_parameters", context);
  if (!frame.allowed)
    return;

  for (const auto *parameter : native) {
    if (!can_expand(payload, "parameters", context))
      break;
    write_decl(parameter, *payload.add_parameters(), context);
  }
  if (native.getRequiresClause())
    write_expr(native.getRequiresClause(), *payload.mutable_requires_clause(),
               context);
}
void write_template_argument(const clang::TemplateArgument &native,
                             pb::TemplateArgument &payload,
                             SerializationContext &context) {
  ExpansionFrame frame("write_template_argument", context);
  if (!frame.allowed)
    return;

  switch (native.getKind()) {
  case clang::TemplateArgument::Null:
    payload.mutable_null_argument();
    break;
  case clang::TemplateArgument::Type:
    write_type(native.getAsType(), *payload.mutable_type(), context);
    break;
  case clang::TemplateArgument::Declaration:
    write_symbol(*native.getAsDecl(),
                 *payload.mutable_declaration()->mutable_declaration(),
                 context);
    write_type(native.getParamTypeForDecl(),
               *payload.mutable_declaration()->mutable_parameter_type(),
               context);
    break;
  case clang::TemplateArgument::NullPtr:
    write_type(native.getNullPtrType(), *payload.mutable_null_pointer_type(),
               context);
    break;
  case clang::TemplateArgument::Integral:
    write_apsint(native.getAsIntegral(),
                 *payload.mutable_integral()->mutable_value());
    write_type(native.getIntegralType(),
               *payload.mutable_integral()->mutable_type(), context);
    break;
  case clang::TemplateArgument::StructuralValue:
    write_apvalue(native.getAsStructuralValue(),
                  *payload.mutable_structural_value()->mutable_value(),
                  native.getStructuralValueType(), context);
    write_type(native.getStructuralValueType(),
               *payload.mutable_structural_value()->mutable_type(), context);
    break;
  case clang::TemplateArgument::Template:
    write_template_name(native.getAsTemplate(),
                        *payload.mutable_template_name(), context);
    break;
  case clang::TemplateArgument::TemplateExpansion:
    write_template_name(
        native.getAsTemplateOrTemplatePattern(),
        *payload.mutable_template_expansion()->mutable_pattern(), context);
    if (native.getNumTemplateExpansions())
      payload.mutable_template_expansion()->set_expansion_count(
          *native.getNumTemplateExpansions());
    break;
  case clang::TemplateArgument::Expression:
    write_expr(native.getAsExpr(), *payload.mutable_expression(), context);
    break;
  case clang::TemplateArgument::Pack:
    for (const auto &element : native.pack_elements()) {
      if (!can_expand(*payload.mutable_pack(), "elements", context))
        break;
      write_template_argument(element, *payload.mutable_pack()->add_elements(),
                              context);
    }
    break;
  }
}
void write_template_name(clang::TemplateName native, pb::TemplateName &payload,
                         SerializationContext &context) {
  ExpansionFrame frame("write_template_name", context);
  if (!frame.allowed)
    return;

  if (native.isNull()) {
    payload.mutable_null_name();
    return;
  }
  switch (native.getKind()) {
  case clang::TemplateName::Template:
    write_symbol(*native.getAsTemplateDecl(), *payload.mutable_declaration(),
                 context);
    break;
  case clang::TemplateName::OverloadedTemplate:
    for (const auto *declaration : native.getAsOverloadedTemplate()->decls()) {
      if (!can_expand(*payload.mutable_overload(), "declarations", context))
        break;
      write_symbol(*declaration,
                   *payload.mutable_overload()->add_declarations(), context);
    }
    break;
  case clang::TemplateName::AssumedTemplate:
    write_declaration_name(native.getAsAssumedTemplateName()->getDeclName(),
                           *payload.mutable_assumed(), context);
    break;
  case clang::TemplateName::QualifiedTemplate:
    write_nested_name(native.getAsQualifiedTemplateName()->getQualifier(),
                      *payload.mutable_qualified()->mutable_qualifier(),
                      context);
    write_template_name(
        native.getAsQualifiedTemplateName()->getUnderlyingTemplate(),
        *payload.mutable_qualified()->mutable_unqualified(), context);
    break;
  case clang::TemplateName::DependentTemplate: {
    const auto *dependent = native.getAsDependentTemplateName();
    write_nested_name(dependent->getQualifier(),
                      *payload.mutable_dependent()->mutable_qualifier(),
                      context);
#if CLANG_VERSION_MAJOR >= 21
    const auto name = dependent->getName();
    if (name.getIdentifier())
      payload.mutable_dependent()->mutable_name()->set_identifier(
          name.getIdentifier()->getName().str());
    else
      payload.mutable_dependent()->mutable_name()->set_overloaded_operator(
          operator_kind(name.getOperator()));
#else
    if (dependent->isIdentifier())
      payload.mutable_dependent()->mutable_name()->set_identifier(
          dependent->getIdentifier()->getName().str());
    else
      payload.mutable_dependent()->mutable_name()->set_overloaded_operator(
          operator_kind(dependent->getOperator()));
#endif
    break;
  }
  case clang::TemplateName::SubstTemplateTemplateParm: {
    const auto *substitution = native.getAsSubstTemplateTemplateParm();
    auto *value = payload.mutable_substituted();
    write_symbol(*substitution->getParameter(), *value->mutable_parameter(),
                 context);
    write_template_name(substitution->getReplacement(),
                        *value->mutable_replacement(), context);
    value->set_parameter_index(substitution->getIndex());
    if (substitution->getPackIndex())
      value->set_pack_index(*substitution->getPackIndex());
    value->set_is_final(substitution->getFinal());
    break;
  }
  case clang::TemplateName::SubstTemplateTemplateParmPack: {
    const auto *substitution = native.getAsSubstTemplateTemplateParmPack();
    auto *value = payload.mutable_substituted_pack();
    write_symbol(*substitution->getParameterPack(), *value->mutable_parameter(),
                 context);
    for (const auto &argument :
         substitution->getArgumentPack().pack_elements()) {
      if (!can_expand(*value, "arguments", context))
        break;
      write_template_argument(argument, *value->add_arguments(), context);
    }
    value->set_parameter_index(substitution->getIndex());
    value->set_is_final(substitution->getFinal());
    break;
  }
  case clang::TemplateName::UsingTemplate:
    write_symbol(*native.getAsUsingShadowDecl(),
                 *payload.mutable_using_shadow(), context);
    break;
  case clang::TemplateName::DeducedTemplate: {
    const auto *deduced = native.getAsDeducedTemplateName();
    auto *value = payload.mutable_deduced();
    write_template_name(deduced->getUnderlying(), *value->mutable_underlying(),
                        context);
    auto defaults = deduced->getDefaultArguments();
    value->set_default_argument_start(defaults.StartPos);
    for (const auto &argument : defaults.Args) {
      if (!can_expand(*value, "default_arguments", context))
        break;
      write_template_argument(argument, *value->add_default_arguments(),
                              context);
    }
    break;
  }
  }
}

void write_signature(const clang::FunctionDecl &native,
                     pb::FunctionSignature &payload,
                     SerializationContext &context) {
  ExpansionFrame frame("write_signature", context);
  if (!frame.allowed)
    return;

  write_type_description(native.getReturnType(), *payload.mutable_return_type(),
                         context);
  payload.set_is_variadic(native.isVariadic());
  for (const auto *parameter : native.parameters()) {
    if (!can_expand(payload, "parameters", context))
      break;

    auto *value = payload.add_parameters();
    value->set_name(parameter->getNameAsString());
    write_type_description(parameter->getType(), *value->mutable_type(),
                           context);
    value->set_is_parameter_pack(parameter->isParameterPack());
  }
  if (const auto *method = llvm::dyn_cast<clang::CXXMethodDecl>(&native)) {
    payload.set_is_const(method->isConst());
    payload.set_is_volatile(method->isVolatile());
    payload.set_is_static(method->isStatic());
    payload.set_ref_qualifier(ref_qualifier(method->getRefQualifier()));
  } else {
    payload.set_is_const(false);
    payload.set_is_volatile(false);
    payload.set_is_static(native.getStorageClass() == clang::SC_Static);
    payload.set_ref_qualifier(pb::REF_QUALIFIER_NONE);
  }
  if (const auto *template_decl = native.getDescribedFunctionTemplate())
    for (const auto *parameter : *template_decl->getTemplateParameters()) {
      if (!can_expand(payload, "template_parameters", context))
        break;
      parameter_description(*parameter, *payload.add_template_parameters(),
                            context);
    }
#if CLANG_VERSION_MAJOR >= 21
  llvm::SmallVector<clang::AssociatedConstraint, 4> constraints;
  if (const auto *template_decl = native.getDescribedFunctionTemplate())
    template_decl->getAssociatedConstraints(constraints);
  else
    native.getAssociatedConstraints(constraints);
  for (const auto &constraint : constraints) {
    if (!can_expand(payload, "associated_constraints", context))
      break;
    constraint_description(*constraint.ConstraintExpr,
                           *payload.add_associated_constraints(), context);
  }
#else
  llvm::SmallVector<const clang::Expr *, 4> constraints;
  if (const auto *template_decl = native.getDescribedFunctionTemplate())
    template_decl->getAssociatedConstraints(constraints);
  else
    native.getAssociatedConstraints(constraints);
  for (const auto *constraint : constraints) {
    if (!can_expand(payload, "associated_constraints", context))
      break;
    constraint_description(*constraint, *payload.add_associated_constraints(),
                           context);
  }
#endif
  const auto *function = native.getType()->getAs<clang::FunctionType>();
  if (!function)
    return;
  auto *calling = payload.mutable_calling_convention();
  type_helpers::write_function_ext(*function, *calling, context);
  if (const auto *prototype =
          llvm::dyn_cast<clang::FunctionProtoType>(function)) {
    auto *exception = payload.mutable_exception_specification();
    exception->set_kind(type_helpers::exception_specification(
        prototype->getExceptionSpecType()));
    if (prototype->getExceptionSpecType() == clang::EST_Dynamic)
      for (auto type : prototype->exceptions()) {
        if (!can_expand(*exception, "exception_types", context))
          break;
        write_type_description(type, *exception->add_exception_types(),
                               context);
      }
    if (clang::isComputedNoexcept(prototype->getExceptionSpecType()) &&
        prototype->getNoexceptExpr())
      constraint_description(*prototype->getNoexceptExpr(),
                             *exception->mutable_dependent_condition(),
                             context);
    if (prototype->getExceptionSpecType() != clang::EST_DependentNoexcept &&
        prototype->getExceptionSpecType() != clang::EST_Unevaluated &&
        prototype->getExceptionSpecType() != clang::EST_Uninstantiated &&
        prototype->getExceptionSpecType() != clang::EST_Unparsed)
      exception->set_is_noexcept(prototype->isNothrow());
  }
}
} // namespace ctk::clang_layer::serialization::helpers
