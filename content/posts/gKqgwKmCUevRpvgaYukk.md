---
{
  "uid": "gKqgwKmCUevRpvgaYukk",
  "title": "golang获取当前时间",
  "slug": "golang",
  "alias": "posts/golang",
  "published_date": "2026-01-18T06:46:00+00:00",
  "all_tags": "[]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "获取当前时间并按指定格式显示 package main import ( \"fmt\" \"time\" ) func main() { fmt.Println(time.Now().Format(\"200601021504\")) fmt.Println(\"执行完毕，请按回车键退出...\") var input string",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-01-18T06:46:00+00:00",
  "last_modified": "2026-11-18T07:44:30.189462+00:00"
}
---
获取当前时间并按指定格式显示

```text
package main

import (
	"fmt"
	"time"
)

func main() {
	fmt.Println(time.Now().Format("200601021504"))

	fmt.Println("执行完毕，请按回车键退出...")
	var input string
	fmt.Scanln(&input) // 等待用户输入
}

```
