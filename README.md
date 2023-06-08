# ichigo_web

イチゴ推定結果発報用Webアプリ（Vue3）


## 準備

### node.jsセットアップ（※Linuxの場合）

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP1:</span> nvmをインストールする
```sh
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
```

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP2:</span> node.jsをインストールする
```sh
nvm install v14.21.3
```

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP3:</span> 実行に必要なパッケージをインストールする
```sh
npm install
```

### 実行方法（※デバッグ時のみ）

以下コマンドを打つことで、ウェブサーバが起動する。
```sh
npm run dev
```
ブラウザを開き、以下URLを打ち込む。
http://localhost:8001/

### デプロイ方法
<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP1:</span> ビルドする

```sh
npm run build
```
※ビルド成功した場合, ichigo_webフォルダ直下にdistフォルダが生成される。

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP2:</span> nginxをインストールする
```sh
sudo apt-get install nginx
```

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP3:</span> アプリ一式をnginxの所定のフォルダへコピーする
```sh
sudo cp -r dist  /var/www/dist_ichigo_web
```

<span style="background:black; color:white; border-radius: 3px; padding: 5px;">STEP4:</span> /etc/nginx/nginx.confを以下のように編集する。
（※内容は適宜読み替えて設定のこと）
```nginx
worker_processes  2;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;

    server {
        listen       8083;
        server_name  localhost;

	root /var/www/dist_ichigo_web;

        location /ichigo_api/socket.io {
            proxy_pass http://127.0.0.1:9987/ichigo_api/socket.io;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
}
```

最後のブラウザを開き、以下URLを入力すると、ウェブアプリが表示される。
http://localhost:8083/


