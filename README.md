# jitm-examples

Practical recipes for building predictive models with [JITM.ai](https://jitm.ai) —
each one designed to be reproducible on your own data in under an hour.

## Examples

| Example | Predicts | Inputs | Best for |
|---|---|---|---|
| [garmin-5k-predictor](examples/garmin-5k-predictor) | Your 5K race time (~30 sec MAE) | 12 lifestyle metrics from a Garmin export | Anyone with a Garmin watch and a year of data |

More coming soon.

## How an example works

Every folder under `examples/` ships the same structure:

- **`README.md`** — the story, the metrics, and a step-by-step recipe you can
  follow by hand.
- **`skill.md`** — a [Claude Code](https://claude.ai/code) skill. Drop it in
  `~/.claude/skills/` and type `/<skill-name>` to have Claude Code walk you
  through the recipe end-to-end on your own data.
- **`scripts/`** — Python data prep scripts. No notebooks, no hidden state.
- **`sample/`** — a tiny synthetic file showing the training schema. We
  never ship real personal data.

## Run it yourself

You'll need:

- A [JITM.ai](https://jitm.ai) account (free tier works for a single model)
- Python 3.10+ with `pandas`
- The JITM MCP server connected to your agent (optional but makes the
  step-by-step automation effortless)

Open the example you want, follow the README, and bring your own data.

## Why "examples" matter for a model platform

A predictive model is only as good as the data and the framing around it.
These examples show the small judgement calls that make a model worth
trusting:

- Which columns leak the answer and have to be excluded
- When a clean 12-feature model beats a kitchen-sink 89-feature model on
  *meaning* even if the headline metric is lower
- How to turn a one-shot model into a daily-tracking habit you actually use

## Contributing

Have a domain you'd like to see as an example? Open an issue. Have your own
recipe? PRs welcome — follow the existing folder structure.

## License

MIT. See [LICENSE](LICENSE).
