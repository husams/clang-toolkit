#include "ctk/script/engine.hpp"
#include "ctk/script/error.hpp"
#include <google/protobuf/util/json_util.h>
#ifdef CTK_BUILD_SCRIPT
#include "interpreter.hpp"
#endif
namespace ctk::script {
Result
Engine::run(const std::string &source, Environment *environment, Limits limits,
            const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
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
            detail::Interpreter(environment, limits, checkpoint).run(program)};
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
