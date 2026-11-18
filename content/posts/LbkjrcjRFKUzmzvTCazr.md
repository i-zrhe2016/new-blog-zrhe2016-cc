---
{
  "uid": "LbkjrcjRFKUzmzvTCazr",
  "title": "Kubernetes 故障案例：一个 Pod 正常，另一个 CrashLoopBackOff",
  "slug": "kubernetes-crashloopbackoff-java-version-mismatch",
  "alias": "posts/kubernetes-crashloopbackoff-java-version-mismatch",
  "published_date": "2026-10-28T00:00:00+00:00",
  "all_tags": "[\"Kubernetes\", \"Java\", \"故障排查\"]",
  "publish": true,
  "discoverable": false,
  "is_page": false,
  "canonical_url": "",
  "meta_description": "从 UnsupportedClassVersionError 日志定位 Java 21 字节码与 Java 17 容器运行环境不兼容的问题，整理 Kubernetes Pod 重启排查流程与修复方案。",
  "meta_image": "",
  "lang": "",
  "class_name": "",
  "first_published_at": "2026-10-28T00:00:00+00:00",
  "last_modified": "2026-11-18T07:44:30.212213+00:00"
}
---
故障原因：Java 编译版本与容器运行版本不兼容。

- 应用编译版本：Java 21
- 容器运行版本：Java 17
- 故障结果：JVM 启动失败，容器反复重启
- 旧 Pod 正常：可能仍在运行旧版本镜像

## 1. 故障现象

```text
Deployment
├── Pod A   Running
└── Pod B   CrashLoopBackOff
```

新 Pod 的关键错误：

```text
UnsupportedClassVersionError

class file version 65.0
runtime supports up to 61.0
```

## 2. 故障架构图

![PlantUML diagram](/static/migrated/diagrams/plantuml/c6eae322-09bb1200-ff3b0de3-46eb5a6b-f4a58652-d233749a-dbde4126-a2d90d18.svg)
## 3. 根本原因

![PlantUML diagram](/static/migrated/diagrams/plantuml/1638bc98-30406df6-4914e5ef-d6cd3512-d5e08ce3-9c4d7b6f-bfc9b75b-ab0e2b63.svg)
Java 字节码版本对应关系：

| Java 版本 | Class File Version |
| ------- | ------------------ |
| Java 17 | 61                 |
| Java 21 | 65                 |

Java 17 无法直接运行 Java 21 编译的字节码。

## 4. 为什么旧 Pod 正常？

![PlantUML diagram](/static/migrated/diagrams/plantuml/a0bf5de4-c0961c87-a4f96da0-13fde067-85d9c8f2-279db02d-b4b429d2-8cd3c29a.svg)
注意：旧 Pod 继续正常运行，可能是滚动更新保留了旧实例。该解释尚未通过 Deployment 配置、ReplicaSet 归属和镜像信息确认。

## 5. 排查流程

![PlantUML diagram](/static/migrated/diagrams/plantuml/11dd927a-abcf099a-dae78efd-72fff75d-1ffc11d9-4b9cab52-c633d1f0-8ec56c00.svg)
## 6. 常用排查命令

```bash
# 查看 Pod 状态
kubectl get pods -o wide

# 查看上次崩溃日志
kubectl logs <pod-name> --previous

# 查看 Pod 事件
kubectl describe pod <pod-name>

# 查看 ReplicaSet
kubectl get rs

# 查看 Deployment 更新状态
kubectl rollout status deployment/<name>

# 比较实际镜像
kubectl get pods -o custom-columns=\
NAME:.metadata.name,\
IMAGE:.spec.containers[*].image,\
IMAGE_ID:.status.containerStatuses[*].imageID
```

## 7. 修复方案

![PlantUML diagram](/static/migrated/diagrams/plantuml/707771e3-e1c8a7a8-5d6f3833-a789dec4-bcd4cb47-b24a6db3-973fa698-2bfc9045.svg)
## 8. 最终总结

| 维度 | 结论 |
| -------- | ---------------------- |
| 故障表现 | 新 Pod CrashLoopBackOff |
| 直接原因 | JVM 无法加载较新版本的字节码 |
| 可能的变更问题 | 镜像 JRE 或应用编译目标不一致 |
| 旧 Pod 正常 | 可能是滚动更新保留旧实例 |
| 解决方向 | 统一 Java 编译与运行版本 |
| 核心经验 | 优先检查崩溃日志，而不是盲目重启 Pod |

一句话总结：CrashLoopBackOff 是结果，Java 版本不兼容才是本案例日志明确揭示的故障原因。
