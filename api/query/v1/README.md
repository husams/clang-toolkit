# Query command contract

This contract implements the commands in the [Clang Toolkit Network Layer
Design](https://chatgpt.com/space/page_561b779557cc8191a5aace9bf6273191)
(revision 43). All messages use `ctk.query.v1`.

| Schema | Contents |
| --- | --- |
| `query.proto` | `QueryService` and public imports of the complete contract |
| `commands.proto` | File/compiler inputs, fixed-file request and incremental commands |
| `events.proto` | Stream events, semantic match summaries and control acknowledgements |
| `errors.proto` | Command rejection and admission-limit details |

| RPC | Input | Output | Use |
| --- | --- | --- | --- |
| `Query` | One `QueryRequest` | Stream of `QueryEvent` | Fixed files, foreground or background |
| `QuerySession` | Stream of `QueryCommand` | Stream of `QueryEvent` | Incremental inputs and explicit pause/resume |

Background execution schedules the same `Query` stream asynchronously on the
client. Both RPCs share the application's retained analysis session; completing
a query does not discard retained analysis resources.

## Incremental commands

| Command | Meaning |
| --- | --- |
| `StartQuery` | Define the nonempty query once, before other commands |
| `AddFiles` | Admit a complete file/compiler-profile batch atomically |
| `Match` | Start matching accepted files; subsequent accepted files join automatically |
| `Pause` | Pause at cooperative safe points; buffered/in-flight events can still arrive |
| `Resume` | Continue explicitly paused work |

Each `QueryCommand` contains exactly one payload. Its client-selected
`request_id` correlates resulting events and rejections; it is not an analysis
session identifier. The query cannot change within a call.

Client half-close is native gRPC EOF, not a sixth command. It ends input while
accepted work continues. It does not resume a paused call. Resume before closing
input, or use native gRPC cancellation. Cancellation and deadlines retain their
transport outcomes. The call finishes after accepted work ends and outgoing
writes drain.

## Events and errors

The event envelope carries `Queued`, `Started`, `Progress`, `MatchEvent`,
`Completed`, `Rejected` or `Control`. File/profile events may interleave.
Progress reports counts, and the accepted total can increase after `AddFiles`.
Control actions are `query-defined`, `files-accepted`, `matching`, `paused` and
`resumed`. Matches contain binding names mapped to semantic values.

Successful collection requires `Completed` **and** terminal gRPC `OK`, including
when there are zero matches. Non-OK termination makes collected events partial.

Admission rejection reports `LIMIT_REACHED` and every violated limit with
current, configured, requested and projected values. File limits count main
file/compiler-profile inputs; memory values are accounted bytes. The shared
`session.overhead_memory_bytes` allowance is distinct from retained session memory.
A rejected incremental batch preserves the stream and previously accepted work.
Queue exhaustion also reports resource exhaustion, without admission violations.
Initial admission failure terminates the RPC with `RESOURCE_EXHAUSTED`.

Other terminal errors map to gRPC `INVALID_ARGUMENT`, `NOT_FOUND`, `INTERNAL`,
`FAILED_PRECONDITION` or `CANCELLED` as appropriate. The current adapter carries
serialized `Rejected` directly in `grpc-status-details-bin`; clients must decode
it using this contract rather than as `google.rpc.Status`.

## Generation and compatibility

The module split preserves message names, field numbers/types, oneofs and RPC
paths/streaming directions from the original single-file contract. Public imports
preserve `query.pb.h` and Python `query_pb2` message access. File descriptors now
identify the owning command/event/error module; regenerate bindings together.

CMake generates and links all four C++ schemas plus the service stub. Run
`scripts/generate_query_python.sh` to refresh checked-in Python bindings; set
`CTK_PYTHON` to an existing interpreter when needed. Wire compatibility is checked
against the original descriptor fixture, and network tests exercise both RPCs.
