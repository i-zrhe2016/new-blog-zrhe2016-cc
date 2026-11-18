---
{
  "uid": "IPITuNzSSUqVYeosFmNG",
  "title": "配置git连接github",
  "slug": "gitgithub",
  "alias": "posts/gitgithub",
  "published_date": "2026-02-26T04:51:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "chmod 600 ./key eval \"$(ssh-agent -s)\" ssh-add ~/.ssh/key ssh -T git@github.com git config --global user.name \"zrhe2016\" git config --global user.email \"zrhe201",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-02-26T04:51:00+00:00",
  "last_modified": "2026-11-18T07:44:30.183933+00:00"
}
---
```text
chmod 600 ./key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/key
ssh -T git@github.com

git config --global user.name "zrhe2016"
git config --global user.email "zrhe2016@gmail.com"

```
