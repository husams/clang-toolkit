export class ConfigurationError extends Error {
  constructor(
    readonly source: string,
    readonly key: string,
    message: string,
    cause?: unknown,
  ) {
    super(
      `${source}${key ? `: ${key}` : ""}: ${message}`,
      cause === undefined ? undefined : { cause },
    );
    this.name = "ConfigurationError";
  }
}
