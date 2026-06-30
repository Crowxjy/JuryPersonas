# Expert Method Cards

方法卡片用于描述专家评审时调用的稳定工具、公式、检查表和走查流程。

它和 persona/knowledge 的边界:

- persona:专家是谁、站在什么立场、怎样说话。
- knowledge:专家掌握哪些行业事实、案例、红线。
- methods:专家用什么方法做判断,以及这些方法的输入、步骤、输出和边界。

persona 通过 frontmatter 的 `method_lens` 显式挂载方法:

```yaml
method_lens:
  primary: [break_even, store_traffic_audit]
  secondary: [group_buy_roi_check, compliance_redline_check]
  forbidden: [fengshui_location_reasoning]
```

编译 system prompt 时只注入该角色挂载的 `primary/secondary` 方法,并保留
`forbidden` 禁用项。方法卡片本身可声明 `artifact_types`,用于后续按评审对象裁剪。

## 配套确定性工具(可选)

方法卡可在 frontmatter 声明一个配套的可执行工具,让专家评审时优先用工具确定性计算,
而不是心算估数:

```yaml
tool:
  path: tools/methods/break_even_calc.py
  desc: 确定性盈亏平衡计算器。
  usage: "python3 tools/methods/break_even_calc.py --stdin --pretty"
  input_fields: rent_monthly, labor_monthly, utility_monthly, gross_margin_pct, ...
```

编译 prompt 时,`compile_persona.py` 会在该方法卡正文后附一段「配套确定性工具」提示。
工具本身遵循项目约定:输入 JSON、输出 JSON、证据不足时拒算或留空(不编造数字)。
当前已落地: `break_even`(盈亏平衡)。
