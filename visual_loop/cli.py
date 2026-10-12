"""命令行入口：
  intake  --inputs inputs.json                 脏输入 → 意图树 + 假设清单
  propose --config site.json --kind resize --target logo --out-dir previews
  verify  --declared declared.json --before a.json --after b.json
  diff    --before a.json --after b.json       像素 diff（渲染对比）
"""
import argparse
import json
import sys
from pathlib import Path

from .api import (align_reference, build_intent_tree, diff_configs, propose,
                  verify_change)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="visual_loop", description="视觉反馈闭环")
    sub = parser.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("intake", help="脏输入 → 意图树+假设清单")
    i.add_argument("--inputs", required=True, help="JSON：transcript + images")

    p = sub.add_parser("propose", help="提案式修改（附预览截图）")
    p.add_argument("--config", required=True)
    p.add_argument("--kind", choices=["resize", "color"], required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--hint", default="")
    p.add_argument("--out-dir", default="previews")

    v = sub.add_parser("verify", help="属性断言：声明的改动确实发生")
    v.add_argument("--declared", required=True)
    v.add_argument("--before", required=True)
    v.add_argument("--after", required=True)

    d = sub.add_parser("diff", help="两配置渲染像素 diff")
    d.add_argument("--before", required=True)
    d.add_argument("--after", required=True)

    a = sub.add_parser("align", help="参考表达 → 模板+差异清单")
    a.add_argument("--ref", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "intake":
        inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
        out = build_intent_tree(inputs)
    elif args.cmd == "propose":
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        instruction = {"kind": args.kind, "target": args.target}
        if args.kind == "color":
            instruction["hint"] = args.hint or "高级的蓝"
        else:
            instruction["direction"] = "bigger"
        out = propose(config, instruction, args.out_dir)
    elif args.cmd == "verify":
        declared = json.loads(Path(args.declared).read_text(encoding="utf-8"))
        before = json.loads(Path(args.before).read_text(encoding="utf-8"))
        after = json.loads(Path(args.after).read_text(encoding="utf-8"))
        out = verify_change(declared, before, after)
        if not out["all_passed"]:
            sys.exit(1)
    elif args.cmd == "diff":
        before = json.loads(Path(args.before).read_text(encoding="utf-8"))
        after = json.loads(Path(args.after).read_text(encoding="utf-8"))
        out = diff_configs(before, after)
    elif args.cmd == "align":
        out = align_reference(args.ref)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
