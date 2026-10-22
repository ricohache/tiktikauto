"""Atomic JSON checkpoints, content hashes and exclusive Windows/POSIX locks."""
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


class Checkpoints:
    def __init__(self, directory):
        self.path = Path(directory) / 'checkpoints.json'
        self.records = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}

    def run(self, name, inputs, action):
        fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        previous = self.records.get(name, {})
        if previous.get('fingerprint') == fingerprint and all(Path(p).is_file() and digest(p) == h for p, h in previous.get('files', {}).items()):
            if previous.get('files'):
                print(f'RESUMED {name}', flush=True)
                return previous['result']
        result, files = action()
        if not files or any(not Path(p).is_file() or not Path(p).stat().st_size for p in files):
            raise RuntimeError(f'{name}: no validated artifacts')
        self.records[name] = {'fingerprint': fingerprint, 'files': {str(p): digest(p) for p in files}, 'result': result}
        save_json(self.path, self.records)
        return result


@contextmanager
def exclusive_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0)
        if stream.read(1) == b'':
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError('Another pilot is running') from exc
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
