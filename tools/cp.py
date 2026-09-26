#!/usr/bin/env python3
"""Local contest workflow. Run with .venv/bin/python tools/cp.py --help."""
import argparse
import ast
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PYLIB = ROOT / "lib/python"
CPPLIB = ROOT / "lib/cpp"
ACL = ROOT / "third_party/ac-library"
PYTHON = ROOT / ".venv/bin/python"
OJ = ROOT / ".venv/bin/oj"


def call(args, **kwargs):
    print("+ " + shlex.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def source_path(value):
    path = Path(value).resolve()
    if not path.is_file() or path.suffix not in {".py", ".cpp"}:
        raise ValueError("main.py または main.cpp を指定してください")
    path.relative_to(ROOT)
    if path.is_relative_to(ROOT / "lib") or path.is_relative_to(ROOT / "tools"):
        raise ValueError("ライブラリやツールではなく、問題の解答ファイルを指定してください")
    return path


def problem_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("問題URLは https:// から始まるURLを指定してください")
    return value


def bundle_python(source, lib_root=PYLIB):
    emitted, visiting = set(), set()
    symbols = {}

    def expand(path, is_library=False):
        path = path.resolve()
        if path in visiting:
            raise ValueError(f"循環依存: {path}")
        if path in emitted:
            return ""
        visiting.add(path)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        replacements = []
        for node in ast.walk(tree):
            local_from = isinstance(node, ast.ImportFrom) and (
                node.module == "cp_lib" or (node.module or "").startswith("cp_lib."))
            local_import = isinstance(node, ast.Import) and any(
                n.name == "cp_lib" or n.name.startswith("cp_lib.") for n in node.names)
            if local_import or (isinstance(node, ast.ImportFrom) and node.level):
                raise ValueError("自作ライブラリは from cp_lib.module import Symbol で読み込んでください")
            if is_library and isinstance(node, ast.ImportFrom) and node.module == "__future__":
                raise ValueError("自作ライブラリ内の __future__ import は非対応です")
            if not local_from:
                continue
            if node not in tree.body or node.col_offset or any(n.asname or n.name == "*" for n in node.names):
                raise ValueError("cp_libはトップレベルで、別名・*を使わず読み込んでください")
            if node.module == "cp_lib":
                raise ValueError("cp_lib直下のモジュール名まで指定してください")
            module = lib_root.joinpath(*node.module.split(".")).with_suffix(".py").resolve()
            module.relative_to(lib_root.resolve())
            if not module.is_file():
                raise ValueError(f"ライブラリがありません: {module}")
            # A local import must occupy complete lines; reject semicolon surprises.
            lines = text.splitlines(keepends=True)
            tail = lines[node.end_lineno - 1].encode("utf-8")[node.end_col_offset:].decode("utf-8").strip()
            if tail and not tail.startswith("#"):
                raise ValueError("cp_libのimportは独立した行に記述してください")
            replacements.append((node.lineno - 1, node.end_lineno,
                                 f"# BEGIN {node.module}\n" + expand(module, True) + f"# END {node.module}\n"))
        if is_library:
            for node in tree.body:
                names = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names = [node.name]
                elif isinstance(node, ast.Assign):
                    names = [n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    names = [node.target.id]
                for name in names:
                    if name in symbols and symbols[name] != path:
                        raise ValueError(f"ライブラリの名前が衝突します: {name}")
                    symbols[name] = path
        lines = text.splitlines(keepends=True)
        for start, end, replacement in sorted(replacements, reverse=True):
            lines[start:end] = [replacement]
        visiting.remove(path)
        emitted.add(path)
        return "".join(lines).rstrip() + "\n\n"

    result = expand(source)
    compile(result, "submission.py", "exec")
    return result


def bundle_cpp(source, include_roots=(CPPLIB, ACL)):
    emitted, visiting = set(), set()
    include = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]\s*(?://.*)?$')

    def expand(path):
        path = path.resolve()
        if path in visiting:
            raise ValueError(f"循環include: {path}")
        if path in emitted:
            return ""
        visiting.add(path)
        result = [f"// BEGIN {path.name}\n"]
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            if re.match(r'^\s*#\s*pragma\s+once\s*$', line):
                continue
            match = include.match(line)
            if match and (match[1] == '"' or match[2].startswith(("cp/", "atcoder/"))):
                name = match[2]
                bases = (path.parent, *include_roots) if match[1] == '"' else include_roots
                dependency = next((base / name for base in bases if (base / name).is_file()), None)
                if dependency is None:
                    raise ValueError(f"ヘッダがありません: {name}")
                resolved = dependency.resolve()
                allowed = (source.parent.resolve(), *(root.resolve() for root in include_roots))
                if not any(resolved.is_relative_to(root) for root in allowed):
                    raise ValueError(f"許可されたライブラリ外のinclude: {name}")
                result.append(expand(resolved))
            else:
                result.append(line)
        visiting.remove(path)
        emitted.add(path)
        result.append(f"\n// END {path.name}\n")
        return "".join(result)

    return expand(source)


def command_for(source, standalone=False, debug=False):
    if source.suffix == ".py":
        return [str(PYTHON), "-I", str(source)] if standalone else [str(PYTHON), str(source)]
    tag = hashlib.sha256(str(source).encode()).hexdigest()[:12]
    output = ROOT / ".build" / (tag + ("-debug" if debug else ""))
    output.parent.mkdir(exist_ok=True)
    flags = ["-O0", "-g3", "-D_GLIBCXX_ASSERTIONS"] if debug else ["-O2"]
    includes = [] if standalone else ["-I", CPPLIB, "-I", ACL]
    call(["g++", "-std=c++20", "-Wall", "-Wextra", *flags, *includes, source, "-o", output])
    if debug:
        # Fixed filename for the active-file VS Code debugger.
        target = ROOT / ".build/debug-main"
        shutil.copy2(output, target)
        output = target
    return [str(output)]


def environment(standalone=False):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    if not standalone:
        env["PYTHONPATH"] = str(PYLIB)
    return env


def test_file(source, test_dir, timeout=2.0, standalone=False):
    test_dir = Path(test_dir).resolve()
    inputs = list(test_dir.glob("*.in"))
    if not inputs or any(not p.with_suffix(".out").is_file() for p in inputs):
        raise ValueError(f"テストには対応する *.in と *.out が必要です: {test_dir}")
    if not OJ.is_file():
        raise ValueError("oj未導入です。READMEのセットアップ手順を実行してください")
    command = command_for(source, standalone)
    # Empty cwd and Python isolated mode detect accidental local dependencies.
    with tempfile.TemporaryDirectory(prefix="cp-test-") as cwd:
        call([OJ, "test", "-c", shlex.join(command), "-d", test_dir, "-t", str(timeout)],
             cwd=cwd, env=environment(standalone))


def bundle(source):
    relative = source.relative_to(ROOT)
    if relative.parts[0] == "dist":
        raise ValueError("distではなく元のmain.py / main.cppを指定してください")
    target = ROOT / "dist" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    content = bundle_python(source) if source.suffix == ".py" else bundle_cpp(source)
    target.write_text(content, encoding="utf-8")
    print(f"提出ファイル: {target}", flush=True)
    return target


def read_url(source, explicit=None):
    if explicit:
        return problem_url(explicit)
    metadata = source.parent / "problem.json"
    if not metadata.is_file():
        raise ValueError("problem.jsonがありません。--urlで問題URLを指定してください")
    return problem_url(json.loads(metadata.read_text(encoding="utf-8"))["url"])


def new_problem(args):
    url = problem_url(args.url)
    parsed = urlsplit(url)
    parts = [p for p in parsed.path.split("/") if p]
    if parsed.hostname == "atcoder.jp" and len(parts) == 4 and parts[0] == "contests" and parts[2] == "tasks":
        name = f"atcoder/{parts[1]}/{parts[3]}/{args.lang}"
    else:
        name = "/".join((parsed.hostname, *parts[-2:], args.lang))
    relative = Path(args.name or name)
    target = (ROOT / "contests" / relative).resolve()
    target.relative_to((ROOT / "contests").resolve())
    create_problem(target, url, args.lang)
    if not args.no_download:
        download(target, url)


def create_problem(target, url, language):
    target.mkdir(parents=True, exist_ok=False)
    suffix = ".py" if language == "python" else ".cpp"
    shutil.copy2(ROOT / "templates" / ("main" + suffix), target / ("main" + suffix))
    (target / "problem.json").write_text(json.dumps({"url": url}, indent=2) + "\n", encoding="utf-8")
    (target / "test").mkdir()
    (target / "input.txt").touch()
    print(f"作成しました: {target}", flush=True)


def contest_tasks_url(value):
    parsed = urlsplit(problem_url(value))
    match = re.fullmatch(r"/contests/([A-Za-z0-9_-]+)/tasks/?", parsed.path)
    if parsed.netloc != "atcoder.jp" or not match:
        raise ValueError("AtCoderの問題一覧URLを指定してください: https://atcoder.jp/contests/arc100/tasks")
    return f"https://atcoder.jp/contests/{match[1]}/tasks"


def abc_tasks_url(value):
    parsed = urlsplit(problem_url(value))
    match = re.fullmatch(r"/contests/(abc[0-9]+)/tasks/?", parsed.path)
    if parsed.netloc != "atcoder.jp" or not match:
        raise ValueError("ABCの問題一覧URLを指定してください: https://atcoder.jp/contests/abc350/tasks")
    return f"https://atcoder.jp/contests/{match[1]}/tasks"


class TaskLinks(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.path = urlsplit(url).path + "/"
        self.urls = []
        self.seen = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        parsed = urlsplit(urljoin(self.url, href))
        if parsed.scheme != "https" or parsed.netloc != "atcoder.jp":
            return
        if not parsed.path.startswith(self.path):
            return
        task_id = parsed.path[len(self.path):]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
            return
        url = "https://atcoder.jp" + parsed.path
        if url not in self.seen:
            self.seen.add(url)
            self.urls.append(url)


def fetch_contest_tasks(url):
    request = Request(url, headers={"User-Agent": "cp-workflow/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
    except (URLError, OSError, UnicodeError) as error:
        raise ValueError(f"問題一覧を取得できませんでした: {url} ({error})") from error
    parser = TaskLinks(url)
    parser.feed(html)
    if not parser.urls:
        raise ValueError("問題一覧に問題リンクがありません。URL・問題の公開状況・ログインの必要性を確認してください")
    return parser.urls


def fetch_abc_tasks(url):
    # Compatibility for callers of the original ABC helper.
    return fetch_contest_tasks(url)


def new_abc(args):
    abc_tasks_url(args.url)
    new_contest(args)


def new_contest(args):
    url = contest_tasks_url(args.url)
    urls = fetch_contest_tasks(url)
    contest = urlsplit(url).path.split("/")[2]
    print(f"{contest}: {len(urls)}問 / Python・C++の両方を準備します", flush=True)
    pending = []
    created = skipped = 0
    # Prepare every template before attempting sample downloads.
    for task_url in urls:
        task_id = urlsplit(task_url).path.rsplit("/", 1)[1]
        targets = []
        for language in ("python", "cpp"):
            target = ROOT / "contests/atcoder" / contest / task_id / language
            target.resolve().relative_to((ROOT / "contests").resolve())
            if target.exists() or target.is_symlink():
                print(f"既存のためスキップ: {target}", flush=True)
                skipped += 1
                continue
            create_problem(target, task_url, language)
            targets.append(target)
            created += 1
        if targets:
            pending.append((task_url, targets))
    print(f"解答フォルダ: 新規 {created} / 既存 {skipped}", flush=True)
    if args.no_download:
        return
    failed = []
    for task_url, targets in pending:
        # Download once per problem and copy only into newly created folders.
        try:
            with tempfile.TemporaryDirectory(prefix="cp-samples-") as temp:
                directory = Path(temp)
                download(directory, task_url)
                for target in targets:
                    shutil.copytree(directory / "test", target / "test", dirs_exist_ok=True)
                    if (directory / "input.txt").is_file():
                        shutil.copy2(directory / "input.txt", target / "input.txt")
        except (subprocess.CalledProcessError, OSError) as error:
            print(f"サンプル取得・保存に失敗: {task_url} ({error})", file=sys.stderr)
            failed.append(task_url)
    if failed:
        raise ValueError(
            f"解答ファイルは作成済みです。{len(failed)}問のサンプル取得・保存に失敗しました。"
            "各言語のmain.py / main.cppでdownloadコマンドを実行するか、手動でtest/に保存してください。"
        )


def download(directory, url):
    try:
        call([OJ, "download", url, "-d", directory / "test"])
    except subprocess.CalledProcessError:
        print("取得に失敗しました。ブラウザからサンプルをtest/sample-1.inと.outに保存できます。", file=sys.stderr)
        raise
    samples = sorted((directory / "test").glob("*.in"))
    if samples and (not (directory / "input.txt").exists() or not (directory / "input.txt").stat().st_size):
        shutil.copy2(samples[0], directory / "input.txt")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    new = commands.add_parser("new", help="問題フォルダ・テンプレート・サンプルを作成")
    new.add_argument("url")
    new.add_argument("--lang", choices=["python", "cpp"], required=True)
    new.add_argument("--name", help="contests以下の保存先（既存フォルダは上書きしません）")
    new.add_argument("--no-download", action="store_true")
    contest = commands.add_parser("new-contest", help="AtCoderの全問題をPython・C++の両方で一括作成")
    contest.add_argument("url", help="https://atcoder.jp/contests/arc100/tasks 形式の問題一覧URL")
    contest.add_argument("--no-download", action="store_true", help="サンプルを取得せず解答用ファイルのみ作成")
    abc = commands.add_parser("new-abc", help="ABCの全問題をPython・C++の両方で一括作成")
    abc.add_argument("url", help="https://atcoder.jp/contests/abc350/tasks 形式の問題一覧URL")
    abc.add_argument("--no-download", action="store_true", help="サンプルを取得せず解答用ファイルのみ作成")
    for name in ("build", "run", "test", "bundle", "prepare", "download", "submit", "open", "copy"):
        cmd = commands.add_parser(name)
        cmd.add_argument("file")
        if name in {"test", "prepare", "submit", "copy"}:
            cmd.add_argument("--time-limit", type=float, default=2.0)
        if name == "build":
            cmd.add_argument("--debug", action="store_true")
        if name == "run":
            cmd.add_argument("--input", help="省略時は同じフォルダのinput.txtを使用")
        if name in {"download", "submit", "open"}:
            cmd.add_argument("--url")
        if name == "submit":
            cmd.add_argument("--language", required=True, help="提出先の現在の言語ID")
    commands.add_parser("doctor")
    commands.add_parser("login").add_argument("url", nargs="?", default="https://atcoder.jp/")
    args = parser.parse_args(argv)
    if args.action == "new":
        new_problem(args)
        return
    if args.action == "new-contest":
        new_contest(args)
        return
    if args.action == "new-abc":
        new_abc(args)
        return
    if args.action == "doctor":
        for label, path in {"Python": PYTHON, "oj": OJ, "AC Library": ACL / "atcoder/all"}.items():
            print(f"{label}: {'OK' if path.exists() else 'MISSING'} {path}")
            if not path.exists():
                raise ValueError(f"{label}が未導入です")
        call([PYTHON, "--version"])
        call(["g++", "--version"])
        call(["gdb", "--version"])
        call([OJ, "--version"])
        return
    if args.action == "login":
        call([OJ, "login", problem_url(args.url)])
        return
    source = source_path(args.file)
    if args.action == "build":
        command_for(source, debug=args.debug)
    elif args.action == "run":
        input_path = Path(args.input) if args.input else source.parent / "input.txt"
        with input_path.open("rb") as data:
            call(command_for(source), stdin=data, cwd=source.parent, env=environment())
    elif args.action == "test":
        test_file(source, source.parent / "test", args.time_limit)
    elif args.action in {"bundle", "prepare", "submit", "copy"}:
        # Resolve the submission target before doing work; never guess a language.
        url = read_url(source, args.url) if args.action == "submit" else None
        target = bundle(source)
        if args.action != "bundle":
            test_file(target, source.parent / "test", args.time_limit, standalone=True)
        if args.action == "copy":
            clip = shutil.which("clip.exe") or "/mnt/c/Windows/System32/clip.exe"
            call([clip], input=target.read_text(encoding="utf-8").encode("utf-16-le"))
            print("テスト済みの提出コードをWindowsのクリップボードへコピーしました")
        if args.action == "submit":
            print(f"提出先: {url}\n言語ID: {args.language}\nファイル: {target}", flush=True)
            call([OJ, "submit", "--language", args.language, url, target])
    elif args.action == "download":
        download(source.parent, read_url(source, args.url))
    elif args.action == "open":
        url = read_url(source, args.url)
        print(f"問題・提出ページ: {url}", flush=True)
        # Python webbrowser does not consistently use the Windows default browser under WSL.
        powershell = shutil.which("powershell.exe") or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        import base64
        script = "Start-Process '" + url.replace("'", "''") + "'"
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        call([powershell, "-NoProfile", "-EncodedCommand", encoded])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, SyntaxError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"コマンド失敗 (exit {error.returncode})", file=sys.stderr)
        sys.exit(error.returncode if error.returncode > 0 else 1)
