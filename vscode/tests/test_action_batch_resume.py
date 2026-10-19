from __future__ import annotations

import gzip
import hashlib
import json
import struct
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'console'))

from action_batch_resume import ResumeError, restore_completed_batch


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checkpoint(tmp_path: Path) -> tuple[dict, dict, list[str], dict, Path, Path, Path, dict]:
    archive = tmp_path / 'archive'
    archive.mkdir()
    sources = [tmp_path / 'a.cpp', tmp_path / 'b.cpp', tmp_path / 'c.cpp']
    for index, source in enumerate(sources):
        source.write_text(f'int value_{index};\n')
    dependency = tmp_path / 'compile_commands.json'
    dependency.write_text('[]\n')

    members = [gzip.compress(f'group-{index}\n'.encode(), mtime=0) for index in range(3)]
    (archive / 'all-results.jsonl.gz').write_bytes(b''.join(members))
    offsets = []
    physical = 0
    for member in members:
        offsets.append(struct.pack('!QQ', physical, 0))
        physical += len(member)
    (archive / 'all-results.offsets').write_bytes(b''.join(offsets))
    statuses = []
    for index in range(3):
        result = archive / f'old-file-{index + 1}.jsonl.gz'
        result.write_bytes(gzip.compress(f'file-{index + 1}\n'.encode(), mtime=0))
        statuses.append({
            'file': str(sources[index]),
            'status': 'succeeded' if index < 2 else 'failed',
            'matches': 1,
            'totalMatches': 1,
            'resultBytes': 11 + index,
            'fullResultPath': str(result),
            'attempted': True,
            'message': None,
            'canonicalFile': None,
        })

    action = {'revision': 'rev-1', 'generated': 'let f = 1'}
    settings = {'compilationDatabase': str(dependency)}
    request = {
        'values': {'limit': 4},
        'profiles': {str(sources[0]): {'compilationDatabase': str(dependency)}},
    }
    report = {
        'resultFile': str(tmp_path / 'old-run' / 'all-results.jsonl.gz'),
        'totalMatches': 3,
        'fileStatuses': statuses,
    }
    manifest = {
        'version': 1,
        'files': [str(path) for path in sources],
        'settings': settings,
        'values': request['values'],
        'profiles': request['profiles'],
        'actionRevision': action['revision'],
        'actionGeneratedSha256': hashlib.sha256(action['generated'].encode()).hexdigest(),
        'sourceSha256': {str(path): _sha(path) for path in sources},
        'dependencySha256': {str(dependency): _sha(dependency)},
        'archive': str(archive),
        'report': report,
    }
    manifest_path = tmp_path / 'checkpoint.json'
    manifest_path.write_text(json.dumps(manifest))
    request['resumeManifest'] = str(manifest_path)
    destination = tmp_path / 'new-run'
    destination.mkdir()
    return (request, action, [str(path) for path in sources], settings,
            destination, destination / 'all-results.jsonl.gz',
            destination / 'all-results.offsets', manifest)


def _restore(context: tuple) -> object:
    request, action, files, settings, destination, results, offsets, _ = context
    return restore_completed_batch(
        request, action, files, settings, destination, results, offsets,
    )


def test_restores_only_contiguous_success_prefix_before_hole(tmp_path: Path) -> None:
    context = _checkpoint(tmp_path)
    request, action, files, settings, destination, result_file, offsets_file, _ = context
    restored = _restore(context)

    assert restored.matches == 2
    assert restored.result_bytes == 23
    assert [status['file'] for status in restored.statuses] == files[:2]
    assert all(status['attempted'] and status['resumed'] for status in restored.statuses)
    assert all('message' not in status and 'canonicalFile' not in status
               for status in restored.statuses)
    assert [Path(status['fullResultPath']).name for status in restored.statuses] == [
        'file-0001.jsonl.gz', 'file-0002.jsonl.gz',
    ]
    archive = Path(json.loads(Path(request['resumeManifest']).read_text())['archive'])
    members = [gzip.compress(f'group-{index}\n'.encode(), mtime=0) for index in range(3)]
    assert result_file.read_bytes() == b''.join(members[:2])
    assert gzip.decompress(result_file.read_bytes()) == b'group-0\ngroup-1\n'
    assert offsets_file.read_bytes() == (archive / 'all-results.offsets').read_bytes()[:32]
    assert gzip.decompress((destination / 'file-0001.jsonl.gz').read_bytes()) == b'file-1\n'


@pytest.mark.parametrize('changed', [
    'source', 'action', 'settings', 'values', 'profiles', 'dependency',
    'stale', 'sourceValidationError', 'sourceChangedFiles',
])
def test_rejects_checkpoint_when_any_input_or_validation_changed(
    tmp_path: Path, changed: str,
) -> None:
    context = list(_checkpoint(tmp_path))
    request, action, files, settings, _, _, _, manifest = context
    if changed == 'source':
        Path(files[0]).write_text('int changed;\n')
    elif changed == 'action':
        action['generated'] = 'let f = 2'
    elif changed == 'settings':
        settings['timeout'] = 12
    elif changed == 'values':
        request['values']['limit'] = 5
    elif changed == 'profiles':
        request['profiles']['another.cpp'] = {}
    elif changed == 'dependency':
        dependency = Path(next(iter(manifest['dependencySha256'])))
        dependency.write_text('[{"changed": true}]\n')
    elif changed == 'stale':
        manifest['report']['stale'] = True
        Path(request['resumeManifest']).write_text(json.dumps(manifest))
    elif changed == 'sourceValidationError':
        manifest['report']['sourceValidationError'] = 'source snapshot mismatch'
        Path(request['resumeManifest']).write_text(json.dumps(manifest))
    else:
        manifest['report']['sourceChangedFiles'] = [files[0]]
        Path(request['resumeManifest']).write_text(json.dumps(manifest))

    with pytest.raises(ResumeError):
        _restore(tuple(context))


def test_rejects_corrupt_offset_index(tmp_path: Path) -> None:
    context = _checkpoint(tmp_path)
    archive = Path(context[-1]['archive'])
    (archive / 'all-results.offsets').write_bytes(b'bad')
    with pytest.raises(ResumeError, match='offset index'):
        _restore(context)


def test_rejects_prefix_boundary_inside_gzip_member(tmp_path: Path) -> None:
    context = list(_checkpoint(tmp_path))
    manifest = context[-1]
    archive = Path(manifest['archive'])
    offsets_path = archive / 'all-results.offsets'
    original = offsets_path.read_bytes()
    offsets_path.write_bytes(original[:32] + struct.pack('!QQ', 2, 1))
    Path(context[0]['resumeManifest']).write_text(json.dumps(manifest))

    with pytest.raises(ResumeError, match='inside a gzip member'):
        _restore(tuple(context))


def test_complete_archive_restore_is_independent_of_checkpoint_on_append(tmp_path: Path) -> None:
    context = list(_checkpoint(tmp_path))
    request = context[0]
    manifest = context[-1]
    for status in manifest['report']['fileStatuses']:
        status['status'] = 'succeeded'
    Path(request['resumeManifest']).write_text(json.dumps(manifest))
    archive = Path(manifest['archive'])
    original_archive = (archive / 'all-results.jsonl.gz').read_bytes()
    original_offsets = (archive / 'all-results.offsets').read_bytes()

    restored = _restore(tuple(context))
    assert restored.matches == 3
    with context[5].open('ab') as output:
        output.write(gzip.compress(b'new-run-group\n', mtime=0))
    with context[6].open('ab') as output:
        output.write(struct.pack('!QQ', len(original_archive), 0))

    assert (archive / 'all-results.jsonl.gz').read_bytes() == original_archive
    assert (archive / 'all-results.offsets').read_bytes() == original_offsets


def test_no_resume_manifest_returns_empty_result(tmp_path: Path) -> None:
    assert restore_completed_batch(
        {}, {}, [], {}, tmp_path, tmp_path / 'results.gz', tmp_path / 'offsets',
    ).statuses == ()
