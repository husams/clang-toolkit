#pragma once
#include "query/v1/query.pb.h"
#include <optional>

namespace ctk::net {
// QueryCallState synchronizes these transitions with transport detachment.
// This object owns the payload for precisely the duration of a gRPC write.
class StreamWritePump {
public:
  bool writing() const { return payload_.has_value(); }
  bool finishing() const { return finishing_; }
  const query::v1::QueryEvent *begin_write(query::v1::QueryEvent event) {
    payload_ = std::move(event);
    return &*payload_;
  }
  void write_completed() { payload_.reset(); }
  void begin_finish() { finishing_ = true; }

private:
  std::optional<query::v1::QueryEvent> payload_;
  bool finishing_{false};
};
} // namespace ctk::net
