#include "cpp_source.hpp"
#include "grammar/syntax.hpp"

#include <stdexcept>
#include <string_view>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {
namespace {

const Syntax *child(const Syntax &tree, std::string_view kind) {
  for (const auto &node : tree.children)
    if (node.name == kind)
      return &node;
  return nullptr;
}

const Syntax *expression(const Syntax &tree) {
  auto *node = &tree;
  while (node->children.size() == 1 &&
         (node->name == "proto_pipe_expr" ||
          node->name == "proto_recovery_expr" ||
          node->name == "proto_comparison" ||
          node->name == "host_expression"))
    node = &node->children.front();
  return node;
}

std::string cpp_string(llvm::StringRef text) {
  std::string quoted = "\"";
  for (unsigned char byte : text) {
    if (byte == '"' || byte == '\\') {
      quoted += '\\';
      quoted += static_cast<char>(byte);
    } else if (byte >= 32 && byte < 127) {
      quoted += static_cast<char>(byte);
    } else {
      quoted += '\\';
      quoted += static_cast<char>('0' + (byte >> 6));
      quoted += static_cast<char>('0' + ((byte >> 3) & 7));
      quoted += static_cast<char>('0' + (byte & 7));
    }
  }
  return quoted + '"';
}

[[noreturn]] void unsupported(const char *message) {
  throw std::runtime_error(message);
}

std::string matcher(const Syntax &node, bool root) {
  if (node.name != "matcher" || node.children.empty())
    unsupported("expected a typed Clang matcher");
  const auto name = node.children.front().text;
  const auto *binding = child(node, "legacy_bind");
  const auto *args = child(node, "legacy_arguments");
  if (root) {
    if ((name != "functionDecl" && name != "cxxMethodDecl") || !binding)
      unsupported("the C++ backend requires a functionDecl or cxxMethodDecl with .bind()");
  } else if (binding) {
    unsupported("only the outer matcher can bind a node");
  } else if (name == "hasName" || name == "unless") {
    if (!args || args->children.size() != 1)
      unsupported("expected one matcher predicate argument");
  } else if (args || (name != "isDefinition" && name != "isExpansionInMainFile" &&
                      name != "isImplicit" && name != "isConst")) {
    unsupported("unsupported C++ matcher predicate");
  }

  std::string result(name);
  result += '(';
  if (args) {
    bool comma = false;
    for (const auto &arg : args->children) {
      if (arg.name == "LEGACY_COMMA")
        continue;
      if (comma)
        result += ", ";
      comma = true;
      if (name == "hasName" && arg.name == "LEGACY_STRING")
        result += cpp_string(decode_ctk_string(arg.text));
      else
        result += matcher(*expression(arg), false);
    }
  }
  result += ')';
  if (binding)
    result += ".bind(" + cpp_string(decode_ctk_string(
                               child(*binding, "LEGACY_STRING")->text)) + ")";
  return result;
}

std::string typed_query(const Syntax &tree, llvm::StringRef source,
                        llvm::StringRef path) {
  const auto *start = child(tree, "proto_start");
  const auto *program = start ? child(*start, "proto_program") : nullptr;
  std::vector<const Syntax *> statements;
  if (program)
    for (const auto &node : program->children)
      if (node.name != "proto_separators")
        statements.push_back(&node);
  if (statements.size() != 3 || statements[0]->name != "proto_let_stmt" ||
      statements[1]->name != "proto_let_stmt")
    unsupported("the C++ backend expects a parse binding, match binding and foreach");
  const auto name = [](const Syntax &node) -> std::string_view {
    const auto *pattern = child(node, "proto_name_pattern");
    if (!pattern)
      unsupported("expected a simple binding name");
    return pattern->children.front().text;
  };
  const auto reference = [](const Syntax &node, std::string_view expected) {
    const auto *ref = expression(node);
    return ref->name == "proto_reference" && ref->children.front().text == expected;
  };
  const auto target = name(*statements[0]);
  const auto rows = name(*statements[1]);
  const auto *parse = expression(statements[0]->children.back());
  const auto *match = expression(statements[1]->children.back());
  if (parse->name != "legacy_parse_expression" || parse->children.size() != 2 ||
      target == rows || match->name != "match" || match->children.size() != 4 ||
      !reference(match->children.back(), target))
    unsupported("expected parse arg.file and match in the parsed target binding");
  const auto *file = expression(parse->children.back());
  if (file->name != "proto_postfix" || file->children.size() != 2 ||
      !reference(file->children.front(), "arg") ||
      file->children.back().name != "proto_member_part" ||
      file->children.back().children.back().text != "file")
    unsupported("expected parse arg.file");

  const auto *query = expression(match->children[1]);
  const auto code = matcher(*query, true);
  const auto bind = decode_ctk_string(
      child(*child(*query, "legacy_bind"), "LEGACY_STRING")->text);
  const auto *loop = expression(*statements[2]);
  if (loop->name != "proto_foreach_expr" || loop->children.size() != 4 ||
      !reference(loop->children[2], rows))
    unsupported("expected foreach over the matched rows");
  const auto *block = child(loop->children.back(), "proto_block");
  const auto *body = block ? child(*block, "proto_block_contents") : nullptr;
  const Syntax *print = nullptr;
  if (body)
    for (const auto &node : body->children) {
      if (node.name == "proto_separators")
        continue;
      if (print || node.name != "proto_print_stmt")
        unsupported("expected one print in foreach");
      print = &node;
    }
  if (!print)
    unsupported("expected one print in foreach");
  const auto *printed = expression(print->children.back());
  if (printed->name != "proto_postfix" || printed->children.size() != 3 ||
      !reference(printed->children.front(), name(*loop)) ||
      printed->children[1].name != "proto_member_part" ||
      printed->children[1].children.back().text != bind ||
      printed->children[2].name != "proto_member_part")
    unsupported("expected a bound declaration field");
  const auto projection = printed->children[2].children.back().text;
  const auto *getter = projection == "decl_name" ? "getNameAsString" :
                       projection == "qualified_name" ? "getQualifiedNameAsString" : nullptr;
  if (!getter)
    unsupported("expected decl_name or qualified_name");

  std::string result;
  llvm::raw_string_ostream output(result);
  output << "#include <ctk/jit/runtime.hpp>\n#include <string>\n#include <vector>\n"
            "void run(ctk::jit::RunContext &ctx) {\n"
            "  using namespace clang::ast_matchers;\n#line "
         << 1 + source.take_front(match->begin).count('\n') << ' ' << cpp_string(path)
         << "\n  const auto matcher = " << code << ";\n#line 1 \"<ctk-jit>\"\n"
            "  std::vector<std::string> names;\n"
            "  ctx.match(matcher, [&](const MatchFinder::MatchResult &result) {\n"
            "    if (const auto *node = result.Nodes.getNodeAs<clang::FunctionDecl>("
         << cpp_string(bind) << "))\n      names.push_back(node->" << getter
         << "());\n  });\n  for (const auto &name : names) ctx.emit_text(name);\n}\n";
  return result;
}

} // namespace

llvm::Expected<std::string> cpp_source(llvm::StringRef source,
                                      llvm::StringRef path, bool ctk) {
  std::string result;
  if (ctk) {
    auto tree = parse_ctk(source);
    if (!tree)
      return tree.takeError();
    try {
      result = typed_query(*tree, source, path);
    } catch (const std::exception &error) {
      return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                     "%s", error.what());
    }
  } else {
    result = "#line 1 " + cpp_string(path) + "\n" + source.str();
  }
  result += "\n#line 1 \"<ctk-jit-entry>\"\n"
            "extern \"C\" void ctk_jit_run_v1(ctk::jit::RunContext *ctx) { run(*ctx); }\n";
  return result;
}

} // namespace ctk::jit
