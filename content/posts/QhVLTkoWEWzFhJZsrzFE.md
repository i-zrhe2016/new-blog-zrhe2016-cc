---
{
  "uid": "QhVLTkoWEWzFhJZsrzFE",
  "title": "配置apt绕过代理",
  "slug": "apt",
  "alias": "posts/apt",
  "published_date": "2026-01-10T17:26:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "vim ~/.bashrc export http_proxy=\"socks5://192.168.5.34:10808\" export https_proxy=\"socks5://192.168.5.34:10808\" export all_proxy=\"socks5://192.168.5.34:10808\" so",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-01-10T17:26:00+00:00",
  "last_modified": "2026-11-18T07:44:30.159261+00:00"
}
---
```text
vim ~/.bashrc
export http_proxy="socks5://192.168.5.34:10808"
export https_proxy="socks5://192.168.5.34:10808"
export all_proxy="socks5://192.168.5.34:10808"
source ~/.bashrc
curl -I https://www.google.com

```

全局配置sock5代理但是apt不支持sock5，这里直接修改apt配置直接禁止使用代理

```text
cat >/etc/apt/apt.conf.d/99no-proxy <<'EOF'
Acquire::http::Proxy "false";
Acquire::https::Proxy "false";
EOF

```
