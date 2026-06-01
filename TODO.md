# TODO

Known issues and deferred improvements for future releases.

---

## Deferred from 0.2.0 Audit

### Security / Privacy

- **Key-name-only redaction misses sensitive values in innocuous keys** (Medium)
  - `environment.py` / `redaction.py`: The redaction regex only matches variable *names* (e.g., `PASSWORD`, `API_KEY`). An env var like `MY_APP_CONFIG={"db_password":"secret"}` or `JAVA_OPTS=-Dpassword=x` will not be redacted.
  - Recommendation: Consider value-scanning heuristics (detect URLs with embedded credentials, detect base64 tokens of certain lengths), or document the limitation prominently for users.

### Correctness

- **EventStream migration path: `event_stream.directory` is a no-op** (Low)
  - `tracker.py:273`: `_merge_and_migrate()` sets `self.event_stream.directory = new_dir`, but `EventStream` has no `directory` attribute. Events continue writing to the old path after directory migration. This is a rare path (mid-run `output_dir` change).
  - Recommendation: Close the old event stream and reopen at the new path, or update `stream_path` and reopen the file handle.

- **`script_name` not sanitized for filesystem-invalid characters** (Low-Medium)
  - `tracker.py:57`: `Path(sys.argv[0]).stem` could theoretically contain characters invalid on Windows (e.g., `<>:"|?*`). On Unix this is a non-issue. The ghost-mode fallback handles `mkdir` failure gracefully, so this won't crash.
  - Recommendation: Sanitize by replacing non-alphanumeric/dash/underscore/dot characters with `_`.

### Reliability

- **ResourceWatcher peak values written without lock** (Low-Medium)
  - `resources.py:109-130`: `peak_rss_bytes`, `peak_cpu_percent`, and `_consecutive_failures` are read/written from both the daemon thread and the `stop()` caller. On CPython with the GIL, this is safe. On free-threaded Python (PEP 703, 3.13+), this could race.
  - Recommendation: Add a `threading.Lock` around peak-value updates, or accept that `join()` (now added) makes this moot for the normal flow.

- **File handle leak in `_merge_and_migrate` on exception** (Low)
  - `tracker.py:281`: If `open(...)` succeeds but a later exception occurs, the new file handle is not closed in the except path.
  - Recommendation: Use a local variable and only assign to `self.console_interceptor.file` after success.

### Performance

- **TOCTOU on `_max_records` check in SubprocessSpy** (Low / Benign)
  - `subprocesses.py:99,157`: The length check is outside the lock. In concurrent scenarios, `_max_records` can be exceeded by at most `N_threads - 1` extra records. This is a soft safety cap, not a security boundary.
  - Recommendation: Accept as benign or move the check inside the lock (minor perf cost).
