# 競技プログラミング環境

作業場所は **Ubuntu-24.04 内の `/home/toyoda/competitive-programming`** です。
Windows側の `competitive-programming-setup` は構築用の控えです。
普段の編集は必ずWSL側のプロジェクトで行ってください。

## 開く

PowerShellで次を実行します。

```powershell
code --remote wsl+Ubuntu-24.04 /home/toyoda/competitive-programming
```

左下が `WSL: Ubuntu-24.04` になっていることを確認します。
フォルダの信頼を尋ねられた場合は、自分のこのプロジェクトを信頼して開きます。
Codexはサイドバー、または `Ctrl+Shift+P` → `Codex: Open Codex Sidebar` で開きます。
初回にサインイン画面が出たら、本人のアカウントでサインインしてください。

## まず動かす

1. `examples/python/main.py` を開き、`Ctrl+Shift+B` → サンプルテスト。
2. `examples/cpp/main.cpp` も同様にテスト。
3. `Ctrl+Shift+P` → `Tasks: Run Task` → `CP: Prepare submission (bundle + test)`。
4. `dist/examples/.../main.py` または `main.cpp` に提出用コードができます。

例題はUnion-Findの接続判定です。クエリ `0 a b` は結合、`1 a b` は同じ集合かを0/1で出力します。
C++例題は自作DSUとAC Libraryの両方を利用して比較します。
この例題には提出先URLを設定していません。動作確認用コードを誤って送信しないためです。

## 問題を解く

`Tasks: Run Task` → `CP: New problem` で問題URLと言語を選びます。
AtCoderでは `contests/atcoder/コンテストID/問題ID/python` または `cpp` が作られます。
両言語を別フォルダで管理できます。既存フォルダは上書きしません。

VS Codeのターミナルから使う場合（以降はUbuntuのbash）：

```bash
cd ~/competitive-programming
source .venv/bin/activate
python tools/cp.py new https://atcoder.jp/contests/abs/tasks/abc086_a --lang python
python tools/cp.py new https://atcoder.jp/contests/abs/tasks/abc086_a --lang cpp
```

作成された `main.py` または `main.cpp` を編集します。
新規テンプレートは解答未実装なので、そのままではサンプルに合格しません。
入力は標準入力、答えは標準出力に書きます。

| 操作 | VS Codeタスク |
|---|---|
| サンプル比較 | `CP: Test active file`（Ctrl+Shift+B） |
| input.txtを使って実行 | `CP: Run with input.txt` |
| ライブラリ展開＋生成物の再テスト | `CP: Prepare submission (bundle + test)` |
| テスト済み提出コードをコピー | `CP: Copy tested submission` |
| 対象の問題ページをブラウザで開く | `CP: Open problem page` |
| サンプルの追加取得 | `CP: Download samples` |
| CLI提出 | `CP: Submit via oj (login required)` |
| 環境診断 | `CP: Check environment` |
| 自作ライブラリ・ツールの検証 | `CP: Test libraries and tools` |

タスク実行時は、対象問題の **main.py / main.cppをアクティブにしてください**。
提出用の`dist`ファイルを直接編集せず、元の解答を修正して再生成します。

## サンプル取得に失敗した場合

AtCoder等の認証・アクセス制御により、ojによる取得が失敗する場合があります。
新規フォルダは残るので、ブラウザでサンプルをコピーし、次の組で保存してください。

```text
test/sample-1.in
test/sample-1.out
test/sample-2.in
test/sample-2.out
```

`input.txt` は単体実行・デバッグ用で、正誤判定には `test/` を使います。
自分で考えたケースも `test/custom-1.in` と `.out` の組で追加できます。
対話問題や複数の正答がある問題には、この単純な出力比較をそのまま適用できません。
通常タスクの制限時間は1ケース2秒です。変更するには例えば：

```bash
python tools/cp.py test contests/atcoder/abs/abc086_a/python/main.py --time-limit 5
```

浮動小数点誤差を許容する問題は、`oj test --help` の `--error` オプションを使うなど、問題に合った判定方法に切り替えてください。

## 提出

### ブラウザで提出する（認証に左右されにくい方法）

1. `CP: Copy tested submission` を実行します。自動展開・単独テストに合格するとWindowsのクリップボードにコピーします。
2. `CP: Open problem page` で対象問題を開き、その問題の提出画面に進みます。
3. 言語を選び、コードを貼り付けて提出します。
4. 提出結果を確認します。サンプル成功だけではACは保証されません。

コピー機能が使えない場合も、`dist/` の生成ファイルを開いてコピーできます。
`Exec format error` が表示される場合は、WSLのWindows連携登録が欠けている可能性があります。
このPCの構築時にも発生し、標準の登録を復旧しました。再発時はPowerShellで次を実行すると、
OSの永続設定を変更せず、実行中のWSL連携登録だけを復旧できます。

```powershell
wsl -d Ubuntu-24.04 -u root -- bash /home/toyoda/competitive-programming/tools/restore-wsl-interop.sh
```

Pythonはローカルが **CPython 3.12**、C++は **GCC 13 / GNU C++20** です。
提出先の言語バージョン・ライブラリ一覧を確認して選んでください。
PyPy向けの速度・挙動はこのCPythonでのテストだけでは保証できません。

### ターミナルから提出する

```bash
source .venv/bin/activate
python tools/cp.py login https://atcoder.jp/
python tools/cp.py submit path/to/main.py --language <現在の提出先の言語ID>
```

`<現在の提出先の言語ID>` はプレースホルダーなので実際のIDへ置き換えます。
言語IDは固定せず、提出サイトの現在の選択肢で確認してください。
問題URLは問題フォルダ内の `problem.json` から読みます。`--url https://...` で明示もできます。
生成物のテストが失敗すると送信しません。最後にojの確認プロンプトが表示されます。
AtCoderのCAPTCHA等でCLIログイン・提出が失敗する場合は、ブラウザで提出してください。
ログイン・本物のアカウントからの提出は環境検証では実行していません。
パスワードやCookieをコード・Git・Codexのチャットに貼り付けないでください。

## ライブラリ

Python標準ライブラリ（collections, heapq, bisect, itertools等）はそのまま使用できます。
ローカルでpipインストールした外部パッケージは、提出先でも利用可能とは限りません。
この環境ではPythonの自作ライブラリ以外の外部パッケージを提出コードへ自動同梱しません。

Pythonの自作コードは `lib/python/cp_lib/*.py` に置きます。

```python
from cp_lib.dsu import DSU

uf = DSU(n)
uf.merge(a, b)
print(uf.same(a, b))
```

自動結合は、トップレベルの `from cp_lib.module import Symbol` を対象にします。
別名import、`*`、相対import、関数内での自作import、自作ライブラリ内のfuture importは非対応です。
単独行にimportを書き、ライブラリは関数・クラス中心で、読み込み時に入出力しない設計にしてください。
展開後は同じ名前空間になるため、解答側も含めてグローバル名が衝突しないようにします。
必要なモジュールを再帰展開し、同じモジュールは一度だけ埋め込みます。

C++の自作コードは `lib/cpp/cp/*.hpp` に置きます。

```cpp
#include "cp/dsu.hpp"
#include <atcoder/segtree>
```

`cp`名前空間と`#pragma once`を使ってください。
自作ヘッダとAC Libraryを提出ファイルへ展開します。標準ヘッダはそのまま残します。
自作includeはファイルの先頭で無条件に行い、マクロ生成includeや条件ごとの再includeは使わないでください。
AC Libraryのライセンスは `third_party/ac-library/LICENSE` にあります。
更新時は`ACL_REVISION`を更新し、ライブラリテストを再実行します。

提出準備では、Pythonを `-I`（隔離モード）で、C++を自作ヘッダの検索パスなしで実行・コンパイルします。
実行場所も一時ディレクトリにして、プロジェクト内のファイルへの依存を検出します。
仮想環境の外部パッケージは引き続き利用できるため、その提出先での利用可否は別途確認してください。

## デバッグ

対象の `main.py` / `main.cpp` を開き、同じフォルダの `input.txt` に入力を書きます。
ブレークポイントを置き、実行とデバッグから言語に合った `CP: ...` 構成を選んでF5を押します。
Pythonはdebugpy、C++はGDBを使います。C++は `-O0 -g3 -D_GLIBCXX_ASSERTIONS` でビルドします。

## 再セットアップ・履歴管理

Ubuntuに `python3`, `python3-venv`, `g++`, `gdb`, `git` が必要です。
このPCでは既存のUbuntu環境を活用しています。

```bash
bash tools/setup.sh
source .venv/bin/activate
python -m unittest discover -s tests -v
```

`requirements.lock`に実際のPython依存版、`ACL_REVISION`にAC Libraryのコミットを記録しています。
Gitリポジトリを初期化済みです。解答やライブラリの履歴は必要に応じてコミットしてください。
`.venv`, `.build`, `dist`, ダウンロードしたAC Library本体はGit対象外です。

## Codexの利用

`AGENTS.md`に環境の構成と作業ルールを記載しています。
練習時は「このライブラリに境界値のテストを追加して」などと依頼できます。
本番は大会の生成AIルールに従ってください。AtCoderの開催中のABC/ARC/AGCではAI利用が原則禁止です。
AIを使わない本番用のVS Codeプロファイルを作り、CodexやAI補完を無効にしても、この環境のタスクは動きます。

公式資料：
- https://code.visualstudio.com/docs/remote/wsl
- https://learn.chatgpt.com/docs/codex/ide
- https://github.com/online-judge-tools/oj
- https://atcoder.github.io/ac-library/master/document_ja/index.html
- https://info.atcoder.jp/entry/llm-rules-ja
