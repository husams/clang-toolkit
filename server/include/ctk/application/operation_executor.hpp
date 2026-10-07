#pragma once
#include <cstddef>
#include <functional>
#include <memory>

namespace ctk::application {
class OperationExecutor {
public:
  virtual ~OperationExecutor() = default;
  virtual bool enqueue(std::function<void()> task) = 0;
  virtual void stop_admission() = 0;
};
std::shared_ptr<OperationExecutor> make_operation_executor(std::size_t workers,
                                                           std::size_t pending);
} // namespace ctk::application
