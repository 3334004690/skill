# API 授权配置

运行前由用户或管理员预先配置 `AIMAXHUG_API_KEY`（环境变量优先，其次为项目根目录的 `.env`）：

```
AIMAXHUG_API_KEY=sk-xxxxx
```

每次请求时脚本通过 `Authorization: Bearer sk-xxx` 头携带。脚本不会自行创建 `.env` 或其他配置文件。

## 自检与依赖修复

在 `SKILL.md` 所在目录，用同一个 Python 解释器执行：

```bash
python scripts/preflight.py
python scripts/preflight.py --install-deps
```

第一条仅做本地检查；第二条在缺少已声明依赖时运行该解释器的 `pip install -r scripts/requirements.txt` 并重新检查。也可直接运行：

```bash
python -m pip install -r scripts/requirements.txt
```

若当前包源无法找到这些已声明的依赖，检查 pip 错误；在用户未限定包源且网络可达时，可仅对本次安装使用官方 PyPI，再运行自检，无需修改全局 pip 配置：

```bash
python -m pip install --index-url https://pypi.org/simple -r scripts/requirements.txt
python scripts/preflight.py
```

- 自检只报告依赖和 Key 是否配置，不打印 Key、不发起付费请求，也不验证 Key 有效性、余额或模型权限；这些以真实接口响应为准。
- `list-models` 是离线命令，无需 Key。缺依赖先修复依赖；缺 Key 时明确报告 **`AIMAXHUG_API_KEY` 未配置**，暂停鉴权调用，仍可完成素材检查、参数表等本地工作。
- 不读取或展示完整 `.env`，不把 Key 写进提示词、交付文件、命令行或日志。运行时禁止自行新建/改写 `.env`，也不伪造 Key；由用户或管理员通过既有配置渠道提供。
- 安装或鉴权失败时报告具体错误和下一步，不能把失败说成模型能力不支持。用户已授权直接执行时，不再因“首次使用”重复确认。
