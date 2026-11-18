---
{
  "uid": "ZnKiwNLNZvocVCACfucA",
  "title": "install and run codex on headless ubuntu",
  "slug": "install-and-run-codex-on-headless-ubuntu",
  "alias": "posts/install-and-run-codex-on-headless-ubuntu",
  "published_date": "2026-01-10T18:33:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "install node.js curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash source ~/.bashrc nvm install --lts node -v npm -v install codex ",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-01-10T18:33:00+00:00",
  "last_modified": "2026-11-18T07:44:30.195715+00:00"
}
---
install node.js

```text
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install --lts
node -v
npm -v

```

### install codex

```text
npm i -g @openai/codex

```

### login codex

enable device code login on chatgpt account

open link and use code to login

```text
codex login --device-auth

```

### 方式2 配置端口转发

本地请求将回调地址转发到虚拟机或者vps

```text
ssh -i "/path/to/private_key" -L 1455:127.0.0.1:1455 root@192.168.147.130

```
