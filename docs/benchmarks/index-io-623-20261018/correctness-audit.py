from __future__ import annotations
import collections, hashlib, json, sqlite3, sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python /tmp/ctk623-final-correctness-audit.py PRIOR_RUN NEW_RUN')
old, new = map(lambda x: Path(x).resolve(), sys.argv[1:])

def read_json(path):
    return json.loads(path.read_text())

def digest_rows(rows):
    raw = json.dumps(sorted(rows), separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def normalized_input_map(run):
    metadata = read_json(run / 'run.json')
    paths = read_json(run / 'input-manifest-before.json')
    result = {}
    for path, value in paths.items():
        p = Path(path).resolve()
        if p == Path(metadata['compile_commands']).resolve() or run == p or run in p.parents:
            continue
        result[str(p)] = value
    return result

def input_changes(a, b):
    left, right = normalized_input_map(a), normalized_input_map(b)
    all_paths = left.keys() | right.keys()
    return sorted(p for p in all_paths if left.get(p) != right.get(p))

def load_db(run):
    files = list((run / 'storage/symbol-index').glob('*/symbols.sqlite3'))
    assert len(files) == 1, (run, files)
    db = sqlite3.connect(files[0].as_uri() + '?mode=ro', uri=True, timeout=5)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    assert tables == ['metadata', 'symbol', 'translation_unit'], (run, tables)
    units = {}
    for row in db.execute('SELECT id,main_file,working_directory,arguments,command_hash,dependencies_json,indexed_at FROM translation_unit'):
        units[row[0]] = row
    symbols = collections.defaultdict(list)
    for row in db.execute('SELECT tu_id,usr,name,qualified_name,kind,file_path,byte_offset,line,column_no,is_definition,signature FROM symbol'):
        symbols[row[0]].append(tuple(row[1:]))
    return db, tables, units, symbols

def extractor_fingerprints(run):
    db, _, _, _ = load_db(run)
    values = set()
    for (raw,) in db.execute("SELECT arguments FROM translation_unit WHERE indexed_at>0"):
        context = json.loads(raw)
        values.add(context.get('extractor'))
    db.close()
    return sorted(value for value in values if value is not None)

def contributions(run, changed_paths):
    db, tables, units, symbols = load_db(run)
    indexed = [r for r in units.values() if r[6] > 0]
    main = {}
    group_hashes = {}
    for ident, rows in symbols.items():
        kept = [r for r in rows if r[4] not in changed_paths]
        group_hashes[ident] = digest_rows(kept)
    for row in indexed:
        ident, file, working_directory, arguments_json, command_hash, manifest, _ = row
        deps = json.loads(manifest)
        groups = sorted({group_hashes[g] for key, g in deps.items()
                         if key.startswith('@symbol-group:') and g in group_hashes})
        context = json.loads(arguments_json)
        # Extractor is an executable/build fingerprint, not part of the source
        # compile context; it changes between baseline and optimized binaries.
        # Preserve compiler, toolchain, every argument (including macro variants),
        # environment, main file, and working directory for one-to-one matching.
        context.pop('extractor', None)
        key = (file, working_directory,
               json.dumps(context, sort_keys=True, separators=(',', ':')))
        assert key not in main, ('duplicate normalized TU context', key)
        main[key] = (group_hashes.get(ident, digest_rows([])), groups)
    assert len(main) == len(indexed), (len(main), len(indexed))
    sql_counts = dict(
        main_tus=len(indexed),
        header_groups=sum(r[6] == 0 for r in units.values()),
        symbols=sum(map(len, symbols.values())),
        non_definitions=sum(not row[8] for rows in symbols.values() for row in rows),
        nonempty_signatures=sum(bool(row[9]) for rows in symbols.values() for row in rows),
        standard_header_paths=sum('/include/c++/' in row[4] or '/lib/clang/' in row[4] and '/include/' in row[4]
                                  for rows in symbols.values() for row in rows),
        anonymous_namespace_names=sum('(anonymous namespace)' in row[2] for rows in symbols.values() for row in rows),
    )
    db.close()
    return main, sql_counts

def verify_run(run):
    result, meta = read_json(run / 'result.json'), read_json(run / 'run.json')
    assert result.get('success') is True, result.get('error')
    status = result['final_status']
    assert status['state'] == 'INDEX_STATE_COMPLETE'
    assert int(status['translation_units_total']) == int(status['translation_units_completed']) == int(status['translation_units_indexed']) == 623
    assert int(status.get('translation_units_failed', 0)) == int(status.get('translation_units_skipped', 0)) == 0
    assert result.get('control_calls_before_completion') == 1
    assert len(result.get('control_calls', [])) == 1 and result['control_calls'][0]['method'] == 'StartProjectIndex'
    assert not result.get('poll_errors') and not result.get('failures') and not result.get('changed_inputs')
    assert result.get('shutdown_after_completion') is True
    assert result['metadata']['compile_commands_sha256'] == meta['compile_commands_sha256']
    assert result.get('binary_sha256_after') == meta.get('binary_sha256')
    before = read_json(run / 'input-manifest-before.json')
    assert len(before) == meta['input_hashes']
    samples = read_json(run / 'request-samples-final.json')
    active = [r for r in samples if r.get('phase') == 'indexing']
    assert active and all('error' not in r and r['ms'] < 2000 for r in active)
    lookup = [r for r in active if r['kind'] in ('exact','prefix','usr') and r.get('facts',{}).get('cross_tu')]
    out_line = [r for r in active if r['kind'] == 'out_of_line_definition' and r.get('facts',{}).get('available')]
    assert lookup and out_line
    return result, meta, active

old_result, old_meta, _ = verify_run(old)
new_result, new_meta, active = verify_run(new)
assert old_meta['compile_commands_sha256'] == new_meta['compile_commands_sha256'], '623-TU cohort differs'
old_extractors, new_extractors = extractor_fingerprints(old), extractor_fingerprints(new)
changed = input_changes(old, new)
old_rows, old_counts = contributions(old, set(changed))
new_rows, new_counts = contributions(new, set(changed))
assert old_counts['main_tus'] == new_counts['main_tus'] == 623
assert old_counts['non_definitions'] == new_counts['non_definitions'] == 0
assert old_counts['nonempty_signatures'] == new_counts['nonempty_signatures'] == 0
assert old_counts['standard_header_paths'] == new_counts['standard_header_paths'] == 0
assert old_counts['anonymous_namespace_names'] == new_counts['anonymous_namespace_names'] == 0
assert len(old_rows) == len(new_rows) == 623
assert old_rows.keys() == new_rows.keys(), (len(old_rows), len(new_rows))
diffs = [dict(main_file=k[0], working_directory=k[1], normalized_compile_context=k[2], before=old_rows[k], after=new_rows[k])
         for k in old_rows if old_rows[k] != new_rows[k]]
assert not diffs, diffs[:10]
resources = [json.loads(x) for x in (new / 'resources.jsonl').read_text().splitlines() if x.strip()]
inside = [x for x in resources if new_result['started_monotonic'] <= x['monotonic'] <= new_result['started_monotonic'] + new_result['completion_bracket_seconds'][0]]
worker_counts = [sum(p['name'] == 'ctk-index-worker' for p in x['processes']) for x in inside]
assert worker_counts and max(worker_counts) == 4, max(worker_counts, default=0)
server_pids = {p['pid'] for x in inside for p in x['processes'] if p['name'] == 'ctk-server'}
assert len(server_pids) == 1, server_pids
worker_nice = [p['nice'] for x in inside for p in x['processes'] if p['name'] == 'ctk-index-worker']
worker_nice_by_pid = collections.defaultdict(list)
for x in inside:
    for p in x['processes']:
        if p['name'] == 'ctk-index-worker':
            worker_nice_by_pid[p['pid']].append(p['nice'])
steady_worker_samples = [values[1:] for values in worker_nice_by_pid.values()
                        if len(values) > 1]
assert worker_nice and steady_worker_samples
assert all(all(value >= 15 for value in values) and any(value >= 15 for value in values)
           for values in steady_worker_samples), 'sampled worker did not reach nice>=15 after startup'
report = dict(verdict='PASS', previous_run=str(old), new_run=str(new),
              cohort_sha256=new_meta['compile_commands_sha256'],
              previous_seconds=old_result['elapsed_seconds'], new_seconds=new_result['elapsed_seconds'],
              unchanged_definition_provenance_comparison='all 623 main-TU contributions matched one-to-one by main file, working directory, compiler/toolchain, full argument list, and environment (excluding only the differing extractor build fingerprint); referenced header-group contributions match after filtering only input files whose pinned hashes differ between these runs',
              old_extractor_fingerprints=old_extractors, new_extractor_fingerprints=new_extractors,
              extractor_fingerprint_is_the_only_normalized_tu_key_field=True,
              changed_input_paths=changed, changed_input_path_count=len(changed),
              excluded_modified_definition_paths=changed,
              exclusion_reason='Only paths present in either run input manifest whose SHA-256 differs between the pinned runs are filtered from definition-row comparison; these source/generated-input changes are separately listed, all other per-TU and referenced header-group rows are compared with USR, qualified name, kind, file, offset, line, column, definition flag, and signature.',
              per_tu_contribution_count=len(old_rows), per_tu_mismatches=diffs,
              old_sqlite_counts=old_counts, new_sqlite_counts=new_counts,
              new_run_max_live_workers=max(worker_counts),
              new_run_worker_nice_min_observed=min(worker_nice),
              new_run_worker_nice_sampled_pid_count=len(worker_nice_by_pid),
              new_run_worker_nice_first_observation_zero_pids=sum(values[0] == 0 for values in worker_nice_by_pid.values()),
              new_run_worker_nice_zero_sample_count=sum(value == 0 for value in worker_nice),
              new_run_resource_audit_worker_nice_sample_counts=read_json(new / 'resource-audit.json').get('full_run', {}).get('worker_nice_sample_counts'),
              new_run_worker_nice_steady_state_min=min(value for values in steady_worker_samples for value in values),
              new_run_worker_nice_transitioned_to_background=sum(values[0] < 15 and any(value >= 15 for value in values[1:]) for values in worker_nice_by_pid.values()),
              worker_priority_audit='Every worker observed more than once was nice>=15 on all samples after its first observation; some launch-time samples captured nice=0 before reprioritization.',
              new_run_server_pids=sorted(server_pids),
              active_probe_count=len(active), two_second_probe_deadline_passed=True,
              unchanged_hashes=len(normalized_input_map(new))-len(changed),
              binary_hashes_pinned=new_result['binary_sha256_after'])
(new / 'final-correctness-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
