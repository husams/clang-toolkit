#pragma once

#include <atomic>
#include <memory>

namespace ctk::compat {

class StopToken {
public:
  bool stop_requested() const noexcept { return stopped_ && stopped_->load(); }

  bool stop_possible() const noexcept { return static_cast<bool>(stopped_); }

private:
  friend class StopSource;
  std::shared_ptr<std::atomic<bool>> stopped_;
};

class StopSource {
public:
  StopToken get_token() const noexcept {
    StopToken token;
    token.stopped_ = stopped_;
    return token;
  }

  void request_stop() const noexcept { stopped_->store(true); }

private:
  std::shared_ptr<std::atomic<bool>> stopped_ = std::make_shared<std::atomic<bool>>(false);
};

} // namespace ctk::compat
