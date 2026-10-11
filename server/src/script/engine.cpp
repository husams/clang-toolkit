#include "ctk/script/engine.hpp"
#include "ctk/script/error.hpp"
#include <google/protobuf/util/json_util.h>
#ifdef CTK_BUILD_SCRIPT
#include "interpreter.hpp"
#include "scoped_block.hpp"
#endif
namespace ctk::script {
namespace {
#ifdef CTK_BUILD_SCRIPT
bool expression_contains_batch(const detail::Expression &expression);
bool statements_contain_batch(
    const std::vector<detail::Statement> &statements) {
  for (const auto &statement : statements) {
    if ((statement.expression &&
         expression_contains_batch(*statement.expression)) ||
        (statement.destination &&
         expression_contains_batch(*statement.destination)) ||
        statements_contain_batch(statement.body))
      return true;
  }
  return false;
}
bool expression_contains_batch(const detail::Expression &expression) {
  if (expression.kind == detail::Expression::Kind::Batch)
    return true;
  if (expression.source && expression_contains_batch(*expression.source))
    return true;
  if (expression.target && expression_contains_batch(*expression.target))
    return true;
  for (const auto &element : expression.elements)
    if (element && expression_contains_batch(*element))
      return true;
  for (const auto &argument : expression.arguments)
    if (argument.expression && expression_contains_batch(*argument.expression))
      return true;
  if (expression.block &&
      (statements_contain_batch(expression.block->statements) ||
       (expression.block->yielded &&
        expression_contains_batch(*expression.block->yielded)) ||
       (expression.block->target &&
        expression_contains_batch(*expression.block->target))))
    return true;
  return expression.batch_body &&
         statements_contain_batch(expression.batch_body->statements);
}
#endif
} // namespace
bool Engine::contains_batch(const std::string &source) const {
#ifdef CTK_BUILD_SCRIPT
  return statements_contain_batch(detail::parse(source).statements);
#else
  (void)source;
  return false;
#endif
}
Result Engine::run(
    const std::string &source, Environment *environment, Limits limits,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::map<std::string, ctk::analysis::v1::ScriptValue> &initial_values,
    ExportSink export_sink, bool collect_final) {
  try {
    if (!limits.max_steps || limits.max_steps > 10000 ||
        !limits.max_source_bytes || !limits.max_retained_bytes ||
        !limits.max_response_bytes)
      throw Error(ctk::clang_layer::MatchCode::InvalidArgument,
                  "invalid script execution limits");
    if (source.size() > limits.max_source_bytes)
      throw Error(ctk::clang_layer::MatchCode::ResourceExhausted,
                  "script source byte limit exceeded");
    if (!checkpoint())
      throw Error(ctk::clang_layer::MatchCode::Cancelled, "script cancelled");
#ifdef CTK_BUILD_SCRIPT
    auto program = detail::parse(source);
    return {ctk::clang_layer::MatchCode::Ok,
            {},
            detail::Interpreter(environment, limits, checkpoint, initial_values,
                                std::move(export_sink), collect_final)
                .run(program)};
#else
    return {ctk::clang_layer::MatchCode::FailedPrecondition,
            "server scripting is disabled",
            {}};
#endif
  } catch (const Error &error) {
    return {error.code, error.what(), {}};
  } catch (const std::exception &error) {
    return {ctk::clang_layer::MatchCode::Internal, error.what(), {}};
  }
}
std::string Engine::eval(const std::string &source) {
  auto result = run(source);
  if (result.code != ctk::clang_layer::MatchCode::Ok)
    throw Error(result.code, result.message);
  std::string json;
  if (!google::protobuf::util::MessageToJsonString(result.response, &json).ok())
    throw Error(ctk::clang_layer::MatchCode::Internal,
                "script JSON serialization failed");
  return json;
}
} // namespace ctk::script
