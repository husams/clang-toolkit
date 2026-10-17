import { runAnalysis } from "./engine.js";
import { requestSchema } from "./model.js";

const chunks: Buffer[] = [];
for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
const send = (value: unknown): void => {
  process.stdout.write(`${JSON.stringify(value)}\n`);
};
try {
  const request = requestSchema.parse(
    JSON.parse(Buffer.concat(chunks).toString("utf8")),
  );
  const report = await runAnalysis(request, (file, index) =>
    send({ type: "progress", file, index }),
  );
  send({ type: "complete", report });
} catch (error) {
  send({
    type: "error",
    message: error instanceof Error ? error.message : String(error),
  });
  process.exitCode = 1;
}
