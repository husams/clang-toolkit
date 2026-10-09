import type * as grpc from '@grpc/grpc-js';
import type { EnumTypeDefinition, MessageTypeDefinition } from '@grpc/proto-loader';

import type { APAddrLabelDiff as _ctk_ast_v1_APAddrLabelDiff, APAddrLabelDiff__Output as _ctk_ast_v1_APAddrLabelDiff__Output } from './ctk/ast/v1/APAddrLabelDiff.js';
import type { APArrayValue as _ctk_ast_v1_APArrayValue, APArrayValue__Output as _ctk_ast_v1_APArrayValue__Output } from './ctk/ast/v1/APArrayValue.js';
import type { APDynamicAllocation as _ctk_ast_v1_APDynamicAllocation, APDynamicAllocation__Output as _ctk_ast_v1_APDynamicAllocation__Output } from './ctk/ast/v1/APDynamicAllocation.js';
import type { APFixedPointBits as _ctk_ast_v1_APFixedPointBits, APFixedPointBits__Output as _ctk_ast_v1_APFixedPointBits__Output } from './ctk/ast/v1/APFixedPointBits.js';
import type { APFloatBits as _ctk_ast_v1_APFloatBits, APFloatBits__Output as _ctk_ast_v1_APFloatBits__Output } from './ctk/ast/v1/APFloatBits.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from './ctk/ast/v1/APIntBits.js';
import type { APLValue as _ctk_ast_v1_APLValue, APLValue__Output as _ctk_ast_v1_APLValue__Output } from './ctk/ast/v1/APLValue.js';
import type { APLValueBase as _ctk_ast_v1_APLValueBase, APLValueBase__Output as _ctk_ast_v1_APLValueBase__Output } from './ctk/ast/v1/APLValueBase.js';
import type { APLValuePathEntry as _ctk_ast_v1_APLValuePathEntry, APLValuePathEntry__Output as _ctk_ast_v1_APLValuePathEntry__Output } from './ctk/ast/v1/APLValuePathEntry.js';
import type { APMemberPointer as _ctk_ast_v1_APMemberPointer, APMemberPointer__Output as _ctk_ast_v1_APMemberPointer__Output } from './ctk/ast/v1/APMemberPointer.js';
import type { APSIntBits as _ctk_ast_v1_APSIntBits, APSIntBits__Output as _ctk_ast_v1_APSIntBits__Output } from './ctk/ast/v1/APSIntBits.js';
import type { APStructBaseValue as _ctk_ast_v1_APStructBaseValue, APStructBaseValue__Output as _ctk_ast_v1_APStructBaseValue__Output } from './ctk/ast/v1/APStructBaseValue.js';
import type { APStructFieldValue as _ctk_ast_v1_APStructFieldValue, APStructFieldValue__Output as _ctk_ast_v1_APStructFieldValue__Output } from './ctk/ast/v1/APStructFieldValue.js';
import type { APStructValue as _ctk_ast_v1_APStructValue, APStructValue__Output as _ctk_ast_v1_APStructValue__Output } from './ctk/ast/v1/APStructValue.js';
import type { APTypeInfoLValue as _ctk_ast_v1_APTypeInfoLValue, APTypeInfoLValue__Output as _ctk_ast_v1_APTypeInfoLValue__Output } from './ctk/ast/v1/APTypeInfoLValue.js';
import type { APUnionValue as _ctk_ast_v1_APUnionValue, APUnionValue__Output as _ctk_ast_v1_APUnionValue__Output } from './ctk/ast/v1/APUnionValue.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from './ctk/ast/v1/APValue.js';
import type { APValueSequence as _ctk_ast_v1_APValueSequence, APValueSequence__Output as _ctk_ast_v1_APValueSequence__Output } from './ctk/ast/v1/APValueSequence.js';
import type { AccessSpecDecl as _ctk_ast_v1_AccessSpecDecl, AccessSpecDecl__Output as _ctk_ast_v1_AccessSpecDecl__Output } from './ctk/ast/v1/AccessSpecDecl.js';
import type { AddrLabelExpr as _ctk_ast_v1_AddrLabelExpr, AddrLabelExpr__Output as _ctk_ast_v1_AddrLabelExpr__Output } from './ctk/ast/v1/AddrLabelExpr.js';
import type { AddressSpace as _ctk_ast_v1_AddressSpace, AddressSpace__Output as _ctk_ast_v1_AddressSpace__Output } from './ctk/ast/v1/AddressSpace.js';
import type { AdjustedType as _ctk_ast_v1_AdjustedType, AdjustedType__Output as _ctk_ast_v1_AdjustedType__Output } from './ctk/ast/v1/AdjustedType.js';
import type { ArrayInitIndexExpr as _ctk_ast_v1_ArrayInitIndexExpr, ArrayInitIndexExpr__Output as _ctk_ast_v1_ArrayInitIndexExpr__Output } from './ctk/ast/v1/ArrayInitIndexExpr.js';
import type { ArrayInitLoopExpr as _ctk_ast_v1_ArrayInitLoopExpr, ArrayInitLoopExpr__Output as _ctk_ast_v1_ArrayInitLoopExpr__Output } from './ctk/ast/v1/ArrayInitLoopExpr.js';
import type { ArraySubscriptExpr as _ctk_ast_v1_ArraySubscriptExpr, ArraySubscriptExpr__Output as _ctk_ast_v1_ArraySubscriptExpr__Output } from './ctk/ast/v1/ArraySubscriptExpr.js';
import type { ArrayTypeTraitExpr as _ctk_ast_v1_ArrayTypeTraitExpr, ArrayTypeTraitExpr__Output as _ctk_ast_v1_ArrayTypeTraitExpr__Output } from './ctk/ast/v1/ArrayTypeTraitExpr.js';
import type { AsmOperand as _ctk_ast_v1_AsmOperand, AsmOperand__Output as _ctk_ast_v1_AsmOperand__Output } from './ctk/ast/v1/AsmOperand.js';
import type { AstNode as _ctk_ast_v1_AstNode, AstNode__Output as _ctk_ast_v1_AstNode__Output } from './ctk/ast/v1/AstNode.js';
import type { AtomicExpr as _ctk_ast_v1_AtomicExpr, AtomicExpr__Output as _ctk_ast_v1_AtomicExpr__Output } from './ctk/ast/v1/AtomicExpr.js';
import type { AtomicType as _ctk_ast_v1_AtomicType, AtomicType__Output as _ctk_ast_v1_AtomicType__Output } from './ctk/ast/v1/AtomicType.js';
import type { AttributeValue as _ctk_ast_v1_AttributeValue, AttributeValue__Output as _ctk_ast_v1_AttributeValue__Output } from './ctk/ast/v1/AttributeValue.js';
import type { AttributedStmt as _ctk_ast_v1_AttributedStmt, AttributedStmt__Output as _ctk_ast_v1_AttributedStmt__Output } from './ctk/ast/v1/AttributedStmt.js';
import type { AttributedType as _ctk_ast_v1_AttributedType, AttributedType__Output as _ctk_ast_v1_AttributedType__Output } from './ctk/ast/v1/AttributedType.js';
import type { AutoType as _ctk_ast_v1_AutoType, AutoType__Output as _ctk_ast_v1_AutoType__Output } from './ctk/ast/v1/AutoType.js';
import type { BTFTagAttributedType as _ctk_ast_v1_BTFTagAttributedType, BTFTagAttributedType__Output as _ctk_ast_v1_BTFTagAttributedType__Output } from './ctk/ast/v1/BTFTagAttributedType.js';
import type { BinaryConditionalOperator as _ctk_ast_v1_BinaryConditionalOperator, BinaryConditionalOperator__Output as _ctk_ast_v1_BinaryConditionalOperator__Output } from './ctk/ast/v1/BinaryConditionalOperator.js';
import type { BinaryOperator as _ctk_ast_v1_BinaryOperator, BinaryOperator__Output as _ctk_ast_v1_BinaryOperator__Output } from './ctk/ast/v1/BinaryOperator.js';
import type { BindingDecl as _ctk_ast_v1_BindingDecl, BindingDecl__Output as _ctk_ast_v1_BindingDecl__Output } from './ctk/ast/v1/BindingDecl.js';
import type { BitIntType as _ctk_ast_v1_BitIntType, BitIntType__Output as _ctk_ast_v1_BitIntType__Output } from './ctk/ast/v1/BitIntType.js';
import type { BlockCaptureInfo as _ctk_ast_v1_BlockCaptureInfo, BlockCaptureInfo__Output as _ctk_ast_v1_BlockCaptureInfo__Output } from './ctk/ast/v1/BlockCaptureInfo.js';
import type { BlockDecl as _ctk_ast_v1_BlockDecl, BlockDecl__Output as _ctk_ast_v1_BlockDecl__Output } from './ctk/ast/v1/BlockDecl.js';
import type { BlockExpr as _ctk_ast_v1_BlockExpr, BlockExpr__Output as _ctk_ast_v1_BlockExpr__Output } from './ctk/ast/v1/BlockExpr.js';
import type { BlockPointerType as _ctk_ast_v1_BlockPointerType, BlockPointerType__Output as _ctk_ast_v1_BlockPointerType__Output } from './ctk/ast/v1/BlockPointerType.js';
import type { BreakStmt as _ctk_ast_v1_BreakStmt, BreakStmt__Output as _ctk_ast_v1_BreakStmt__Output } from './ctk/ast/v1/BreakStmt.js';
import type { BuiltinBitCastExpr as _ctk_ast_v1_BuiltinBitCastExpr, BuiltinBitCastExpr__Output as _ctk_ast_v1_BuiltinBitCastExpr__Output } from './ctk/ast/v1/BuiltinBitCastExpr.js';
import type { BuiltinTemplateDecl as _ctk_ast_v1_BuiltinTemplateDecl, BuiltinTemplateDecl__Output as _ctk_ast_v1_BuiltinTemplateDecl__Output } from './ctk/ast/v1/BuiltinTemplateDecl.js';
import type { BuiltinType as _ctk_ast_v1_BuiltinType, BuiltinType__Output as _ctk_ast_v1_BuiltinType__Output } from './ctk/ast/v1/BuiltinType.js';
import type { CStyleCastExpr as _ctk_ast_v1_CStyleCastExpr, CStyleCastExpr__Output as _ctk_ast_v1_CStyleCastExpr__Output } from './ctk/ast/v1/CStyleCastExpr.js';
import type { CXXAddrspaceCastExpr as _ctk_ast_v1_CXXAddrspaceCastExpr, CXXAddrspaceCastExpr__Output as _ctk_ast_v1_CXXAddrspaceCastExpr__Output } from './ctk/ast/v1/CXXAddrspaceCastExpr.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from './ctk/ast/v1/CXXBaseSpecifier.js';
import type { CXXBindTemporaryExpr as _ctk_ast_v1_CXXBindTemporaryExpr, CXXBindTemporaryExpr__Output as _ctk_ast_v1_CXXBindTemporaryExpr__Output } from './ctk/ast/v1/CXXBindTemporaryExpr.js';
import type { CXXBoolLiteralExpr as _ctk_ast_v1_CXXBoolLiteralExpr, CXXBoolLiteralExpr__Output as _ctk_ast_v1_CXXBoolLiteralExpr__Output } from './ctk/ast/v1/CXXBoolLiteralExpr.js';
import type { CXXCatchStmt as _ctk_ast_v1_CXXCatchStmt, CXXCatchStmt__Output as _ctk_ast_v1_CXXCatchStmt__Output } from './ctk/ast/v1/CXXCatchStmt.js';
import type { CXXConstCastExpr as _ctk_ast_v1_CXXConstCastExpr, CXXConstCastExpr__Output as _ctk_ast_v1_CXXConstCastExpr__Output } from './ctk/ast/v1/CXXConstCastExpr.js';
import type { CXXConstructExpr as _ctk_ast_v1_CXXConstructExpr, CXXConstructExpr__Output as _ctk_ast_v1_CXXConstructExpr__Output } from './ctk/ast/v1/CXXConstructExpr.js';
import type { CXXConstructExprInfo as _ctk_ast_v1_CXXConstructExprInfo, CXXConstructExprInfo__Output as _ctk_ast_v1_CXXConstructExprInfo__Output } from './ctk/ast/v1/CXXConstructExprInfo.js';
import type { CXXConstructorDecl as _ctk_ast_v1_CXXConstructorDecl, CXXConstructorDecl__Output as _ctk_ast_v1_CXXConstructorDecl__Output } from './ctk/ast/v1/CXXConstructorDecl.js';
import type { CXXConversionDecl as _ctk_ast_v1_CXXConversionDecl, CXXConversionDecl__Output as _ctk_ast_v1_CXXConversionDecl__Output } from './ctk/ast/v1/CXXConversionDecl.js';
import type { CXXCtorInitializer as _ctk_ast_v1_CXXCtorInitializer, CXXCtorInitializer__Output as _ctk_ast_v1_CXXCtorInitializer__Output } from './ctk/ast/v1/CXXCtorInitializer.js';
import type { CXXDeductionGuideDecl as _ctk_ast_v1_CXXDeductionGuideDecl, CXXDeductionGuideDecl__Output as _ctk_ast_v1_CXXDeductionGuideDecl__Output } from './ctk/ast/v1/CXXDeductionGuideDecl.js';
import type { CXXDefaultArgExpr as _ctk_ast_v1_CXXDefaultArgExpr, CXXDefaultArgExpr__Output as _ctk_ast_v1_CXXDefaultArgExpr__Output } from './ctk/ast/v1/CXXDefaultArgExpr.js';
import type { CXXDefaultInitExpr as _ctk_ast_v1_CXXDefaultInitExpr, CXXDefaultInitExpr__Output as _ctk_ast_v1_CXXDefaultInitExpr__Output } from './ctk/ast/v1/CXXDefaultInitExpr.js';
import type { CXXDeleteExpr as _ctk_ast_v1_CXXDeleteExpr, CXXDeleteExpr__Output as _ctk_ast_v1_CXXDeleteExpr__Output } from './ctk/ast/v1/CXXDeleteExpr.js';
import type { CXXDependentScopeMemberExpr as _ctk_ast_v1_CXXDependentScopeMemberExpr, CXXDependentScopeMemberExpr__Output as _ctk_ast_v1_CXXDependentScopeMemberExpr__Output } from './ctk/ast/v1/CXXDependentScopeMemberExpr.js';
import type { CXXDestructorDecl as _ctk_ast_v1_CXXDestructorDecl, CXXDestructorDecl__Output as _ctk_ast_v1_CXXDestructorDecl__Output } from './ctk/ast/v1/CXXDestructorDecl.js';
import type { CXXDynamicCastExpr as _ctk_ast_v1_CXXDynamicCastExpr, CXXDynamicCastExpr__Output as _ctk_ast_v1_CXXDynamicCastExpr__Output } from './ctk/ast/v1/CXXDynamicCastExpr.js';
import type { CXXFoldExpr as _ctk_ast_v1_CXXFoldExpr, CXXFoldExpr__Output as _ctk_ast_v1_CXXFoldExpr__Output } from './ctk/ast/v1/CXXFoldExpr.js';
import type { CXXForRangeStmt as _ctk_ast_v1_CXXForRangeStmt, CXXForRangeStmt__Output as _ctk_ast_v1_CXXForRangeStmt__Output } from './ctk/ast/v1/CXXForRangeStmt.js';
import type { CXXFunctionalCastExpr as _ctk_ast_v1_CXXFunctionalCastExpr, CXXFunctionalCastExpr__Output as _ctk_ast_v1_CXXFunctionalCastExpr__Output } from './ctk/ast/v1/CXXFunctionalCastExpr.js';
import type { CXXInheritedCtorInitExpr as _ctk_ast_v1_CXXInheritedCtorInitExpr, CXXInheritedCtorInitExpr__Output as _ctk_ast_v1_CXXInheritedCtorInitExpr__Output } from './ctk/ast/v1/CXXInheritedCtorInitExpr.js';
import type { CXXMemberCallExpr as _ctk_ast_v1_CXXMemberCallExpr, CXXMemberCallExpr__Output as _ctk_ast_v1_CXXMemberCallExpr__Output } from './ctk/ast/v1/CXXMemberCallExpr.js';
import type { CXXMethodDecl as _ctk_ast_v1_CXXMethodDecl, CXXMethodDecl__Output as _ctk_ast_v1_CXXMethodDecl__Output } from './ctk/ast/v1/CXXMethodDecl.js';
import type { CXXMethodDeclInfo as _ctk_ast_v1_CXXMethodDeclInfo, CXXMethodDeclInfo__Output as _ctk_ast_v1_CXXMethodDeclInfo__Output } from './ctk/ast/v1/CXXMethodDeclInfo.js';
import type { CXXNewExpr as _ctk_ast_v1_CXXNewExpr, CXXNewExpr__Output as _ctk_ast_v1_CXXNewExpr__Output } from './ctk/ast/v1/CXXNewExpr.js';
import type { CXXNoexceptExpr as _ctk_ast_v1_CXXNoexceptExpr, CXXNoexceptExpr__Output as _ctk_ast_v1_CXXNoexceptExpr__Output } from './ctk/ast/v1/CXXNoexceptExpr.js';
import type { CXXNullPtrLiteralExpr as _ctk_ast_v1_CXXNullPtrLiteralExpr, CXXNullPtrLiteralExpr__Output as _ctk_ast_v1_CXXNullPtrLiteralExpr__Output } from './ctk/ast/v1/CXXNullPtrLiteralExpr.js';
import type { CXXOperatorCallExpr as _ctk_ast_v1_CXXOperatorCallExpr, CXXOperatorCallExpr__Output as _ctk_ast_v1_CXXOperatorCallExpr__Output } from './ctk/ast/v1/CXXOperatorCallExpr.js';
import type { CXXParenListInitExpr as _ctk_ast_v1_CXXParenListInitExpr, CXXParenListInitExpr__Output as _ctk_ast_v1_CXXParenListInitExpr__Output } from './ctk/ast/v1/CXXParenListInitExpr.js';
import type { CXXPseudoDestructorExpr as _ctk_ast_v1_CXXPseudoDestructorExpr, CXXPseudoDestructorExpr__Output as _ctk_ast_v1_CXXPseudoDestructorExpr__Output } from './ctk/ast/v1/CXXPseudoDestructorExpr.js';
import type { CXXRecordDecl as _ctk_ast_v1_CXXRecordDecl, CXXRecordDecl__Output as _ctk_ast_v1_CXXRecordDecl__Output } from './ctk/ast/v1/CXXRecordDecl.js';
import type { CXXReinterpretCastExpr as _ctk_ast_v1_CXXReinterpretCastExpr, CXXReinterpretCastExpr__Output as _ctk_ast_v1_CXXReinterpretCastExpr__Output } from './ctk/ast/v1/CXXReinterpretCastExpr.js';
import type { CXXRewrittenBinaryOperator as _ctk_ast_v1_CXXRewrittenBinaryOperator, CXXRewrittenBinaryOperator__Output as _ctk_ast_v1_CXXRewrittenBinaryOperator__Output } from './ctk/ast/v1/CXXRewrittenBinaryOperator.js';
import type { CXXScalarValueInitExpr as _ctk_ast_v1_CXXScalarValueInitExpr, CXXScalarValueInitExpr__Output as _ctk_ast_v1_CXXScalarValueInitExpr__Output } from './ctk/ast/v1/CXXScalarValueInitExpr.js';
import type { CXXStaticCastExpr as _ctk_ast_v1_CXXStaticCastExpr, CXXStaticCastExpr__Output as _ctk_ast_v1_CXXStaticCastExpr__Output } from './ctk/ast/v1/CXXStaticCastExpr.js';
import type { CXXStdInitializerListExpr as _ctk_ast_v1_CXXStdInitializerListExpr, CXXStdInitializerListExpr__Output as _ctk_ast_v1_CXXStdInitializerListExpr__Output } from './ctk/ast/v1/CXXStdInitializerListExpr.js';
import type { CXXTemporary as _ctk_ast_v1_CXXTemporary, CXXTemporary__Output as _ctk_ast_v1_CXXTemporary__Output } from './ctk/ast/v1/CXXTemporary.js';
import type { CXXTemporaryObjectExpr as _ctk_ast_v1_CXXTemporaryObjectExpr, CXXTemporaryObjectExpr__Output as _ctk_ast_v1_CXXTemporaryObjectExpr__Output } from './ctk/ast/v1/CXXTemporaryObjectExpr.js';
import type { CXXThisExpr as _ctk_ast_v1_CXXThisExpr, CXXThisExpr__Output as _ctk_ast_v1_CXXThisExpr__Output } from './ctk/ast/v1/CXXThisExpr.js';
import type { CXXThrowExpr as _ctk_ast_v1_CXXThrowExpr, CXXThrowExpr__Output as _ctk_ast_v1_CXXThrowExpr__Output } from './ctk/ast/v1/CXXThrowExpr.js';
import type { CXXTryStmt as _ctk_ast_v1_CXXTryStmt, CXXTryStmt__Output as _ctk_ast_v1_CXXTryStmt__Output } from './ctk/ast/v1/CXXTryStmt.js';
import type { CXXTypeidExpr as _ctk_ast_v1_CXXTypeidExpr, CXXTypeidExpr__Output as _ctk_ast_v1_CXXTypeidExpr__Output } from './ctk/ast/v1/CXXTypeidExpr.js';
import type { CXXUnresolvedConstructExpr as _ctk_ast_v1_CXXUnresolvedConstructExpr, CXXUnresolvedConstructExpr__Output as _ctk_ast_v1_CXXUnresolvedConstructExpr__Output } from './ctk/ast/v1/CXXUnresolvedConstructExpr.js';
import type { CXXUuidofExpr as _ctk_ast_v1_CXXUuidofExpr, CXXUuidofExpr__Output as _ctk_ast_v1_CXXUuidofExpr__Output } from './ctk/ast/v1/CXXUuidofExpr.js';
import type { CallExpr as _ctk_ast_v1_CallExpr, CallExpr__Output as _ctk_ast_v1_CallExpr__Output } from './ctk/ast/v1/CallExpr.js';
import type { CallExprInfo as _ctk_ast_v1_CallExprInfo, CallExprInfo__Output as _ctk_ast_v1_CallExprInfo__Output } from './ctk/ast/v1/CallExprInfo.js';
import type { CaseStmt as _ctk_ast_v1_CaseStmt, CaseStmt__Output as _ctk_ast_v1_CaseStmt__Output } from './ctk/ast/v1/CaseStmt.js';
import type { CastExprInfo as _ctk_ast_v1_CastExprInfo, CastExprInfo__Output as _ctk_ast_v1_CastExprInfo__Output } from './ctk/ast/v1/CastExprInfo.js';
import type { CharacterLiteral as _ctk_ast_v1_CharacterLiteral, CharacterLiteral__Output as _ctk_ast_v1_CharacterLiteral__Output } from './ctk/ast/v1/CharacterLiteral.js';
import type { ChooseExpr as _ctk_ast_v1_ChooseExpr, ChooseExpr__Output as _ctk_ast_v1_ChooseExpr__Output } from './ctk/ast/v1/ChooseExpr.js';
import type { ClassTemplateDecl as _ctk_ast_v1_ClassTemplateDecl, ClassTemplateDecl__Output as _ctk_ast_v1_ClassTemplateDecl__Output } from './ctk/ast/v1/ClassTemplateDecl.js';
import type { ClassTemplatePartialSpecializationDecl as _ctk_ast_v1_ClassTemplatePartialSpecializationDecl, ClassTemplatePartialSpecializationDecl__Output as _ctk_ast_v1_ClassTemplatePartialSpecializationDecl__Output } from './ctk/ast/v1/ClassTemplatePartialSpecializationDecl.js';
import type { ClassTemplateSpecializationDecl as _ctk_ast_v1_ClassTemplateSpecializationDecl, ClassTemplateSpecializationDecl__Output as _ctk_ast_v1_ClassTemplateSpecializationDecl__Output } from './ctk/ast/v1/ClassTemplateSpecializationDecl.js';
import type { CleanupValue as _ctk_ast_v1_CleanupValue, CleanupValue__Output as _ctk_ast_v1_CleanupValue__Output } from './ctk/ast/v1/CleanupValue.js';
import type { CoawaitExpr as _ctk_ast_v1_CoawaitExpr, CoawaitExpr__Output as _ctk_ast_v1_CoawaitExpr__Output } from './ctk/ast/v1/CoawaitExpr.js';
import type { ComplexFloatValue as _ctk_ast_v1_ComplexFloatValue, ComplexFloatValue__Output as _ctk_ast_v1_ComplexFloatValue__Output } from './ctk/ast/v1/ComplexFloatValue.js';
import type { ComplexIntValue as _ctk_ast_v1_ComplexIntValue, ComplexIntValue__Output as _ctk_ast_v1_ComplexIntValue__Output } from './ctk/ast/v1/ComplexIntValue.js';
import type { ComplexType as _ctk_ast_v1_ComplexType, ComplexType__Output as _ctk_ast_v1_ComplexType__Output } from './ctk/ast/v1/ComplexType.js';
import type { CompoundAssignOperator as _ctk_ast_v1_CompoundAssignOperator, CompoundAssignOperator__Output as _ctk_ast_v1_CompoundAssignOperator__Output } from './ctk/ast/v1/CompoundAssignOperator.js';
import type { CompoundLiteralExpr as _ctk_ast_v1_CompoundLiteralExpr, CompoundLiteralExpr__Output as _ctk_ast_v1_CompoundLiteralExpr__Output } from './ctk/ast/v1/CompoundLiteralExpr.js';
import type { CompoundStmt as _ctk_ast_v1_CompoundStmt, CompoundStmt__Output as _ctk_ast_v1_CompoundStmt__Output } from './ctk/ast/v1/CompoundStmt.js';
import type { ConceptDecl as _ctk_ast_v1_ConceptDecl, ConceptDecl__Output as _ctk_ast_v1_ConceptDecl__Output } from './ctk/ast/v1/ConceptDecl.js';
import type { ConceptReference as _ctk_ast_v1_ConceptReference, ConceptReference__Output as _ctk_ast_v1_ConceptReference__Output } from './ctk/ast/v1/ConceptReference.js';
import type { ConceptRequirement as _ctk_ast_v1_ConceptRequirement, ConceptRequirement__Output as _ctk_ast_v1_ConceptRequirement__Output } from './ctk/ast/v1/ConceptRequirement.js';
import type { ConceptSpecializationExpr as _ctk_ast_v1_ConceptSpecializationExpr, ConceptSpecializationExpr__Output as _ctk_ast_v1_ConceptSpecializationExpr__Output } from './ctk/ast/v1/ConceptSpecializationExpr.js';
import type { ConditionalOperator as _ctk_ast_v1_ConditionalOperator, ConditionalOperator__Output as _ctk_ast_v1_ConditionalOperator__Output } from './ctk/ast/v1/ConditionalOperator.js';
import type { ConstantArrayType as _ctk_ast_v1_ConstantArrayType, ConstantArrayType__Output as _ctk_ast_v1_ConstantArrayType__Output } from './ctk/ast/v1/ConstantArrayType.js';
import type { ConstantExpr as _ctk_ast_v1_ConstantExpr, ConstantExpr__Output as _ctk_ast_v1_ConstantExpr__Output } from './ctk/ast/v1/ConstantExpr.js';
import type { ConstantMatrixType as _ctk_ast_v1_ConstantMatrixType, ConstantMatrixType__Output as _ctk_ast_v1_ConstantMatrixType__Output } from './ctk/ast/v1/ConstantMatrixType.js';
import type { ConstraintDescription as _ctk_ast_v1_ConstraintDescription, ConstraintDescription__Output as _ctk_ast_v1_ConstraintDescription__Output } from './ctk/ast/v1/ConstraintDescription.js';
import type { ConstraintDetail as _ctk_ast_v1_ConstraintDetail, ConstraintDetail__Output as _ctk_ast_v1_ConstraintDetail__Output } from './ctk/ast/v1/ConstraintDetail.js';
import type { ConstraintSatisfaction as _ctk_ast_v1_ConstraintSatisfaction, ConstraintSatisfaction__Output as _ctk_ast_v1_ConstraintSatisfaction__Output } from './ctk/ast/v1/ConstraintSatisfaction.js';
import type { ConstructorUsingShadowDecl as _ctk_ast_v1_ConstructorUsingShadowDecl, ConstructorUsingShadowDecl__Output as _ctk_ast_v1_ConstructorUsingShadowDecl__Output } from './ctk/ast/v1/ConstructorUsingShadowDecl.js';
import type { ContinueStmt as _ctk_ast_v1_ContinueStmt, ContinueStmt__Output as _ctk_ast_v1_ContinueStmt__Output } from './ctk/ast/v1/ContinueStmt.js';
import type { ConvertVectorExpr as _ctk_ast_v1_ConvertVectorExpr, ConvertVectorExpr__Output as _ctk_ast_v1_ConvertVectorExpr__Output } from './ctk/ast/v1/ConvertVectorExpr.js';
import type { CoreturnStmt as _ctk_ast_v1_CoreturnStmt, CoreturnStmt__Output as _ctk_ast_v1_CoreturnStmt__Output } from './ctk/ast/v1/CoreturnStmt.js';
import type { CoroutineBodyStmt as _ctk_ast_v1_CoroutineBodyStmt, CoroutineBodyStmt__Output as _ctk_ast_v1_CoroutineBodyStmt__Output } from './ctk/ast/v1/CoroutineBodyStmt.js';
import type { CountAttributedType as _ctk_ast_v1_CountAttributedType, CountAttributedType__Output as _ctk_ast_v1_CountAttributedType__Output } from './ctk/ast/v1/CountAttributedType.js';
import type { CoyieldExpr as _ctk_ast_v1_CoyieldExpr, CoyieldExpr__Output as _ctk_ast_v1_CoyieldExpr__Output } from './ctk/ast/v1/CoyieldExpr.js';
import type { DecayedType as _ctk_ast_v1_DecayedType, DecayedType__Output as _ctk_ast_v1_DecayedType__Output } from './ctk/ast/v1/DecayedType.js';
import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from './ctk/ast/v1/DeclInfo.js';
import type { DeclRefExpr as _ctk_ast_v1_DeclRefExpr, DeclRefExpr__Output as _ctk_ast_v1_DeclRefExpr__Output } from './ctk/ast/v1/DeclRefExpr.js';
import type { DeclStmt as _ctk_ast_v1_DeclStmt, DeclStmt__Output as _ctk_ast_v1_DeclStmt__Output } from './ctk/ast/v1/DeclStmt.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from './ctk/ast/v1/DeclarationName.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from './ctk/ast/v1/DeclarationSymbol.js';
import type { DeclarationTemplateArgument as _ctk_ast_v1_DeclarationTemplateArgument, DeclarationTemplateArgument__Output as _ctk_ast_v1_DeclarationTemplateArgument__Output } from './ctk/ast/v1/DeclarationTemplateArgument.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from './ctk/ast/v1/DeclarationValue.js';
import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from './ctk/ast/v1/DeclaratorDeclInfo.js';
import type { DecltypeType as _ctk_ast_v1_DecltypeType, DecltypeType__Output as _ctk_ast_v1_DecltypeType__Output } from './ctk/ast/v1/DecltypeType.js';
import type { DecompositionDecl as _ctk_ast_v1_DecompositionDecl, DecompositionDecl__Output as _ctk_ast_v1_DecompositionDecl__Output } from './ctk/ast/v1/DecompositionDecl.js';
import type { DeducedTemplateName as _ctk_ast_v1_DeducedTemplateName, DeducedTemplateName__Output as _ctk_ast_v1_DeducedTemplateName__Output } from './ctk/ast/v1/DeducedTemplateName.js';
import type { DeducedTemplateSpecializationType as _ctk_ast_v1_DeducedTemplateSpecializationType, DeducedTemplateSpecializationType__Output as _ctk_ast_v1_DeducedTemplateSpecializationType__Output } from './ctk/ast/v1/DeducedTemplateSpecializationType.js';
import type { DefaultStmt as _ctk_ast_v1_DefaultStmt, DefaultStmt__Output as _ctk_ast_v1_DefaultStmt__Output } from './ctk/ast/v1/DefaultStmt.js';
import type { DependentAddressSpaceType as _ctk_ast_v1_DependentAddressSpaceType, DependentAddressSpaceType__Output as _ctk_ast_v1_DependentAddressSpaceType__Output } from './ctk/ast/v1/DependentAddressSpaceType.js';
import type { DependentBitIntType as _ctk_ast_v1_DependentBitIntType, DependentBitIntType__Output as _ctk_ast_v1_DependentBitIntType__Output } from './ctk/ast/v1/DependentBitIntType.js';
import type { DependentCoawaitExpr as _ctk_ast_v1_DependentCoawaitExpr, DependentCoawaitExpr__Output as _ctk_ast_v1_DependentCoawaitExpr__Output } from './ctk/ast/v1/DependentCoawaitExpr.js';
import type { DependentDecltypeType as _ctk_ast_v1_DependentDecltypeType, DependentDecltypeType__Output as _ctk_ast_v1_DependentDecltypeType__Output } from './ctk/ast/v1/DependentDecltypeType.js';
import type { DependentNameType as _ctk_ast_v1_DependentNameType, DependentNameType__Output as _ctk_ast_v1_DependentNameType__Output } from './ctk/ast/v1/DependentNameType.js';
import type { DependentScopeDeclRefExpr as _ctk_ast_v1_DependentScopeDeclRefExpr, DependentScopeDeclRefExpr__Output as _ctk_ast_v1_DependentScopeDeclRefExpr__Output } from './ctk/ast/v1/DependentScopeDeclRefExpr.js';
import type { DependentSizedArrayType as _ctk_ast_v1_DependentSizedArrayType, DependentSizedArrayType__Output as _ctk_ast_v1_DependentSizedArrayType__Output } from './ctk/ast/v1/DependentSizedArrayType.js';
import type { DependentSizedExtVectorType as _ctk_ast_v1_DependentSizedExtVectorType, DependentSizedExtVectorType__Output as _ctk_ast_v1_DependentSizedExtVectorType__Output } from './ctk/ast/v1/DependentSizedExtVectorType.js';
import type { DependentSizedMatrixType as _ctk_ast_v1_DependentSizedMatrixType, DependentSizedMatrixType__Output as _ctk_ast_v1_DependentSizedMatrixType__Output } from './ctk/ast/v1/DependentSizedMatrixType.js';
import type { DependentTemplateName as _ctk_ast_v1_DependentTemplateName, DependentTemplateName__Output as _ctk_ast_v1_DependentTemplateName__Output } from './ctk/ast/v1/DependentTemplateName.js';
import type { DependentTypeOfExprType as _ctk_ast_v1_DependentTypeOfExprType, DependentTypeOfExprType__Output as _ctk_ast_v1_DependentTypeOfExprType__Output } from './ctk/ast/v1/DependentTypeOfExprType.js';
import type { DependentVectorType as _ctk_ast_v1_DependentVectorType, DependentVectorType__Output as _ctk_ast_v1_DependentVectorType__Output } from './ctk/ast/v1/DependentVectorType.js';
import type { DesignatedInitExpr as _ctk_ast_v1_DesignatedInitExpr, DesignatedInitExpr__Output as _ctk_ast_v1_DesignatedInitExpr__Output } from './ctk/ast/v1/DesignatedInitExpr.js';
import type { DesignatedInitUpdateExpr as _ctk_ast_v1_DesignatedInitUpdateExpr, DesignatedInitUpdateExpr__Output as _ctk_ast_v1_DesignatedInitUpdateExpr__Output } from './ctk/ast/v1/DesignatedInitUpdateExpr.js';
import type { Designator as _ctk_ast_v1_Designator, Designator__Output as _ctk_ast_v1_Designator__Output } from './ctk/ast/v1/Designator.js';
import type { DoStmt as _ctk_ast_v1_DoStmt, DoStmt__Output as _ctk_ast_v1_DoStmt__Output } from './ctk/ast/v1/DoStmt.js';
import type { EmbedExpr as _ctk_ast_v1_EmbedExpr, EmbedExpr__Output as _ctk_ast_v1_EmbedExpr__Output } from './ctk/ast/v1/EmbedExpr.js';
import type { EmbedParameter as _ctk_ast_v1_EmbedParameter, EmbedParameter__Output as _ctk_ast_v1_EmbedParameter__Output } from './ctk/ast/v1/EmbedParameter.js';
import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from './ctk/ast/v1/Empty.js';
import type { EmptyDecl as _ctk_ast_v1_EmptyDecl, EmptyDecl__Output as _ctk_ast_v1_EmptyDecl__Output } from './ctk/ast/v1/EmptyDecl.js';
import type { EnumConstantDecl as _ctk_ast_v1_EnumConstantDecl, EnumConstantDecl__Output as _ctk_ast_v1_EnumConstantDecl__Output } from './ctk/ast/v1/EnumConstantDecl.js';
import type { EnumDecl as _ctk_ast_v1_EnumDecl, EnumDecl__Output as _ctk_ast_v1_EnumDecl__Output } from './ctk/ast/v1/EnumDecl.js';
import type { EnumType as _ctk_ast_v1_EnumType, EnumType__Output as _ctk_ast_v1_EnumType__Output } from './ctk/ast/v1/EnumType.js';
import type { ExceptionDescription as _ctk_ast_v1_ExceptionDescription, ExceptionDescription__Output as _ctk_ast_v1_ExceptionDescription__Output } from './ctk/ast/v1/ExceptionDescription.js';
import type { ExportDecl as _ctk_ast_v1_ExportDecl, ExportDecl__Output as _ctk_ast_v1_ExportDecl__Output } from './ctk/ast/v1/ExportDecl.js';
import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from './ctk/ast/v1/ExprInfo.js';
import type { ExprRequirement as _ctk_ast_v1_ExprRequirement, ExprRequirement__Output as _ctk_ast_v1_ExprRequirement__Output } from './ctk/ast/v1/ExprRequirement.js';
import type { ExprWithCleanups as _ctk_ast_v1_ExprWithCleanups, ExprWithCleanups__Output as _ctk_ast_v1_ExprWithCleanups__Output } from './ctk/ast/v1/ExprWithCleanups.js';
import type { ExpressionTraitExpr as _ctk_ast_v1_ExpressionTraitExpr, ExpressionTraitExpr__Output as _ctk_ast_v1_ExpressionTraitExpr__Output } from './ctk/ast/v1/ExpressionTraitExpr.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from './ctk/ast/v1/ExpressionValue.js';
import type { ExtVectorElementExpr as _ctk_ast_v1_ExtVectorElementExpr, ExtVectorElementExpr__Output as _ctk_ast_v1_ExtVectorElementExpr__Output } from './ctk/ast/v1/ExtVectorElementExpr.js';
import type { ExtVectorType as _ctk_ast_v1_ExtVectorType, ExtVectorType__Output as _ctk_ast_v1_ExtVectorType__Output } from './ctk/ast/v1/ExtVectorType.js';
import type { ExternCContextDecl as _ctk_ast_v1_ExternCContextDecl, ExternCContextDecl__Output as _ctk_ast_v1_ExternCContextDecl__Output } from './ctk/ast/v1/ExternCContextDecl.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from './ctk/ast/v1/FieldAvailability.js';
import type { FieldDecl as _ctk_ast_v1_FieldDecl, FieldDecl__Output as _ctk_ast_v1_FieldDecl__Output } from './ctk/ast/v1/FieldDecl.js';
import type { FileScopeAsmDecl as _ctk_ast_v1_FileScopeAsmDecl, FileScopeAsmDecl__Output as _ctk_ast_v1_FileScopeAsmDecl__Output } from './ctk/ast/v1/FileScopeAsmDecl.js';
import type { FixedPointLiteral as _ctk_ast_v1_FixedPointLiteral, FixedPointLiteral__Output as _ctk_ast_v1_FixedPointLiteral__Output } from './ctk/ast/v1/FixedPointLiteral.js';
import type { FloatingLiteral as _ctk_ast_v1_FloatingLiteral, FloatingLiteral__Output as _ctk_ast_v1_FloatingLiteral__Output } from './ctk/ast/v1/FloatingLiteral.js';
import type { ForStmt as _ctk_ast_v1_ForStmt, ForStmt__Output as _ctk_ast_v1_ForStmt__Output } from './ctk/ast/v1/ForStmt.js';
import type { FriendDecl as _ctk_ast_v1_FriendDecl, FriendDecl__Output as _ctk_ast_v1_FriendDecl__Output } from './ctk/ast/v1/FriendDecl.js';
import type { FriendTemplateDecl as _ctk_ast_v1_FriendTemplateDecl, FriendTemplateDecl__Output as _ctk_ast_v1_FriendTemplateDecl__Output } from './ctk/ast/v1/FriendTemplateDecl.js';
import type { FunctionDecl as _ctk_ast_v1_FunctionDecl, FunctionDecl__Output as _ctk_ast_v1_FunctionDecl__Output } from './ctk/ast/v1/FunctionDecl.js';
import type { FunctionDeclInfo as _ctk_ast_v1_FunctionDeclInfo, FunctionDeclInfo__Output as _ctk_ast_v1_FunctionDeclInfo__Output } from './ctk/ast/v1/FunctionDeclInfo.js';
import type { FunctionExtInfo as _ctk_ast_v1_FunctionExtInfo, FunctionExtInfo__Output as _ctk_ast_v1_FunctionExtInfo__Output } from './ctk/ast/v1/FunctionExtInfo.js';
import type { FunctionParmPackExpr as _ctk_ast_v1_FunctionParmPackExpr, FunctionParmPackExpr__Output as _ctk_ast_v1_FunctionParmPackExpr__Output } from './ctk/ast/v1/FunctionParmPackExpr.js';
import type { FunctionProtoExtInfo as _ctk_ast_v1_FunctionProtoExtInfo, FunctionProtoExtInfo__Output as _ctk_ast_v1_FunctionProtoExtInfo__Output } from './ctk/ast/v1/FunctionProtoExtInfo.js';
import type { FunctionProtoType as _ctk_ast_v1_FunctionProtoType, FunctionProtoType__Output as _ctk_ast_v1_FunctionProtoType__Output } from './ctk/ast/v1/FunctionProtoType.js';
import type { FunctionSignature as _ctk_ast_v1_FunctionSignature, FunctionSignature__Output as _ctk_ast_v1_FunctionSignature__Output } from './ctk/ast/v1/FunctionSignature.js';
import type { FunctionTemplateDecl as _ctk_ast_v1_FunctionTemplateDecl, FunctionTemplateDecl__Output as _ctk_ast_v1_FunctionTemplateDecl__Output } from './ctk/ast/v1/FunctionTemplateDecl.js';
import type { GCCAsmStmt as _ctk_ast_v1_GCCAsmStmt, GCCAsmStmt__Output as _ctk_ast_v1_GCCAsmStmt__Output } from './ctk/ast/v1/GCCAsmStmt.js';
import type { GNUNullExpr as _ctk_ast_v1_GNUNullExpr, GNUNullExpr__Output as _ctk_ast_v1_GNUNullExpr__Output } from './ctk/ast/v1/GNUNullExpr.js';
import type { GenericAssociation as _ctk_ast_v1_GenericAssociation, GenericAssociation__Output as _ctk_ast_v1_GenericAssociation__Output } from './ctk/ast/v1/GenericAssociation.js';
import type { GenericSelectionExpr as _ctk_ast_v1_GenericSelectionExpr, GenericSelectionExpr__Output as _ctk_ast_v1_GenericSelectionExpr__Output } from './ctk/ast/v1/GenericSelectionExpr.js';
import type { GotoStmt as _ctk_ast_v1_GotoStmt, GotoStmt__Output as _ctk_ast_v1_GotoStmt__Output } from './ctk/ast/v1/GotoStmt.js';
import type { IfStmt as _ctk_ast_v1_IfStmt, IfStmt__Output as _ctk_ast_v1_IfStmt__Output } from './ctk/ast/v1/IfStmt.js';
import type { ImaginaryLiteral as _ctk_ast_v1_ImaginaryLiteral, ImaginaryLiteral__Output as _ctk_ast_v1_ImaginaryLiteral__Output } from './ctk/ast/v1/ImaginaryLiteral.js';
import type { ImplicitCastExpr as _ctk_ast_v1_ImplicitCastExpr, ImplicitCastExpr__Output as _ctk_ast_v1_ImplicitCastExpr__Output } from './ctk/ast/v1/ImplicitCastExpr.js';
import type { ImplicitConceptSpecializationDecl as _ctk_ast_v1_ImplicitConceptSpecializationDecl, ImplicitConceptSpecializationDecl__Output as _ctk_ast_v1_ImplicitConceptSpecializationDecl__Output } from './ctk/ast/v1/ImplicitConceptSpecializationDecl.js';
import type { ImplicitParamDecl as _ctk_ast_v1_ImplicitParamDecl, ImplicitParamDecl__Output as _ctk_ast_v1_ImplicitParamDecl__Output } from './ctk/ast/v1/ImplicitParamDecl.js';
import type { ImplicitValueInitExpr as _ctk_ast_v1_ImplicitValueInitExpr, ImplicitValueInitExpr__Output as _ctk_ast_v1_ImplicitValueInitExpr__Output } from './ctk/ast/v1/ImplicitValueInitExpr.js';
import type { ImportDecl as _ctk_ast_v1_ImportDecl, ImportDecl__Output as _ctk_ast_v1_ImportDecl__Output } from './ctk/ast/v1/ImportDecl.js';
import type { IncompleteArrayType as _ctk_ast_v1_IncompleteArrayType, IncompleteArrayType__Output as _ctk_ast_v1_IncompleteArrayType__Output } from './ctk/ast/v1/IncompleteArrayType.js';
import type { IndirectFieldDecl as _ctk_ast_v1_IndirectFieldDecl, IndirectFieldDecl__Output as _ctk_ast_v1_IndirectFieldDecl__Output } from './ctk/ast/v1/IndirectFieldDecl.js';
import type { IndirectGotoStmt as _ctk_ast_v1_IndirectGotoStmt, IndirectGotoStmt__Output as _ctk_ast_v1_IndirectGotoStmt__Output } from './ctk/ast/v1/IndirectGotoStmt.js';
import type { InitListExpr as _ctk_ast_v1_InitListExpr, InitListExpr__Output as _ctk_ast_v1_InitListExpr__Output } from './ctk/ast/v1/InitListExpr.js';
import type { InjectedClassNameType as _ctk_ast_v1_InjectedClassNameType, InjectedClassNameType__Output as _ctk_ast_v1_InjectedClassNameType__Output } from './ctk/ast/v1/InjectedClassNameType.js';
import type { IntegerLiteral as _ctk_ast_v1_IntegerLiteral, IntegerLiteral__Output as _ctk_ast_v1_IntegerLiteral__Output } from './ctk/ast/v1/IntegerLiteral.js';
import type { IntegralTemplateArgument as _ctk_ast_v1_IntegralTemplateArgument, IntegralTemplateArgument__Output as _ctk_ast_v1_IntegralTemplateArgument__Output } from './ctk/ast/v1/IntegralTemplateArgument.js';
import type { LValueReferenceType as _ctk_ast_v1_LValueReferenceType, LValueReferenceType__Output as _ctk_ast_v1_LValueReferenceType__Output } from './ctk/ast/v1/LValueReferenceType.js';
import type { LabelDecl as _ctk_ast_v1_LabelDecl, LabelDecl__Output as _ctk_ast_v1_LabelDecl__Output } from './ctk/ast/v1/LabelDecl.js';
import type { LabelStmt as _ctk_ast_v1_LabelStmt, LabelStmt__Output as _ctk_ast_v1_LabelStmt__Output } from './ctk/ast/v1/LabelStmt.js';
import type { LambdaCapture as _ctk_ast_v1_LambdaCapture, LambdaCapture__Output as _ctk_ast_v1_LambdaCapture__Output } from './ctk/ast/v1/LambdaCapture.js';
import type { LambdaExpr as _ctk_ast_v1_LambdaExpr, LambdaExpr__Output as _ctk_ast_v1_LambdaExpr__Output } from './ctk/ast/v1/LambdaExpr.js';
import type { LifetimeExtendedTemporaryDecl as _ctk_ast_v1_LifetimeExtendedTemporaryDecl, LifetimeExtendedTemporaryDecl__Output as _ctk_ast_v1_LifetimeExtendedTemporaryDecl__Output } from './ctk/ast/v1/LifetimeExtendedTemporaryDecl.js';
import type { LinkageSpecDecl as _ctk_ast_v1_LinkageSpecDecl, LinkageSpecDecl__Output as _ctk_ast_v1_LinkageSpecDecl__Output } from './ctk/ast/v1/LinkageSpecDecl.js';
import type { MSAsmStmt as _ctk_ast_v1_MSAsmStmt, MSAsmStmt__Output as _ctk_ast_v1_MSAsmStmt__Output } from './ctk/ast/v1/MSAsmStmt.js';
import type { MSDependentExistsStmt as _ctk_ast_v1_MSDependentExistsStmt, MSDependentExistsStmt__Output as _ctk_ast_v1_MSDependentExistsStmt__Output } from './ctk/ast/v1/MSDependentExistsStmt.js';
import type { MSGuidDecl as _ctk_ast_v1_MSGuidDecl, MSGuidDecl__Output as _ctk_ast_v1_MSGuidDecl__Output } from './ctk/ast/v1/MSGuidDecl.js';
import type { MSPropertyDecl as _ctk_ast_v1_MSPropertyDecl, MSPropertyDecl__Output as _ctk_ast_v1_MSPropertyDecl__Output } from './ctk/ast/v1/MSPropertyDecl.js';
import type { MSPropertyRefExpr as _ctk_ast_v1_MSPropertyRefExpr, MSPropertyRefExpr__Output as _ctk_ast_v1_MSPropertyRefExpr__Output } from './ctk/ast/v1/MSPropertyRefExpr.js';
import type { MSPropertySubscriptExpr as _ctk_ast_v1_MSPropertySubscriptExpr, MSPropertySubscriptExpr__Output as _ctk_ast_v1_MSPropertySubscriptExpr__Output } from './ctk/ast/v1/MSPropertySubscriptExpr.js';
import type { MacroQualifiedType as _ctk_ast_v1_MacroQualifiedType, MacroQualifiedType__Output as _ctk_ast_v1_MacroQualifiedType__Output } from './ctk/ast/v1/MacroQualifiedType.js';
import type { MaterializeTemporaryExpr as _ctk_ast_v1_MaterializeTemporaryExpr, MaterializeTemporaryExpr__Output as _ctk_ast_v1_MaterializeTemporaryExpr__Output } from './ctk/ast/v1/MaterializeTemporaryExpr.js';
import type { MatrixSingleSubscriptExpr as _ctk_ast_v1_MatrixSingleSubscriptExpr, MatrixSingleSubscriptExpr__Output as _ctk_ast_v1_MatrixSingleSubscriptExpr__Output } from './ctk/ast/v1/MatrixSingleSubscriptExpr.js';
import type { MatrixSubscriptExpr as _ctk_ast_v1_MatrixSubscriptExpr, MatrixSubscriptExpr__Output as _ctk_ast_v1_MatrixSubscriptExpr__Output } from './ctk/ast/v1/MatrixSubscriptExpr.js';
import type { MemberExpr as _ctk_ast_v1_MemberExpr, MemberExpr__Output as _ctk_ast_v1_MemberExpr__Output } from './ctk/ast/v1/MemberExpr.js';
import type { MemberPointerType as _ctk_ast_v1_MemberPointerType, MemberPointerType__Output as _ctk_ast_v1_MemberPointerType__Output } from './ctk/ast/v1/MemberPointerType.js';
import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from './ctk/ast/v1/NamedDeclInfo.js';
import type { NamespaceAliasDecl as _ctk_ast_v1_NamespaceAliasDecl, NamespaceAliasDecl__Output as _ctk_ast_v1_NamespaceAliasDecl__Output } from './ctk/ast/v1/NamespaceAliasDecl.js';
import type { NamespaceDecl as _ctk_ast_v1_NamespaceDecl, NamespaceDecl__Output as _ctk_ast_v1_NamespaceDecl__Output } from './ctk/ast/v1/NamespaceDecl.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from './ctk/ast/v1/NestedNameSpecifier.js';
import type { NestedNamespaceName as _ctk_ast_v1_NestedNamespaceName, NestedNamespaceName__Output as _ctk_ast_v1_NestedNamespaceName__Output } from './ctk/ast/v1/NestedNamespaceName.js';
import type { NestedRequirement as _ctk_ast_v1_NestedRequirement, NestedRequirement__Output as _ctk_ast_v1_NestedRequirement__Output } from './ctk/ast/v1/NestedRequirement.js';
import type { NoInitExpr as _ctk_ast_v1_NoInitExpr, NoInitExpr__Output as _ctk_ast_v1_NoInitExpr__Output } from './ctk/ast/v1/NoInitExpr.js';
import type { NonTypeTemplateParmDecl as _ctk_ast_v1_NonTypeTemplateParmDecl, NonTypeTemplateParmDecl__Output as _ctk_ast_v1_NonTypeTemplateParmDecl__Output } from './ctk/ast/v1/NonTypeTemplateParmDecl.js';
import type { NullStmt as _ctk_ast_v1_NullStmt, NullStmt__Output as _ctk_ast_v1_NullStmt__Output } from './ctk/ast/v1/NullStmt.js';
import type { OffsetOfComponent as _ctk_ast_v1_OffsetOfComponent, OffsetOfComponent__Output as _ctk_ast_v1_OffsetOfComponent__Output } from './ctk/ast/v1/OffsetOfComponent.js';
import type { OffsetOfExpr as _ctk_ast_v1_OffsetOfExpr, OffsetOfExpr__Output as _ctk_ast_v1_OffsetOfExpr__Output } from './ctk/ast/v1/OffsetOfExpr.js';
import type { OpaqueValueExpr as _ctk_ast_v1_OpaqueValueExpr, OpaqueValueExpr__Output as _ctk_ast_v1_OpaqueValueExpr__Output } from './ctk/ast/v1/OpaqueValueExpr.js';
import type { OverloadedTemplateName as _ctk_ast_v1_OverloadedTemplateName, OverloadedTemplateName__Output as _ctk_ast_v1_OverloadedTemplateName__Output } from './ctk/ast/v1/OverloadedTemplateName.js';
import type { PackExpansionExpr as _ctk_ast_v1_PackExpansionExpr, PackExpansionExpr__Output as _ctk_ast_v1_PackExpansionExpr__Output } from './ctk/ast/v1/PackExpansionExpr.js';
import type { PackExpansionType as _ctk_ast_v1_PackExpansionType, PackExpansionType__Output as _ctk_ast_v1_PackExpansionType__Output } from './ctk/ast/v1/PackExpansionType.js';
import type { PackIndexingExpr as _ctk_ast_v1_PackIndexingExpr, PackIndexingExpr__Output as _ctk_ast_v1_PackIndexingExpr__Output } from './ctk/ast/v1/PackIndexingExpr.js';
import type { PackIndexingType as _ctk_ast_v1_PackIndexingType, PackIndexingType__Output as _ctk_ast_v1_PackIndexingType__Output } from './ctk/ast/v1/PackIndexingType.js';
import type { ParameterValue as _ctk_ast_v1_ParameterValue, ParameterValue__Output as _ctk_ast_v1_ParameterValue__Output } from './ctk/ast/v1/ParameterValue.js';
import type { ParenExpr as _ctk_ast_v1_ParenExpr, ParenExpr__Output as _ctk_ast_v1_ParenExpr__Output } from './ctk/ast/v1/ParenExpr.js';
import type { ParenListExpr as _ctk_ast_v1_ParenListExpr, ParenListExpr__Output as _ctk_ast_v1_ParenListExpr__Output } from './ctk/ast/v1/ParenListExpr.js';
import type { ParenType as _ctk_ast_v1_ParenType, ParenType__Output as _ctk_ast_v1_ParenType__Output } from './ctk/ast/v1/ParenType.js';
import type { ParmVarDecl as _ctk_ast_v1_ParmVarDecl, ParmVarDecl__Output as _ctk_ast_v1_ParmVarDecl__Output } from './ctk/ast/v1/ParmVarDecl.js';
import type { PointerType as _ctk_ast_v1_PointerType, PointerType__Output as _ctk_ast_v1_PointerType__Output } from './ctk/ast/v1/PointerType.js';
import type { PragmaCommentDecl as _ctk_ast_v1_PragmaCommentDecl, PragmaCommentDecl__Output as _ctk_ast_v1_PragmaCommentDecl__Output } from './ctk/ast/v1/PragmaCommentDecl.js';
import type { PragmaDetectMismatchDecl as _ctk_ast_v1_PragmaDetectMismatchDecl, PragmaDetectMismatchDecl__Output as _ctk_ast_v1_PragmaDetectMismatchDecl__Output } from './ctk/ast/v1/PragmaDetectMismatchDecl.js';
import type { PredefinedExpr as _ctk_ast_v1_PredefinedExpr, PredefinedExpr__Output as _ctk_ast_v1_PredefinedExpr__Output } from './ctk/ast/v1/PredefinedExpr.js';
import type { PredefinedSugarType as _ctk_ast_v1_PredefinedSugarType, PredefinedSugarType__Output as _ctk_ast_v1_PredefinedSugarType__Output } from './ctk/ast/v1/PredefinedSugarType.js';
import type { PseudoObjectExpr as _ctk_ast_v1_PseudoObjectExpr, PseudoObjectExpr__Output as _ctk_ast_v1_PseudoObjectExpr__Output } from './ctk/ast/v1/PseudoObjectExpr.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from './ctk/ast/v1/QualType.js';
import type { QualifiedTemplateName as _ctk_ast_v1_QualifiedTemplateName, QualifiedTemplateName__Output as _ctk_ast_v1_QualifiedTemplateName__Output } from './ctk/ast/v1/QualifiedTemplateName.js';
import type { Qualifiers as _ctk_ast_v1_Qualifiers, Qualifiers__Output as _ctk_ast_v1_Qualifiers__Output } from './ctk/ast/v1/Qualifiers.js';
import type { RValueReferenceType as _ctk_ast_v1_RValueReferenceType, RValueReferenceType__Output as _ctk_ast_v1_RValueReferenceType__Output } from './ctk/ast/v1/RValueReferenceType.js';
import type { RecordDecl as _ctk_ast_v1_RecordDecl, RecordDecl__Output as _ctk_ast_v1_RecordDecl__Output } from './ctk/ast/v1/RecordDecl.js';
import type { RecordDeclInfo as _ctk_ast_v1_RecordDeclInfo, RecordDeclInfo__Output as _ctk_ast_v1_RecordDeclInfo__Output } from './ctk/ast/v1/RecordDeclInfo.js';
import type { RecordType as _ctk_ast_v1_RecordType, RecordType__Output as _ctk_ast_v1_RecordType__Output } from './ctk/ast/v1/RecordType.js';
import type { RecoveryExpr as _ctk_ast_v1_RecoveryExpr, RecoveryExpr__Output as _ctk_ast_v1_RecoveryExpr__Output } from './ctk/ast/v1/RecoveryExpr.js';
import type { RequirementInfo as _ctk_ast_v1_RequirementInfo, RequirementInfo__Output as _ctk_ast_v1_RequirementInfo__Output } from './ctk/ast/v1/RequirementInfo.js';
import type { RequiresExpr as _ctk_ast_v1_RequiresExpr, RequiresExpr__Output as _ctk_ast_v1_RequiresExpr__Output } from './ctk/ast/v1/RequiresExpr.js';
import type { RequiresExprBodyDecl as _ctk_ast_v1_RequiresExprBodyDecl, RequiresExprBodyDecl__Output as _ctk_ast_v1_RequiresExprBodyDecl__Output } from './ctk/ast/v1/RequiresExprBodyDecl.js';
import type { ReturnStmt as _ctk_ast_v1_ReturnStmt, ReturnStmt__Output as _ctk_ast_v1_ReturnStmt__Output } from './ctk/ast/v1/ReturnStmt.js';
import type { ReturnTypeRequirement as _ctk_ast_v1_ReturnTypeRequirement, ReturnTypeRequirement__Output as _ctk_ast_v1_ReturnTypeRequirement__Output } from './ctk/ast/v1/ReturnTypeRequirement.js';
import type { SEHExceptStmt as _ctk_ast_v1_SEHExceptStmt, SEHExceptStmt__Output as _ctk_ast_v1_SEHExceptStmt__Output } from './ctk/ast/v1/SEHExceptStmt.js';
import type { SEHFinallyStmt as _ctk_ast_v1_SEHFinallyStmt, SEHFinallyStmt__Output as _ctk_ast_v1_SEHFinallyStmt__Output } from './ctk/ast/v1/SEHFinallyStmt.js';
import type { SEHLeaveStmt as _ctk_ast_v1_SEHLeaveStmt, SEHLeaveStmt__Output as _ctk_ast_v1_SEHLeaveStmt__Output } from './ctk/ast/v1/SEHLeaveStmt.js';
import type { SEHTryStmt as _ctk_ast_v1_SEHTryStmt, SEHTryStmt__Output as _ctk_ast_v1_SEHTryStmt__Output } from './ctk/ast/v1/SEHTryStmt.js';
import type { SemanticResult as _ctk_ast_v1_SemanticResult, SemanticResult__Output as _ctk_ast_v1_SemanticResult__Output } from './ctk/ast/v1/SemanticResult.js';
import type { ShuffleVectorExpr as _ctk_ast_v1_ShuffleVectorExpr, ShuffleVectorExpr__Output as _ctk_ast_v1_ShuffleVectorExpr__Output } from './ctk/ast/v1/ShuffleVectorExpr.js';
import type { SizeOfPackExpr as _ctk_ast_v1_SizeOfPackExpr, SizeOfPackExpr__Output as _ctk_ast_v1_SizeOfPackExpr__Output } from './ctk/ast/v1/SizeOfPackExpr.js';
import type { SourceLocExpr as _ctk_ast_v1_SourceLocExpr, SourceLocExpr__Output as _ctk_ast_v1_SourceLocExpr__Output } from './ctk/ast/v1/SourceLocExpr.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from './ctk/ast/v1/StatementValue.js';
import type { StaticAssertDecl as _ctk_ast_v1_StaticAssertDecl, StaticAssertDecl__Output as _ctk_ast_v1_StaticAssertDecl__Output } from './ctk/ast/v1/StaticAssertDecl.js';
import type { StmtExpr as _ctk_ast_v1_StmtExpr, StmtExpr__Output as _ctk_ast_v1_StmtExpr__Output } from './ctk/ast/v1/StmtExpr.js';
import type { StringLiteral as _ctk_ast_v1_StringLiteral, StringLiteral__Output as _ctk_ast_v1_StringLiteral__Output } from './ctk/ast/v1/StringLiteral.js';
import type { StructuralTemplateArgument as _ctk_ast_v1_StructuralTemplateArgument, StructuralTemplateArgument__Output as _ctk_ast_v1_StructuralTemplateArgument__Output } from './ctk/ast/v1/StructuralTemplateArgument.js';
import type { SubstBuiltinTemplatePackType as _ctk_ast_v1_SubstBuiltinTemplatePackType, SubstBuiltinTemplatePackType__Output as _ctk_ast_v1_SubstBuiltinTemplatePackType__Output } from './ctk/ast/v1/SubstBuiltinTemplatePackType.js';
import type { SubstNonTypeTemplateParmExpr as _ctk_ast_v1_SubstNonTypeTemplateParmExpr, SubstNonTypeTemplateParmExpr__Output as _ctk_ast_v1_SubstNonTypeTemplateParmExpr__Output } from './ctk/ast/v1/SubstNonTypeTemplateParmExpr.js';
import type { SubstNonTypeTemplateParmPackExpr as _ctk_ast_v1_SubstNonTypeTemplateParmPackExpr, SubstNonTypeTemplateParmPackExpr__Output as _ctk_ast_v1_SubstNonTypeTemplateParmPackExpr__Output } from './ctk/ast/v1/SubstNonTypeTemplateParmPackExpr.js';
import type { SubstTemplateTypeParmPackType as _ctk_ast_v1_SubstTemplateTypeParmPackType, SubstTemplateTypeParmPackType__Output as _ctk_ast_v1_SubstTemplateTypeParmPackType__Output } from './ctk/ast/v1/SubstTemplateTypeParmPackType.js';
import type { SubstTemplateTypeParmType as _ctk_ast_v1_SubstTemplateTypeParmType, SubstTemplateTypeParmType__Output as _ctk_ast_v1_SubstTemplateTypeParmType__Output } from './ctk/ast/v1/SubstTemplateTypeParmType.js';
import type { SubstitutedTemplateName as _ctk_ast_v1_SubstitutedTemplateName, SubstitutedTemplateName__Output as _ctk_ast_v1_SubstitutedTemplateName__Output } from './ctk/ast/v1/SubstitutedTemplateName.js';
import type { SubstitutedTemplatePack as _ctk_ast_v1_SubstitutedTemplatePack, SubstitutedTemplatePack__Output as _ctk_ast_v1_SubstitutedTemplatePack__Output } from './ctk/ast/v1/SubstitutedTemplatePack.js';
import type { SubstitutionDiagnostic as _ctk_ast_v1_SubstitutionDiagnostic, SubstitutionDiagnostic__Output as _ctk_ast_v1_SubstitutionDiagnostic__Output } from './ctk/ast/v1/SubstitutionDiagnostic.js';
import type { SwitchStmt as _ctk_ast_v1_SwitchStmt, SwitchStmt__Output as _ctk_ast_v1_SwitchStmt__Output } from './ctk/ast/v1/SwitchStmt.js';
import type { TagDeclInfo as _ctk_ast_v1_TagDeclInfo, TagDeclInfo__Output as _ctk_ast_v1_TagDeclInfo__Output } from './ctk/ast/v1/TagDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from './ctk/ast/v1/TemplateArgument.js';
import type { TemplateArgumentDescription as _ctk_ast_v1_TemplateArgumentDescription, TemplateArgumentDescription__Output as _ctk_ast_v1_TemplateArgumentDescription__Output } from './ctk/ast/v1/TemplateArgumentDescription.js';
import type { TemplateArgumentPack as _ctk_ast_v1_TemplateArgumentPack, TemplateArgumentPack__Output as _ctk_ast_v1_TemplateArgumentPack__Output } from './ctk/ast/v1/TemplateArgumentPack.js';
import type { TemplateExpansionArgument as _ctk_ast_v1_TemplateExpansionArgument, TemplateExpansionArgument__Output as _ctk_ast_v1_TemplateExpansionArgument__Output } from './ctk/ast/v1/TemplateExpansionArgument.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from './ctk/ast/v1/TemplateName.js';
import type { TemplateParamObjectDecl as _ctk_ast_v1_TemplateParamObjectDecl, TemplateParamObjectDecl__Output as _ctk_ast_v1_TemplateParamObjectDecl__Output } from './ctk/ast/v1/TemplateParamObjectDecl.js';
import type { TemplateParameterDescription as _ctk_ast_v1_TemplateParameterDescription, TemplateParameterDescription__Output as _ctk_ast_v1_TemplateParameterDescription__Output } from './ctk/ast/v1/TemplateParameterDescription.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from './ctk/ast/v1/TemplateParameterList.js';
import type { TemplateSpecializationType as _ctk_ast_v1_TemplateSpecializationType, TemplateSpecializationType__Output as _ctk_ast_v1_TemplateSpecializationType__Output } from './ctk/ast/v1/TemplateSpecializationType.js';
import type { TemplateTemplateParmDecl as _ctk_ast_v1_TemplateTemplateParmDecl, TemplateTemplateParmDecl__Output as _ctk_ast_v1_TemplateTemplateParmDecl__Output } from './ctk/ast/v1/TemplateTemplateParmDecl.js';
import type { TemplateTypeParmDecl as _ctk_ast_v1_TemplateTypeParmDecl, TemplateTypeParmDecl__Output as _ctk_ast_v1_TemplateTypeParmDecl__Output } from './ctk/ast/v1/TemplateTypeParmDecl.js';
import type { TemplateTypeParmType as _ctk_ast_v1_TemplateTypeParmType, TemplateTypeParmType__Output as _ctk_ast_v1_TemplateTypeParmType__Output } from './ctk/ast/v1/TemplateTypeParmType.js';
import type { TopLevelStmtDecl as _ctk_ast_v1_TopLevelStmtDecl, TopLevelStmtDecl__Output as _ctk_ast_v1_TopLevelStmtDecl__Output } from './ctk/ast/v1/TopLevelStmtDecl.js';
import type { TranslationUnitDecl as _ctk_ast_v1_TranslationUnitDecl, TranslationUnitDecl__Output as _ctk_ast_v1_TranslationUnitDecl__Output } from './ctk/ast/v1/TranslationUnitDecl.js';
import type { TypeAliasDecl as _ctk_ast_v1_TypeAliasDecl, TypeAliasDecl__Output as _ctk_ast_v1_TypeAliasDecl__Output } from './ctk/ast/v1/TypeAliasDecl.js';
import type { TypeAliasTemplateDecl as _ctk_ast_v1_TypeAliasTemplateDecl, TypeAliasTemplateDecl__Output as _ctk_ast_v1_TypeAliasTemplateDecl__Output } from './ctk/ast/v1/TypeAliasTemplateDecl.js';
import type { TypeConstraint as _ctk_ast_v1_TypeConstraint, TypeConstraint__Output as _ctk_ast_v1_TypeConstraint__Output } from './ctk/ast/v1/TypeConstraint.js';
import type { TypeDeclInfo as _ctk_ast_v1_TypeDeclInfo, TypeDeclInfo__Output as _ctk_ast_v1_TypeDeclInfo__Output } from './ctk/ast/v1/TypeDeclInfo.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from './ctk/ast/v1/TypeDescription.js';
import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from './ctk/ast/v1/TypeInfo.js';
import type { TypeOfExprType as _ctk_ast_v1_TypeOfExprType, TypeOfExprType__Output as _ctk_ast_v1_TypeOfExprType__Output } from './ctk/ast/v1/TypeOfExprType.js';
import type { TypeOfType as _ctk_ast_v1_TypeOfType, TypeOfType__Output as _ctk_ast_v1_TypeOfType__Output } from './ctk/ast/v1/TypeOfType.js';
import type { TypeRequirement as _ctk_ast_v1_TypeRequirement, TypeRequirement__Output as _ctk_ast_v1_TypeRequirement__Output } from './ctk/ast/v1/TypeRequirement.js';
import type { TypeTraitExpr as _ctk_ast_v1_TypeTraitExpr, TypeTraitExpr__Output as _ctk_ast_v1_TypeTraitExpr__Output } from './ctk/ast/v1/TypeTraitExpr.js';
import type { TypeValue as _ctk_ast_v1_TypeValue, TypeValue__Output as _ctk_ast_v1_TypeValue__Output } from './ctk/ast/v1/TypeValue.js';
import type { TypedefDecl as _ctk_ast_v1_TypedefDecl, TypedefDecl__Output as _ctk_ast_v1_TypedefDecl__Output } from './ctk/ast/v1/TypedefDecl.js';
import type { TypedefType as _ctk_ast_v1_TypedefType, TypedefType__Output as _ctk_ast_v1_TypedefType__Output } from './ctk/ast/v1/TypedefType.js';
import type { UnaryExprOrTypeTraitExpr as _ctk_ast_v1_UnaryExprOrTypeTraitExpr, UnaryExprOrTypeTraitExpr__Output as _ctk_ast_v1_UnaryExprOrTypeTraitExpr__Output } from './ctk/ast/v1/UnaryExprOrTypeTraitExpr.js';
import type { UnaryOperator as _ctk_ast_v1_UnaryOperator, UnaryOperator__Output as _ctk_ast_v1_UnaryOperator__Output } from './ctk/ast/v1/UnaryOperator.js';
import type { UnaryTransformType as _ctk_ast_v1_UnaryTransformType, UnaryTransformType__Output as _ctk_ast_v1_UnaryTransformType__Output } from './ctk/ast/v1/UnaryTransformType.js';
import type { UnnamedGlobalConstantDecl as _ctk_ast_v1_UnnamedGlobalConstantDecl, UnnamedGlobalConstantDecl__Output as _ctk_ast_v1_UnnamedGlobalConstantDecl__Output } from './ctk/ast/v1/UnnamedGlobalConstantDecl.js';
import type { UnresolvedLookupExpr as _ctk_ast_v1_UnresolvedLookupExpr, UnresolvedLookupExpr__Output as _ctk_ast_v1_UnresolvedLookupExpr__Output } from './ctk/ast/v1/UnresolvedLookupExpr.js';
import type { UnresolvedMemberExpr as _ctk_ast_v1_UnresolvedMemberExpr, UnresolvedMemberExpr__Output as _ctk_ast_v1_UnresolvedMemberExpr__Output } from './ctk/ast/v1/UnresolvedMemberExpr.js';
import type { UnresolvedUsingIfExistsDecl as _ctk_ast_v1_UnresolvedUsingIfExistsDecl, UnresolvedUsingIfExistsDecl__Output as _ctk_ast_v1_UnresolvedUsingIfExistsDecl__Output } from './ctk/ast/v1/UnresolvedUsingIfExistsDecl.js';
import type { UnresolvedUsingType as _ctk_ast_v1_UnresolvedUsingType, UnresolvedUsingType__Output as _ctk_ast_v1_UnresolvedUsingType__Output } from './ctk/ast/v1/UnresolvedUsingType.js';
import type { UnresolvedUsingTypenameDecl as _ctk_ast_v1_UnresolvedUsingTypenameDecl, UnresolvedUsingTypenameDecl__Output as _ctk_ast_v1_UnresolvedUsingTypenameDecl__Output } from './ctk/ast/v1/UnresolvedUsingTypenameDecl.js';
import type { UnresolvedUsingValueDecl as _ctk_ast_v1_UnresolvedUsingValueDecl, UnresolvedUsingValueDecl__Output as _ctk_ast_v1_UnresolvedUsingValueDecl__Output } from './ctk/ast/v1/UnresolvedUsingValueDecl.js';
import type { UnsupportedValue as _ctk_ast_v1_UnsupportedValue, UnsupportedValue__Output as _ctk_ast_v1_UnsupportedValue__Output } from './ctk/ast/v1/UnsupportedValue.js';
import type { UserDefinedLiteral as _ctk_ast_v1_UserDefinedLiteral, UserDefinedLiteral__Output as _ctk_ast_v1_UserDefinedLiteral__Output } from './ctk/ast/v1/UserDefinedLiteral.js';
import type { UsingDecl as _ctk_ast_v1_UsingDecl, UsingDecl__Output as _ctk_ast_v1_UsingDecl__Output } from './ctk/ast/v1/UsingDecl.js';
import type { UsingDirectiveDecl as _ctk_ast_v1_UsingDirectiveDecl, UsingDirectiveDecl__Output as _ctk_ast_v1_UsingDirectiveDecl__Output } from './ctk/ast/v1/UsingDirectiveDecl.js';
import type { UsingEnumDecl as _ctk_ast_v1_UsingEnumDecl, UsingEnumDecl__Output as _ctk_ast_v1_UsingEnumDecl__Output } from './ctk/ast/v1/UsingEnumDecl.js';
import type { UsingPackDecl as _ctk_ast_v1_UsingPackDecl, UsingPackDecl__Output as _ctk_ast_v1_UsingPackDecl__Output } from './ctk/ast/v1/UsingPackDecl.js';
import type { UsingShadowDecl as _ctk_ast_v1_UsingShadowDecl, UsingShadowDecl__Output as _ctk_ast_v1_UsingShadowDecl__Output } from './ctk/ast/v1/UsingShadowDecl.js';
import type { UsingType as _ctk_ast_v1_UsingType, UsingType__Output as _ctk_ast_v1_UsingType__Output } from './ctk/ast/v1/UsingType.js';
import type { VAArgExpr as _ctk_ast_v1_VAArgExpr, VAArgExpr__Output as _ctk_ast_v1_VAArgExpr__Output } from './ctk/ast/v1/VAArgExpr.js';
import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from './ctk/ast/v1/ValueDeclInfo.js';
import type { VarDecl as _ctk_ast_v1_VarDecl, VarDecl__Output as _ctk_ast_v1_VarDecl__Output } from './ctk/ast/v1/VarDecl.js';
import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from './ctk/ast/v1/VarDeclInfo.js';
import type { VarTemplateDecl as _ctk_ast_v1_VarTemplateDecl, VarTemplateDecl__Output as _ctk_ast_v1_VarTemplateDecl__Output } from './ctk/ast/v1/VarTemplateDecl.js';
import type { VarTemplatePartialSpecializationDecl as _ctk_ast_v1_VarTemplatePartialSpecializationDecl, VarTemplatePartialSpecializationDecl__Output as _ctk_ast_v1_VarTemplatePartialSpecializationDecl__Output } from './ctk/ast/v1/VarTemplatePartialSpecializationDecl.js';
import type { VarTemplateSpecializationDecl as _ctk_ast_v1_VarTemplateSpecializationDecl, VarTemplateSpecializationDecl__Output as _ctk_ast_v1_VarTemplateSpecializationDecl__Output } from './ctk/ast/v1/VarTemplateSpecializationDecl.js';
import type { VariableArrayType as _ctk_ast_v1_VariableArrayType, VariableArrayType__Output as _ctk_ast_v1_VariableArrayType__Output } from './ctk/ast/v1/VariableArrayType.js';
import type { VectorType as _ctk_ast_v1_VectorType, VectorType__Output as _ctk_ast_v1_VectorType__Output } from './ctk/ast/v1/VectorType.js';
import type { WhileStmt as _ctk_ast_v1_WhileStmt, WhileStmt__Output as _ctk_ast_v1_WhileStmt__Output } from './ctk/ast/v1/WhileStmt.js';
import type { AttachSessionRequest as _ctk_match_v1_AttachSessionRequest, AttachSessionRequest__Output as _ctk_match_v1_AttachSessionRequest__Output } from './ctk/match/v1/AttachSessionRequest.js';
import type { BindingMatchTarget as _ctk_match_v1_BindingMatchTarget, BindingMatchTarget__Output as _ctk_match_v1_BindingMatchTarget__Output } from './ctk/match/v1/BindingMatchTarget.js';
import type { CacheResources as _ctk_match_v1_CacheResources, CacheResources__Output as _ctk_match_v1_CacheResources__Output } from './ctk/match/v1/CacheResources.js';
import type { CallSiteFacts as _ctk_match_v1_CallSiteFacts, CallSiteFacts__Output as _ctk_match_v1_CallSiteFacts__Output } from './ctk/match/v1/CallSiteFacts.js';
import type { CloseSessionRequest as _ctk_match_v1_CloseSessionRequest, CloseSessionRequest__Output as _ctk_match_v1_CloseSessionRequest__Output } from './ctk/match/v1/CloseSessionRequest.js';
import type { CloseSessionResponse as _ctk_match_v1_CloseSessionResponse, CloseSessionResponse__Output as _ctk_match_v1_CloseSessionResponse__Output } from './ctk/match/v1/CloseSessionResponse.js';
import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from './ctk/match/v1/FileMatchTarget.js';
import type { ListSessionsRequest as _ctk_match_v1_ListSessionsRequest, ListSessionsRequest__Output as _ctk_match_v1_ListSessionsRequest__Output } from './ctk/match/v1/ListSessionsRequest.js';
import type { ListSessionsResponse as _ctk_match_v1_ListSessionsResponse, ListSessionsResponse__Output as _ctk_match_v1_ListSessionsResponse__Output } from './ctk/match/v1/ListSessionsResponse.js';
import type { MatchBinding as _ctk_match_v1_MatchBinding, MatchBinding__Output as _ctk_match_v1_MatchBinding__Output } from './ctk/match/v1/MatchBinding.js';
import type { MatchRequest as _ctk_match_v1_MatchRequest, MatchRequest__Output as _ctk_match_v1_MatchRequest__Output } from './ctk/match/v1/MatchRequest.js';
import type { MatchResponse as _ctk_match_v1_MatchResponse, MatchResponse__Output as _ctk_match_v1_MatchResponse__Output } from './ctk/match/v1/MatchResponse.js';
import type { MatchResult as _ctk_match_v1_MatchResult, MatchResult__Output as _ctk_match_v1_MatchResult__Output } from './ctk/match/v1/MatchResult.js';
import type { MatchServiceClient as _ctk_match_v1_MatchServiceClient, MatchServiceDefinition as _ctk_match_v1_MatchServiceDefinition } from './ctk/match/v1/MatchService.js';
import type { MatchSourcePoint as _ctk_match_v1_MatchSourcePoint, MatchSourcePoint__Output as _ctk_match_v1_MatchSourcePoint__Output } from './ctk/match/v1/MatchSourcePoint.js';
import type { MatchSourceRange as _ctk_match_v1_MatchSourceRange, MatchSourceRange__Output as _ctk_match_v1_MatchSourceRange__Output } from './ctk/match/v1/MatchSourceRange.js';
import type { MatchStreamCompleted as _ctk_match_v1_MatchStreamCompleted, MatchStreamCompleted__Output as _ctk_match_v1_MatchStreamCompleted__Output } from './ctk/match/v1/MatchStreamCompleted.js';
import type { MatchStreamEvent as _ctk_match_v1_MatchStreamEvent, MatchStreamEvent__Output as _ctk_match_v1_MatchStreamEvent__Output } from './ctk/match/v1/MatchStreamEvent.js';
import type { ParseRequest as _ctk_match_v1_ParseRequest, ParseRequest__Output as _ctk_match_v1_ParseRequest__Output } from './ctk/match/v1/ParseRequest.js';
import type { ParseResponse as _ctk_match_v1_ParseResponse, ParseResponse__Output as _ctk_match_v1_ParseResponse__Output } from './ctk/match/v1/ParseResponse.js';
import type { PruneCachesRequest as _ctk_match_v1_PruneCachesRequest, PruneCachesRequest__Output as _ctk_match_v1_PruneCachesRequest__Output } from './ctk/match/v1/PruneCachesRequest.js';
import type { PruneCachesResponse as _ctk_match_v1_PruneCachesResponse, PruneCachesResponse__Output as _ctk_match_v1_PruneCachesResponse__Output } from './ctk/match/v1/PruneCachesResponse.js';
import type { ServerStatusRequest as _ctk_match_v1_ServerStatusRequest, ServerStatusRequest__Output as _ctk_match_v1_ServerStatusRequest__Output } from './ctk/match/v1/ServerStatusRequest.js';
import type { ServerStatusResponse as _ctk_match_v1_ServerStatusResponse, ServerStatusResponse__Output as _ctk_match_v1_ServerStatusResponse__Output } from './ctk/match/v1/ServerStatusResponse.js';
import type { SessionInfo as _ctk_match_v1_SessionInfo, SessionInfo__Output as _ctk_match_v1_SessionInfo__Output } from './ctk/match/v1/SessionInfo.js';
import type { SessionMatchTarget as _ctk_match_v1_SessionMatchTarget, SessionMatchTarget__Output as _ctk_match_v1_SessionMatchTarget__Output } from './ctk/match/v1/SessionMatchTarget.js';
import type { Timestamp as _google_protobuf_Timestamp, Timestamp__Output as _google_protobuf_Timestamp__Output } from './google/protobuf/Timestamp.js';

type SubtypeConstructor<Constructor extends new (...args: any) => any, Subtype> = {
  new(...args: ConstructorParameters<Constructor>): Subtype;
};

export interface ProtoGrpcType {
  ctk: {
    ast: {
      v1: {
        APAddrLabelDiff: MessageTypeDefinition<_ctk_ast_v1_APAddrLabelDiff, _ctk_ast_v1_APAddrLabelDiff__Output>
        APArrayValue: MessageTypeDefinition<_ctk_ast_v1_APArrayValue, _ctk_ast_v1_APArrayValue__Output>
        APDynamicAllocation: MessageTypeDefinition<_ctk_ast_v1_APDynamicAllocation, _ctk_ast_v1_APDynamicAllocation__Output>
        APFixedPointBits: MessageTypeDefinition<_ctk_ast_v1_APFixedPointBits, _ctk_ast_v1_APFixedPointBits__Output>
        APFloatBits: MessageTypeDefinition<_ctk_ast_v1_APFloatBits, _ctk_ast_v1_APFloatBits__Output>
        APIntBits: MessageTypeDefinition<_ctk_ast_v1_APIntBits, _ctk_ast_v1_APIntBits__Output>
        APLValue: MessageTypeDefinition<_ctk_ast_v1_APLValue, _ctk_ast_v1_APLValue__Output>
        APLValueBase: MessageTypeDefinition<_ctk_ast_v1_APLValueBase, _ctk_ast_v1_APLValueBase__Output>
        APLValuePathEntry: MessageTypeDefinition<_ctk_ast_v1_APLValuePathEntry, _ctk_ast_v1_APLValuePathEntry__Output>
        APMemberPointer: MessageTypeDefinition<_ctk_ast_v1_APMemberPointer, _ctk_ast_v1_APMemberPointer__Output>
        APSIntBits: MessageTypeDefinition<_ctk_ast_v1_APSIntBits, _ctk_ast_v1_APSIntBits__Output>
        APStructBaseValue: MessageTypeDefinition<_ctk_ast_v1_APStructBaseValue, _ctk_ast_v1_APStructBaseValue__Output>
        APStructFieldValue: MessageTypeDefinition<_ctk_ast_v1_APStructFieldValue, _ctk_ast_v1_APStructFieldValue__Output>
        APStructValue: MessageTypeDefinition<_ctk_ast_v1_APStructValue, _ctk_ast_v1_APStructValue__Output>
        APTypeInfoLValue: MessageTypeDefinition<_ctk_ast_v1_APTypeInfoLValue, _ctk_ast_v1_APTypeInfoLValue__Output>
        APUnionValue: MessageTypeDefinition<_ctk_ast_v1_APUnionValue, _ctk_ast_v1_APUnionValue__Output>
        APValue: MessageTypeDefinition<_ctk_ast_v1_APValue, _ctk_ast_v1_APValue__Output>
        APValueSequence: MessageTypeDefinition<_ctk_ast_v1_APValueSequence, _ctk_ast_v1_APValueSequence__Output>
        AccessSpecDecl: MessageTypeDefinition<_ctk_ast_v1_AccessSpecDecl, _ctk_ast_v1_AccessSpecDecl__Output>
        AccessSpecifier: EnumTypeDefinition
        AddrLabelExpr: MessageTypeDefinition<_ctk_ast_v1_AddrLabelExpr, _ctk_ast_v1_AddrLabelExpr__Output>
        AddressSpace: MessageTypeDefinition<_ctk_ast_v1_AddressSpace, _ctk_ast_v1_AddressSpace__Output>
        AdjustedType: MessageTypeDefinition<_ctk_ast_v1_AdjustedType, _ctk_ast_v1_AdjustedType__Output>
        ArrayInitIndexExpr: MessageTypeDefinition<_ctk_ast_v1_ArrayInitIndexExpr, _ctk_ast_v1_ArrayInitIndexExpr__Output>
        ArrayInitLoopExpr: MessageTypeDefinition<_ctk_ast_v1_ArrayInitLoopExpr, _ctk_ast_v1_ArrayInitLoopExpr__Output>
        ArraySizeModifier: EnumTypeDefinition
        ArraySubscriptExpr: MessageTypeDefinition<_ctk_ast_v1_ArraySubscriptExpr, _ctk_ast_v1_ArraySubscriptExpr__Output>
        ArrayTypeTrait: EnumTypeDefinition
        ArrayTypeTraitExpr: MessageTypeDefinition<_ctk_ast_v1_ArrayTypeTraitExpr, _ctk_ast_v1_ArrayTypeTraitExpr__Output>
        AsmOperand: MessageTypeDefinition<_ctk_ast_v1_AsmOperand, _ctk_ast_v1_AsmOperand__Output>
        AstNode: MessageTypeDefinition<_ctk_ast_v1_AstNode, _ctk_ast_v1_AstNode__Output>
        AtomicExpr: MessageTypeDefinition<_ctk_ast_v1_AtomicExpr, _ctk_ast_v1_AtomicExpr__Output>
        AtomicOpcode: EnumTypeDefinition
        AtomicType: MessageTypeDefinition<_ctk_ast_v1_AtomicType, _ctk_ast_v1_AtomicType__Output>
        AttributeValue: MessageTypeDefinition<_ctk_ast_v1_AttributeValue, _ctk_ast_v1_AttributeValue__Output>
        AttributedStmt: MessageTypeDefinition<_ctk_ast_v1_AttributedStmt, _ctk_ast_v1_AttributedStmt__Output>
        AttributedType: MessageTypeDefinition<_ctk_ast_v1_AttributedType, _ctk_ast_v1_AttributedType__Output>
        AttributedTypeKind: EnumTypeDefinition
        AutoKeyword: EnumTypeDefinition
        AutoType: MessageTypeDefinition<_ctk_ast_v1_AutoType, _ctk_ast_v1_AutoType__Output>
        BTFTagAttributedType: MessageTypeDefinition<_ctk_ast_v1_BTFTagAttributedType, _ctk_ast_v1_BTFTagAttributedType__Output>
        BinaryConditionalOperator: MessageTypeDefinition<_ctk_ast_v1_BinaryConditionalOperator, _ctk_ast_v1_BinaryConditionalOperator__Output>
        BinaryOpcode: EnumTypeDefinition
        BinaryOperator: MessageTypeDefinition<_ctk_ast_v1_BinaryOperator, _ctk_ast_v1_BinaryOperator__Output>
        BindingDecl: MessageTypeDefinition<_ctk_ast_v1_BindingDecl, _ctk_ast_v1_BindingDecl__Output>
        BitIntType: MessageTypeDefinition<_ctk_ast_v1_BitIntType, _ctk_ast_v1_BitIntType__Output>
        BlockCaptureInfo: MessageTypeDefinition<_ctk_ast_v1_BlockCaptureInfo, _ctk_ast_v1_BlockCaptureInfo__Output>
        BlockDecl: MessageTypeDefinition<_ctk_ast_v1_BlockDecl, _ctk_ast_v1_BlockDecl__Output>
        BlockExpr: MessageTypeDefinition<_ctk_ast_v1_BlockExpr, _ctk_ast_v1_BlockExpr__Output>
        BlockPointerType: MessageTypeDefinition<_ctk_ast_v1_BlockPointerType, _ctk_ast_v1_BlockPointerType__Output>
        BreakStmt: MessageTypeDefinition<_ctk_ast_v1_BreakStmt, _ctk_ast_v1_BreakStmt__Output>
        BuiltinBitCastExpr: MessageTypeDefinition<_ctk_ast_v1_BuiltinBitCastExpr, _ctk_ast_v1_BuiltinBitCastExpr__Output>
        BuiltinKind: EnumTypeDefinition
        BuiltinTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_BuiltinTemplateDecl, _ctk_ast_v1_BuiltinTemplateDecl__Output>
        BuiltinType: MessageTypeDefinition<_ctk_ast_v1_BuiltinType, _ctk_ast_v1_BuiltinType__Output>
        CStyleCastExpr: MessageTypeDefinition<_ctk_ast_v1_CStyleCastExpr, _ctk_ast_v1_CStyleCastExpr__Output>
        CXXAddrspaceCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXAddrspaceCastExpr, _ctk_ast_v1_CXXAddrspaceCastExpr__Output>
        CXXBaseSpecifier: MessageTypeDefinition<_ctk_ast_v1_CXXBaseSpecifier, _ctk_ast_v1_CXXBaseSpecifier__Output>
        CXXBindTemporaryExpr: MessageTypeDefinition<_ctk_ast_v1_CXXBindTemporaryExpr, _ctk_ast_v1_CXXBindTemporaryExpr__Output>
        CXXBoolLiteralExpr: MessageTypeDefinition<_ctk_ast_v1_CXXBoolLiteralExpr, _ctk_ast_v1_CXXBoolLiteralExpr__Output>
        CXXCatchStmt: MessageTypeDefinition<_ctk_ast_v1_CXXCatchStmt, _ctk_ast_v1_CXXCatchStmt__Output>
        CXXConstCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXConstCastExpr, _ctk_ast_v1_CXXConstCastExpr__Output>
        CXXConstructExpr: MessageTypeDefinition<_ctk_ast_v1_CXXConstructExpr, _ctk_ast_v1_CXXConstructExpr__Output>
        CXXConstructExprInfo: MessageTypeDefinition<_ctk_ast_v1_CXXConstructExprInfo, _ctk_ast_v1_CXXConstructExprInfo__Output>
        CXXConstructorDecl: MessageTypeDefinition<_ctk_ast_v1_CXXConstructorDecl, _ctk_ast_v1_CXXConstructorDecl__Output>
        CXXConversionDecl: MessageTypeDefinition<_ctk_ast_v1_CXXConversionDecl, _ctk_ast_v1_CXXConversionDecl__Output>
        CXXCtorInitializer: MessageTypeDefinition<_ctk_ast_v1_CXXCtorInitializer, _ctk_ast_v1_CXXCtorInitializer__Output>
        CXXDeductionGuideDecl: MessageTypeDefinition<_ctk_ast_v1_CXXDeductionGuideDecl, _ctk_ast_v1_CXXDeductionGuideDecl__Output>
        CXXDefaultArgExpr: MessageTypeDefinition<_ctk_ast_v1_CXXDefaultArgExpr, _ctk_ast_v1_CXXDefaultArgExpr__Output>
        CXXDefaultInitExpr: MessageTypeDefinition<_ctk_ast_v1_CXXDefaultInitExpr, _ctk_ast_v1_CXXDefaultInitExpr__Output>
        CXXDeleteExpr: MessageTypeDefinition<_ctk_ast_v1_CXXDeleteExpr, _ctk_ast_v1_CXXDeleteExpr__Output>
        CXXDependentScopeMemberExpr: MessageTypeDefinition<_ctk_ast_v1_CXXDependentScopeMemberExpr, _ctk_ast_v1_CXXDependentScopeMemberExpr__Output>
        CXXDestructorDecl: MessageTypeDefinition<_ctk_ast_v1_CXXDestructorDecl, _ctk_ast_v1_CXXDestructorDecl__Output>
        CXXDynamicCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXDynamicCastExpr, _ctk_ast_v1_CXXDynamicCastExpr__Output>
        CXXFoldExpr: MessageTypeDefinition<_ctk_ast_v1_CXXFoldExpr, _ctk_ast_v1_CXXFoldExpr__Output>
        CXXForRangeStmt: MessageTypeDefinition<_ctk_ast_v1_CXXForRangeStmt, _ctk_ast_v1_CXXForRangeStmt__Output>
        CXXFunctionalCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXFunctionalCastExpr, _ctk_ast_v1_CXXFunctionalCastExpr__Output>
        CXXInheritedCtorInitExpr: MessageTypeDefinition<_ctk_ast_v1_CXXInheritedCtorInitExpr, _ctk_ast_v1_CXXInheritedCtorInitExpr__Output>
        CXXMemberCallExpr: MessageTypeDefinition<_ctk_ast_v1_CXXMemberCallExpr, _ctk_ast_v1_CXXMemberCallExpr__Output>
        CXXMethodDecl: MessageTypeDefinition<_ctk_ast_v1_CXXMethodDecl, _ctk_ast_v1_CXXMethodDecl__Output>
        CXXMethodDeclInfo: MessageTypeDefinition<_ctk_ast_v1_CXXMethodDeclInfo, _ctk_ast_v1_CXXMethodDeclInfo__Output>
        CXXNewExpr: MessageTypeDefinition<_ctk_ast_v1_CXXNewExpr, _ctk_ast_v1_CXXNewExpr__Output>
        CXXNoexceptExpr: MessageTypeDefinition<_ctk_ast_v1_CXXNoexceptExpr, _ctk_ast_v1_CXXNoexceptExpr__Output>
        CXXNullPtrLiteralExpr: MessageTypeDefinition<_ctk_ast_v1_CXXNullPtrLiteralExpr, _ctk_ast_v1_CXXNullPtrLiteralExpr__Output>
        CXXOperatorCallExpr: MessageTypeDefinition<_ctk_ast_v1_CXXOperatorCallExpr, _ctk_ast_v1_CXXOperatorCallExpr__Output>
        CXXParenListInitExpr: MessageTypeDefinition<_ctk_ast_v1_CXXParenListInitExpr, _ctk_ast_v1_CXXParenListInitExpr__Output>
        CXXPseudoDestructorExpr: MessageTypeDefinition<_ctk_ast_v1_CXXPseudoDestructorExpr, _ctk_ast_v1_CXXPseudoDestructorExpr__Output>
        CXXRecordDecl: MessageTypeDefinition<_ctk_ast_v1_CXXRecordDecl, _ctk_ast_v1_CXXRecordDecl__Output>
        CXXReinterpretCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXReinterpretCastExpr, _ctk_ast_v1_CXXReinterpretCastExpr__Output>
        CXXRewrittenBinaryOperator: MessageTypeDefinition<_ctk_ast_v1_CXXRewrittenBinaryOperator, _ctk_ast_v1_CXXRewrittenBinaryOperator__Output>
        CXXScalarValueInitExpr: MessageTypeDefinition<_ctk_ast_v1_CXXScalarValueInitExpr, _ctk_ast_v1_CXXScalarValueInitExpr__Output>
        CXXStaticCastExpr: MessageTypeDefinition<_ctk_ast_v1_CXXStaticCastExpr, _ctk_ast_v1_CXXStaticCastExpr__Output>
        CXXStdInitializerListExpr: MessageTypeDefinition<_ctk_ast_v1_CXXStdInitializerListExpr, _ctk_ast_v1_CXXStdInitializerListExpr__Output>
        CXXTemporary: MessageTypeDefinition<_ctk_ast_v1_CXXTemporary, _ctk_ast_v1_CXXTemporary__Output>
        CXXTemporaryObjectExpr: MessageTypeDefinition<_ctk_ast_v1_CXXTemporaryObjectExpr, _ctk_ast_v1_CXXTemporaryObjectExpr__Output>
        CXXThisExpr: MessageTypeDefinition<_ctk_ast_v1_CXXThisExpr, _ctk_ast_v1_CXXThisExpr__Output>
        CXXThrowExpr: MessageTypeDefinition<_ctk_ast_v1_CXXThrowExpr, _ctk_ast_v1_CXXThrowExpr__Output>
        CXXTryStmt: MessageTypeDefinition<_ctk_ast_v1_CXXTryStmt, _ctk_ast_v1_CXXTryStmt__Output>
        CXXTypeidExpr: MessageTypeDefinition<_ctk_ast_v1_CXXTypeidExpr, _ctk_ast_v1_CXXTypeidExpr__Output>
        CXXUnresolvedConstructExpr: MessageTypeDefinition<_ctk_ast_v1_CXXUnresolvedConstructExpr, _ctk_ast_v1_CXXUnresolvedConstructExpr__Output>
        CXXUuidofExpr: MessageTypeDefinition<_ctk_ast_v1_CXXUuidofExpr, _ctk_ast_v1_CXXUuidofExpr__Output>
        CallExpr: MessageTypeDefinition<_ctk_ast_v1_CallExpr, _ctk_ast_v1_CallExpr__Output>
        CallExprInfo: MessageTypeDefinition<_ctk_ast_v1_CallExprInfo, _ctk_ast_v1_CallExprInfo__Output>
        CaseStmt: MessageTypeDefinition<_ctk_ast_v1_CaseStmt, _ctk_ast_v1_CaseStmt__Output>
        CastExprInfo: MessageTypeDefinition<_ctk_ast_v1_CastExprInfo, _ctk_ast_v1_CastExprInfo__Output>
        CastKind: EnumTypeDefinition
        CharacterKind: EnumTypeDefinition
        CharacterLiteral: MessageTypeDefinition<_ctk_ast_v1_CharacterLiteral, _ctk_ast_v1_CharacterLiteral__Output>
        ChooseExpr: MessageTypeDefinition<_ctk_ast_v1_ChooseExpr, _ctk_ast_v1_ChooseExpr__Output>
        ClassTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_ClassTemplateDecl, _ctk_ast_v1_ClassTemplateDecl__Output>
        ClassTemplatePartialSpecializationDecl: MessageTypeDefinition<_ctk_ast_v1_ClassTemplatePartialSpecializationDecl, _ctk_ast_v1_ClassTemplatePartialSpecializationDecl__Output>
        ClassTemplateSpecializationDecl: MessageTypeDefinition<_ctk_ast_v1_ClassTemplateSpecializationDecl, _ctk_ast_v1_ClassTemplateSpecializationDecl__Output>
        CleanupValue: MessageTypeDefinition<_ctk_ast_v1_CleanupValue, _ctk_ast_v1_CleanupValue__Output>
        CoawaitExpr: MessageTypeDefinition<_ctk_ast_v1_CoawaitExpr, _ctk_ast_v1_CoawaitExpr__Output>
        ComplexFloatValue: MessageTypeDefinition<_ctk_ast_v1_ComplexFloatValue, _ctk_ast_v1_ComplexFloatValue__Output>
        ComplexIntValue: MessageTypeDefinition<_ctk_ast_v1_ComplexIntValue, _ctk_ast_v1_ComplexIntValue__Output>
        ComplexType: MessageTypeDefinition<_ctk_ast_v1_ComplexType, _ctk_ast_v1_ComplexType__Output>
        CompoundAssignOperator: MessageTypeDefinition<_ctk_ast_v1_CompoundAssignOperator, _ctk_ast_v1_CompoundAssignOperator__Output>
        CompoundLiteralExpr: MessageTypeDefinition<_ctk_ast_v1_CompoundLiteralExpr, _ctk_ast_v1_CompoundLiteralExpr__Output>
        CompoundStmt: MessageTypeDefinition<_ctk_ast_v1_CompoundStmt, _ctk_ast_v1_CompoundStmt__Output>
        ConceptDecl: MessageTypeDefinition<_ctk_ast_v1_ConceptDecl, _ctk_ast_v1_ConceptDecl__Output>
        ConceptReference: MessageTypeDefinition<_ctk_ast_v1_ConceptReference, _ctk_ast_v1_ConceptReference__Output>
        ConceptRequirement: MessageTypeDefinition<_ctk_ast_v1_ConceptRequirement, _ctk_ast_v1_ConceptRequirement__Output>
        ConceptSpecializationExpr: MessageTypeDefinition<_ctk_ast_v1_ConceptSpecializationExpr, _ctk_ast_v1_ConceptSpecializationExpr__Output>
        ConditionalOperator: MessageTypeDefinition<_ctk_ast_v1_ConditionalOperator, _ctk_ast_v1_ConditionalOperator__Output>
        ConstantArrayType: MessageTypeDefinition<_ctk_ast_v1_ConstantArrayType, _ctk_ast_v1_ConstantArrayType__Output>
        ConstantExpr: MessageTypeDefinition<_ctk_ast_v1_ConstantExpr, _ctk_ast_v1_ConstantExpr__Output>
        ConstantExprResult: EnumTypeDefinition
        ConstantMatrixType: MessageTypeDefinition<_ctk_ast_v1_ConstantMatrixType, _ctk_ast_v1_ConstantMatrixType__Output>
        ConstraintDescription: MessageTypeDefinition<_ctk_ast_v1_ConstraintDescription, _ctk_ast_v1_ConstraintDescription__Output>
        ConstraintDetail: MessageTypeDefinition<_ctk_ast_v1_ConstraintDetail, _ctk_ast_v1_ConstraintDetail__Output>
        ConstraintSatisfaction: MessageTypeDefinition<_ctk_ast_v1_ConstraintSatisfaction, _ctk_ast_v1_ConstraintSatisfaction__Output>
        ConstructionKind: EnumTypeDefinition
        ConstructorUsingShadowDecl: MessageTypeDefinition<_ctk_ast_v1_ConstructorUsingShadowDecl, _ctk_ast_v1_ConstructorUsingShadowDecl__Output>
        ContinueStmt: MessageTypeDefinition<_ctk_ast_v1_ContinueStmt, _ctk_ast_v1_ContinueStmt__Output>
        ConvertVectorExpr: MessageTypeDefinition<_ctk_ast_v1_ConvertVectorExpr, _ctk_ast_v1_ConvertVectorExpr__Output>
        CoreturnStmt: MessageTypeDefinition<_ctk_ast_v1_CoreturnStmt, _ctk_ast_v1_CoreturnStmt__Output>
        CoroutineBodyStmt: MessageTypeDefinition<_ctk_ast_v1_CoroutineBodyStmt, _ctk_ast_v1_CoroutineBodyStmt__Output>
        CountAttributedType: MessageTypeDefinition<_ctk_ast_v1_CountAttributedType, _ctk_ast_v1_CountAttributedType__Output>
        CoyieldExpr: MessageTypeDefinition<_ctk_ast_v1_CoyieldExpr, _ctk_ast_v1_CoyieldExpr__Output>
        DecayedType: MessageTypeDefinition<_ctk_ast_v1_DecayedType, _ctk_ast_v1_DecayedType__Output>
        DeclBuiltinTemplateKind: EnumTypeDefinition
        DeclDeductionCandidateKind: EnumTypeDefinition
        DeclInfo: MessageTypeDefinition<_ctk_ast_v1_DeclInfo, _ctk_ast_v1_DeclInfo__Output>
        DeclLinkageLanguage: EnumTypeDefinition
        DeclPragmaCommentKind: EnumTypeDefinition
        DeclRefExpr: MessageTypeDefinition<_ctk_ast_v1_DeclRefExpr, _ctk_ast_v1_DeclRefExpr__Output>
        DeclSourceDeductionGuideKind: EnumTypeDefinition
        DeclStmt: MessageTypeDefinition<_ctk_ast_v1_DeclStmt, _ctk_ast_v1_DeclStmt__Output>
        DeclTemplateSpecializationKind: EnumTypeDefinition
        DeclVariableInitializationStyle: EnumTypeDefinition
        DeclVariableTLSKind: EnumTypeDefinition
        DeclarationName: MessageTypeDefinition<_ctk_ast_v1_DeclarationName, _ctk_ast_v1_DeclarationName__Output>
        DeclarationSymbol: MessageTypeDefinition<_ctk_ast_v1_DeclarationSymbol, _ctk_ast_v1_DeclarationSymbol__Output>
        DeclarationTemplateArgument: MessageTypeDefinition<_ctk_ast_v1_DeclarationTemplateArgument, _ctk_ast_v1_DeclarationTemplateArgument__Output>
        DeclarationValue: MessageTypeDefinition<_ctk_ast_v1_DeclarationValue, _ctk_ast_v1_DeclarationValue__Output>
        DeclaratorDeclInfo: MessageTypeDefinition<_ctk_ast_v1_DeclaratorDeclInfo, _ctk_ast_v1_DeclaratorDeclInfo__Output>
        DecltypeType: MessageTypeDefinition<_ctk_ast_v1_DecltypeType, _ctk_ast_v1_DecltypeType__Output>
        DecompositionDecl: MessageTypeDefinition<_ctk_ast_v1_DecompositionDecl, _ctk_ast_v1_DecompositionDecl__Output>
        DeducedTemplateName: MessageTypeDefinition<_ctk_ast_v1_DeducedTemplateName, _ctk_ast_v1_DeducedTemplateName__Output>
        DeducedTemplateSpecializationType: MessageTypeDefinition<_ctk_ast_v1_DeducedTemplateSpecializationType, _ctk_ast_v1_DeducedTemplateSpecializationType__Output>
        DefaultStmt: MessageTypeDefinition<_ctk_ast_v1_DefaultStmt, _ctk_ast_v1_DefaultStmt__Output>
        DependentAddressSpaceType: MessageTypeDefinition<_ctk_ast_v1_DependentAddressSpaceType, _ctk_ast_v1_DependentAddressSpaceType__Output>
        DependentBitIntType: MessageTypeDefinition<_ctk_ast_v1_DependentBitIntType, _ctk_ast_v1_DependentBitIntType__Output>
        DependentCoawaitExpr: MessageTypeDefinition<_ctk_ast_v1_DependentCoawaitExpr, _ctk_ast_v1_DependentCoawaitExpr__Output>
        DependentDecltypeType: MessageTypeDefinition<_ctk_ast_v1_DependentDecltypeType, _ctk_ast_v1_DependentDecltypeType__Output>
        DependentNameType: MessageTypeDefinition<_ctk_ast_v1_DependentNameType, _ctk_ast_v1_DependentNameType__Output>
        DependentScopeDeclRefExpr: MessageTypeDefinition<_ctk_ast_v1_DependentScopeDeclRefExpr, _ctk_ast_v1_DependentScopeDeclRefExpr__Output>
        DependentSizedArrayType: MessageTypeDefinition<_ctk_ast_v1_DependentSizedArrayType, _ctk_ast_v1_DependentSizedArrayType__Output>
        DependentSizedExtVectorType: MessageTypeDefinition<_ctk_ast_v1_DependentSizedExtVectorType, _ctk_ast_v1_DependentSizedExtVectorType__Output>
        DependentSizedMatrixType: MessageTypeDefinition<_ctk_ast_v1_DependentSizedMatrixType, _ctk_ast_v1_DependentSizedMatrixType__Output>
        DependentTemplateName: MessageTypeDefinition<_ctk_ast_v1_DependentTemplateName, _ctk_ast_v1_DependentTemplateName__Output>
        DependentTypeOfExprType: MessageTypeDefinition<_ctk_ast_v1_DependentTypeOfExprType, _ctk_ast_v1_DependentTypeOfExprType__Output>
        DependentVectorType: MessageTypeDefinition<_ctk_ast_v1_DependentVectorType, _ctk_ast_v1_DependentVectorType__Output>
        DesignatedInitExpr: MessageTypeDefinition<_ctk_ast_v1_DesignatedInitExpr, _ctk_ast_v1_DesignatedInitExpr__Output>
        DesignatedInitUpdateExpr: MessageTypeDefinition<_ctk_ast_v1_DesignatedInitUpdateExpr, _ctk_ast_v1_DesignatedInitUpdateExpr__Output>
        Designator: MessageTypeDefinition<_ctk_ast_v1_Designator, _ctk_ast_v1_Designator__Output>
        DoStmt: MessageTypeDefinition<_ctk_ast_v1_DoStmt, _ctk_ast_v1_DoStmt__Output>
        DynamicCountKind: EnumTypeDefinition
        EmbedExpr: MessageTypeDefinition<_ctk_ast_v1_EmbedExpr, _ctk_ast_v1_EmbedExpr__Output>
        EmbedParameter: MessageTypeDefinition<_ctk_ast_v1_EmbedParameter, _ctk_ast_v1_EmbedParameter__Output>
        Empty: MessageTypeDefinition<_ctk_ast_v1_Empty, _ctk_ast_v1_Empty__Output>
        EmptyDecl: MessageTypeDefinition<_ctk_ast_v1_EmptyDecl, _ctk_ast_v1_EmptyDecl__Output>
        EnumConstantDecl: MessageTypeDefinition<_ctk_ast_v1_EnumConstantDecl, _ctk_ast_v1_EnumConstantDecl__Output>
        EnumDecl: MessageTypeDefinition<_ctk_ast_v1_EnumDecl, _ctk_ast_v1_EnumDecl__Output>
        EnumType: MessageTypeDefinition<_ctk_ast_v1_EnumType, _ctk_ast_v1_EnumType__Output>
        ExceptionDescription: MessageTypeDefinition<_ctk_ast_v1_ExceptionDescription, _ctk_ast_v1_ExceptionDescription__Output>
        ExceptionSpecification: EnumTypeDefinition
        ExportDecl: MessageTypeDefinition<_ctk_ast_v1_ExportDecl, _ctk_ast_v1_ExportDecl__Output>
        ExprInfo: MessageTypeDefinition<_ctk_ast_v1_ExprInfo, _ctk_ast_v1_ExprInfo__Output>
        ExprRequirement: MessageTypeDefinition<_ctk_ast_v1_ExprRequirement, _ctk_ast_v1_ExprRequirement__Output>
        ExprRequirementSatisfactionStatus: EnumTypeDefinition
        ExprWithCleanups: MessageTypeDefinition<_ctk_ast_v1_ExprWithCleanups, _ctk_ast_v1_ExprWithCleanups__Output>
        ExpressionTrait: EnumTypeDefinition
        ExpressionTraitExpr: MessageTypeDefinition<_ctk_ast_v1_ExpressionTraitExpr, _ctk_ast_v1_ExpressionTraitExpr__Output>
        ExpressionValue: MessageTypeDefinition<_ctk_ast_v1_ExpressionValue, _ctk_ast_v1_ExpressionValue__Output>
        ExtVectorElementExpr: MessageTypeDefinition<_ctk_ast_v1_ExtVectorElementExpr, _ctk_ast_v1_ExtVectorElementExpr__Output>
        ExtVectorType: MessageTypeDefinition<_ctk_ast_v1_ExtVectorType, _ctk_ast_v1_ExtVectorType__Output>
        ExternCContextDecl: MessageTypeDefinition<_ctk_ast_v1_ExternCContextDecl, _ctk_ast_v1_ExternCContextDecl__Output>
        FieldAvailability: MessageTypeDefinition<_ctk_ast_v1_FieldAvailability, _ctk_ast_v1_FieldAvailability__Output>
        FieldDecl: MessageTypeDefinition<_ctk_ast_v1_FieldDecl, _ctk_ast_v1_FieldDecl__Output>
        FieldState: EnumTypeDefinition
        FileScopeAsmDecl: MessageTypeDefinition<_ctk_ast_v1_FileScopeAsmDecl, _ctk_ast_v1_FileScopeAsmDecl__Output>
        FixedPointLiteral: MessageTypeDefinition<_ctk_ast_v1_FixedPointLiteral, _ctk_ast_v1_FixedPointLiteral__Output>
        FloatingLiteral: MessageTypeDefinition<_ctk_ast_v1_FloatingLiteral, _ctk_ast_v1_FloatingLiteral__Output>
        FloatingSemantics: EnumTypeDefinition
        ForStmt: MessageTypeDefinition<_ctk_ast_v1_ForStmt, _ctk_ast_v1_ForStmt__Output>
        FriendDecl: MessageTypeDefinition<_ctk_ast_v1_FriendDecl, _ctk_ast_v1_FriendDecl__Output>
        FriendTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_FriendTemplateDecl, _ctk_ast_v1_FriendTemplateDecl__Output>
        FunctionCallingConvention: EnumTypeDefinition
        FunctionDecl: MessageTypeDefinition<_ctk_ast_v1_FunctionDecl, _ctk_ast_v1_FunctionDecl__Output>
        FunctionDeclInfo: MessageTypeDefinition<_ctk_ast_v1_FunctionDeclInfo, _ctk_ast_v1_FunctionDeclInfo__Output>
        FunctionExtInfo: MessageTypeDefinition<_ctk_ast_v1_FunctionExtInfo, _ctk_ast_v1_FunctionExtInfo__Output>
        FunctionParmPackExpr: MessageTypeDefinition<_ctk_ast_v1_FunctionParmPackExpr, _ctk_ast_v1_FunctionParmPackExpr__Output>
        FunctionProtoExtInfo: MessageTypeDefinition<_ctk_ast_v1_FunctionProtoExtInfo, _ctk_ast_v1_FunctionProtoExtInfo__Output>
        FunctionProtoType: MessageTypeDefinition<_ctk_ast_v1_FunctionProtoType, _ctk_ast_v1_FunctionProtoType__Output>
        FunctionSignature: MessageTypeDefinition<_ctk_ast_v1_FunctionSignature, _ctk_ast_v1_FunctionSignature__Output>
        FunctionTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_FunctionTemplateDecl, _ctk_ast_v1_FunctionTemplateDecl__Output>
        GCCAsmStmt: MessageTypeDefinition<_ctk_ast_v1_GCCAsmStmt, _ctk_ast_v1_GCCAsmStmt__Output>
        GNUNullExpr: MessageTypeDefinition<_ctk_ast_v1_GNUNullExpr, _ctk_ast_v1_GNUNullExpr__Output>
        GenericAssociation: MessageTypeDefinition<_ctk_ast_v1_GenericAssociation, _ctk_ast_v1_GenericAssociation__Output>
        GenericSelectionExpr: MessageTypeDefinition<_ctk_ast_v1_GenericSelectionExpr, _ctk_ast_v1_GenericSelectionExpr__Output>
        GotoStmt: MessageTypeDefinition<_ctk_ast_v1_GotoStmt, _ctk_ast_v1_GotoStmt__Output>
        IfStmt: MessageTypeDefinition<_ctk_ast_v1_IfStmt, _ctk_ast_v1_IfStmt__Output>
        ImaginaryLiteral: MessageTypeDefinition<_ctk_ast_v1_ImaginaryLiteral, _ctk_ast_v1_ImaginaryLiteral__Output>
        ImplicitCastExpr: MessageTypeDefinition<_ctk_ast_v1_ImplicitCastExpr, _ctk_ast_v1_ImplicitCastExpr__Output>
        ImplicitConceptSpecializationDecl: MessageTypeDefinition<_ctk_ast_v1_ImplicitConceptSpecializationDecl, _ctk_ast_v1_ImplicitConceptSpecializationDecl__Output>
        ImplicitParamDecl: MessageTypeDefinition<_ctk_ast_v1_ImplicitParamDecl, _ctk_ast_v1_ImplicitParamDecl__Output>
        ImplicitValueInitExpr: MessageTypeDefinition<_ctk_ast_v1_ImplicitValueInitExpr, _ctk_ast_v1_ImplicitValueInitExpr__Output>
        ImportDecl: MessageTypeDefinition<_ctk_ast_v1_ImportDecl, _ctk_ast_v1_ImportDecl__Output>
        IncompleteArrayType: MessageTypeDefinition<_ctk_ast_v1_IncompleteArrayType, _ctk_ast_v1_IncompleteArrayType__Output>
        IndirectFieldDecl: MessageTypeDefinition<_ctk_ast_v1_IndirectFieldDecl, _ctk_ast_v1_IndirectFieldDecl__Output>
        IndirectGotoStmt: MessageTypeDefinition<_ctk_ast_v1_IndirectGotoStmt, _ctk_ast_v1_IndirectGotoStmt__Output>
        InitListExpr: MessageTypeDefinition<_ctk_ast_v1_InitListExpr, _ctk_ast_v1_InitListExpr__Output>
        InjectedClassNameType: MessageTypeDefinition<_ctk_ast_v1_InjectedClassNameType, _ctk_ast_v1_InjectedClassNameType__Output>
        IntegerLiteral: MessageTypeDefinition<_ctk_ast_v1_IntegerLiteral, _ctk_ast_v1_IntegerLiteral__Output>
        IntegralTemplateArgument: MessageTypeDefinition<_ctk_ast_v1_IntegralTemplateArgument, _ctk_ast_v1_IntegralTemplateArgument__Output>
        LValueReferenceType: MessageTypeDefinition<_ctk_ast_v1_LValueReferenceType, _ctk_ast_v1_LValueReferenceType__Output>
        LabelDecl: MessageTypeDefinition<_ctk_ast_v1_LabelDecl, _ctk_ast_v1_LabelDecl__Output>
        LabelStmt: MessageTypeDefinition<_ctk_ast_v1_LabelStmt, _ctk_ast_v1_LabelStmt__Output>
        LambdaCapture: MessageTypeDefinition<_ctk_ast_v1_LambdaCapture, _ctk_ast_v1_LambdaCapture__Output>
        LambdaCaptureKind: EnumTypeDefinition
        LambdaExpr: MessageTypeDefinition<_ctk_ast_v1_LambdaExpr, _ctk_ast_v1_LambdaExpr__Output>
        LifetimeExtendedTemporaryDecl: MessageTypeDefinition<_ctk_ast_v1_LifetimeExtendedTemporaryDecl, _ctk_ast_v1_LifetimeExtendedTemporaryDecl__Output>
        LinkageSpecDecl: MessageTypeDefinition<_ctk_ast_v1_LinkageSpecDecl, _ctk_ast_v1_LinkageSpecDecl__Output>
        MSAsmStmt: MessageTypeDefinition<_ctk_ast_v1_MSAsmStmt, _ctk_ast_v1_MSAsmStmt__Output>
        MSDependentExistsStmt: MessageTypeDefinition<_ctk_ast_v1_MSDependentExistsStmt, _ctk_ast_v1_MSDependentExistsStmt__Output>
        MSGuidDecl: MessageTypeDefinition<_ctk_ast_v1_MSGuidDecl, _ctk_ast_v1_MSGuidDecl__Output>
        MSPropertyDecl: MessageTypeDefinition<_ctk_ast_v1_MSPropertyDecl, _ctk_ast_v1_MSPropertyDecl__Output>
        MSPropertyRefExpr: MessageTypeDefinition<_ctk_ast_v1_MSPropertyRefExpr, _ctk_ast_v1_MSPropertyRefExpr__Output>
        MSPropertySubscriptExpr: MessageTypeDefinition<_ctk_ast_v1_MSPropertySubscriptExpr, _ctk_ast_v1_MSPropertySubscriptExpr__Output>
        MacroQualifiedType: MessageTypeDefinition<_ctk_ast_v1_MacroQualifiedType, _ctk_ast_v1_MacroQualifiedType__Output>
        MaterializeTemporaryExpr: MessageTypeDefinition<_ctk_ast_v1_MaterializeTemporaryExpr, _ctk_ast_v1_MaterializeTemporaryExpr__Output>
        MatrixSingleSubscriptExpr: MessageTypeDefinition<_ctk_ast_v1_MatrixSingleSubscriptExpr, _ctk_ast_v1_MatrixSingleSubscriptExpr__Output>
        MatrixSubscriptExpr: MessageTypeDefinition<_ctk_ast_v1_MatrixSubscriptExpr, _ctk_ast_v1_MatrixSubscriptExpr__Output>
        MemberExpr: MessageTypeDefinition<_ctk_ast_v1_MemberExpr, _ctk_ast_v1_MemberExpr__Output>
        MemberPointerType: MessageTypeDefinition<_ctk_ast_v1_MemberPointerType, _ctk_ast_v1_MemberPointerType__Output>
        NamedDeclInfo: MessageTypeDefinition<_ctk_ast_v1_NamedDeclInfo, _ctk_ast_v1_NamedDeclInfo__Output>
        NamespaceAliasDecl: MessageTypeDefinition<_ctk_ast_v1_NamespaceAliasDecl, _ctk_ast_v1_NamespaceAliasDecl__Output>
        NamespaceDecl: MessageTypeDefinition<_ctk_ast_v1_NamespaceDecl, _ctk_ast_v1_NamespaceDecl__Output>
        NestedNameSpecifier: MessageTypeDefinition<_ctk_ast_v1_NestedNameSpecifier, _ctk_ast_v1_NestedNameSpecifier__Output>
        NestedNamespaceName: MessageTypeDefinition<_ctk_ast_v1_NestedNamespaceName, _ctk_ast_v1_NestedNamespaceName__Output>
        NestedRequirement: MessageTypeDefinition<_ctk_ast_v1_NestedRequirement, _ctk_ast_v1_NestedRequirement__Output>
        NoInitExpr: MessageTypeDefinition<_ctk_ast_v1_NoInitExpr, _ctk_ast_v1_NoInitExpr__Output>
        NonTypeTemplateParmDecl: MessageTypeDefinition<_ctk_ast_v1_NonTypeTemplateParmDecl, _ctk_ast_v1_NonTypeTemplateParmDecl__Output>
        NullStmt: MessageTypeDefinition<_ctk_ast_v1_NullStmt, _ctk_ast_v1_NullStmt__Output>
        ObjectKind: EnumTypeDefinition
        OffsetOfComponent: MessageTypeDefinition<_ctk_ast_v1_OffsetOfComponent, _ctk_ast_v1_OffsetOfComponent__Output>
        OffsetOfExpr: MessageTypeDefinition<_ctk_ast_v1_OffsetOfExpr, _ctk_ast_v1_OffsetOfExpr__Output>
        OpaqueValueExpr: MessageTypeDefinition<_ctk_ast_v1_OpaqueValueExpr, _ctk_ast_v1_OpaqueValueExpr__Output>
        OverloadedOperatorKind: EnumTypeDefinition
        OverloadedTemplateName: MessageTypeDefinition<_ctk_ast_v1_OverloadedTemplateName, _ctk_ast_v1_OverloadedTemplateName__Output>
        PackExpansionExpr: MessageTypeDefinition<_ctk_ast_v1_PackExpansionExpr, _ctk_ast_v1_PackExpansionExpr__Output>
        PackExpansionType: MessageTypeDefinition<_ctk_ast_v1_PackExpansionType, _ctk_ast_v1_PackExpansionType__Output>
        PackIndexingExpr: MessageTypeDefinition<_ctk_ast_v1_PackIndexingExpr, _ctk_ast_v1_PackIndexingExpr__Output>
        PackIndexingType: MessageTypeDefinition<_ctk_ast_v1_PackIndexingType, _ctk_ast_v1_PackIndexingType__Output>
        ParameterValue: MessageTypeDefinition<_ctk_ast_v1_ParameterValue, _ctk_ast_v1_ParameterValue__Output>
        ParenExpr: MessageTypeDefinition<_ctk_ast_v1_ParenExpr, _ctk_ast_v1_ParenExpr__Output>
        ParenListExpr: MessageTypeDefinition<_ctk_ast_v1_ParenListExpr, _ctk_ast_v1_ParenListExpr__Output>
        ParenType: MessageTypeDefinition<_ctk_ast_v1_ParenType, _ctk_ast_v1_ParenType__Output>
        ParmVarDecl: MessageTypeDefinition<_ctk_ast_v1_ParmVarDecl, _ctk_ast_v1_ParmVarDecl__Output>
        PointerType: MessageTypeDefinition<_ctk_ast_v1_PointerType, _ctk_ast_v1_PointerType__Output>
        PragmaCommentDecl: MessageTypeDefinition<_ctk_ast_v1_PragmaCommentDecl, _ctk_ast_v1_PragmaCommentDecl__Output>
        PragmaDetectMismatchDecl: MessageTypeDefinition<_ctk_ast_v1_PragmaDetectMismatchDecl, _ctk_ast_v1_PragmaDetectMismatchDecl__Output>
        PredefinedExpr: MessageTypeDefinition<_ctk_ast_v1_PredefinedExpr, _ctk_ast_v1_PredefinedExpr__Output>
        PredefinedIdentKind: EnumTypeDefinition
        PredefinedSugarType: MessageTypeDefinition<_ctk_ast_v1_PredefinedSugarType, _ctk_ast_v1_PredefinedSugarType__Output>
        PredefinedTypeKind: EnumTypeDefinition
        PseudoObjectExpr: MessageTypeDefinition<_ctk_ast_v1_PseudoObjectExpr, _ctk_ast_v1_PseudoObjectExpr__Output>
        QualType: MessageTypeDefinition<_ctk_ast_v1_QualType, _ctk_ast_v1_QualType__Output>
        QualifiedTemplateName: MessageTypeDefinition<_ctk_ast_v1_QualifiedTemplateName, _ctk_ast_v1_QualifiedTemplateName__Output>
        Qualifiers: MessageTypeDefinition<_ctk_ast_v1_Qualifiers, _ctk_ast_v1_Qualifiers__Output>
        RValueReferenceType: MessageTypeDefinition<_ctk_ast_v1_RValueReferenceType, _ctk_ast_v1_RValueReferenceType__Output>
        RecordDecl: MessageTypeDefinition<_ctk_ast_v1_RecordDecl, _ctk_ast_v1_RecordDecl__Output>
        RecordDeclInfo: MessageTypeDefinition<_ctk_ast_v1_RecordDeclInfo, _ctk_ast_v1_RecordDeclInfo__Output>
        RecordType: MessageTypeDefinition<_ctk_ast_v1_RecordType, _ctk_ast_v1_RecordType__Output>
        RecoveryExpr: MessageTypeDefinition<_ctk_ast_v1_RecoveryExpr, _ctk_ast_v1_RecoveryExpr__Output>
        RefQualifier: EnumTypeDefinition
        RequirementInfo: MessageTypeDefinition<_ctk_ast_v1_RequirementInfo, _ctk_ast_v1_RequirementInfo__Output>
        RequiresExpr: MessageTypeDefinition<_ctk_ast_v1_RequiresExpr, _ctk_ast_v1_RequiresExpr__Output>
        RequiresExprBodyDecl: MessageTypeDefinition<_ctk_ast_v1_RequiresExprBodyDecl, _ctk_ast_v1_RequiresExprBodyDecl__Output>
        ReturnStmt: MessageTypeDefinition<_ctk_ast_v1_ReturnStmt, _ctk_ast_v1_ReturnStmt__Output>
        ReturnTypeRequirement: MessageTypeDefinition<_ctk_ast_v1_ReturnTypeRequirement, _ctk_ast_v1_ReturnTypeRequirement__Output>
        SEHExceptStmt: MessageTypeDefinition<_ctk_ast_v1_SEHExceptStmt, _ctk_ast_v1_SEHExceptStmt__Output>
        SEHFinallyStmt: MessageTypeDefinition<_ctk_ast_v1_SEHFinallyStmt, _ctk_ast_v1_SEHFinallyStmt__Output>
        SEHLeaveStmt: MessageTypeDefinition<_ctk_ast_v1_SEHLeaveStmt, _ctk_ast_v1_SEHLeaveStmt__Output>
        SEHTryStmt: MessageTypeDefinition<_ctk_ast_v1_SEHTryStmt, _ctk_ast_v1_SEHTryStmt__Output>
        SemanticResult: MessageTypeDefinition<_ctk_ast_v1_SemanticResult, _ctk_ast_v1_SemanticResult__Output>
        ShuffleVectorExpr: MessageTypeDefinition<_ctk_ast_v1_ShuffleVectorExpr, _ctk_ast_v1_ShuffleVectorExpr__Output>
        SizeOfPackExpr: MessageTypeDefinition<_ctk_ast_v1_SizeOfPackExpr, _ctk_ast_v1_SizeOfPackExpr__Output>
        SourceLocExpr: MessageTypeDefinition<_ctk_ast_v1_SourceLocExpr, _ctk_ast_v1_SourceLocExpr__Output>
        SourceLocExprKind: EnumTypeDefinition
        StatementValue: MessageTypeDefinition<_ctk_ast_v1_StatementValue, _ctk_ast_v1_StatementValue__Output>
        StaticAssertDecl: MessageTypeDefinition<_ctk_ast_v1_StaticAssertDecl, _ctk_ast_v1_StaticAssertDecl__Output>
        StmtExpr: MessageTypeDefinition<_ctk_ast_v1_StmtExpr, _ctk_ast_v1_StmtExpr__Output>
        StorageClass: EnumTypeDefinition
        StringLiteral: MessageTypeDefinition<_ctk_ast_v1_StringLiteral, _ctk_ast_v1_StringLiteral__Output>
        StringLiteralKind: EnumTypeDefinition
        StructuralTemplateArgument: MessageTypeDefinition<_ctk_ast_v1_StructuralTemplateArgument, _ctk_ast_v1_StructuralTemplateArgument__Output>
        SubstBuiltinTemplatePackType: MessageTypeDefinition<_ctk_ast_v1_SubstBuiltinTemplatePackType, _ctk_ast_v1_SubstBuiltinTemplatePackType__Output>
        SubstNonTypeTemplateParmExpr: MessageTypeDefinition<_ctk_ast_v1_SubstNonTypeTemplateParmExpr, _ctk_ast_v1_SubstNonTypeTemplateParmExpr__Output>
        SubstNonTypeTemplateParmPackExpr: MessageTypeDefinition<_ctk_ast_v1_SubstNonTypeTemplateParmPackExpr, _ctk_ast_v1_SubstNonTypeTemplateParmPackExpr__Output>
        SubstTemplateTypeParmPackType: MessageTypeDefinition<_ctk_ast_v1_SubstTemplateTypeParmPackType, _ctk_ast_v1_SubstTemplateTypeParmPackType__Output>
        SubstTemplateTypeParmType: MessageTypeDefinition<_ctk_ast_v1_SubstTemplateTypeParmType, _ctk_ast_v1_SubstTemplateTypeParmType__Output>
        SubstitutedTemplateName: MessageTypeDefinition<_ctk_ast_v1_SubstitutedTemplateName, _ctk_ast_v1_SubstitutedTemplateName__Output>
        SubstitutedTemplatePack: MessageTypeDefinition<_ctk_ast_v1_SubstitutedTemplatePack, _ctk_ast_v1_SubstitutedTemplatePack__Output>
        SubstitutionDiagnostic: MessageTypeDefinition<_ctk_ast_v1_SubstitutionDiagnostic, _ctk_ast_v1_SubstitutionDiagnostic__Output>
        SwitchStmt: MessageTypeDefinition<_ctk_ast_v1_SwitchStmt, _ctk_ast_v1_SwitchStmt__Output>
        SymbolKind: EnumTypeDefinition
        TagDeclInfo: MessageTypeDefinition<_ctk_ast_v1_TagDeclInfo, _ctk_ast_v1_TagDeclInfo__Output>
        TagKind: EnumTypeDefinition
        TemplateArgument: MessageTypeDefinition<_ctk_ast_v1_TemplateArgument, _ctk_ast_v1_TemplateArgument__Output>
        TemplateArgumentDescription: MessageTypeDefinition<_ctk_ast_v1_TemplateArgumentDescription, _ctk_ast_v1_TemplateArgumentDescription__Output>
        TemplateArgumentDescriptionKind: EnumTypeDefinition
        TemplateArgumentPack: MessageTypeDefinition<_ctk_ast_v1_TemplateArgumentPack, _ctk_ast_v1_TemplateArgumentPack__Output>
        TemplateExpansionArgument: MessageTypeDefinition<_ctk_ast_v1_TemplateExpansionArgument, _ctk_ast_v1_TemplateExpansionArgument__Output>
        TemplateName: MessageTypeDefinition<_ctk_ast_v1_TemplateName, _ctk_ast_v1_TemplateName__Output>
        TemplateParamObjectDecl: MessageTypeDefinition<_ctk_ast_v1_TemplateParamObjectDecl, _ctk_ast_v1_TemplateParamObjectDecl__Output>
        TemplateParameterDescription: MessageTypeDefinition<_ctk_ast_v1_TemplateParameterDescription, _ctk_ast_v1_TemplateParameterDescription__Output>
        TemplateParameterDescriptionKind: EnumTypeDefinition
        TemplateParameterList: MessageTypeDefinition<_ctk_ast_v1_TemplateParameterList, _ctk_ast_v1_TemplateParameterList__Output>
        TemplateSpecializationType: MessageTypeDefinition<_ctk_ast_v1_TemplateSpecializationType, _ctk_ast_v1_TemplateSpecializationType__Output>
        TemplateTemplateParmDecl: MessageTypeDefinition<_ctk_ast_v1_TemplateTemplateParmDecl, _ctk_ast_v1_TemplateTemplateParmDecl__Output>
        TemplateTypeParmDecl: MessageTypeDefinition<_ctk_ast_v1_TemplateTypeParmDecl, _ctk_ast_v1_TemplateTypeParmDecl__Output>
        TemplateTypeParmType: MessageTypeDefinition<_ctk_ast_v1_TemplateTypeParmType, _ctk_ast_v1_TemplateTypeParmType__Output>
        TopLevelStmtDecl: MessageTypeDefinition<_ctk_ast_v1_TopLevelStmtDecl, _ctk_ast_v1_TopLevelStmtDecl__Output>
        TranslationUnitDecl: MessageTypeDefinition<_ctk_ast_v1_TranslationUnitDecl, _ctk_ast_v1_TranslationUnitDecl__Output>
        TypeAliasDecl: MessageTypeDefinition<_ctk_ast_v1_TypeAliasDecl, _ctk_ast_v1_TypeAliasDecl__Output>
        TypeAliasTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_TypeAliasTemplateDecl, _ctk_ast_v1_TypeAliasTemplateDecl__Output>
        TypeConstraint: MessageTypeDefinition<_ctk_ast_v1_TypeConstraint, _ctk_ast_v1_TypeConstraint__Output>
        TypeDeclInfo: MessageTypeDefinition<_ctk_ast_v1_TypeDeclInfo, _ctk_ast_v1_TypeDeclInfo__Output>
        TypeDescription: MessageTypeDefinition<_ctk_ast_v1_TypeDescription, _ctk_ast_v1_TypeDescription__Output>
        TypeInfo: MessageTypeDefinition<_ctk_ast_v1_TypeInfo, _ctk_ast_v1_TypeInfo__Output>
        TypeOfExprType: MessageTypeDefinition<_ctk_ast_v1_TypeOfExprType, _ctk_ast_v1_TypeOfExprType__Output>
        TypeOfKind: EnumTypeDefinition
        TypeOfType: MessageTypeDefinition<_ctk_ast_v1_TypeOfType, _ctk_ast_v1_TypeOfType__Output>
        TypeRequirement: MessageTypeDefinition<_ctk_ast_v1_TypeRequirement, _ctk_ast_v1_TypeRequirement__Output>
        TypeTrait: EnumTypeDefinition
        TypeTraitExpr: MessageTypeDefinition<_ctk_ast_v1_TypeTraitExpr, _ctk_ast_v1_TypeTraitExpr__Output>
        TypeValue: MessageTypeDefinition<_ctk_ast_v1_TypeValue, _ctk_ast_v1_TypeValue__Output>
        TypedefDecl: MessageTypeDefinition<_ctk_ast_v1_TypedefDecl, _ctk_ast_v1_TypedefDecl__Output>
        TypedefType: MessageTypeDefinition<_ctk_ast_v1_TypedefType, _ctk_ast_v1_TypedefType__Output>
        UnaryExprOrTypeTraitExpr: MessageTypeDefinition<_ctk_ast_v1_UnaryExprOrTypeTraitExpr, _ctk_ast_v1_UnaryExprOrTypeTraitExpr__Output>
        UnaryExprTrait: EnumTypeDefinition
        UnaryOpcode: EnumTypeDefinition
        UnaryOperator: MessageTypeDefinition<_ctk_ast_v1_UnaryOperator, _ctk_ast_v1_UnaryOperator__Output>
        UnaryTransformKind: EnumTypeDefinition
        UnaryTransformType: MessageTypeDefinition<_ctk_ast_v1_UnaryTransformType, _ctk_ast_v1_UnaryTransformType__Output>
        UnnamedGlobalConstantDecl: MessageTypeDefinition<_ctk_ast_v1_UnnamedGlobalConstantDecl, _ctk_ast_v1_UnnamedGlobalConstantDecl__Output>
        UnresolvedLookupExpr: MessageTypeDefinition<_ctk_ast_v1_UnresolvedLookupExpr, _ctk_ast_v1_UnresolvedLookupExpr__Output>
        UnresolvedMemberExpr: MessageTypeDefinition<_ctk_ast_v1_UnresolvedMemberExpr, _ctk_ast_v1_UnresolvedMemberExpr__Output>
        UnresolvedUsingIfExistsDecl: MessageTypeDefinition<_ctk_ast_v1_UnresolvedUsingIfExistsDecl, _ctk_ast_v1_UnresolvedUsingIfExistsDecl__Output>
        UnresolvedUsingType: MessageTypeDefinition<_ctk_ast_v1_UnresolvedUsingType, _ctk_ast_v1_UnresolvedUsingType__Output>
        UnresolvedUsingTypenameDecl: MessageTypeDefinition<_ctk_ast_v1_UnresolvedUsingTypenameDecl, _ctk_ast_v1_UnresolvedUsingTypenameDecl__Output>
        UnresolvedUsingValueDecl: MessageTypeDefinition<_ctk_ast_v1_UnresolvedUsingValueDecl, _ctk_ast_v1_UnresolvedUsingValueDecl__Output>
        UnsupportedReason: EnumTypeDefinition
        UnsupportedValue: MessageTypeDefinition<_ctk_ast_v1_UnsupportedValue, _ctk_ast_v1_UnsupportedValue__Output>
        UserDefinedLiteral: MessageTypeDefinition<_ctk_ast_v1_UserDefinedLiteral, _ctk_ast_v1_UserDefinedLiteral__Output>
        UsingDecl: MessageTypeDefinition<_ctk_ast_v1_UsingDecl, _ctk_ast_v1_UsingDecl__Output>
        UsingDirectiveDecl: MessageTypeDefinition<_ctk_ast_v1_UsingDirectiveDecl, _ctk_ast_v1_UsingDirectiveDecl__Output>
        UsingEnumDecl: MessageTypeDefinition<_ctk_ast_v1_UsingEnumDecl, _ctk_ast_v1_UsingEnumDecl__Output>
        UsingPackDecl: MessageTypeDefinition<_ctk_ast_v1_UsingPackDecl, _ctk_ast_v1_UsingPackDecl__Output>
        UsingShadowDecl: MessageTypeDefinition<_ctk_ast_v1_UsingShadowDecl, _ctk_ast_v1_UsingShadowDecl__Output>
        UsingType: MessageTypeDefinition<_ctk_ast_v1_UsingType, _ctk_ast_v1_UsingType__Output>
        VAArgExpr: MessageTypeDefinition<_ctk_ast_v1_VAArgExpr, _ctk_ast_v1_VAArgExpr__Output>
        ValueCategory: EnumTypeDefinition
        ValueDeclInfo: MessageTypeDefinition<_ctk_ast_v1_ValueDeclInfo, _ctk_ast_v1_ValueDeclInfo__Output>
        VarDecl: MessageTypeDefinition<_ctk_ast_v1_VarDecl, _ctk_ast_v1_VarDecl__Output>
        VarDeclInfo: MessageTypeDefinition<_ctk_ast_v1_VarDeclInfo, _ctk_ast_v1_VarDeclInfo__Output>
        VarTemplateDecl: MessageTypeDefinition<_ctk_ast_v1_VarTemplateDecl, _ctk_ast_v1_VarTemplateDecl__Output>
        VarTemplatePartialSpecializationDecl: MessageTypeDefinition<_ctk_ast_v1_VarTemplatePartialSpecializationDecl, _ctk_ast_v1_VarTemplatePartialSpecializationDecl__Output>
        VarTemplateSpecializationDecl: MessageTypeDefinition<_ctk_ast_v1_VarTemplateSpecializationDecl, _ctk_ast_v1_VarTemplateSpecializationDecl__Output>
        VariableArrayType: MessageTypeDefinition<_ctk_ast_v1_VariableArrayType, _ctk_ast_v1_VariableArrayType__Output>
        VectorKind: EnumTypeDefinition
        VectorType: MessageTypeDefinition<_ctk_ast_v1_VectorType, _ctk_ast_v1_VectorType__Output>
        WhileStmt: MessageTypeDefinition<_ctk_ast_v1_WhileStmt, _ctk_ast_v1_WhileStmt__Output>
      }
    }
    match: {
      v1: {
        AttachSessionRequest: MessageTypeDefinition<_ctk_match_v1_AttachSessionRequest, _ctk_match_v1_AttachSessionRequest__Output>
        BindingMatchScope: EnumTypeDefinition
        BindingMatchTarget: MessageTypeDefinition<_ctk_match_v1_BindingMatchTarget, _ctk_match_v1_BindingMatchTarget__Output>
        CacheResources: MessageTypeDefinition<_ctk_match_v1_CacheResources, _ctk_match_v1_CacheResources__Output>
        CallDispatch: EnumTypeDefinition
        CallSiteFacts: MessageTypeDefinition<_ctk_match_v1_CallSiteFacts, _ctk_match_v1_CallSiteFacts__Output>
        CloseSessionRequest: MessageTypeDefinition<_ctk_match_v1_CloseSessionRequest, _ctk_match_v1_CloseSessionRequest__Output>
        CloseSessionResponse: MessageTypeDefinition<_ctk_match_v1_CloseSessionResponse, _ctk_match_v1_CloseSessionResponse__Output>
        FileMatchTarget: MessageTypeDefinition<_ctk_match_v1_FileMatchTarget, _ctk_match_v1_FileMatchTarget__Output>
        ListSessionsRequest: MessageTypeDefinition<_ctk_match_v1_ListSessionsRequest, _ctk_match_v1_ListSessionsRequest__Output>
        ListSessionsResponse: MessageTypeDefinition<_ctk_match_v1_ListSessionsResponse, _ctk_match_v1_ListSessionsResponse__Output>
        MatchBinding: MessageTypeDefinition<_ctk_match_v1_MatchBinding, _ctk_match_v1_MatchBinding__Output>
        MatchRequest: MessageTypeDefinition<_ctk_match_v1_MatchRequest, _ctk_match_v1_MatchRequest__Output>
        MatchResponse: MessageTypeDefinition<_ctk_match_v1_MatchResponse, _ctk_match_v1_MatchResponse__Output>
        MatchResult: MessageTypeDefinition<_ctk_match_v1_MatchResult, _ctk_match_v1_MatchResult__Output>
        MatchService: SubtypeConstructor<typeof grpc.Client, _ctk_match_v1_MatchServiceClient> & { service: _ctk_match_v1_MatchServiceDefinition }
        MatchSourcePoint: MessageTypeDefinition<_ctk_match_v1_MatchSourcePoint, _ctk_match_v1_MatchSourcePoint__Output>
        MatchSourceRange: MessageTypeDefinition<_ctk_match_v1_MatchSourceRange, _ctk_match_v1_MatchSourceRange__Output>
        MatchStreamCompleted: MessageTypeDefinition<_ctk_match_v1_MatchStreamCompleted, _ctk_match_v1_MatchStreamCompleted__Output>
        MatchStreamEvent: MessageTypeDefinition<_ctk_match_v1_MatchStreamEvent, _ctk_match_v1_MatchStreamEvent__Output>
        MatchTraversalMode: EnumTypeDefinition
        ParseRequest: MessageTypeDefinition<_ctk_match_v1_ParseRequest, _ctk_match_v1_ParseRequest__Output>
        ParseResponse: MessageTypeDefinition<_ctk_match_v1_ParseResponse, _ctk_match_v1_ParseResponse__Output>
        PruneCachesRequest: MessageTypeDefinition<_ctk_match_v1_PruneCachesRequest, _ctk_match_v1_PruneCachesRequest__Output>
        PruneCachesResponse: MessageTypeDefinition<_ctk_match_v1_PruneCachesResponse, _ctk_match_v1_PruneCachesResponse__Output>
        ServerStatusRequest: MessageTypeDefinition<_ctk_match_v1_ServerStatusRequest, _ctk_match_v1_ServerStatusRequest__Output>
        ServerStatusResponse: MessageTypeDefinition<_ctk_match_v1_ServerStatusResponse, _ctk_match_v1_ServerStatusResponse__Output>
        SessionInfo: MessageTypeDefinition<_ctk_match_v1_SessionInfo, _ctk_match_v1_SessionInfo__Output>
        SessionMatchTarget: MessageTypeDefinition<_ctk_match_v1_SessionMatchTarget, _ctk_match_v1_SessionMatchTarget__Output>
      }
    }
  }
  google: {
    protobuf: {
      Timestamp: MessageTypeDefinition<_google_protobuf_Timestamp, _google_protobuf_Timestamp__Output>
    }
  }
}

