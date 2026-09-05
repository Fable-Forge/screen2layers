[简体中文](README.md) | [English](README.en.md)

<div align="center">

# ⚒️ Screen2Layers

**把扁平 UI 截图重建为可移动切片、布局 SVG 与 Figma 友好的分层包。**

> Reconstruct flat UI screenshots into movable slices and Figma-ready layered kits.

<p>
  <a href="https://github.com/Fable-Forge/screen2layers/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0969da"></a>
  <img alt="Maturity: beta" src="https://img.shields.io/badge/maturity-beta-8250df">
  <img alt="Agents: Codex and Claude Code" src="https://img.shields.io/badge/agents-Codex_%C2%B7_Claude_Code-1f883d">
</p>

</div>

**[适用场景](#use-cases) · [快速安装](#quick-install) · [兼容性](#compatibility) · [验证边界](#validation) · [联系](#contact)**

---

<a id="use-cases"></a>
## 适合什么时候用

当你的请求与上面的目标一致时，让 Agent 加载本仓库的 `SKILL.md`。触发条件、边界和完整工作流以 `SKILL.md` 为准。

<a id="quick-install"></a>
## 快速安装

把下面这句话交给支持命令行的 Agent：

```text
帮我安装 screen2layers：https://raw.githubusercontent.com/Fable-Forge/screen2layers/main/docs/install.md
```

也可以使用 Agent Skills CLI：

```bash
npx skills add Fable-Forge/screen2layers
```

安装前请阅读 [安装说明](docs/install.md)。更新和卸载分别见 [更新说明](docs/update.md) 与 [卸载说明](docs/uninstall.md)。

<a id="compatibility"></a>
## 兼容性

- 支持：Codex · Claude Code · Agent Skills
- 成熟度：`beta`
- GitHub Topics：`figma`, `ui`, `image-processing`, `layers`, `game-ui`

兼容性表示仓库格式和安装路径已覆盖这些 Agent，不代表所有正在运行的会话都会热加载。安装后应在新会话中做自然语言触发测试。

## 仓库结构

- `SKILL.md`：触发条件、边界与主工作流
- `agents/openai.yaml`：Codex 展示元数据
- `references/`：按需加载的详细资料（如有）
- `scripts/`：可复用工具与仓库验证器（如有）
- `docs/`：安装、更新与卸载说明

<a id="validation"></a>
## 验证边界

结构校验、安装可见、真实触发和最终产出质量是四件不同的事。CI 通过只能证明仓库结构和静态规则通过；真实 Agent 触发仍需单独验收。

<a id="contact"></a>
## 联系与合作

- 📚 全部 Skill：[FableForge Agent Skills](https://github.com/Fable-Forge/fableforge-agent-skills)
- 📧 Email：[53815263@qq.com](mailto:53815263@qq.com)
- 🐛 Bug 与功能建议：[screen2layers Issues](https://github.com/Fable-Forge/screen2layers/issues)
- 💬 使用交流与业务合作：[FableForge Discussions](https://github.com/Fable-Forge/fableforge-agent-skills/discussions) 或邮件

## License

[MIT](LICENSE) © 2026 FableForge
