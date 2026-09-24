# 構築結果（2026-09-24）

## 作業場所

- 実際のプロジェクト: Ubuntu-24.04 `/home/toyoda/competitive-programming`
- Windows上の構築用控え: `C:\Users\toyod\Desktop\Claude\competitive-programming-setup`
- 起動ファイル: `C:\Users\toyod\Desktop\Claude\open-competitive-programming.cmd`

## 既存環境を利用

- WSL2 / Ubuntu 24.04
- Python 3.12.3
- GCC 13.3.0（GNU C++20でビルド）
- GDB 15.0.50
- VS Code 1.139.0

## 追加したもの

- VS CodeのWSL接続とCodex拡張
- WSL側のPython・Pylance・debugpy・C/C++・Codex拡張
- プロジェクト専用Python仮想環境
- online-judge-tools 11.5.1 / online-judge-api-client 10.10.1
- Python 3.12でojを動かすためのsetuptools 80.9.0
- AC Library（具体的な版はACL_REVISION）
- 両言語のテンプレート、自作DSU、サンプル、自動展開、VS Code Tasks・デバッガ設定
- Gitリポジトリの初期化（ユーザー名の変更・コミット・リモートへの送信はしていません）

## 検証

- ライブラリとツールの自動検証14件が成功（既存12件＋問題生成・コピー処理2件）。
- Python / C++ のサンプル実行・比較が成功。
- 自作Pythonモジュールを含む提出ファイルを隔離モードで実行し成功。
- 自作C++ヘッダとAC Libraryを含む提出ファイルを、追加includeパスなしでコンパイル・実行し成功。
- C++のDSUをAC Libraryと乱数で比較し、AddressSanitizer / UndefinedBehaviorSanitizer付き検証が成功。
- Pythonのデバッグ用入力ラッパー、GDBでの入力ファイル付き実行が成功。
- AtCoder Beginners Selection / ABC086Aのサンプル2件をojで取得できた。
- pipの依存整合性確認が成功。
- VS CodeのWSL接続をCLIの接続診断で確認。
- Windowsプロセス呼び出しとclip.exeの起動を確認。既存クリップボードは変更していません。

当初、WSLの標準Windows実行形式登録が欠けていたため、実行中の登録を復旧しました。
永続的なOS設定は変更していません。再発時の復旧手順はREADMEにあります。

## 本人による操作が必要なこと

- Codex拡張にサインイン画面が出た場合のサインイン。
- 提出サイトへのログインと、実際の提出・結果確認。
- CLIログイン／提出がサイトの認証で失敗する場合は、生成したコードをブラウザから提出。

実アカウントによるログイン・提出、GUIのブレークポイント操作は、この検証では行っていません。
