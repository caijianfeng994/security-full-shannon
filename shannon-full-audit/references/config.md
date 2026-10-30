# Shannon 配置（按需阅读）

仅在用户要登录态扫描、TOTP、限制攻击范围时使用。完整字段以官方 [docs/configuration.md](https://github.com/KeygraphHQ/shannon/blob/main/docs/configuration.md) 为准。

把文件放在目标仓外（例如 `~/.shannon/configs/app.yaml`），用 `-c` 传入。不要把密码提交进 git。

```yaml
# 示例：表单登录 + 规则
authentication:
  login_url: https://staging.example.com/login
  username_env: SHANNON_LOGIN_USER
  password_env: SHANNON_LOGIN_PASSWORD

rules_of_engagement:
  # 禁止打生产、禁止 DoS
  excluded_paths:
    - /admin/dangerous-wipe
```

凭证用环境变量注入，Skill 和对话里只写变量名。
