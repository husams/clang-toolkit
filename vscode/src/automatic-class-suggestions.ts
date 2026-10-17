interface Draft<T> {
  key: string;
  value: T;
}

/** Coalesce typing and discard results after cursor, document or focus changes. */
export class AutomaticClassSuggestions<T> {
  private timer: ReturnType<typeof setTimeout> | undefined;
  private generation = 0;
  private disposed = false;

  constructor(
    private readonly current: () => Draft<T> | undefined,
    private readonly matches: (value: T) => Promise<boolean>,
    private readonly show: () => PromiseLike<unknown>,
    private readonly log: (error: unknown) => void,
  ) {}

  changed(): void {
    this.cancel();
    if (this.disposed) return;
    const generation = this.generation;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      const draft = this.current();
      if (!draft) return;
      void this.matches(draft.value)
        .then(async (matches) => {
          if (
            matches &&
            this.generation === generation &&
            this.current()?.key === draft.key
          )
            await this.show();
        })
        .catch(this.log);
    }, 160);
  }

  cancel(): void {
    this.generation++;
    clearTimeout(this.timer);
    this.timer = undefined;
  }

  dispose(): void {
    this.disposed = true;
    this.cancel();
  }
}
