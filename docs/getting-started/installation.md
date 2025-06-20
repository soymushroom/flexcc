# Installation

flexcc は Windows 専用アプリケーションです。また、アプリケーションの動作には `Python >= 3.13` および `uv` モジュールが必要です。

- [Python](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv/tree/main)

Python および uv のセットアップが完了したら、github のメニューから `Download ZIP` を選択してダウンロードしたファイルを展開するか、CLI上で以下のコマンドを実行します。

```bash
git clone https://github.com/soymushroom/flexcc.git
```

アプリケーションディレクトリが展開されたら、CLI上でそのディレクトリに移動します。CLIからリポジトリをクローンした場合は、以下のコマンドで移動します。

```bash
cd flexcc
```

アプリケーションディレクトリに移動したのち、以下のコマンドで動作環境を設定します。

```bash
uv sync
```

環境設定が完了するのを待ち、以下のコマンドで flexcc を起動します。

```bash
uv run app.py
```