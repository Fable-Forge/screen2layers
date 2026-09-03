# Update screen2layers

## 给使用者

```text
更新 screen2layers：https://raw.githubusercontent.com/Fable-Forge/screen2layers/main/docs/update.md
```

## 给执行更新的 Agent

1. 定位已安装目录并确认目标确实是 `screen2layers`。
2. 获取 `https://github.com/Fable-Forge/screen2layers` 的最新版本。
3. 在覆盖前比较本地 payload；若用户修改过，停止并展示差异。
4. 重新运行安装命令或按 `docs/install.md` 手动同步 payload。
5. 重新做结构校验、逐文件哈希和新会话触发测试。

推荐命令：

```bash
npx skills add Fable-Forge/screen2layers
```

不要用“命令成功”替代安装内容和实际触发验证。
