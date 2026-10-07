#include "query_executor.hpp"

namespace ctk::application {
std::shared_ptr<OperationExecutor>
make_operation_executor(std::size_t workers, std::size_t pending) {
  return std::make_shared<detail::QueryExecutor>(workers, pending);
}
} // namespace ctk::application
