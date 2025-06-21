# Dev scripts

flexcc のスクリプト実行では、ユーザーが独自に実装したスクリプトを呼び出すことも可能です。

コンソールのメニューから `Create new script` のテキストボックスにスクリプト名を設定し、`🥪Create!` ボタンをクリックします。

![alt text](image-14.png)

![alt text](image-16.png)

スクリプトが生成されると `Create new script` 下部の `Script finder` に生成されたスクリプトのパスが表示されます。

![alt text](image-17.png)

表示されたパスには以下のファイルがあります。必要に応じて編集してください。

- `attributes.yaml`: スクリプト名や制作者名、バージョン等の属性が記録されています。
- `main.py`: スクリプトの本体です。

![alt text](image-18.png)

以下ではコードエディタ [Visual Studio Code (VSCode)](https://code.visualstudio.com/){target=_blank} での開発手順について説明します。